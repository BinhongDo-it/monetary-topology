"""B99: on the 605 repackaging pairs, which RxNorm concept each end sits under, and which NDC CMS uses for it.

Reads published files only and writes one JSON. No criterion, no flag.

Inputs:
    NADAC_GROUP_CHECK_JSON  the per-pair NADAC rows of scripts/b99_nadac_group_check.py (NDC-11 at both ends)
    RXNAV_JSONL             RxNav getNDCStatus replies, one line per NDC-11 (scripts/fetch_b99_rxnav_ndc.py)
    FRF_CSV                 the CMS Formulary Reference File, CY 2026 September release (RXCUI, TTY, description)
    SPUF_FORMULARY_TXT      the basic drugs formulary file of the CMS Part D quarterly SPUF (pipe-delimited;
                            FORMULARY_ID, RXCUI and NDC, the NDC being the "11-digit proxy NDC associated with the
                            drug product" in the SPUF record layout)

For every pair it prints: the RXCUIs of the repackaged NDC-11s and of the source NDC-11s (the concept RxNav maps
each NDC to now, or its last concept in the NDC's history if it has none now); whether the two ends share an RXCUI;
that RXCUI's line on the FRF; the NDC or NDCs the plan formularies print next to it and how many formularies list
it; and whether that NDC is one of the repackaged NDCs, one of the source NDCs, or another labeler's.

usage: python -I b99_partd_ref_check.py NADAC_GROUP_CHECK_JSON RXNAV_JSONL FRF_CSV SPUF_FORMULARY_TXT OUT_JSON
"""
import collections
import csv
import json
import sys


def rxcui_of(reply: dict):
    st = reply.get("ndcStatus") or {}
    if st.get("rxcui"):
        return st["rxcui"], st.get("status"), st.get("conceptName")
    hist = st.get("ndcHistory") or []
    for h in sorted(hist, key=lambda x: x.get("endDate") or "", reverse=True):
        if h.get("activeRxcui"):
            return h["activeRxcui"], st.get("status"), st.get("conceptName")
    return None, st.get("status"), st.get("conceptName")


def main(argv) -> int:
    groups_path, rxnav_path, frf_path, spuf_path, out_path = argv
    pairs = json.load(open(groups_path, encoding="utf-8"))["pairs"]
    rx = {}
    with open(rxnav_path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                d = json.loads(line)
                rx[d["ndc"]] = rxcui_of(d["reply"])
    frf = {}
    with open(frf_path, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        frf_header = rd.fieldnames
        for r in rd:
            frf[r["RxCUI"].strip()] = {"TTY": r["TTY"].strip(), "RxNorm Description": r["RxNorm Description"].strip()}
    proxy = collections.defaultdict(collections.Counter)   # rxcui -> NDC -> formularies
    with open(spuf_path, encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh, delimiter="|")
        spuf_header = rd.fieldnames
        seen = set()
        for r in rd:
            key = (r["FORMULARY_ID"], r["RXCUI"], r["NDC"])
            if key in seen:
                continue
            seen.add(key)
            proxy[r["RXCUI"].strip()][r["NDC"].strip()] += 1
    out = []
    for p in pairs:
        rep = sorted(row[0] for row in p["rows_repack"])
        src = sorted(row[0] for row in p["rows_source"])
        rr = {n: rx.get(n, (None, "not looked up", None)) for n in rep}
        rs = {n: rx.get(n, (None, "not looked up", None)) for n in src}
        cu_r = sorted({v[0] for v in rr.values() if v[0]})
        cu_s = sorted({v[0] for v in rs.values() if v[0]})
        shared = sorted(set(cu_r) & set(cu_s))
        entry = {"repack": p["repack"], "source": p["source"],
                 "repack_ndcs": {n: list(v) for n, v in rr.items()}, "source_ndcs": {n: list(v) for n, v in rs.items()},
                 "rxcuis_repack": cu_r, "rxcuis_source": cu_s, "shared_rxcuis": shared,
                 "same_rxcui": bool(shared) and set(cu_r) <= set(cu_s),
                 "concepts": {}}
        for c in sorted(set(cu_r) | set(cu_s)):
            ndcs = proxy.get(c, {})
            entry["concepts"][c] = {
                "frf": frf.get(c),
                "proxy_ndcs_on_formularies": dict(sorted(ndcs.items())),
                "formularies_listing_it": sum(ndcs.values()),
                "proxy_is": sorted({("repack" if n in rep else "source" if n in src
                                     else "repack labeler" if n[:5] == p["repack"][:5]
                                     else "source labeler" if n[:5] == p["source"][:5]
                                     else "another labeler") for n in ndcs})}
        out.append(entry)
    proxy_kinds = collections.Counter()
    for e in out:
        for c in e["shared_rxcuis"]:
            proxy_kinds["/".join(e["concepts"][c]["proxy_is"]) or "no formulary lists it"] += 1
    rxcui_ndc_counts = collections.Counter(len(v) for v in proxy.values())
    summary = {
        "pairs": len(out),
        "frf_header": frf_header, "frf_rxcuis": len(frf),
        "spuf_formulary_header": spuf_header,
        "spuf_rxcuis": len(proxy), "spuf_ndcs_per_rxcui_histogram": sorted(rxcui_ndc_counts.items()),
        "ndcs_looked_up": len(rx),
        "ndcs_without_an_rxcui": sorted(n for n, v in rx.items() if not v[0]),
        "pairs_same_rxcui": sum(e["same_rxcui"] for e in out),
        "pairs_sharing_some_rxcui": sum(bool(e["shared_rxcuis"]) for e in out),
        "pairs_sharing_no_rxcui": [e for e in out if not e["shared_rxcuis"]],
        "pairs_shared_rxcui_on_the_frf": sum(any(e["concepts"][c]["frf"] for c in e["shared_rxcuis"]) for e in out),
        "shared_rxcui_tty": sorted(collections.Counter(
            (e["concepts"][c]["frf"] or {}).get("TTY", "not on the FRF") for e in out for c in e["shared_rxcuis"]).items()),
        "shared_rxcui_by_where_the_proxy_ndc_sits": sorted(proxy_kinds.items()),
        "shared_rxcuis_with_two_or_more_proxy_ndcs": sorted({c for e in out for c in e["shared_rxcuis"]
                                                             if len(e["concepts"][c]["proxy_ndcs_on_formularies"]) > 1}),
    }
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"summary": summary, "pairs": out}, fh, indent=1, sort_keys=True)
    s = dict(summary)
    s["pairs_sharing_no_rxcui"] = [(e["repack"], e["source"], e["rxcuis_repack"], e["rxcuis_source"])
                                   for e in summary["pairs_sharing_no_rxcui"]]
    print(json.dumps(s, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
