"""B126 squares: does a house's price premium depend on the vintage it sells?

Reads data/b126/parsed/ and writes results/b126_squares.json. Uses the lot cleaning of
experiments/b126_readings.py.

The rival, written as a premise and its consequence (`11e` fifth part):
  premise     a lot's price is the wine's value plus a level for the house that sells it, one
              number per house (a scalar field on houses)
  entailment  for two vintages u, v and two houses A, B in one quarter, the square
                  S = [p(u,A) - p(u,B)] - [p(v,A) - p(v,B)]
              is zero: the house levels cancel and so do the vintages' values
The framework says the square is not zero: each house carries its own paths to a given vintage
(its last hammer, its specialist's estimate, its reserve), and the number of those paths is not
the same on every vintage. That is a point prediction against a point prediction, so the square
can carry a `rival` criterion (`11e` sixth part).

Objects:
  cell    one quarter, one unit (wine x vintage), one house: the lots in it
  square  two units and two houses of one quarter, all four cells present. Its price in each
          cell is one lot drawn at random, so every square is built from four single lots
  floor   the same statistic on pseudo-squares whose two houses are one house: from a cell with
          two lots or more, the two lots drawn apart play A1 and A2. Under any model the true
          value is zero, so the pseudo-square's spread is lot noise plus in-quarter timing
  loops   the independent cycles of each quarter's unit x house graph, b1 = E - V + C (`D22`);
          squares are counted and printed, and their number is not the number of loops

Draws: DRAWS random draws of the lots; each statistic is the median over draws.

Knobs, scanned (`11f`): SIZES (750 ml only, or all), CLEAN (0, 3).
Scope is not a knob: Yquem alone (the densest wine) and all wines are two objects, read apart as
B126-12y and B126-12. A first version scanned scope with the knobs, which folded the difference
between them, the reading itself, into "the sign moves".

Criteria (`11d`):
  B126-11  instrument   the floor exists: pseudo-squares on every scan point
  B126-12  rival        the separable house level, all wines: median |S| of real squares over the
                        median |S| of pseudo-squares. Polarity per `11e` first part, second clause: PASS means
                        the rival's point prediction fails (squares read above the floor at
                        every scan point); FAIL means it holds (at or under the floor at every
                        point); moving across the scan is no verdict
  B126-12y own_reading  Yquem alone, the densest wine: the framework expects the squares on the floor
                        there (both houses have many paths to every vintage), the rival expects the
                        same, so it carries no rival criterion (`11e` sixth part)
A scan point reads above the floor when the ratio's 5th percentile over 500 resamples of whole
quarters clears 1, and on it when the 5-95 band holds 1.
  B126-12a rival        as B126-12, squares whose two vintages are of one wine
  B126-12b rival        as B126-12, squares across two wines (a house's taste for one estate
                        over another can make these non-zero with no path in it)
  B126-14  own_reading  inside one wine: each unit's median |S| over the squares it sits in,
                        rank-correlated with its density; negative is the framework's reading.
                        The same statistic on the pseudo-squares is printed beside it: if the
                        floor falls with density as steeply, the reading is lot noise
  B126-13  bookkeeping  loops (b1), squares and cells per quarter printed

Run from the repo root:
    python experiments/b126_squares.py
    python experiments/b126_squares.py --selftest
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b126_readings as R  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

OUT = R.ROOT / "results" / "b126_squares.json"
YQUEM = "chateau-dyquem-premier-cru-superieur-sauternes"
SCAN = {"sizes": ["750", "all"], "clean": [0.0, 3.0], "scope": ["yquem", "all"]}
DEFAULT = {"sizes": "750", "clean": 3.0, "scope": "all"}
DRAWS = 50


def cells(lots: list[dict], cfg: dict) -> dict:
    """(quarter, unit, house) -> list of log prices per 750 ml."""
    out: dict = {}
    for l in R.clean_lots(lots, cfg["clean"]):
        if l["slug"] in R.EXCLUDE or l["format_conflict"] or not l.get("own_750_usd"):
            continue
        if cfg["sizes"] == "750" and l["format_ml"] != 750:
            continue
        if cfg["scope"] == "yquem" and l["slug"] != YQUEM:
            continue
        dd = R.d(l["date"])
        q = f"{dd.year}Q{(dd.month - 1) // 3 + 1}"
        out.setdefault((q, (l["slug"], l["vintage"]), l["house"]), []).append(math.log(l["own_750_usd"]))
    return out


def by_quarter(c: dict) -> dict:
    out: dict = {}
    for (q, u, h), ps in c.items():
        out.setdefault(q, {}).setdefault(u, {})[h] = ps
    return out


def loops(units: dict) -> int:
    parent: dict = {}

    def f(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    E = 0
    for u, hs in units.items():
        for h in hs:
            E += 1
            parent[f(("u", u))] = f(("h", h))
    V = len(units) + len({h for hs in units.values() for h in hs})
    C = len({f(("u", u)) for u in units})
    return E - V + C


def square_index(bq: dict) -> list[tuple]:
    """Every (quarter, u, v, A, B) with all four cells present."""
    out = []
    for q, units in sorted(bq.items()):
        for a, b in itertools.combinations(sorted(units), 2):
            for h1, h2 in itertools.combinations(sorted(set(units[a]) & set(units[b])), 2):
                out.append((q, a, b, h1, h2))
    return out


def pseudo_index(bq: dict) -> list[tuple]:
    """Every (quarter, u, v, house) where both units have two lots or more at that house."""
    out = []
    for q, units in sorted(bq.items()):
        for a, b in itertools.combinations(sorted(units), 2):
            for h in sorted(set(units[a]) & set(units[b])):
                if len(units[a][h]) >= 2 and len(units[b][h]) >= 2:
                    out.append((q, a, b, h))
    return out


def draw_stats(bq: dict, sq: list, ps: list, rng: random.Random) -> tuple[list[float], list[float]]:
    real = []
    for q, a, b, h1, h2 in sq:
        U = bq[q]
        real.append(abs((rng.choice(U[a][h1]) - rng.choice(U[a][h2])) - (rng.choice(U[b][h1]) - rng.choice(U[b][h2]))))
    fake = []
    for q, a, b, h in ps:
        U = bq[q]
        a1, a2 = rng.sample(U[a][h], 2)
        b1, b2 = rng.sample(U[b][h], 2)
        fake.append(abs((a1 - a2) - (b1 - b2)))
    return real, fake


BOOT = 500


def bootstrap_ratio(sq: list, ps: list, real: list[float], fake: list[float], rng: random.Random) -> list[float]:
    """The ratio's own resolution: quarters resampled with replacement, the squares and
    pseudo-squares of each drawn quarter taken whole (squares inside a quarter share cells)."""
    qs = sorted({x[0] for x in sq} | {x[0] for x in ps})
    rq: dict = {}
    fq: dict = {}
    for x, v in zip(sq, real):
        rq.setdefault(x[0], []).append(v)
    for x, v in zip(ps, fake):
        fq.setdefault(x[0], []).append(v)
    out = []
    for _ in range(BOOT):
        pick = [rng.choice(qs) for _ in qs]
        r = [v for q in pick for v in rq.get(q, [])]
        f = [v for q in pick for v in fq.get(q, [])]
        if r and f and st.median(f) > 0:
            out.append(st.median(r) / st.median(f))
    return out


def keep_pair(a: tuple, b: tuple, pair: str) -> bool:
    """pair: "any"; "same_wine" (two vintages of one wine); "cross_wine" (two wines). A square
    across wines can carry a house's taste for one estate over another, a difference between
    classes of wine that has nothing to do with paths; a square inside one wine cannot."""
    if pair == "same_wine":
        return a[0] == b[0]
    if pair == "cross_wine":
        return a[0] != b[0]
    return True


def densities(cov: list[dict], lag: int = 3) -> dict:
    """Site lots per year, the jump reading's definition at its default lag."""
    out = {}
    for c in cov:
        start = max(R.SITE_START, R.date(c["vintage"] + lag, 1, 1))
        years = max((R.FETCHED - start).days / 365.25, 0.5)
        if c.get("site_lots"):
            out[(c["slug"], c["vintage"])] = c["site_lots"] / years
    return out


