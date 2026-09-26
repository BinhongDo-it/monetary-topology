"""B127 readings, first round: the resale-to-retail ratio of Birkin Togo, by year (B127-2, B127-5).

Reads the pages on disk through experiments/b127_parse.py, the list prices in
data/b127/list_prices.csv and the ECB reference rates in data/b127/fx/, and writes
results/b127_ratio.json.

Object. A sold, closed lot with its result visible, titled Birkin 25, 30 or 35 in Togo, with no
variant word (Touch, Shadow, Cargo and the rest are other specifications) and no Sellier style.
Its ratio is the final price with buyer's premium over the list price of the same size and
leather in the same market and year.

Why only Birkin Togo (ruled 2026-09-23): it is the only specification with a list price for every
year 2019-2026 in both the US and Europe. It is the thick end of the quota-bag resale market, the
most produced and most standard specification, and the reading does not stand for luxury buyers
at large: few people are ever offered a quota bag.

Market. USD sales against the US list; EUR sales against the EU list; the rest converted to USD
at the ECB rate on the closing day and read against the US list, and flagged. Knob BASIS: "local"
reads only sales with a list in their own currency; "usd" reads every sale in USD against the US
list. Knob LIST_YEAR: the list of the sale's year, or of the year before (a January increase may
not have reached lots bought earlier). Both scanned (`11f`).

Deletion. On sales where unsold lots were removed from the site (lot numbers with gaps and no
unsold row), the lots left are the ones whose bids met the reserve, so the ratio of that sale is
high by an amount that cannot be recovered; each sale's gap count is printed beside it.

Criteria (`11d`):
  B127-2  rival        one price per position: the resale-to-retail ratio is 1. PASS means the
                       ratio's band (5th-95th percentile over 500 resamples of whole sales)
                       lies above 1 in every year at every scan point; FAIL means it holds 1 or
                       lies under it everywhere; anything else is no verdict
  B127-5  own_reading  the yearly median ratios printed with their bands; B28's and the brokers'
                       direction (narrowing since 2022) is read as a sign of the 2025 minus 2022
                       median at every scan point
  B127-1b bookkeeping  per sale: currency, rows used, gap count

Run from the repo root:
    python experiments/b127_readings.py
    python experiments/b127_readings.py --selftest
"""
from __future__ import annotations

import argparse
import collections
import csv
import io
import itertools
import json
import math
import random
import statistics as st
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b127_parse as P  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LIST = ROOT / "data" / "b127" / "list_prices.csv"
FX = ROOT / "data" / "b127" / "fx" / "eurofxref-hist.zip"
OUT = ROOT / "results" / "b127_ratio.json"
SCAN = {"basis": ["local", "usd"], "list_year": ["same", "previous"]}
SIZES = (25, 30, 35)
BOOT = 500


