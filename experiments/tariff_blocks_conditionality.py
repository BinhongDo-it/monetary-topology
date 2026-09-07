"""Second arm on the tariff-block corpus: does an externally imposed programme
condition leave a readable mark on the block structure of a national schedule.

Arm one read the corpus as it stands. This arm asks whether countries under a
conditional programme cluster on the block count, which is what a propagating
template would look like.

Two sources. The schedules are the record written by
`experiments/tariff_blocks_count.py`. The programmes and the conditions are the
IMF conditionality dataset of Kentikelenis and Stubbs, whose main file is a
country-year panel carrying months under an arrangement and condition counts by
policy area, and whose raw file is one row per condition carrying its text. Both
were downloaded by hand; neither is redistributed here and the raw workbook is
read through a cache that rerunning rebuilds.

Criteria are written here and the record carries their text. No threshold sits
on any estimate: TB-11 prints two distributions, TB-12 prints a gradient against
the block count, and TB-13 is a coverage check on the name matching.

The three outcomes for TB-11 were fixed before the pull: a cluster on one side
and not the other is the station's result; two distributions of the same shape
is a negative reading and is reported as one; and either side too small to show
a shape is undecided.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "raw" / "IMF Conditionality Dataset"
CACHE = ROOT / "data" / "cache" / "tb"
YEARS = (2015, 2016)

# World-Bank spellings in the survey against the conditionality dataset's own.
ALIAS = {
    "Egypt, Arab Rep.": "Egypt",
    "Iran, Islamic Rep.": "Iran",
    "Korea, Rep.": "Korea",
    "Yemen, Rep.": "Yemen",
}

# A condition counts as naming an electricity price if its text carries one of
# these. Written before the texts were read, and every hit is printed in the
# record rather than only counted.
PRICE_PAT = re.compile(r"electric|power tariff|power sector|utilit|tariff", re.I)


def survey_rows() -> list[tuple[str, int, int]]:
    """(country, blocks drawn, distinct charges written) from arm one's record."""
    rec = json.loads((ROOT / "results" / "tariff_blocks_count.json").read_text(encoding="utf-8"))
    out = []
    for r in rec["clean"]:
        name = re.split(r"\s+\d", r["country"])[0].strip()
        out.append((name, int(r["n"]), len(set(r["charges"]))))
    return out


def load_main() -> pd.DataFrame:
    z = zipfile.ZipFile(SRC / "IMFMonitor_Conditionality_Main.zip")
    df = pd.read_stata(
        io.BytesIO(z.read("IMFMonitor_Conditionality_Main.dta")),
        convert_categoricals=False,
    ).copy()
    df["yr"] = pd.to_datetime(df["year"]).dt.year
    return df