def unit_rho(index: list, vals: list[float], dens: dict, min_sq: int = 3, perms: int = 2000) -> dict:
    """Each unit's median |S| over the squares it sits in, rank-correlated with its density,
    with a one-sided permutation p (density shuffled across units)."""
    per: dict = {}
    for x, v in zip(index, vals):
        for u in (x[1], x[2]):
            per.setdefault(u, []).append(v)
    us = [u for u, v in per.items() if len(v) >= min_sq and u in dens]
    if len(us) < 5:
        return {"units": len(us), "rho": None, "p": None}
    xs = [dens[u] for u in us]
    ys = [st.median(per[u]) for u in us]
    r0 = spearmanr(xs, ys).statistic
    rng = random.Random(128)
    hits = 0
    for _ in range(perms):
        sh = xs[:]
        rng.shuffle(sh)
        hits += spearmanr(sh, ys).statistic <= r0
    return {"units": len(us), "rho": float(r0), "p": (hits + 1) / (perms + 1)}


def read_once(lots: list[dict], cfg: dict, draws: int = DRAWS, dens: dict | None = None) -> dict:
    bq = by_quarter(cells(lots, cfg))
    pair = cfg.get("pair", "any")
    sq = [x for x in square_index(bq) if keep_pair(x[1], x[2], pair)]
    ps = [x for x in pseudo_index(bq) if keep_pair(x[1], x[2], pair)]
    per_q = {q: {"units": len(u), "houses": len({h for hs in u.values() for h in hs}), "loops": loops(u),
                 "squares": sum(1 for s in sq if s[0] == q), "pseudo": sum(1 for s in ps if s[0] == q)}
             for q, u in sorted(bq.items())}
    rng = random.Random(126)
    med_r, med_f, q90_f, share_over = [], [], [], []
    boot = []
    dens_real = dens_floor = None
    for i in range(draws):
        r, f = draw_stats(bq, sq, ps, rng)
        if i == 0 and r and f:
            boot = bootstrap_ratio(sq, ps, r, f, random.Random(127))
            if dens is not None:
                dens_real = unit_rho(sq, r, dens)
                dens_floor = unit_rho(ps, f, dens)
        if r and f:
            med_r.append(st.median(r))
            med_f.append(st.median(f))
            q9 = st.quantiles(f, n=10)[-1] if len(f) >= 10 else max(f)
            q90_f.append(q9)
            share_over.append(sum(x > q9 for x in r) / len(r))
    return {"cfg": cfg, "squares": len(sq), "pseudo_squares": len(ps),
            "loops": sum(v["loops"] for v in per_q.values()),
            "quarters_with_loops": sum(1 for v in per_q.values() if v["loops"] > 0),
            "median_abs_square": st.median(med_r) if med_r else None,
            "median_abs_floor": st.median(med_f) if med_f else None,
            "ratio": (st.median(med_r) / st.median(med_f)) if med_r and med_f and st.median(med_f) > 0 else None,
            "ratio_boot_5_95": [st.quantiles(boot, n=20)[0], st.quantiles(boot, n=20)[-1]] if len(boot) >= 20 else None,
            "floor_q90": st.median(q90_f) if q90_f else None,
            "share_squares_over_floor_q90": st.median(share_over) if share_over else None,
            "density_real": dens_real, "density_floor": dens_floor,
            "per_quarter": per_q}


