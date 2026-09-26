"""B130: Singapore's public housing against A49's prediction.

A49 (A-track) predicts that under residence binding, with dwellings at cost and a lender with no
ceiling on its cash, those who can commit to staying buy, and renting shrinks to those who
cannot; without binding the same loan does not shrink renting. Singapore runs both segments
side by side: HDB flats (one per household, owner-occupied through a five-year minimum
occupation period, rented out whole only by citizen owners after it, bought only by citizen or
permanent-resident households) and private condominiums (no such rules).

Criteria:
  B130-1  instrument   every source file on disk passes its fetch check, and every number read
                       from the HDB key-statistics PDF is found on the page it is attributed to
  B130-2  own_reading  owner-occupied share of resident households, HDB against condominiums,
                       every year the table prints: the difference and its sign
  B130-3  own_reading  how many resident households at most rent HDB flats on the open market,
                       against the flats rented out whole; hence a floor on the non-resident share
  B130-4  rival        premise: tenure rises with household income, whatever the segment's rules.
                       Entailed: where condominium residents earn more per member than residents
                       of every HDB flat type, their owner-occupied share is at least HDB's.
                       PASS means that inequality fails (the rival is wrong in that year).

Run from the repo root:
    python experiments/b130_readings.py
    python experiments/b130_readings.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import b130_fetch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "b130" / "raw"
OUT = ROOT / "results" / "b130_readings.json"

#: numbers read from HDB Key Statistics 2024/2025, with the 1-based page each sits on and the
#: label it is printed under (rule 25: every item carries its source)
HDB_ITEMS = {
    "renting_out_active_cases_2025_03_31": (10, "59,567", "Active cases for Renting Out of Flat (as at 31 March 2025)"),
    "sold_flats_under_management": (15, "1,089,522", "Dwelling Units Under Management, Sold Flats, Total"),
    "rental_flats_under_management": (15, "63,558", "Dwelling Units Under Management, Rental Flats, Total"),
    "rental_flats_1_room": (15, "30,494", "Rental Flats, 1-Room, Total"),
    "resident_population_in_hdb_pct": (7, "76.0", "Percentage of Singapore resident population living in HDB flats"),
}
HDB_TYPES = ("HDB 1- And 2-Room Flats", "HDB 3-Room Flats", "HDB 4-Room Flats",
             "HDB 5-Room And Executive Flats")
INCOME_COLS = {"HDB 1- And 2-Room Flats": "HDB1_and2_RoomFlats1", "HDB 3-Room Flats": "HDB3_RoomFlats",
               "HDB 4-Room Flats": "HDB4_RoomFlats", "HDB 5-Room And Executive Flats": "HDB5_RoomandExecutiveFlats"}


# -- loading -----------------------------------------------------------------------------

def owner_share() -> dict[str, dict[str, float]]:
    d = json.loads((RAW / "singstat_m810401.json").read_text(encoding="utf-8"))
    return {r["rowText"].strip(): {c["key"]: float(c["value"]) for c in r["columns"] if c["value"] not in ("", "na", "-")}
            for r in d["Data"]["row"]}


def households() -> dict[str, dict[str, float]]:
    d = json.loads((RAW / "dgs_households_by_dwelling.json").read_text(encoding="utf-8"))
    out = {}
    for rec in d["result"]["records"]:
        name = rec["DataSeries"].strip().replace("Condominiums And Other Apartments",
                                                  "Condominiums & Other Apartments")
        out[name] = {k: float(v) for k, v in rec.items() if k.isdigit() and v not in (None, "", "na")}
    return out


def income() -> dict[str, dict[str, float]]:
    d = json.loads((RAW / "dgs_income_per_member_by_dwelling.json").read_text(encoding="utf-8"))
    out = {}
    for rec in d["result"]["records"]:
        y = str(rec["Dollar"]).strip()
        out[y] = {k: float(v) for k, v in rec.items() if k not in ("_id", "Dollar") and v not in (None, "", "na")}
    return out


def pdf_pages() -> list[str]:
    from pypdf import PdfReader
    r = PdfReader(str(RAW / "hdb_key_statistics_2024_2025.pdf"))
    return [p.extract_text() or "" for p in r.pages]


# -- criteria ----------------------------------------------------------------------------

def c1(pages: list[str], raw: Path = RAW) -> tuple[bool, dict]:
    files = {n: b130_fetch.check(n, (raw / n).read_bytes()) if (raw / n).exists() else "missing"
             for n in b130_fetch.FILES}
    found = {k: (page, num, num in pages[page - 1]) for k, (page, num, _) in HDB_ITEMS.items()}
    ok = all(v is None for v in files.values()) and all(f[2] for f in found.values())
    coverage = {f"page {i + 1}": len(t) for i, t in enumerate(pages)}
    return ok, {"files": {k: v or "ok" for k, v in files.items()},
                "hdb_items": {k: {"page": p, "value": n, "found_on_page": f, "label": HDB_ITEMS[k][2]}
                              for k, (p, n, f) in found.items()},
                "pdf_pages_opened": len(pages), "pdf_chars_per_page": coverage}


def c2(own: dict) -> tuple[bool, dict]:
    hdb, condo, landed = own["Total HDB Dwellings"], own["Condominiums & Other Apartments"], own["Landed Properties"]
    years = sorted(set(hdb) & set(condo))
    rows = {y: {"hdb": hdb[y], "condo": condo[y], "landed": landed.get(y),
                "hdb_minus_condo": round(hdb[y] - condo[y], 1)} for y in years}
    signs = {"+": sum(r["hdb_minus_condo"] > 0 for r in rows.values()),
             "-": sum(r["hdb_minus_condo"] < 0 for r in rows.values()),
             "0": sum(r["hdb_minus_condo"] == 0 for r in rows.values())}
    return bool(rows), {"years": rows, "sign_counts": signs, "n_years": len(years)}


def c3(own: dict, hh: dict, items: dict, year: str = "2025") -> tuple[bool, dict]:
    """Upper bound on resident households renting HDB flats on the open market, and the floor on
    the non-resident share of whole-flat tenancies it gives."""
    non_owner = {t: hh[t][year] * (1.0 - own[t][year] / 100.0) for t in HDB_TYPES}
    three_up = sum(non_owner[t] for t in HDB_TYPES[1:])
    small = non_owner[HDB_TYPES[0]]
    whole = items["renting_out_active_cases_2025_03_31"]
    rental_flats = items["rental_flats_under_management"]
    tight = three_up                     # 1-2 room non-owners taken as public-rental tenants
    loose = three_up + small             # every non-owner counted as a market tenant
    if whole <= 0.0:
        return False, {"year": year, "why": "no whole-flat rentals to set the bound against"}
    out = {
        "year": year,
        "non_owner_households_by_type": {t: round(v) for t, v in non_owner.items()},
        "non_owners_3_room_and_up": round(three_up),
        "non_owners_1_2_room": round(small),
        "public_rental_flats_under_management": rental_flats,
        "flats_rented_out_whole": whole,
        "bound_1_2_room_as_public_rental": {
            "resident_market_tenants_at_most": round(tight),
            "non_resident_share_of_whole_flat_tenancies_at_least": round(1.0 - tight / whole, 4)},
        "bound_every_non_owner_a_market_tenant": {
            "resident_market_tenants_at_most": round(loose),
            "non_resident_share_of_whole_flat_tenancies_at_least": max(0.0, round(1.0 - loose / whole, 4))},
        "consistency": {"1_2_room_non_owners_le_public_rental_flats": small <= rental_flats},
        "why_each_is_an_upper_bound": [
            "non-owners include rent-free households and households renting a bedroom",
            "the tight bound assumes every 1-2 room non-owner is a public-rental tenant; public rental "
            "flats are 1- and 2-room, and they outnumber the 1-2 room non-owners",
            "SingStat counts resident households in June; HDB counts active rentals on 31 March",
        ],
    }
    return three_up > 0.0, out


def c4(own: dict, inc: dict) -> tuple[bool | None, dict]:
    hdb, condo = own["Total HDB Dwellings"], own["Condominiums & Other Apartments"]
    per_year, split = {}, {"B": 0, "C": 0}
    for y, row in sorted(inc.items()):
        if y not in hdb or y not in condo:
            continue
        richer = row["CondominiumsandOtherApartments"] > max(row[INCOME_COLS[t]] for t in HDB_TYPES)
        if not richer:
            per_year[y] = {"read": False, "why": "condominium income not above every HDB type"}
            continue
        d = hdb[y] - condo[y]
        if d == 0:
            per_year[y] = {"read": False, "why": "equal shares at the table's 0.1 point"}
            continue
        # framework: bound segment higher; rival: richer segment at least as high
        cell = "B" if d > 0 else "C"
        split[cell] += 1
        per_year[y] = {"read": True, "hdb_minus_condo": round(d, 1), "cell": cell,
                       "condo_income_per_member": row["CondominiumsandOtherApartments"],
                       "max_hdb_income_per_member": max(row[INCOME_COLS[t]] for t in HDB_TYPES)}
    read = split["B"] + split["C"]
    if read == 0:
        return None, {"grid": "unread", "per_year": per_year}
    grid = "B" if split["C"] == 0 else ("C" if split["B"] == 0 else "mixed")
    rec = {"grid": grid, "per_year": per_year, "rival_shape": "one-sided inequality"}
    if grid == "mixed":
        rec["grid_split"] = {k: v for k, v in split.items() if v}
    return split["C"] == 0, rec


RIVAL = {
    "rival_premise": "Tenure is a function of household resources: ownership rises with household income, "
                     "whatever rules a housing segment carries.",
    "rival_entailment": "Condominium residents earn more per household member than residents of every HDB "
                        "flat type in each year read; so under the premise the condominium owner-occupied "
                        "share is at least the HDB share in each such year.",
}


def build(pages, own, hh, inc):
    items = {k: float(num.replace(",", "")) for k, (_, num, _) in HDB_ITEMS.items()}
    ok1, d1 = c1(pages)
    ok2, d2 = c2(own)
    ok3, d3 = c3(own, hh, items)
    ok4, d4 = c4(own, inc)
    return [
        {"name": "B130-1", "kind": "instrument", "passed": ok1, "detail": d1},
        {"name": "B130-2", "kind": "own_reading", "passed": ok2, "detail": d2},
        {"name": "B130-3", "kind": "own_reading", "passed": ok3, "detail": d3},
        {"name": "B130-4", "kind": "rival", "passed": ok4, "detail": d4,
         "grid": d4["grid"], **({"grid_split": d4["grid_split"]} if "grid_split" in d4 else {}),
         "rival_shape": "one-sided inequality", **RIVAL},
    ]


def selftest() -> None:
    pages, own, hh, inc = pdf_pages(), owner_share(), households(), income()
    crit = {c["name"]: c for c in build(pages, own, hh, inc)}
    assert crit["B130-1"]["passed"], "the real files must pass before the plants mean anything"
    bad_pages = list(pages)
    bad_pages[9] = bad_pages[9].replace("59,567", "59,000")
    assert not c1(bad_pages)[0], "B130-1 must catch a number that is not on its page"
    flipped = {k: dict(v) for k, v in own.items()}
    for y in flipped["Total HDB Dwellings"]:
        flipped["Condominiums & Other Apartments"][y] = flipped["Total HDB Dwellings"][y] + 1.0
    ok, d = c4(flipped, inc)
    assert ok is False and d["grid"] == "C", "B130-4 must fail when condominiums own more every year"
    half = {k: dict(v) for k, v in own.items()}
    ys = sorted(set(half["Total HDB Dwellings"]) & set(inc))
    for y in ys[: len(ys) // 2]:
        half["Condominiums & Other Apartments"][y] = half["Total HDB Dwellings"][y] + 1.0
    ok, d = c4(half, inc)
    assert ok is False and d["grid"] == "mixed" and set(d["grid_split"]) == {"B", "C"}, \
        "B130-4 must split when the years disagree"
    poor = {y: dict(r, CondominiumsandOtherApartments=0.0) for y, r in inc.items()}
    ok, d = c4(own, poor)
    assert ok is None and d["grid"] == "unread", "B130-4 must not read a year where condominiums are not richer"
    assert not c3(own, hh, {"renting_out_active_cases_2025_03_31": 0.0, "rental_flats_under_management": 1.0})[0], \
        "B130-3 must fail with no whole-flat rentals to set the bound against"
    empty = {k: {} for k in own}
    assert not c2(empty)[0], "B130-2 must fail with no years"
    print("selftest ok: B130-1 catches a misplaced number; B130-4 fails, splits and stays unread on "
          "planted tables; B130-3 and B130-2 fail on empty objects")


def main() -> int:
    pages, own, hh, inc = pdf_pages(), owner_share(), households(), income()
    crit = build(pages, own, hh, inc)
    for c in crit:
        flag = {True: "PASS", False: "FAIL", None: "UNREAD"}[c["passed"]]
        print(f"{flag} {c['name']} [{c['kind']}]" + (f" grid {c['grid']}" if "grid" in c else ""))
    d2 = crit[1]["detail"]
    print("\nB130-2 owner-occupied share, HDB | condominiums | landed | HDB - condo")
    for y, r in d2["years"].items():
        print(f"  {y}  {r['hdb']:5.1f} | {r['condo']:5.1f} | {r['landed']} | {r['hdb_minus_condo']:+.1f}")
    print(f"  sign counts {d2['sign_counts']} over {d2['n_years']} years")
    print("\nB130-3", json.dumps(crit[2]["detail"], indent=1, ensure_ascii=False))
    d4 = crit[3]["detail"]
    print(f"\nB130-4 grid {d4['grid']}" + (f" split {d4.get('grid_split')}" if "grid_split" in d4 else ""))
    for y, r in d4["per_year"].items():
        print(f"  {y} {r}")
    record = {"stage": "B130", "criteria": crit,
              "config": {"sources": {k: v for k, v in b130_fetch.FILES.items()},
                         "hdb_items": {k: {"page": p, "value": n, "label": lab} for k, (p, n, lab) in HDB_ITEMS.items()},
                         "c3_year": "2025"}}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] is not False for c in crit if c["kind"] == "instrument") else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        sys.exit(main())
