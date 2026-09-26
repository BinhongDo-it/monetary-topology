"""A50, a side question: how much of what goes into Singapore's CPF comes back out through housing.

A50 read that parked money helps while it stays parked, and that under an authority which counts
the accounts as money, accounts that never pay out drain circulation while accounts spent on
dwellings keep it going. Singapore's CPF is the real account. Printed, no criterion: each year's
net amount withdrawn under the housing schemes (public and private housing), over the year's
contributions received.

Sources (data/b130/raw, fetched by b130_fetch.py): CPF Board, "CPF contributions received, Annual"
(data.gov.sg d_bb9b7f963ef295b750c9925e9e026524; includes government grants, dividends from
Special Discounted Shares and interest paid); "Net amount withdrawn under housing schemes, Annual"
(data.gov.sg d_7cce20f5d2d8ae2582da809e66a1cdd7; net: money used for a dwelling, less what comes
back to the account when the dwelling is sold).

Run from the repo root:
    python experiments/a50_side_cpf_housing.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "b130" / "raw"
OUT = ROOT / "results" / "a50_side_cpf_housing.json"


def records(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))["result"]["records"]


def main() -> int:
    con = {r["yr"]: float(r["con_received"]) for r in records("dgs_cpf_contributions_annual.json")}
    wd: dict[str, dict[str, float]] = {}
    for r in records("dgs_cpf_housing_withdrawn_annual.json"):
        wd.setdefault(r["yr"], {})[r["housing_schm_type"]] = float(r["net_wdl_amt"])
    years = sorted(set(con) & set(wd))
    table = {}
    print("year | contributions (bn) | net withdrawn, HDB (bn) | private (bn) | housing / contributions")
    for y in years:
        pub = wd[y].get("Public Housing (HDB flats)", 0.0)
        pri = wd[y].get("Private Housing", 0.0)
        share = (pub + pri) / con[y]
        table[y] = {"contributions": con[y], "net_withdrawn_hdb": pub, "net_withdrawn_private": pri,
                    "housing_over_contributions": round(share, 4), "hdb_over_contributions": round(pub / con[y], 4)}
        print(f"  {y} | {con[y] / 1e9:6.1f} | {pub / 1e9:5.2f} | {pri / 1e9:5.2f} | {share:.3f}")
    shares = [t["housing_over_contributions"] for t in table.values()]
    first, last = years[0], years[-1]
    summary = {"years": [first, last], "min": min(shares), "max": max(shares),
               "sum_housing_over_sum_contributions": round(sum(t["net_withdrawn_hdb"] + t["net_withdrawn_private"]
                                                               for t in table.values()) / sum(con[y] for y in years), 4)}
    print("summary:", summary)
    OUT.write_text(json.dumps({"stage": "A50-side-cpf-housing", "table": table, "summary": summary,
                               "config": {"sources": ["d_bb9b7f963ef295b750c9925e9e026524",
                                                      "d_7cce20f5d2d8ae2582da809e66a1cdd7"]}},
                              indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