def cell_state(x: dict) -> str | None:
    """One scan point: above the floor when the ratio's bootstrap 5th percentile clears 1; on the
    floor when the 5-95 band holds 1; under it when the 95th is below 1. A first version read
    ratio > 1, a zero-width line (rule 11), and a seeded separable world at 1.02 passed it."""
    b = x.get("ratio_boot_5_95")
    if b is None:
        return None
    if b[0] > 1:
        return "above"
    if b[1] < 1:
        return "under"
    return "on"


def scan_state(scan: list[dict]) -> str:
    cs = {cell_state(x) for x in scan}
    cs.discard(None)
    if not cs:
        return "no object"
    if cs == {"above"}:
        return "above the floor at every scan point"
    if cs <= {"on", "under"}:
        return "on or under the floor at every scan point"
    return "moves across the scan"


RIVAL_MAP = {"above the floor at every scan point": True, "on or under the floor at every scan point": False,
             "moves across the scan": None, "no object": None}
# B126-12y is the framework's own reading on the densest wine: many paths on both sides, so the
# squares sit on the floor. The mapping is the other way round.
OWN_MAP = {"above the floor at every scan point": False, "on or under the floor at every scan point": True,
           "moves across the scan": None, "no object": None}


def detail(scan: list[dict]) -> str:
    return "; ".join(f"{x['cfg']['sizes']}/c{x['cfg']['clean']:g}: |S| {x['median_abs_square']:.3f}"
                     f" floor {x['median_abs_floor']:.3f} ratio {x['ratio']:.2f}"
                     f" band {x['ratio_boot_5_95'][0]:.2f}-{x['ratio_boot_5_95'][1]:.2f}"
                     for x in scan if x["ratio"] is not None and x.get("ratio_boot_5_95"))


