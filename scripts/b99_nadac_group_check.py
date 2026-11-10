"""B99: on the SPL sample pairs, is the NADAC on a repackaged NDC the drug-group rate?

The NADAC methodology (December 2024, p. 7) says that only NDCs with the same drug grouping,
classification for rate setting and pharmacy type indicator share the same NADAC rate, and
(p. 26) that a group's rate is applied to every NDC in the group whether or not costs were
collected for that NDC. This script prints, for every pair in the sample, what the reference
file itself shows about that rule:

    the classification for rate setting at both ends;
    whether the repackaged NDC-11 prices are a subset of the source NDC-11 prices on the
    pair's date (package level, so a source product that spans two drug groups is read
    package by package, not through a product median);
    how many NDCs and labelers carry the repackager's exact printed price on that date.

It reads published files only and writes one JSON. No criterion, no flag.

usage: python -I b99_nadac_group_check.py PAIRS_JSON NADAC_CSV [NADAC_CSV ...] OUT_JSON
"""
import collections
import csv
import json
import sys

FIELDS = ("NDC", "NDC Description", "NADAC Per Unit", "Pricing Unit", "OTC",
          "Explanation Code", "Classification for Rate Setting")


def ndc11(s: str) -> str:
    d = "".join(ch for ch in s if ch.isdigit())
    return d.zfill(11) if d else ""


def main(argv) -> int:
    pairs_path, *csvs, out_path = argv
    pairs = json.load(open(pairs_path, encoding="utf-8"))["usable_list"]
    dates = {p["date"] for p in pairs}
    by_date: dict = collections.defaultdict(dict)   # date -> {ndc11: row}; weekly repeats collapse
    for f in csvs:
        with open(f, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                d = r["Effective Date"].strip()
                if d in dates:
                    by_date[d][ndc11(r["NDC"])] = {k: r[k].strip() for k in FIELDS}
    out = []
    for p in pairs:
        rows = by_date[p["date"]]
        a = {k: v for k, v in rows.items() if k[:9] == p["repack"]}
        b = {k: v for k, v in rows.items() if k[:9] == p["source"]}
        pa = {v["NADAC Per Unit"] for v in a.values()}
        pb = {v["NADAC Per Unit"] for v in b.values()}
        units = {v["Pricing Unit"] for v in a.values()}
        same = {k: v for k, v in rows.items()
                if v["NADAC Per Unit"] in pa and v["Pricing Unit"] in units}
        out.append({
            "repack": p["repack"], "source": p["source"], "date": p["date"],
            "product_median_repack": p["p_repack"], "product_median_source": p["p_source"],
            "product_medians_equal": p["p_repack"] == p["p_source"],
            "package_prices_repack": sorted(pa), "package_prices_source": sorted(pb),
            "repack_prices_within_source_prices": bool(pa) and pa <= pb,
            "class_repack": sorted({v["Classification for Rate Setting"] for v in a.values()}),
            "class_source": sorted({v["Classification for Rate Setting"] for v in b.values()}),
            "ndcs_at_repack_price": len(same),
            "labelers_at_repack_price": len({k[:5] for k in same}),
            "rows_repack": [[k] + [v[f] for f in FIELDS[1:]] for k, v in sorted(a.items())],
            "rows_source": [[k] + [v[f] for f in FIELDS[1:]] for k, v in sorted(b.items())],
        })
    summary = {
        "pairs": len(out),
        "product_medians_equal": sum(x["product_medians_equal"] for x in out),
        "repack_prices_within_source_prices": sum(x["repack_prices_within_source_prices"]
                                                  for x in out),
        "class_pairs": sorted(collections.Counter(
            "/".join(x["class_repack"]) + "|" + "/".join(x["class_source"]) for x in out).items()),
        "labelers_at_repack_price_hist": sorted(collections.Counter(
            x["labelers_at_repack_price"] for x in out).items()),
        "pairs_with_a_third_labeler_at_the_price": sum(x["labelers_at_repack_price"] >= 3
                                                       for x in out),
        "product_medians_differ": [x for x in out if not x["product_medians_equal"]],
        "package_prices_differ": [x for x in out if not x["repack_prices_within_source_prices"]],
    }
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"summary": summary, "pairs": out}, fh, indent=1, sort_keys=True)
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