def load_raw() -> pd.DataFrame:
    """The workbook is slow to parse, so keep a rebuildable cache beside it."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / "imf_conditions_raw.pkl"
    if cached.exists():
        return pd.read_pickle(cached)
    df = pd.read_excel(SRC / "IMFMonitor_Conditionality_Raw.xlsx", sheet_name="Dataset")
    df.to_pickle(cached)
    return df


def matcher(names: set[str]):
    def match(n: str) -> str | None:
        for cand in (n, ALIAS.get(n, n)):
            if cand in names:
                return cand
        tok = ALIAS.get(n, n).split(",")[0].strip()
        hits = sorted(x for x in names if x == tok or x.startswith(tok))
        return hits[0] if len(hits) == 1 else None
    return match


def main() -> None:
    survey = survey_rows()
    main_df = load_main()
    raw = load_raw()

    m_main = matcher(set(main_df["cname"].unique()))
    m_raw = matcher(set(raw["Country Name"].unique()))
    panel = main_df[main_df.yr.isin(YEARS)]

    rows = []
    for name, blocks, values in survey:
        cm = m_main(name)
        s = panel[panel.cname == cm] if cm else panel.iloc[0:0]
        rows.append(
            dict(
                survey=name,
                matched_main=cm,
                matched_raw=m_raw(name),
                blocks=blocks,
                values=values,
                months=float(s["IMFm"].sum()) if len(s) else 0.0,
                soe=float(s["BA1SOE"].sum()) if len(s) else 0.0,
                sp=float(s["BA1SP"].sum()) if len(s) else 0.0,
                total=float(s["BA1TOT"].sum()) if len(s) else 0.0,
            )
        )
    t = pd.DataFrame(rows)

    unmatched_main = sorted(t.loc[t.matched_main.isna(), "survey"])
    absent_from_raw = sorted(t.loc[t.matched_raw.isna(), "survey"])

    # ---- the conditions that name an electricity price -------------------
    targets = set(x for x in t.matched_raw.dropna())
    window = raw[raw["Country Name"].isin(targets) & raw["Condition Year"].isin(YEARS)]
    hits = window[window["Condition Text"].astype(str).str.contains(PRICE_PAT, regex=True)]
    priced = []
    for _, r in hits.iterrows():
        priced.append(
            dict(
                country=str(r["Country Name"]),
                year=int(r["Condition Year"]),
                policy_area=str(r["Condition Policy Area"]),
                condition_type=str(r["Condition Type"]),
                text=str(r["Condition Text"]).strip(),
                source_document=str(r["Condition Source Document"]),
            )
        )
    priced.sort(key=lambda d: (d["country"], d["year"], d["text"][:40]))
    by_country = Counter(d["country"] for d in priced)

    # ---- TB-11: the two distributions ------------------------------------
    inp, outp = t[t.months > 0], t[t.months == 0]
    hin, hout = Counter(inp.blocks), Counter(outp.blocks)
    span = sorted(set(t.blocks))
    dist_in = {int(b): int(hin.get(b, 0)) for b in span}
    dist_out = {int(b): int(hout.get(b, 0)) for b in span}
    mean_in = float(inp.blocks.mean()) if len(inp) else float("nan")
    mean_out = float(outp.blocks.mean()) if len(outp) else float("nan")

    # ---- TB-12: the gradient ---------------------------------------------
    treated = sorted(by_country)
    # Spearman is Pearson on the ranks; computed here rather than imported, so
    # the station carries no dependency for one reading.
    def spearman(a, b):
        return float(a.rank().corr(b.rank()))

    rho_soe = spearman(t["soe"], t["blocks"])
    rho_months = spearman(t["months"], t["blocks"])

    c11 = len(inp) >= 1 and len(outp) >= 1
    c12 = len(treated) >= 1
    c13 = not unmatched_main

    record = {
        "stage": "tariff_block_corpus",
        "arm": "conditionality",
        "config": {
            "years": list(YEARS),
            "schedules": len(t),
            "condition_source": "IMF conditionality dataset, Kentikelenis and Stubbs, "
                                "downloaded by hand; not redistributed",
            "price_pattern": PRICE_PAT.pattern,
            "raw_rows": int(len(raw)),
            "raw_applicable_years_sum": float(
                pd.to_numeric(raw["Condition Number Applicable"], errors="coerce").sum()
            ),
        },
        "criteria": [
            {
                "name": "TB-11",
                "kind": "own_reading",
                "text": "Print the block-count distribution for schedules whose country "
                        "was under an arrangement in either year and for those whose was "
                        "not, cell by cell, with no threshold on either. A cluster on one "
                        "side and not the other is the station's result; the same shape on "
                        "both is a negative reading; either side too small to show a shape "
                        "is undecided.",
                "passed": c11,
                "detail": "under %d, not under %d, means %.2f against %.2f"
                          % (len(inp), len(outp), mean_in, mean_out),
            },
            {
                "name": "TB-12",
                "kind": "own_reading",
                "text": "Print the count of conditions naming an electricity price against "
                        "the block count, as a gradient rather than a level, with the "
                        "treated countries named rather than only counted.",
                "passed": c12,
                "detail": "%d conditions naming a price, over %d of %d countries"
                          % (len(priced), len(treated), len(t)),
            },
            {
                "name": "TB-13",
                "kind": "instrument",
                "text": "Every schedule's country resolves to a name in the conditionality "
                        "panel, and any country absent from the condition file is named "
                        "rather than silently treated as having no conditions.",
                "passed": c13,
                "detail": "%d unmatched in the panel, %d absent from the condition file"
                          % (len(unmatched_main), len(absent_from_raw)),
            },
        ],
        "readings": {
            "schedules": len(t),
            "under_arrangement": len(inp),
            "not_under_arrangement": len(outp),
            "block_distribution_under": dist_in,
            "block_distribution_not_under": dist_out,
            "mean_blocks_under": round(mean_in, 4),
            "mean_blocks_not_under": round(mean_out, 4),
            "countries_with_any_SOE_condition": int((t.soe > 0).sum()),
            "SOE_conditions_total": int(t.soe.sum()),
            "countries_with_any_SP_condition": int((t.sp > 0).sum()),
            "SP_conditions_total": int(t.sp.sum()),
            "conditions_on_these_countries_in_window": int(len(window)),
            "conditions_naming_a_price": len(priced),
            "countries_named_by_a_price_condition": treated,
            "price_conditions_by_country": {k: int(v) for k, v in sorted(by_country.items())},
            "spearman_blocks_vs_SOE_count": round(rho_soe, 4),
            "spearman_blocks_vs_months_under": round(rho_months, 4),
            "absent_from_condition_file": absent_from_raw,
            "unmatched_in_panel": unmatched_main,
        },
        "price_conditions": priced,
        "per_schedule": [
            {k: (None if pd.isna(v) else (float(v) if isinstance(v, float) else v))
             for k, v in r.items()}
            for r in rows
        ],
    }

    out = ROOT / "results" / "tariff_blocks_conditionality.json"
    out.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")

    for c in record["criteria"]:
        print("%-7s %-4s %s" % (c["name"], "PASS" if c["passed"] else "FAIL", c["detail"]))
    print("blocks   %s" % " ".join("%3d" % b for b in span))
    print("under    %s" % " ".join("%3d" % dist_in[b] for b in span))
    print("not      %s" % " ".join("%3d" % dist_out[b] for b in span))
    print("price conditions on %d countries: %s"
          % (len(treated), ", ".join("%s %d" % (k, v) for k, v in sorted(by_country.items()))))
    print("wrote %s" % out.name)


if __name__ == "__main__":
    main()
