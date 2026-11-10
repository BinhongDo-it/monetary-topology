"""B130, side question 3: who buys resale HDB flats, first-timer families against everyone else.

Numerator, transcribed (rule 25: source and place of every item): MND written answer to
Parliamentary Question No. 2568 (Mr Chua Kheng Wee Louis), 9 Jan 2023, Table 1A, "Number of
First-Timer Families who bought Resale HDB flats": 2018 4,500; 2019 5,000; 2020 5,700; 2021
5,800; 2022 (Q1-Q3) 4,100; and their median household income, same table. Notes to the table:
incomes at key collection; "Data includes applicants who took a HDB loan". Families only; first-
timer singles are not in it. Read in the built-in browser on 2026-09-25 (the page loads its body
by script, so a plain fetch returns only the shell).

Denominator: HDB's registered resale applications by quarter and flat type, data.gov.sg resource
d_02aa4bb51bc674f3a2d0b9bb6911d934, fetched whole and cached in data/b130/raw; a cache is used only
if its record count equals the source's total and every quarter read carries each of the six flat
types once. The price records (resource d_8b84c4ee58e3cfc0ece0d773c8ca6abc, "Resale flat prices
based on registration date") are still counted month by month and printed beside it: that
dataset leaves out transactions whose price may not be a full market price (between relatives,
some part-share sales), so it runs about 5 to 7 percent below the registrations.

Table 1A counts families only, so first-timer singles are not in it and its share is a floor. Its
note says the data include applicants who took an HDB loan; if they are the only ones included,
first-timer families with a bank loan are missing too and the floor sits lower still. Table 1A
counts at key collection and the registrations at registration, so the share is the same count
over another denominator, not a buyer-by-buyer share. Two wider counts, each from HDB:
  CPF Housing Grant, resale: more than 11,000 households from 14 Feb to Dec 2023, 31 percent more
      than the same span of 2022 (HDB update of 25 Feb 2024, reported by The Straits Times, 26 Feb
      2024, read in the built-in browser). The grant has an income ceiling, so first-timers above it
      are not in this count either.
  Enhanced CPF Housing Grant: about 72,300 first-timer households since September 2019, 4 in 10 of
      them resale buyers (MND-HDB joint press release, 19 Aug 2024; the count runs to mid-2024).
The quarterly registrations do not split a quarter at 14 Feb, so the span is bounded by the two
nearest quarter sets and also prorated by days.

The rest of the buyers are second-timers (sellers of an HDB flat buying another), private
property owners (allowed, but they must sell the private property within six months: MND
written answer, 13 Jul 2015), first-timers the counts above leave out, and permanent-resident
households (all applicants permanent residents: about 27 percent of resale purchases in 2011,
about 7 percent in 2021; MND written answer, 8 Nov 2022).

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
OFFICIAL_CACHE = RAW / "dgs_resale_applications_quarterly.json"
OUT = ROOT / "results" / "b130_side_buyers.json"
RESOURCE = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"
OFFICIAL = "d_02aa4bb51bc674f3a2d0b9bb6911d934"
FLAT_TYPES = 6
QUARTERS = {"2018": ("2018-Q1", "2018-Q4"), "2019": ("2019-Q1", "2019-Q4"), "2020": ("2020-Q1", "2020-Q4"),
            "2021": ("2021-Q1", "2021-Q4"), "2022 Q1-Q3": ("2022-Q1", "2022-Q3")}
#: CPF Housing Grant, resale, 14 Feb to Dec: 2023 more than 11,000; 2022 is 11,000 / 1.31 (the "31 percent")
CPF_GRANT = {"2023": 11000, "2022": 11000 / 1.31}
AFTER_FEB14 = 46 / 90            # days of Q1 from 14 Feb to 31 Mar, over the 90 days of Q1 (not a leap year)
#: EHG, since Sep 2019 to mid-2024: 72,300 first-timer households, 4 in 10 resale
EHG_RESALE = 72300 * 0.4
EHG_SPAN = (("2019-Q4", "2024-Q2"), ("2019-Q3", "2024-Q2"))
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


def official_problems(recs: list[dict], total: int | None, quarters: set[str]) -> list[str]:
    """Why a copy of the registered-applications table is not whole, or [] when it is."""
    out = []
    if total is None or len(recs) != total:
        out.append(f"{len(recs)} records against the source's total {total}")
    keys = [(r.get("quarter"), r.get("flat_type")) for r in recs if r.get("quarter") in quarters]
    if len(keys) != len(set(keys)):
        out.append("a quarter and flat type appear twice")
    for qt in sorted(quarters):
        n = sum(1 for k in keys if k[0] == qt)
        if n != FLAT_TYPES:
            out.append(f"{qt}: {n} flat types, not {FLAT_TYPES}")
    for r in recs:
        if r.get("quarter") in quarters and not str(r.get("no_of_resale_applications", "")).isdigit():
            out.append(f"{r.get('quarter')} {r.get('flat_type')}: count not a whole number")
    return out


def used_quarters() -> set[str]:
    qs = set()
    for a, b in list(QUARTERS.values()) + [("2022-Q1", "2023-Q4")] + list(EHG_SPAN):
        y0, y1 = int(a[:4]), int(b[:4])
        for y in range(y0, y1 + 1):
            for k in range(1, 5):
                q = f"{y}-Q{k}"
                if a <= q <= b:
                    qs.add(q)
    return qs


def fetch_official() -> dict[str, int]:
    """Registered resale applications by quarter, all flat types summed; the cached copy is used only when whole."""
    need = used_quarters()
    if OFFICIAL_CACHE.exists():
        c = json.loads(OFFICIAL_CACHE.read_text(encoding="utf-8"))
        bad = official_problems(c.get("records", []), c.get("total"), need)
        if not bad:
            recs = c["records"]
        else:
            print("cached registrations not whole: " + "; ".join(bad) + "; fetching again")
            recs = None
    else:
        recs = None
    if recs is None:
        recs, total, off = [], None, 0
        while True:
            q = urllib.parse.urlencode({"resource_id": OFFICIAL, "limit": 1000, "offset": off})
            req = urllib.request.Request("https://data.gov.sg/api/action/datastore_search?" + q, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode("utf-8"))
            total = d["result"].get("total")
            page = d["result"]["records"]
            recs += page
            if len(page) < 1000:
                break
            off += 1000
            time.sleep(1.5)
        bad = official_problems(recs, total, need)
        if bad:
            raise ValueError("registered applications not whole: " + "; ".join(bad))
        OFFICIAL_CACHE.write_text(json.dumps({"resource": OFFICIAL, "total": total, "records": recs},
                                             indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    by_q: dict[str, int] = {}
    for r in recs:
        by_q[r["quarter"]] = by_q.get(r["quarter"], 0) + int(r["no_of_resale_applications"])
    return by_q


def span(by_q: dict[str, int], a: str, b: str) -> int:
    return sum(v for k, v in by_q.items() if a <= k <= b)


def main() -> int:
    cache = fetch()
    by_q = fetch_official()
    rows = {}
    for label, months in MONTHS.items():
        year = label[:4]
        got = [cache.get(f"{year}-{m:02d}") for m in months]
        if any(not isinstance(g, int) for g in got):
            print(f"{label}: months missing, not read")
            continue
        reg = span(by_q, *QUARTERS[label])
        ft = FIRST_TIMER_FAMILIES[label]
        rows[label] = {"registered_applications": reg, "price_records": sum(got), "first_timer_families": ft,
                       "first_timer_family_share": round(ft / reg, 4),
                       "not_first_timer_families": reg - ft,
                       "first_timer_median_income": FIRST_TIMER_MEDIAN_INCOME[label]}
    grant = {}
    for year, n in CPF_GRANT.items():
        q1, rest = by_q[f"{year}-Q1"], span(by_q, f"{year}-Q2", f"{year}-Q4")
        prorated = rest + AFTER_FEB14 * q1
        grant[year] = {"cpf_grant_households": round(n), "registrations_q2_q4": rest, "registrations_q1_q4": rest + q1,
                       "registrations_prorated": round(prorated),
                       "share_low": round(n / (rest + q1), 4), "share_high": round(n / rest, 4),
                       "share_prorated": round(n / prorated, 4)}
    ehg = {f"{a}..{b}": {"registrations": span(by_q, a, b), "ehg_resale_households": round(EHG_RESALE),
                         "share": round(EHG_RESALE / span(by_q, a, b), 4)} for a, b in EHG_SPAN}
    print("period | registered | price records | first-timer families (Table 1A) | share | not first-timer families | their median income")
    for k, r in rows.items():
        print(f"  {k:11s} | {r['registered_applications']:6d} | {r['price_records']:6d} | {r['first_timer_families']:5d} | "
              f"{r['first_timer_family_share']:.3f} | {r['not_first_timer_families']:6d} | ${r['first_timer_median_income']}")
    print("CPF Housing Grant households, resale, 14 Feb to Dec, over registrations:")
    for y, g in grant.items():
        print(f"  {y}: {g['cpf_grant_households']:,} over {g['registrations_q1_q4']:,}..{g['registrations_q2_q4']:,}"
              f" -> {g['share_low']:.3f} to {g['share_high']:.3f}, prorated {g['share_prorated']:.3f}")
    for k, e in ehg.items():
        print(f"  EHG resale {e['ehg_resale_households']:,} over {k}: {e['registrations']:,} -> {e['share']:.3f}")
    OUT.write_text(json.dumps({"stage": "B130-side-buyers", "rows": rows, "cpf_housing_grant": grant, "ehg": ehg,
                               "pr_households_share_of_resale": {"2011": 0.27, "2021": 0.07},
                               "sources": {"numerator": "MND written answer, PQ 2568, 9 Jan 2023, Table 1A (first-timer families; data include applicants who took an HDB loan)",
                                           "denominator": f"data.gov.sg {OFFICIAL}, registered resale applications by quarter and flat type",
                                           "price_records": f"data.gov.sg {RESOURCE}, monthly counts by registration month; excludes non-market-price transactions",
                                           "cpf_housing_grant": "HDB update, 25 Feb 2024 (The Straits Times, 26 Feb 2024): more than 11,000 households, 14 Feb to Dec 2023, up 31 percent on 2022",
                                           "ehg": "MND-HDB joint press release, 19 Aug 2024, paragraph 9",
                                           "pr_households": "MND written answer, 8 Nov 2022",
                                           "private_owner_rule": "MND written answer, 13 Jul 2015"}},
                              indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


def selftest() -> None:
    types = ["1-room", "2-room", "3-room", "4-room", "5-room", "Executive"]
    good = [{"quarter": q, "flat_type": t, "no_of_resale_applications": "10"} for q in ("2020-Q1", "2020-Q2") for t in types]
    need = {"2020-Q1", "2020-Q2"}
    assert official_problems(good, len(good), need) == []
    assert official_problems(good[:-1], len(good), need), "a record cut from the end must fail"
    assert official_problems(good[:-1], len(good) - 1, need), "a quarter short of a flat type must fail"
    assert official_problems(good + good[:1], len(good) + 1, need), "a quarter and flat type twice must fail"
    swapped = [dict(good[0]) if i == 1 else r for i, r in enumerate(good)]      # six rows, one type twice, one missing
    assert official_problems(swapped, len(swapped), need), "a type repeated in place of another must fail"
    assert official_problems([{**r, "no_of_resale_applications": "na"} if i == 0 else r for i, r in enumerate(good)],
                             len(good), need), "a count that is not a number must fail"
    assert official_problems(good, None, need), "a copy without the source's total must fail"
    assert "2023-Q1" in used_quarters() and "2019-Q4" in used_quarters()
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    sys.exit(main())
