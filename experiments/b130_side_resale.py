"""B130, a side question: what the resale price of a bound flat follows.

A47 read that under residence binding an owner is not a bidder, so a tier's price is set by the
money of those who hold no unit. HDB resale flats are bound (one per household, owner-occupied)
but sold at market prices; their buyers are households without an HDB flat, whose money is
mostly wages and the CPF contributions made on them. Private housing is unbound. Printed, no
criterion: the three series as annual averages rebased to 2001 = 100, each price index over
median income, and the correlation of year-on-year log changes.

Sources (data/b130/raw, fetched by b130_fetch.py): HDB Resale Price Index (1Q2009 = 100,
quarterly, HDB); URA Private Residential Property Price Index, all residential (2009-Q1 = 100,
quarterly); MOM median gross monthly income from employment of full-time employed residents,
including employer CPF (annual, June).

Run from the repo root:
    python experiments/b130_side_resale.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "b130" / "raw"
OUT = ROOT / "results" / "b130_side_resale.json"


def records(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))["result"]["records"]


def annual(rows, key="index", where=None):
    by: dict[str, list[float]] = {}
    for r in rows:
        if where and any(r.get(k) != v for k, v in where.items()):
            continue
        y = r["quarter"][:4]
        by.setdefault(y, []).append(float(r[key]))
    return {y: float(np.mean(v)) for y, v in by.items() if len(v) == 4}


def main() -> int:
    hdb = annual(records("dgs_hdb_resale_price_index.json"))
    ura = annual(records("dgs_ura_private_price_index.json"), where={"property_type": "All Residential"})
    inc = {r["year"]: float(r["median_income_incl_emp_cpf"]) for r in records("dgs_median_income_fulltime.json")}
    years = sorted(set(hdb) & set(ura) & set(inc))
    base = years[0]
    reb = {name: {y: 100.0 * s[y] / s[base] for y in years} for name, s in (("hdb", hdb), ("ura", ura), ("income", inc))}
    table = {y: {k: round(reb[k][y], 1) for k in reb} | {
        "hdb_over_income": round(reb["hdb"][y] / reb["income"][y], 3),
        "ura_over_income": round(reb["ura"][y] / reb["income"][y], 3)} for y in years}
    consecutive = [(a, b) for a, b in zip(years, years[1:]) if int(b) == int(a) + 1]
    ch = {k: np.array([np.log(reb[k][b] / reb[k][a]) for a, b in consecutive]) for k in reb}
    corr = {f"{a} vs {b}": round(float(np.corrcoef(ch[a], ch[b])[0, 1]), 3)
            for a, b in (("hdb", "income"), ("ura", "income"), ("hdb", "ura"))}
    ratio = {k: {"min": round(min(t[k] for t in table.values()), 3), "max": round(max(t[k] for t in table.values()), 3),
                 "end": table[years[-1]][k]} for k in ("hdb_over_income", "ura_over_income")}
    missing = sorted(set(str(y) for y in range(int(years[0]), int(years[-1]) + 1)) - set(years))
    print(f"years {years[0]}-{years[-1]}, {len(years)} with all three; missing {missing}")
    print("year | HDB resale | URA private | median income | HDB/income | URA/income  (rebased to", base, "= 100)")
    for y in years:
        t = table[y]
        print(f"  {y} | {t['hdb']:6.1f} | {t['ura']:6.1f} | {t['income']:6.1f} | {t['hdb_over_income']:.3f} | {t['ura_over_income']:.3f}")
    print("price over income, min / max / end:", ratio)
    print(f"correlation of year-on-year log changes over {len(consecutive)} consecutive pairs:", corr)
    OUT.write_text(json.dumps({"stage": "B130-side-resale", "table": table, "ratio_range": ratio,
                               "yoy_log_change_correlation": corr, "n_pairs": len(consecutive),
                               "missing_years": missing,
                               "config": {"base_year": base, "ura_series": "All Residential",
                                          "income": "median_income_incl_emp_cpf",
                                          "annual": "mean of four quarters; years with fewer are dropped"}},
                              indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