def rival_criterion(name: str, scope_label: str, scan: list[dict]) -> dict:
    state = scan_state(scan)
    passed = RIVAL_MAP[state]
    return {"name": name, "kind": "rival",
            "statement": f"separable house level, {scope_label}: the square of two vintages and two houses in one quarter is zero",
            "passed": passed, "state": state, "state_map": RIVAL_MAP,
            "rival_premise": "price = the wine's value + one level per house",
            "rival_entailment": "in S = [p(u,A)-p(u,B)] - [p(v,A)-p(v,B)] the house levels and the values cancel, so S = 0",
            "rival_shape": "point",
            "grid": "B" if passed is True else ("C" if passed is False else "unread"),
            "detail": detail(scan)}


def own_criterion(name: str, scope_label: str, scan: list[dict]) -> dict:
    state = scan_state(scan)
    return {"name": name, "kind": "own_reading",
            "statement": f"{scope_label}, the densest wine: the squares sit on the floor (both houses have many paths to every vintage)",
            "passed": OWN_MAP[state], "state": state, "state_map": OWN_MAP, "detail": detail(scan)}


DENSITY_MAP = {"negative at every scan point": True, "positive at every scan point": False,
               "sign moves across the scan": None, "no object": None}


def density_state(rs: list) -> str:
    sg = {None if r is None else (r > 0) - (r < 0) for r in rs}
    sg.discard(None)
    if not sg:
        return "no object"
    if sg == {-1}:
        return "negative at every scan point"
    if sg == {1}:
        return "positive at every scan point"
    return "sign moves across the scan"


