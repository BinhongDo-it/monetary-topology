"""B130, side question 3: who buys resale HDB flats, first-timer families against everyone else.

Numerator, transcribed (rule 25: source and place of every item): MND written answer to
Parliamentary Question No. 2568 (Mr Chua Kheng Wee Louis), 9 Jan 2023, Table 1A, "Number of
First-Timer Families who bought Resale HDB flats": 2018 4,500; 2019 5,000; 2020 5,700; 2021
5,800; 2022 (Q1-Q3) 4,100; and their median household income, same table. Notes to the table:
incomes at key collection; "Data includes applicants who took a HDB loan". Families only; first-
timer singles are not in it. Read in the built-in browser on 2026-09-25 (the page loads its body
by script, so a plain fetch returns only the shell).

Denominator: resale transactions registered in each month, counted from data.gov.sg "Resale flat
prices based on registration date from Jan-2017 onwards" (resource d_8b84c4ee58e3cfc0ece0d773c8ca6abc)
with one filtered query per month (the answer's `total`). Cached in data/b130/raw; resumable; a
month whose answer does not parse or reports no total is fetched again.

The rest of the buyers are second-timers (sellers of an HDB flat buying another), private
property owners (allowed, but they must sell the private property within six months: MND
written answer, 13 Jul 2015), first-timer singles, and permanent-resident households.

Run from the repo root:
    python experiments/b130_side_buyers.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "b130" / "raw"
CACHE = RAW / "dgs_resale_monthly_totals.json"
OUT = ROOT / "results" / "b130_side_buyers.json"
RESOURCE = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

#: MND PQ 2568, 9 Jan 2023, Table 1A
FIRST_TIMER_FAMILIES = {"2018": 4500, "2019": 5000, "2020": 5700, "2021": 5800, "2022 Q1-Q3": 4100}
FIRST_TIMER_MEDIAN_INCOME = {"2018": 6200, "2019": 6500, "2020": 6400, "2021": 7000, "2022 Q1-Q3": 7500}
MONTHS = {"2018": range(1, 13), "2019": range(1, 13), "2020": range(1, 13), "2021": range(1, 13),
          "2022 Q1-Q3": range(1, 10)}


def month_total(ym: str) -> int:
    q = urllib.parse.urlencode({"resource_id": RESOURCE, "limit": 1, "filters": json.dumps({"month": ym})})
    req = urllib.request.Request("https://data.gov.sg/api/action/datastore_search?" + q, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode("utf-8"))
    if not d.get("success") or d.get("result", {}).get("total") is None:
        raise ValueError(f"{ym}: no total in the answer")
    return int(d["result"]["total"])


def fetch() -> dict[str, int]:
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    for label, months in MONTHS.items():
        year = label[:4]
        for m in months:
            ym = f"{year}-{m:02d}"
            if isinstance(cache.get(ym), int) and cache[ym] > 0:
                continue
            for attempt in range(4):
                try:
                    time.sleep(1.5 * (attempt + 1))
                    cache[ym] = month_total(ym)
                    print(f"ok {ym}: {cache[ym]}")
                    break
                except Exception as e:  # noqa: BLE001 - reported, then retried
                    print(f"retry {ym}: {e}")
            CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return cache


def main() -> int:
    cache = fetch()
    rows = {}
    for label, months in MONTHS.items():
        year = label[:4]
        got = [cache.get(f"{year}-{m:02d}") for m in months]
        if any(not isinstance(g, int) for g in got):
            print(f"{label}: months missing, not read")
            continue
        total = sum(got)
        ft = FIRST_TIMER_FAMILIES[label]
        rows[label] = {"resale_transactions": total, "first_timer_families": ft,
                       "first_timer_family_share": round(ft / total, 4),
                       "everyone_else": total - ft,
                       "first_timer_median_income": FIRST_TIMER_MEDIAN_INCOME[label]}
    print("period | resale transactions | first-timer families | share | everyone else | their median income")
    for k, r in rows.items():
        print(f"  {k:11s} | {r['resale_transactions']:6d} | {r['first_timer_families']:5d} | "
              f"{r['first_timer_family_share']:.3f} | {r['everyone_else']:6d} | ${r['first_timer_median_income']}")
    OUT.write_text(json.dumps({"stage": "B130-side-buyers", "rows": rows,
                               "sources": {"numerator": "MND written answer, PQ 2568, 9 Jan 2023, Table 1A",
                                           "denominator": f"data.gov.sg {RESOURCE}, monthly totals by registration month",
                                           "private_owner_rule": "MND written answer, 13 Jul 2015"}},
                              indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
