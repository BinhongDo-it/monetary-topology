"""Count B99's repackaging pairs on the SPL sample, `D21` first step: how many pairs have both
ends in NADAC. Reads what `scripts/fetch_b99_spl.py` put under `data/raw/b99/spl_sample/` and
writes `spl_sample/pairs.json` and `spl_sample/source_ndc_sample.csv`. It does not write
`data/raw/b99/spl_source_ndc.csv`, the file the station reads, so the station stays unrun on a
sample.

A pair is (repackaged product, source product) as the SPL prints it: the product's own code
and, under it, `asEquivalentEntity/definingMaterialKind/code`, both in code system
2.16.840.1.113883.6.69 (NDC). Products are compared at labeler plus product, nine digits, the
level the station pairs at. The counts go down a ladder, each rung a subset of the one above:

    pairs in the sample
    repack end in NADAC
    both ends in NADAC (any Effective Date)
    both ends on a common Effective Date with one Pricing Unit   (what B99-3 would read)

Run with `python -I` (the documents are untrusted; this only parses them):

    python -I scripts/b99_spl_pairs.py
    python -I scripts/b99_spl_pairs.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b99"
OUT = RAW / "spl_sample"
HL7 = "{urn:hl7-org:v3}"
NDC_OID = "2.16.840.1.113883.6.69"

_spec = importlib.util.spec_from_file_location("b99", ROOT / "experiments" / "b99_drug_routes.py")
b99 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b99)


def pairs_in(body: bytes) -> tuple[list[tuple[str, str, str]], str | None]:
    """[(repack product code, source product code, equivalence code)] and a refusal reason."""
    if b"<!DOCTYPE" in body or b"<!ENTITY" in body:
        return [], "DOCTYPE or ENTITY declaration"
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        return [], f"does not parse ({e})"
    out = []
    for mp in root.iter(HL7 + "manufacturedProduct"):
        own = mp.find(HL7 + "code")
        if own is None or own.get("codeSystem") != NDC_OID:
            continue
        for eq in mp.findall(HL7 + "asEquivalentEntity"):
            kind = eq.find(HL7 + "code")
            src = eq.find(f"{HL7}definingMaterialKind/{HL7}code")
            if src is not None and src.get("codeSystem") == NDC_OID:
                out.append((own.get("code", ""), src.get("code", ""),
                            kind.get("code", "") if kind is not None else ""))
    return out, None


def count(docs: dict[str, bytes], stage_of: dict[str, str], by_product: dict) -> dict:
    refused, rows = {}, []
    for sid, body in sorted(docs.items()):
        ps, why = pairs_in(body)
        if why:
            refused[sid] = why
            continue
        for a, s, k in ps:
            rows.append({"setid": sid, "repack": a, "source": s, "equiv": k,
                         "stage": stage_of.get(sid, "")})
    seen, pairs = {}, []
    for r in rows:
        a, s = b99.product9(r["repack"]), b99.product9(r["source"])
        if not a or not s or a == s or (a, s) in seen:
            continue
        seen[(a, s)] = r
        pairs.append((a, s, r))
    rep_in = [(a, s, r) for a, s, r in pairs if a in by_product]
    both = [(a, s, r) for a, s, r in rep_in if s in by_product]
    # pairs_of takes the codes as the SPL prints them (hyphenated) and keys them itself
    usable, split, unreached = b99.pairs_of([{"repack": r["repack"], "source": r["source"]}
                                             for _a, _s, r in both], by_product)
    equiv: dict = {}
    for r in rows:
        equiv[r["equiv"]] = equiv.get(r["equiv"], 0) + 1
    labs = sorted({a[:5] for a, _s, r in pairs if r["stage"] == "A"})
    return {"documents": len(docs), "refused": refused,
            "documents_with_source": len({r["setid"] for r in rows}),
            "source_rows": len(rows), "equivalence_codes": equiv,
            "pairs": len(pairs), "repack_in_nadac": len(rep_in), "both_in_nadac": len(both),
            "usable_common_date_one_unit": len(usable), "unit_split": split,
            "no_common_date": unreached,
            "stage_A_source_labelers": labs,
            "both_in_nadac_list": [{"repack": a, "source": s, "setid": r["setid"],
                                    "stage": r["stage"]} for a, s, r in both],
            "usable_list": [{"repack": a, "source": s, "date": d, "p_repack": pa,
                             "p_source": pb, "unit": u} for a, s, d, pa, pb, u, _dec in usable]}


def by_stage(c: dict, docs, stage_of, by_product, stage: str) -> dict:
    sub = {k: v for k, v in docs.items() if stage_of.get(k) == stage}
    r = count(sub, stage_of, by_product)
    return {k: r[k] for k in ("documents", "documents_with_source", "pairs", "repack_in_nadac",
                              "both_in_nadac", "usable_common_date_one_unit")}


def main_run() -> int:
    man = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    # a document reached from any stage-A lookup belongs to stage A: stage B's frame is read
    # off stage A, so stage A's count must not move when stage B is fetched
    stage_of = {}
    for p9, look in sorted(man["lookups"].items(), key=lambda kv: (kv[1]["stage"], kv[0])):
        for s in look.get("setids", []):
            stage_of.setdefault(s, look["stage"])
    docs = {}
    for key, e in sorted(man["files"].items()):
        if key.startswith("xml/"):
            body = (OUT / key).read_bytes()
            if b99_sha(body) != e["sha256"]:
                print(f"  {key} is not the recorded file; skipped")
                continue
            docs[key[4:-4]] = body
    nad, _rep = b99.read_table(sorted((RAW / "nadac").glob("*.csv")), b99.NADAC_COLS, "NADAC")
    by_product = b99.nadac_by_product(nad)
    c = count(docs, stage_of, by_product)
    looks = man["lookups"]
    frame = {}
    for st in ("A", "B"):
        ls = [v for v in looks.values() if v["stage"] == st]
        if not ls:
            continue
        frame[st] = {"nadac_products": len(ls),
                     "with_item_code": sum(1 for v in ls if v.get("item_code")),
                     "with_a_setid": sum(1 for v in ls if v.get("setids")),
                     **by_stage(c, docs, stage_of, by_product, st)}
    c["by_stage"] = frame
    c["nadac_products_total"] = len(by_product)
    c["bytes_fetched"] = man["total_bytes"]
    (OUT / "pairs.json").write_text(json.dumps(c, indent=1, sort_keys=True) + "\n",
                                    encoding="utf-8", newline="\n")
    with open(OUT / "source_ndc_sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["repack_ndc", "source_ndc", "setid", "stage"])
        for r in c["both_in_nadac_list"]:
            w.writerow([r["repack"], r["source"], r["setid"], r["stage"]])
    for k in ("documents", "refused", "documents_with_source", "equivalence_codes", "pairs",
              "repack_in_nadac", "both_in_nadac", "usable_common_date_one_unit", "unit_split",
              "no_common_date", "stage_A_source_labelers", "by_stage", "bytes_fetched"):
        print(f"  {k}: {c[k]}")
    return 0


def b99_sha(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest()


def selftest() -> None:
    doc = (b'<document xmlns="urn:hl7-org:v3"><manufacturedProduct><manufacturedProduct>'
           b'<code code="70518-4748" codeSystem="2.16.840.1.113883.6.69"/>'
           b'<asEquivalentEntity classCode="EQUIV"><code code="C64637" '
           b'codeSystem="2.16.840.1.113883.3.26.1.1"/><definingMaterialKind>'
           b'<code code="52817-254" codeSystem="2.16.840.1.113883.6.69"/>'
           b'</definingMaterialKind></asEquivalentEntity></manufacturedProduct>'
           b'</manufacturedProduct></document>')
    ps, why = pairs_in(doc)
    assert why is None and ps == [("70518-4748", "52817-254", "C64637")], ps
    plain = doc.replace(b"asEquivalentEntity", b"asSpecializedKind")
    assert pairs_in(plain)[0] == []                          # no source, no pair
    other = doc.replace(b'52817-254" codeSystem="2.16.840.1.113883.6.69',
                        b'52817-254" codeSystem="2.16.840.1.113883.6.1')
    assert pairs_in(other)[0] == []                          # source not in the NDC system
    assert pairs_in(b'<!DOCTYPE x [<!ENTITY a "b">]>' + doc)[1] is not None
    bp = {"705184748": {"d": (0.2, "EA", 5)}, "528170254": {"d": (0.1, "EA", 5)}}
    c = count({"s1": doc}, {"s1": "A"}, bp)
    assert (c["pairs"], c["both_in_nadac"], c["usable_common_date_one_unit"]) == (1, 1, 1)
    assert c["stage_A_source_labelers"] == ["70518"]
    c2 = count({"s1": doc}, {"s1": "A"}, {"705184748": bp["705184748"]})
    assert (c2["repack_in_nadac"], c2["both_in_nadac"]) == (1, 0)   # source missing
    c3 = count({"s1": doc}, {"s1": "A"},
               {"705184748": {"d": (0.2, "EA", 5)}, "528170254": {"d": (0.1, "ML", 5)}})
    assert (c3["both_in_nadac"], c3["usable_common_date_one_unit"], c3["unit_split"]) == (1, 0, 1)
    print("selftest ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    return main_run()


if __name__ == "__main__":
    sys.exit(main())