def read(lots: list[dict], draws: int = DRAWS, cov: list[dict] | None = None) -> dict:
    dens = densities(cov) if cov else None
    scan = [read_once(lots, {"sizes": s, "clean": c, "scope": sc, "pair": "any"}, draws, dens)
            for s, c, sc in itertools.product(SCAN["sizes"], SCAN["clean"], SCAN["scope"])]
    split = [read_once(lots, {"sizes": s, "clean": c, "scope": "all", "pair": pr}, draws, dens)
             for s, c, pr in itertools.product(SCAN["sizes"], SCAN["clean"], ("same_wine", "cross_wine"))]
    same = [x for x in split if x["cfg"]["pair"] == "same_wine"]
    cross = [x for x in split if x["cfg"]["pair"] == "cross_wine"]

    def dens_detail(xs):
        out = []
        for x in xs:
            dr, df = x.get("density_real") or {}, x.get("density_floor") or {}
            if dr.get("rho") is not None:
                fl = f"{df['rho']:+.3f} (n={df['units']})" if df.get("rho") is not None else "n/a"
                out.append(f"{x['cfg']['sizes']}/c{x['cfg']['clean']:g}: squares {dr['rho']:+.3f} (n={dr['units']}, p {dr['p']:.3f}),"
                           f" floor {fl}")
        return "; ".join(out)

    d_same = density_state([(x.get("density_real") or {}).get("rho") for x in same])
    crit = [
        {"name": "B126-11", "kind": "instrument",
         "statement": "the floor exists: pseudo-squares from one house's lots on every scan point",
         "passed": all(s["pseudo_squares"] > 0 for s in scan),
         "detail": ", ".join(f"{s['cfg']['scope']}/{s['cfg']['sizes']}/c{s['cfg']['clean']:g} {s['pseudo_squares']}" for s in scan)},
        rival_criterion("B126-12", "all wines", [s for s in scan if s["cfg"]["scope"] == "all"]),
        own_criterion("B126-12y", "Yquem alone", [s for s in scan if s["cfg"]["scope"] == "yquem"]),
        rival_criterion("B126-12a", "all wines, squares inside one wine", same),
        rival_criterion("B126-12b", "all wines, squares across two wines", cross),
        {"name": "B126-14", "kind": "own_reading",
         "statement": "inside one wine, a unit's median |square| rank-correlates negatively with its density (thinner units carry larger squares)",
         "passed": DENSITY_MAP[d_same], "state": d_same, "state_map": DENSITY_MAP,
         "detail": dens_detail(same) + " | across wines: " + dens_detail(cross)},
        {"name": "B126-13", "kind": "bookkeeping",
         "statement": "loops (b1), squares and pseudo-squares per quarter printed",
         "passed": all(s["per_quarter"] for s in scan),
         "detail": ", ".join(f"{s['cfg']['scope']}/{s['cfg']['sizes']}/c{s['cfg']['clean']:g} loops {s['loops']} squares {s['squares']}" for s in scan)},
    ]
    return {"scan": scan, "split": split, "criteria": crit}


def report(r: dict) -> None:
    print("scope / sizes / clean: loops (b1), quarters, squares, pseudo-squares, median |S| real vs floor, ratio, share of real squares over the floor's 90th percentile")
    for s in r["scan"]:
        c = s["cfg"]
        rt = f"{s['ratio']:.2f}" if s["ratio"] is not None else "n/a"
        mr = f"{s['median_abs_square']:.3f}" if s["median_abs_square"] is not None else "n/a"
        mf = f"{s['median_abs_floor']:.3f}" if s["median_abs_floor"] is not None else "n/a"
        so = f"{s['share_squares_over_floor_q90']:.2f}" if s["share_squares_over_floor_q90"] is not None else "n/a"
        bd = f"{s['ratio_boot_5_95'][0]:.2f}-{s['ratio_boot_5_95'][1]:.2f}" if s.get("ratio_boot_5_95") else "n/a"
        print(f"  {c['scope']:>5} {c['sizes']:>3} c{c['clean']:g}  loops {s['loops']:>4} in {s['quarters_with_loops']:>2} quarters"
              f"  squares {s['squares']:>5}  pseudo {s['pseudo_squares']:>4}  |S| {mr} vs {mf}  ratio {rt} [{bd}]  over q90 {so}")
    print("\nsquares split, all wines: pair / sizes / clean: squares, pseudo, ratio [band], density rho real (n, p) vs floor")
    for s in r.get("split", []):
        c = s["cfg"]
        bd = f"{s['ratio_boot_5_95'][0]:.2f}-{s['ratio_boot_5_95'][1]:.2f}" if s.get("ratio_boot_5_95") else "n/a"
        dr, df = s.get("density_real") or {}, s.get("density_floor") or {}
        dtxt = (f"{dr['rho']:+.3f} (n={dr['units']}, p {dr['p']:.3f})" if dr.get("rho") is not None else "n/a")
        ftxt = (f"{df['rho']:+.3f} (n={df['units']})" if df.get("rho") is not None else "n/a")
        rt = f"{s['ratio']:.2f}" if s["ratio"] is not None else "n/a"
        print(f"  {c['pair']:>10} {c['sizes']:>3} c{c['clean']:g}  squares {s['squares']:>5} pseudo {s['pseudo_squares']:>4}"
              f"  ratio {rt} [{bd}]  density {dtxt} vs floor {ftxt}")
    d = next(s for s in r["scan"] if all(s["cfg"][k] == v for k, v in DEFAULT.items()))
    print("\nper quarter, default (units, houses, loops, squares, pseudo):")
    for q, v in d["per_quarter"].items():
        if v["loops"]:
            print(f"  {q}  {v['units']:>3} {v['houses']:>2} {v['loops']:>3} {v['squares']:>4} {v['pseudo']:>4}")
    print("\ncriteria")
    for c in r["criteria"]:
        print(f"  {c['name']:8} {c['kind']:12} {c['passed']!s:5}  {c.get('state', '')}")
    print(f"state maps (`11c`): rival {RIVAL_MAP}; own {OWN_MAP}")