def load_list() -> dict:
    out = {}
    with open(LIST, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["model"] == "Birkin" and r["leather"] == "Togo":
                out[(int(r["size"]), r["region"], int(r["year"]))] = float(r["price"])
    return out


def load_fx() -> dict:
    """date -> {currency: units per euro}."""
    z = zipfile.ZipFile(FX)
    rows = list(csv.reader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8"))))
    head = rows[0]
    out = {}
    for r in rows[1:]:
        d = date.fromisoformat(r[0])
        out[d] = {c: float(v) for c, v in zip(head[1:], r[1:]) if c and v not in ("N/A", "")}
    return out


def to_usd(amount: float, cur: str, day: date, fx: dict) -> float | None:
    if cur == "USD":
        return amount
    for k in range(8):                        # the last ECB fixing on or before the day
        rates = fx.get(day - timedelta(days=k))
        if rates and "USD" in rates and (cur == "EUR" or cur in rates):
            eur = amount if cur == "EUR" else amount / rates[cur]
            return eur * rates["USD"]
    return None


def lots(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["is_closed"] and r["result_visible"] and r["is_sold"] and r["price_with_premium"]
            and r["model"] == "Birkin" and r["leather"] == "Togo" and r["size"] in SIZES
            and not r.get("variant") and r.get("style") is None and not r["withdrawn"]]


def ratios(ls: list[dict], lst: dict, fx: dict, cfg: dict) -> list[dict]:
    out = []
    for r in ls:
        day = date.fromisoformat(r["closed"][:10])
        y = day.year - (1 if cfg["list_year"] == "previous" else 0)
        cur = r["currency"]
        if cfg["basis"] == "local":
            region = {"USD": "US", "EUR": "EU", "GBP": "UK"}.get(cur)
            lp = lst.get((r["size"], region, y)) if region else None
            if lp is None:
                continue
            ratio, flag = r["price_with_premium"] / lp, "local"
        else:
            usd = to_usd(r["price_with_premium"], cur, day, fx)
            lp = lst.get((r["size"], "US", y))
            if usd is None or lp is None:
                continue
            ratio, flag = usd / lp, ("local" if cur == "USD" else "converted")
        out.append({"year": day.year, "sale": "/".join(r["sale"]), "size": r["size"], "currency": cur,
                    "ratio": ratio, "basis_flag": flag})
    return out


def band(xs_by_sale: dict, rng: random.Random) -> list[float] | None:
    sales = list(xs_by_sale)
    if len(sales) < 2:
        return None
    meds = []
    for _ in range(BOOT):
        pick = [rng.choice(sales) for _ in sales]
        v = [x for s in pick for x in xs_by_sale[s]]
        meds.append(st.median(v))
    q = st.quantiles(meds, n=20)
    return [q[0], q[-1]]


def read_once(ls, lst, fx, cfg) -> dict:
    rs = ratios(ls, lst, fx, cfg)
    years = {}
    rng = random.Random(127)
    for y in sorted({r["year"] for r in rs}):
        g = [r for r in rs if r["year"] == y]
        by_sale = collections.defaultdict(list)
        for r in g:
            by_sale[r["sale"]].append(r["ratio"])
        per_size = {s: st.median([r["ratio"] for r in g if r["size"] == s]) for s in SIZES if any(r["size"] == s for r in g)}
        size_band = {}
        for s in per_size:
            bs = collections.defaultdict(list)
            for r in g:
                if r["size"] == s:
                    bs[r["sale"]].append(r["ratio"])
            size_band[s] = band(bs, rng)
        years[y] = {"lots": len(g), "sales": len(by_sale), "median": st.median(r["ratio"] for r in g),
                    "band": band(by_sale, rng), "per_size": per_size, "size_band": size_band,
                    "floor": st.median(abs(math.log(x) - math.log(st.median(v))) for v in by_sale.values() if len(v) > 1 for x in v)
                    if any(len(v) > 1 for v in by_sale.values()) else None,
                    "converted_share": sum(r["basis_flag"] == "converted" for r in g) / len(g)}
    return {"cfg": cfg, "years": years}


STATE = {"above 1 in every year at every scan point": True, "holds 1 or under it everywhere": False,
         "moves": None, "no object": None}


def read(rows, lst, fx) -> dict:
    ls = lots(rows)
    scan = [read_once(ls, lst, fx, {"basis": b, "list_year": ly}) for b, ly in itertools.product(SCAN["basis"], SCAN["list_year"])]
    cells = [(s["cfg"], y, v["band"]) for s in scan for y, v in s["years"].items() if v["band"]]
    if not cells:
        state = "no object"
    elif all(b[0] > 1 for _, _, b in cells):
        state = "above 1 in every year at every scan point"
    elif all(b[0] <= 1 for _, _, b in cells):
        state = "holds 1 or under it everywhere"
    else:
        state = "moves"
    above = sorted({y for _, y, b in cells if b[0] > 1})
    on = sorted({y for _, y, b in cells if b[0] <= 1})
    diffs = [s["years"][2025]["median"] - s["years"][2022]["median"] for s in scan if 2022 in s["years"] and 2025 in s["years"]]
    s5 = ("narrowed at every scan point" if diffs and all(d < 0 for d in diffs) else
          "widened at every scan point" if diffs and all(d > 0 for d in diffs) else "moves" if diffs else "no object")
    passed = STATE[state]

    def size_state(size: int) -> tuple[str, str]:
        cs = [(y, v["size_band"].get(size)) for s in scan for y, v in s["years"].items() if v["size_band"].get(size)]
        if not cs:
            return "no object", ""
        det = "; ".join(sorted({f"{y}: {b[0]:.2f}-{b[1]:.2f}" for y, b in cs}))
        if all(b[0] > 1 for _, b in cs):
            return "above 1 in every year at every scan point", det
        if all(b[0] <= 1 <= b[1] or b[1] < 1 for _, b in cs):
            return "holds 1 or under it everywhere", det
        return "moves", det

    s25, d25 = size_state(25)
    s35, d35 = size_state(35)
    s30, d30 = size_state(30)
    OWN35 = {"holds 1 or under it everywhere": True, "above 1 in every year at every scan point": False,
             "moves": None, "no object": None}
    # B127-2 is read per size (2026-09-24; a criterion-shape fix, no reading changes): the pooled
    # first version put Birkin 35, where the framework expects the list price too, under a rival
    # criterion, and a rival criterion only stands where the two predictions differ.
    crit = [
        {"name": "B127-2", "kind": "rival", "statement": "one price per position: Birkin 25 Togo resells at its list price (ratio 1)",
         "passed": STATE[s25], "state": s25, "state_map": STATE,
         "rival_premise": "a position (model, size, leather, year) carries one price, paid alike by every buyer",
         "rival_entailment": "the price a buyer pays at resale equals the list price the allocated buyer paid, so the ratio is 1",
         "rival_shape": "point",
         "grid": "B" if STATE[s25] is True else ("C" if STATE[s25] is False else "unread"),
         "detail": "Birkin 25 bands by year: " + d25},
        {"name": "B127-2b", "kind": "own_reading",
         "statement": "Birkin 35 Togo, where allocation does not bind, resells at or under its list price",
         "passed": OWN35[s35], "state": s35, "state_map": OWN35, "detail": "Birkin 35 bands by year: " + d35},
        {"name": "B127-2p", "kind": "bookkeeping",
         "statement": "the pooled reading and Birkin 30 printed, not judged",
         "passed": bool(scan), "state": f"pooled: {state}; Birkin 30: {s30}",
         "detail": f"pooled years above 1: {above}; holding 1: {on}. Birkin 30 bands: {d30}"},
        {"name": "B127-5", "kind": "own_reading",
         "statement": "the ratio narrowed from 2022 to 2025 (the brokers' direction), read as the sign of the change in yearly medians",
         "passed": {"narrowed at every scan point": True, "widened at every scan point": False}.get(s5),
         "state": s5, "detail": "2025 minus 2022 median over the scan: " + ", ".join(f"{d:+.3f}" for d in diffs)},
    ]
    return {"scan": scan, "criteria": crit, "lots_used": len(ls)}


import re  # noqa: E402

# B127-3 groups: title pattern, list key in list_prices.csv (model, size), tier. Lindy is counted
# with the quota bags by some resellers and not by others, so it is its own middle tier.
GROUPS = [
    ("Birkin 25 Togo", r"Togo Birkin 25\b", ("Birkin", "25"), "quota"),
    ("Birkin 35 Togo", r"Togo Birkin 35\b", ("Birkin", "35"), "quota"),
    ("Kelly 28", r"\bKelly (?:Sellier |Retourn[ée] )?28\b", ("Kelly", "28"), "quota"),
    ("Lindy 26", r"(?<!Mini )\bLindy 26\b", ("Lindy", "26"), "semi"),
    ("Picotin 18", r"\bPicotin (?:Lock )?18\b", ("Picotin", "18"), "non-quota"),
    ("Evelyne TPM", r"\bEvelyne (?:TPM|16)\b", ("Evelyne", "TPM16"), "non-quota"),
]
NONQUOTA_MODELS = ("Evelyne", "Picotin")


def list_us(model: str, size: str) -> dict:
    out = {}
    with open(LIST, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["model"] == model and r["size"] == size and r["region"] == "US" and r["leather"] != "Togo/Epsom-EU":
                if model == "Kelly" and r["style"]:
                    continue                       # Kelly 28 list is one price for both styles
                out[int(r["year"])] = float(r["price"])
    return out


def read_tiers(rows, fx) -> dict:
    """B127-3: 2025 and 2026, every sold closed lot of each group in USD against the US list."""
    ok = [r for r in rows if r["is_closed"] and r["result_visible"] and r["is_sold"] and r["price_with_premium"]
          and not r["withdrawn"] and not r["exotic"]]
    groups = {}
    rng = random.Random(1273)
    for name, pat, key, tier in GROUPS:
        lp = list_us(*key)
        per_year = {}
        for y in (2025, 2026):
            if y not in lp:
                continue
            by_sale = collections.defaultdict(list)
            for r in ok:
                if not re.search(pat, r["title"]):
                    continue
                day = date.fromisoformat(r["closed"][:10])
                if day.year != y:
                    continue
                usd = to_usd(r["price_with_premium"], r["currency"], day, fx)
                if usd:
                    by_sale["/".join(r["sale"])].append(usd / lp[y])
            v = [x for xs in by_sale.values() for x in xs]
            if v:
                per_year[y] = {"lots": len(v), "sales": len(by_sale), "median": st.median(v), "band": band(by_sale, rng)}
        groups[name] = {"tier": tier, "years": per_year}
    verdicts = []
    for y in (2025, 2026):
        q = [g["years"][y]["median"] for g in groups.values() if g["tier"] == "quota" and y in g["years"]]
        n = [g["years"][y]["median"] for g in groups.values() if g["tier"] == "non-quota" and y in g["years"]]
        if q and n:
            verdicts.append(st.median(q) > st.median(n))
    state = ("quota above non-quota in every year" if verdicts and all(verdicts) else
             "quota at or under non-quota in every year" if verdicts and not any(verdicts) else
             "moves" if verdicts else "no object")
    return {"groups": groups, "state": state}


def read_share(rows) -> dict:
    """B127-6, the count half: non-quota Hermès bags (Evelyne, Picotin) among sold Hermès bags
    with a model read, by sale year. No list price is needed."""
    per = {}
    for y in range(2021, 2027):
        herm = [r for r in rows if r["is_closed"] and r["is_sold"] and r["result_visible"] and r["model"]
                and (r["brand"] or "").startswith("Herm") and int(r["sale"][0]) == y]
        nq = [r for r in herm if r["model"] in NONQUOTA_MODELS]
        if herm:
            per[y] = {"hermes_bags": len(herm), "non_quota": len(nq), "share": len(nq) / len(herm)}
    if 2022 in per and 2025 in per:
        down = per[2025]["share"] < per[2022]["share"]
        state = "entry share fell 2022 to 2025" if down else "entry share did not fall 2022 to 2025"
    else:
        state = "no object"
    return {"per_year": per, "state": state}


def report(r) -> None:
    print(f"Birkin 25/30/35 Togo lots used: {r['lots_used']}")
    for s in r["scan"]:
        print(f"\n== basis {s['cfg']['basis']}, list of the {s['cfg']['list_year']} year")
        print("  year  lots  sales  median ratio  band 5-95     per size (25/30/35)        floor   converted")
        for y, v in s["years"].items():
            b = f"{v['band'][0]:.2f}-{v['band'][1]:.2f}" if v["band"] else "   n/a   "
            ps = " ".join(f"{k}:{x:.2f}" for k, x in v["per_size"].items())
            fl = f"{v['floor']:.3f}" if v["floor"] is not None else " n/a"
            print(f"  {y}  {v['lots']:>4}  {v['sales']:>5}  {v['median']:>12.2f}  {b:>11}  {ps:<26} {fl:>6}  {v['converted_share']:.2f}")
    print()
    for c in r["criteria"]:
        print(f"{c['name']} {c['kind']} {c['passed']}  {c['state']}\n   {c['detail']}")


def sale_gaps(rows) -> dict:
    by = collections.defaultdict(list)
    for x in rows:
        if (x["lot_no"] or "").isdigit():
            by["/".join(x["sale"])].append(int(x["lot_no"]))
    return {k: (max(v) - min(v) + 1 - len(v)) for k, v in by.items()}


def run() -> int:
    rows, heads = P.load_all()
    fx = load_fx()
    r = read(rows, load_list(), fx)
    report(r)
    tiers = read_tiers(rows, fx)
    share = read_share(rows)
    print("\nB127-3 groups, USD against the US list (2025, 2026): lots, sales, median ratio, band")
    for name, g in tiers["groups"].items():
        cells = "  ".join(f"{y}: n={v['lots']} s={v['sales']} {v['median']:.2f} [{v['band'][0]:.2f}-{v['band'][1]:.2f}]"
                          if v["band"] else f"{y}: n={v['lots']} s={v['sales']} {v['median']:.2f} [n/a]"
                          for y, v in g["years"].items())
        print(f"  {name:<15} {g['tier']:<10} {cells}")
    print(f"B127-3 state: {tiers['state']}")
    print("\nB127-6 non-quota share of sold Hermès bags, by sale year:")
    for y, v in share["per_year"].items():
        print(f"  {y}: {v['non_quota']:>4} of {v['hermes_bags']:>4}  {v['share']:.3f}")
    print(f"B127-6 state: {share['state']}")
    r["criteria"] += [
        {"name": "B127-3", "kind": "own_reading",
         "statement": "where allocation binds the ratio is higher: quota bags above non-quota bags, 2025 and 2026",
         "passed": {"quota above non-quota in every year": True, "quota at or under non-quota in every year": False}.get(tiers["state"]),
         "state": tiers["state"], "detail": "medians per group and year printed in tiers"},
        {"name": "B127-6", "kind": "own_reading",
         "statement": "the entry tier's share of sold Hermès bags fell from 2022 to 2025 (asymmetric: not falling is no verdict)",
         "passed": True if share["state"] == "entry share fell 2022 to 2025" else None,
         "state": share["state"], "state_map": {"entry share fell 2022 to 2025": True,
                                               "entry share did not fall 2022 to 2025": None, "no object": None},
         "detail": "; ".join(f"{y}: {v['share']:.3f}" for y, v in share["per_year"].items())},
    ]
    r["tiers"], r["entry_share"] = tiers, share
    gaps = sale_gaps(rows)
    used = collections.Counter("/".join(x["sale"]) for x in lots(rows))
    print("\nper sale (B127-1b): rows used, lot-number gaps (removed unsold lots, an upper bound)")
    for k in sorted(used):
        print(f"  {k:<52} {used[k]:>4}  gaps {gaps.get(k, 0)}")
    birkin = [x for x in rows if x["model"] == "Birkin" and x["is_sold"] and x["is_closed"]]
    share = len(lots(rows)) / max(1, len(birkin))
    print(f"\nshare of sold Birkin lots that are plain Togo 25/30/35: {share:.3f} ({len(lots(rows))} of {len(birkin)})")
    rec = {"stage": "B127", "arm": "ratio",
           "config": {"scan": SCAN, "sizes": list(SIZES), "boot": BOOT, "list": "data/b127/list_prices.csv",
                      "fx": "data/b127/fx/eurofxref-hist.zip (ECB)", "source": "data/b127/raw via experiments/b127_parse.py"},
           "per_sale": {k: {"rows_used": used[k], "gaps": gaps.get(k, 0)} for k in used},
           "birkin_togo_share": share, **r}
    OUT.write_text(json.dumps(rec, sort_keys=True, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8", newline="\n")
    print(f"written: {OUT}")
    return 0


def selftest() -> int:
    lst = {(25, "US", 2022): 10000.0, (25, "US", 2023): 10000.0}
    fx = {date(2022, 6, 1): {"USD": 1.0, "HKD": 8.0}}
    def row(price, cur="USD", day="2022-06-01", sale=("2022", "a"), **kw):
        base = {"is_closed": True, "result_visible": True, "is_sold": True, "price_with_premium": price,
                "model": "Birkin", "leather": "Togo", "size": 25, "variant": None, "style": None, "withdrawn": False,
                "closed": day + "T00:00Z", "currency": cur, "sale": sale, "lot_no": "1"}
        base.update(kw)
        return base
    at = [row(10000 * (1 + 0.01 * (i % 3 - 1)), sale=("2022", f"s{i % 4}")) for i in range(40)]
    above = [row(20000 * (1 + 0.01 * (i % 3 - 1)), sale=("2022", f"s{i % 4}")) for i in range(40)]
    checks = [
        ("resale at list: B127-2 does not PASS", read(at, lst, fx)["criteria"][0]["passed"] is not True),
        ("resale at twice list: B127-2 PASS, grid B", read(above, lst, fx)["criteria"][0]["passed"] is True
         and read(above, lst, fx)["criteria"][0]["grid"] == "B"),
        ("Birkin 35 at list reads True, at twice list False",
         read([dict(r, size=35) for r in at], {**lst, (35, "US", 2022): 10000.0}, fx)["criteria"][1]["passed"] is True
         and read([dict(r, size=35) for r in above], {**lst, (35, "US", 2022): 10000.0}, fx)["criteria"][1]["passed"] is False),
        ("a Touch variant is not plain Togo", not lots([row(1, variant="Touch")])),
        ("an open lot is not read", not lots([row(1, is_closed=False)])),
        ("HKD converts through the euro", abs(to_usd(80000, "HKD", date(2022, 6, 1), fx) - 10000) < 1e-6),
    ]
    for n, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {n}")
    return 0 if all(ok for _, ok in checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    return selftest() if ap.parse_args().selftest else run()


if __name__ == "__main__":
    sys.exit(main())
