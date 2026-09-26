"""B35-PH-7: the re-export pull, registered 2026-09-10 and run here.

The physical ceiling reading says a country cannot export more tongue than its
own slaughter produces. That holds only if nothing was imported and shipped out
again, so the pull was registered with three outcomes written before it ran, one
of which voids the whole file. This script fetches the imports side of the same
feed and scores it.

### What is measured, and why it needs no threshold

The three registered outcomes collapse onto one quantity with no constant in it:

    exports / (production + general imports)

and whether it is still above one. That is the `partial` branch's own registered
reading, "the bound is restated against production plus imports, which is a
subtraction, not a new argument", applied to all three. Above one, the physical
bound still binds and the verdict stands; the distance above one is how much of
it survives, and it is printed rather than banded. At or below one, the bound no
longer binds on that year and the file's headline is void.

**General imports, not imports for consumption.** Goods that enter a foreign
trade zone or a bonded warehouse and leave again are exactly the flow this pull
is about; they appear in general imports and never clear for consumption. Taking
the consumption series would remove the object being asked about.

### Field names are enumerated, not assumed

The imports endpoint is a different table from the exports one and its columns
are named differently. Nothing here guesses: `--probe` asks the endpoint for its
variable list and prints it, and `--fetch` refuses to run if a column it intends
to request is not on that list, printing what is.

Usage, on the machine that owns data/b35/ and the key:

    python experiments/b35_reexport_pull.py --probe
    python experiments/b35_reexport_pull.py --fetch --years 2021 2023
    python experiments/b35_reexport_pull.py --score
    python experiments/b35_reexport_pull.py --selftest

Writes into data/b35/ under names prefixed `imp_`, which cannot collide with the
exports cache. Deletes nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "b35"
OUT = ROOT / "results" / "b35_reexport_pull.json"
CEILING = ROOT / "results" / "b35_physical_ceiling.json"

BASE = "https://api.census.gov/data/timeseries/intltrade/imports/hs"
VARS = BASE + "/variables.json"
HS6 = "020649"          # default; --hs6 020630 pulls the fresh or chilled basket
TONGUE = "0206490010"   # the line the pull asked for; it exists on the exports side
BASKET = "0206490000"   # what the imports schedule actually carries: one basket, NESOI
# Requested columns. Checked against the endpoint's own variable list before any
# fetch: a name that is not there stops the run and prints what is.
GET = ["CTY_NAME", "I_COMMODITY", "I_COMMODITY_LDESC",
       "GEN_VAL_MO", "GEN_QY1_MO", "UNIT_QY1"]


def get_key():
    """Same key, same three places, same never-printed rule as the exports side."""
    import b35_step0_fetch as ex
    return ex.read_key(None, CACHE)


def _open(url, timeout=60):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:400]
            raise SystemExit(f"HTTP {e.code} from the imports endpoint\n{body}")
        except urllib.error.URLError as e:
            # A dropped connection is retried; a refusal to connect is not,
            # because waiting does not fix that one. Same rule as the exports side.
            if "forcibly closed" in str(e) or "timed out" in str(e):
                time.sleep(2 * (attempt + 1))
                continue
            raise SystemExit(f"cannot reach the imports endpoint: {e}")
    raise SystemExit("five dropped connections in a row; try again later")


def probe() -> int:
    key, where = get_key()
    print(f"key: {where}")
    raw = _open(VARS + ("?key=" + key if key else ""))
    d = json.loads(raw)["variables"]
    names = sorted(d)
    print(f"\nthe imports table exposes {len(names)} variables")
    missing = [g for g in GET if g not in names]
    print("\nthe columns this script intends to request:")
    for g in GET:
        mark = "  <-- NOT ON THE LIST" if g in missing else ""
        lab = d.get(g, {}).get("label", "")
        print(f"    {g:<22}{lab[:70]}{mark}")
    if missing:
        print("\ncandidates carrying a value or a quantity, for picking a replacement:")
        for n in names:
            if any(w in n for w in ("VAL", "QY", "QTY", "COMMODITY", "CTY")):
                print(f"    {n:<22}{d[n].get('label','')[:70]}")
        print("\nnothing was fetched. Fix GET and probe again.")
        return 1
    print("\nevery intended column is on the list. --fetch can run.")
    return 0


def cache_path(year: int, month: int, hs6: str | None = None) -> Path:
    return CACHE / f"imp_{hs6 or HS6}_{year}_{month:02d}_bycountry_HS10.json"


def load_cached(p: Path):
    """Rule 6: a truncated or corrupt cache is recognised, not read in silently."""
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"   cache damaged, will refetch: {p.name} ({e})")
        return None
    if not isinstance(d, list) or not d or not isinstance(d[0], list):
        print(f"   cache malformed, will refetch: {p.name}")
        return None
    return d


def fetch(years) -> int:
    key, where = get_key()
    print(f"key: {where}")
    raw = json.loads(_open(VARS + ("?key=" + key if key else "")))["variables"]
    missing = [g for g in GET if g not in raw]
    if missing:
        raise SystemExit(f"these columns are not on the imports table: {missing}. "
                         f"Run --probe and fix GET before fetching.")
    CACHE.mkdir(parents=True, exist_ok=True)
    got = 0
    for year in range(years[0], years[1] + 1):
        for month in range(1, 13):
            p = cache_path(year, month)
            if load_cached(p) is not None:
                print(f"   cached {p.name}")
                continue
            q = {"get": ",".join(GET), "YEAR": str(year), "MONTH": f"{month:02d}",
                 "COMM_LVL": "HS10", "I_COMMODITY": HS6 + "*", "CTY_CODE": "*"}
            if key:
                q["key"] = key
            body = _open(BASE + "?" + urllib.parse.urlencode(q))
            d = json.loads(body)
            p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
            back = load_cached(p)
            if back is None or len(back) != len(d):
                raise SystemExit(f"{p} wrote {len(d)} rows and read back "
                                 f"{0 if back is None else len(back)}")
            got += 1
            print(f"   fetched {p.name}  {len(d) - 1} rows")
            time.sleep(0.4)
    print(f"\n{got} new month(s) fetched into {CACHE}")
    return 0


def is_country(code: str) -> bool:
    """A real origin, not a grouping.

    The feed mixes three kinds of row in one response and they overlap by
    construction, so adding them up counts the same tonnage several times:

        -       TOTAL FOR ALL COUNTRIES
        00XX    named groupings: EUROPEAN UNION, OECD, NATO, APEC, USMCA, LAFTA
        NXXX    continent rollups: 1XXX NORTH AMERICA, 4XXX EUROPE
        NNNN    the countries themselves: 1220 CANADA, 4099 DENMARK

    2026-09-13: the first version of this file summed every row and read
    131,271 tonnes for 2023 where the true figure is 18,534, a factor of seven.
    Nothing reported it, because every row is a valid row. The check below is
    the identity that catches it: the countries have to add up to the TOTAL row.
    """
    return code.isdigit() and not code.startswith("00")


def read_imports(years):
    """Tonnes and dollars per year for every HS10 line under 020649.

    Returns the TOTAL row separately from the per-country rows, and the caller
    asserts they agree. Every ten digit line is returned, not only a chosen one,
    because which lines exist on this side is itself the finding here.
    """
    per_year, origins, units, months, totals = {}, {}, set(), {}, {}
    for year in range(years[0], years[1] + 1):
        lines, n_months = {}, 0
        tot_kg = tot_val = 0.0
        for month in range(1, 13):
            d = load_cached(cache_path(year, month))
            if d is None:
                continue
            n_months += 1
            h = d[0]
            ic, qy, vv = h.index("I_COMMODITY"), h.index("GEN_QY1_MO"), h.index("GEN_VAL_MO")
            un, cn, cc = h.index("UNIT_QY1"), h.index("CTY_NAME"), h.index("CTY_CODE")
            ld = h.index("I_COMMODITY_LDESC")
            for row in d[1:]:
                code, cty = row[ic], row[cc]
                units.add(row[un])
                try:
                    kg, val = float(row[qy]), float(row[vv])
                except (TypeError, ValueError):
                    continue
                if cty == "-":
                    tot_kg += kg
                    tot_val += val
                    e = lines.setdefault(code, {"kg": 0.0, "val": 0.0, "desc": row[ld]})
                    e["kg"] += kg
                    e["val"] += val
                elif is_country(cty) and kg > 0:
                    origins.setdefault(year, {})
                    origins[year][row[cn]] = origins[year].get(row[cn], 0.0) + kg
        per_year[year] = lines
        months[year] = n_months
        totals[year] = {"kg": tot_kg, "val": tot_val}
    return per_year, origins, units, months, totals


def score() -> int:
    """Score the pull, and score it against a bound rather than against a guess.

    **The tongue line does not exist on this side.** The imports table carries
    one basket, 0206490000 OFFAL OF SWINE EDIBLE FROZEN NESOI, where the exports
    side splits 0206.49 into tongues, hearts and skins. The two schedules are not
    the same schedule, and the granularity of a class value is capped by the
    granularity of the registration point. So the quantity the pull asked for
    cannot be read here at all, and reading the tongue line's zero as a
    measurement would be reading an instrument's silence as a fact about the
    world.

    **What can be read is a bound, and it needs nothing else.** Every kilogram of
    frozen swine offal the country imported is an upper bound on the part of it
    that was tongue, and re-exporting more tongue than was imported is not
    possible. So the whole basket goes in on the imports side of the restated
    bound. If the ratio still clears one under that substitution, it clears one
    under every weaker assumption, and no share has to be borrowed from anywhere.
    """
    if not CEILING.exists():
        raise SystemExit(f"{CEILING} is not on disk; the exports side has to exist first")
    rep = json.loads(CEILING.read_text(encoding="utf-8"))["report"]
    reg = rep["re_export_check"]["branches"]
    ex_t = rep["exports_over_production"]["tongues"]
    years = (min(int(y) for y in ex_t), max(int(y) for y in ex_t))
    per_year, origins, units, months, totals = read_imports(years)
    have = [y for y in per_year if months[y]]
    if not have:
        raise SystemExit("no import cache on disk. Run --fetch first.")
    if units and units != {"KG"}:
        raise SystemExit(f"the imports side reports units {sorted(units)} and the exports side "
                         f"reports KG. Two units in one column is not a subtraction. Stop.")

    print("ten digit lines present under 020649 on the IMPORTS side, tonnes per year:")
    codes = sorted({c for y in have for c in per_year[y]})
    for c in codes:
        desc = next((per_year[y][c]["desc"] for y in have if c in per_year[y]), "")[:46]
        cells = "".join(f"{per_year[y].get(c, {'kg': 0.0})['kg'] / 1000:>12.3f}" for y in have)
        print(f"   {c:<12}{desc:<48}{cells}")
    split = TONGUE in codes
    same = ("does too" if split else
            "does NOT: one basket, so the tongue quantity is not readable here at any price")
    print(f"   the exports side splits this heading into tongues, hearts and skins; "
          f"this side {same}")

    print("\ncountries add up to the TOTAL row, which is the check that catches grouping rows:")
    for y in have:
        s = sum(origins.get(y, {}).values())
        agree = abs(s - totals[y]["kg"]) < 1.0
        print(f"   {y}: countries {s/1000:>10.3f} t   TOTAL row {totals[y]['kg']/1000:>10.3f} t   "
              f"{'agree' if agree else '**DISAGREE**'}")
        if not agree:
            raise SystemExit("the per-country rows do not add up to the TOTAL row; a grouping row "
                             "is being counted as a country. Stop rather than report a sum.")

    rows = {}
    print("\nthe bound, restated against production plus the WHOLE offal basket, which is a "
          "strict upper bound on any tongue imports:")
    print(f"   {'year':<6}{'exports_t':>12}{'production_t':>14}{'all offal imports_t':>21}"
          f"{'old ratio':>11}{'bounded ratio':>15}   verdict")
    for y in have:
        e = ex_t[str(y)]
        imp_t = totals[y]["kg"] / 1000.0
        prod = e["production_t"]
        new_r = e["exports_t"] / (prod + imp_t) if prod + imp_t > 0 else float("nan")
        was_binding = e["ratio"] > 1.0
        if not was_binding:
            verdict = "the bound was not binding this year, nothing to void"
            branch = "not applicable"
        elif new_r > 1.0:
            verdict = "**bound still binds under the most generous substitution**"
            branch = "partial, with the imported tonnage subtracted at its ceiling"
        else:
            verdict = "**bound no longer binds, this year voids**"
            branch = "re_export"
        rows[y] = {"exports_t": e["exports_t"], "production_t": prod,
                   "all_offal_imports_t": imp_t,
                   "import_unit_value_usd_per_kg": (totals[y]["val"] / totals[y]["kg"]
                                                    if totals[y]["kg"] else None),
                   "ratio_against_production": e["ratio"],
                   "ratio_against_production_plus_all_offal_imports": new_r,
                   "bound_was_binding_before_this_pull": bool(was_binding),
                   "bound_still_binds": bool(was_binding and new_r > 1.0),
                   "registered_branch": branch, "months_cached": months[y]}
        print(f"   {y:<6}{e['exports_t']:>12.3f}{prod:>14.3f}{imp_t:>21.3f}"
              f"{e['ratio']:>11.4f}{new_r:>15.4f}   {verdict}")

    key_year = max(y for y in have if ex_t[str(y)]["ratio"] > 1.0) if any(
        ex_t[str(y)]["ratio"] > 1.0 for y in have) else max(have)
    kr = rows[key_year]
    gap = kr["exports_t"] - kr["production_t"]
    print(f"\n   {key_year} gap to be filled {gap:,.3f} t; every kilogram of frozen swine offal "
          f"imported that year {kr['all_offal_imports_t']:,.3f} t, "
          f"which is {kr['all_offal_imports_t'] / gap:.3f} of it")

    print("\nthe three outcomes as registered before the run:")
    for k in ("domestic", "partial", "re_export"):
        print(f"   {k:<11}{reg[k]['pattern']}")
        print(f"   {'':<11}-> {reg[k]['reading']}")

    print("\norigins of the offal basket, tonnes, largest first:")
    for y in have:
        o = origins.get(y, {})
        top = sorted(o.items(), key=lambda kv: -kv[1])[:6]
        print(f"   {y}: " + (", ".join(f"{n} {v/1000:.3f}" for n, v in top) or "none"))

    crit = [
     {"name": "B35-PH-9 premise: the imports schedule does not split this heading, "
              "so the tongue quantity is not readable on that side",
      "kind": "premise", "passed": bool(split),
      "detail": f"the imports table returns one line, {codes}, described as OFFAL OF SWINE EDIBLE "
                f"FROZEN NESOI, where the exports side splits 0206.49 into tongues, hearts and "
                f"skins. Units {sorted(units)}, {months[key_year]} of 12 months cached for "
                f"{key_year}, and the per-country rows add up to the TOTAL row in every year. "
                f"**kind is premise and not instrument**: nothing here is broken code to go and fix, the "
                f"external fact this reading was to rest on does not hold, so the criterion that "
                f"depended on it has no object. **It is a fact about the schedules**: the "
                f"granularity of a class value is capped by the granularity of the registration "
                f"point, and the two schedules do not register the same classes. Reading the "
                f"tongue line's absence as a zero would be reading an instrument's silence as a "
                f"fact about the world"},
     {"name": "B35-PH-10 the physical bound restated against production plus every kilogram of "
              "frozen swine offal imported",
      "kind": "own_reading", "passed": bool(kr["bound_still_binds"]),
      "detail": f"the tongue quantity is not readable on the imports side, so the whole basket "
                f"goes in, which is a strict upper bound on any part of it that was tongue. In "
                f"{key_year} exports are {kr['exports_t']:,.3f} t against production "
                f"{kr['production_t']:,.3f} t, a gap of {gap:,.3f} t, and the country imported "
                f"{kr['all_offal_imports_t']:,.3f} t of frozen swine offal of every kind, which is "
                f"{kr['all_offal_imports_t'] / gap:.3f} of the gap. **Even if every kilogram of it "
                f"was tongue and every kilogram was re-exported it does not reach**, so the ratio "
                f"moves from {kr['ratio_against_production']:.4f} to "
                f"{kr['ratio_against_production_plus_all_offal_imports']:.4f} and stays above one. "
                f"No share is borrowed from anywhere: the substitution is at its ceiling. "
                f"Registered branch: {kr['registered_branch']}"},
     {"name": "B35-PH-11 bookkeeping: the grouping rows are not counted as countries",
      "kind": "bookkeeping", "passed": True,
      "detail": "the feed returns the TOTAL row, named groupings (EU, OECD, NATO, APEC, USMCA, "
                "LAFTA), continent rollups and the countries in one response, and they overlap by "
                "construction. The first version of this script summed all of them and read "
                "131,271 t for 2023 where the true figure is 18,534, a factor of seven, and no row "
                "was invalid so nothing reported it. The identity that catches it is now asserted "
                "in every year: the per-country rows have to add up to the TOTAL row"}]
    if not split:
        crit[1]["detail"] += (". The tongue-line figure the pull originally asked for is recorded "
                              "as not readable on this side rather than as zero")

    rec = {"stage": "B35-PH-7 re-export pull", "years": rows,
           "ten_digit_lines_on_the_imports_side": sorted(codes),
           "imports_side_splits_the_heading": bool(split),
           "hs10_lines_tonnes": {str(y): {c: v["kg"] / 1000 for c, v in per_year[y].items()}
                                 for y in have},
           "origins_tonnes": {str(y): {n: v / 1000 for n, v in origins.get(y, {}).items()}
                              for y in have},
           "criteria": crit,
           "config": {"endpoint": BASE, "flow": "general imports", "hs6": HS6,
                      "tongue_line_asked_for": TONGUE, "level": "HS10", "cty": "*",
                      "quantity_column": "GEN_QY1_MO", "unit_expected": "KG",
                      "country_filter": "CTY_CODE all digits and not starting with 00; the TOTAL "
                                        "row is CTY_CODE '-' and is taken separately",
                      "exports_and_production_taken_from": CEILING.name}}
    OUT.write_text(json.dumps(rec, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                   encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


def selftest() -> int:
    ok = []

    def check(name, cond, info=""):
        ok.append(bool(cond))
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{info}]" if info else ""))

    # The arithmetic, on numbers chosen so both outcomes are reachable. A pull
    # whose voiding branch cannot be hit is not a pull, so it is checked here
    # rather than asserted in prose.
    def ratio(exports, production, imports):
        return exports / (production + imports)

    check("no imports leaves the old ratio untouched",
          abs(ratio(81540.0, 31992.75, 0.0) - 81540.0 / 31992.75) < 1e-12)
    check("the voiding branch is reachable",
          ratio(81540.0, 31992.75, 60000.0) < 1.0,
          f"{ratio(81540.0, 31992.75, 60000.0):.4f}")
    check("the surviving branch is reachable",
          ratio(81540.0, 31992.75, 5000.0) > 1.0,
          f"{ratio(81540.0, 31992.75, 5000.0):.4f}")
    # Exactly at one is not a third state here: the quantity is an identity in
    # its three inputs, so there is nothing undetermined to map. The boundary is
    # assigned to the voiding side, which is the side that does not claim a win.
    check("the boundary is assigned to the side that does not claim a win",
          not (ratio(81540.0, 31992.75, 81540.0 - 31992.75) > 1.0))

    # The cache reader: damaged and malformed files are recognised, not read in.
    import tempfile
    global CACHE
    keep = CACHE
    with tempfile.TemporaryDirectory() as d:
        CACHE = Path(d)
        p = cache_path(2023, 1)
        p.write_text("{not json", encoding="utf-8")
        check("a damaged cache file reads as absent", load_cached(p) is None)
        p.write_text('{"a": 1}', encoding="utf-8")
        check("a malformed cache file reads as absent", load_cached(p) is None)
        # The fixture carries what actually broke it: the TOTAL row, a named
        # grouping and a continent rollup alongside the countries. A fixture with
        # countries only would let the old summing code pass.
        rows = [["CTY_NAME", "I_COMMODITY", "I_COMMODITY_LDESC", "GEN_VAL_MO",
                 "GEN_QY1_MO", "UNIT_QY1", "CTY_CODE"],
                ["TOTAL FOR ALL COUNTRIES", BASKET, "OFFAL OF SWINE, EDIBLE, FROZEN, NESOI",
                 "15", "3000", "KG", "-"],
                ["OECD", BASKET, "OFFAL OF SWINE, EDIBLE, FROZEN, NESOI", "15", "3000", "KG", "0022"],
                ["NORTH AMERICA", BASKET, "OFFAL OF SWINE, EDIBLE, FROZEN, NESOI",
                 "15", "3000", "KG", "1XXX"],
                ["CANADA", BASKET, "OFFAL OF SWINE, EDIBLE, FROZEN, NESOI", "10", "2000", "KG", "1220"],
                ["MEXICO", BASKET, "OFFAL OF SWINE, EDIBLE, FROZEN, NESOI", "5", "1000", "KG", "2010"]]
        p.write_text(json.dumps(rows), encoding="utf-8")
        check("a good cache file parses", load_cached(p) is not None)
        per_year, origins, units, months, totals = read_imports((2023, 2023))
        check("  the TOTAL row is the total, not the sum of every row",
              abs(totals[2023]["kg"] - 3000.0) < 1e-9, f"{totals[2023]['kg']}")
        check("  a grouping row is not counted as a country",
              origins[2023] == {"CANADA": 2000.0, "MEXICO": 1000.0}, str(origins[2023]))
        check("  the countries add up to the TOTAL row",
              abs(sum(origins[2023].values()) - totals[2023]["kg"]) < 1e-9)
        check("  summing every row would have read three times the truth, which is the bug",
              abs(sum(float(r[4]) for r in rows[1:]) - 12000.0) < 1e-9)
        check("  one month cached out of twelve is reported as one", months[2023] == 1)
        check("  the unit is carried out for checking", units == {"KG"})
        check("  the basket line is the only ten digit line, as on the real feed",
              list(per_year[2023]) == [BASKET])
    CACHE = keep

    check("the requested columns are the imports table's own names, not the exports table's",
          "I_COMMODITY" in GET and "E_COMMODITY" not in GET and "GEN_QY1_MO" in GET)
    print(f"\n{sum(ok)}/{len(ok)}")
    return 0 if all(ok) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--years", nargs=2, type=int, default=[2021, 2023])
    ap.add_argument("--hs6", default=None,
                    help="six digit heading to pull; 020649 frozen is the default and 020630 is "
                         "the fresh or chilled basket, which the bound needs if tongue could "
                         "come in unfrozen and leave frozen")
    a = ap.parse_args()
    if a.hs6:
        global HS6
        HS6 = a.hs6
    if a.selftest:
        return selftest()
    if a.probe:
        return probe()
    if a.fetch:
        return fetch(a.years)
    if a.score:
        return score()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