def run() -> int:
    lots = json.loads((R.PARSED / "lots.json").read_text(encoding="utf-8"))
    cov = json.loads((R.PARSED / "coverage.json").read_text(encoding="utf-8"))
    r = read(lots, cov=cov)
    report(r)
    rec = {"stage": "B126", "arm": "squares",
           "config": {"default": DEFAULT, "scan": SCAN, "draws": DRAWS, "seed": 126, "exclude": R.EXCLUDE,
                      "source": "data/b126/parsed/ via experiments/b126_parse.py"},
           **R.rnd(r)}
    OUT.write_text(json.dumps(rec, sort_keys=True, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"\nwritten: {OUT}")
    return 0


def selftest() -> int:
    """Seeded worlds (`11f`): a separable world must not read above the floor; a world where one
    house's premium depends on the vintage must."""
    def world(premium):
        rnd = random.Random(3)
        lots = []
        for q in range(8):
            day = f"2025-{1 + 3 * (q % 4):02d}-10" if q < 4 else f"2026-{1 + 3 * (q % 4):02d}-10"
            for v in range(2000, 2008):
                value = 5 + 0.1 * (v - 2000)
                for h, lvl in (("a", 0.0), ("b", 0.2), ("c", -0.1)):
                    for _ in range(3):
                        p = value + lvl + premium(h, v) + rnd.gauss(0, 0.03)
                        lots.append({"slug": "w", "vintage": v, "date": day, "house": h, "format_ml": 750,
                                     "format_conflict": False, "own_750_usd": math.exp(p)})
        return lots

    checks = []
    R._CLEAN_CACHE.clear()
    r = read(world(lambda h, v: 0.0), draws=10)
    c = {x["name"]: x for x in r["criteria"]}
    checks.append(("separable world: B126-12 not PASS", c["B126-12"]["passed"] is not True))
    sep = [x for x in r["scan"] if x["cfg"]["scope"] == "all"]
    checks.append(("separable world: every all-wines point reads on the floor", all(cell_state(x) == "on" for x in sep)))
    checks.append(("a world with no Yquem: B126-12y has no object and no verdict",
                   c["B126-12y"]["passed"] is None and c["B126-12y"]["state"] == "no object"))
    R._CLEAN_CACHE.clear()
    r = read(world(lambda h, v: 0.3 * ((v % 3) - 1) if h == "b" else 0.0), draws=10)
    c = {x["name"]: x for x in r["criteria"]}
    # the Yquem scope has no Yquem in a seeded world, so it carries no object; read the all-wines points
    pts = [s for s in r["scan"] if s["cfg"]["scope"] == "all"]
    checks.append(("vintage-dependent premium: squares read above the floor on every all-wines point",
                   all(s["ratio"] is not None and s["ratio"] > 1.5 for s in pts)))
    checks.append(("vintage-dependent premium: B126-12 PASS, grid B", c["B126-12"]["passed"] is True and c["B126-12"]["grid"] == "B"))
    checks.append(("a quarter with two units and two houses both present has one loop",
                   loops({"u": {"a": [1], "b": [1]}, "v": {"a": [1], "b": [1]}}) == 1))
    checks.append(("a tree has no loop", loops({"u": {"a": [1], "b": [1]}, "v": {"a": [1]}}) == 0))
    R._CLEAN_CACHE.clear()
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(ok for _, ok in checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    return selftest() if ap.parse_args().selftest else run()


if __name__ == "__main__":
    sys.exit(main())
