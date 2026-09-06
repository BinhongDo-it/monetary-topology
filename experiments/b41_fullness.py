"""B41-5: how the second difference behaves when the storage is full.

The design asks for the second difference printed separately for positions whose
inventory sits near published capacity and positions whose does not, two groups,
not merged. The facility level version of that split is not available
retrospectively for free: the exchange publishes registered stocks and
deliverable quantities as a current snapshot only, with history behind a paid
product. What is available, free and with history, is the state level: the NASS
Grain Stocks survey publishes off-farm stocks and the capacity of off-farm
storage facilities, by state, four times a year.

So the split this file builds is over time rather than over space. A state's
fullness is one number per quarter shared by every position in it, so it says
when the state was full, not which elevator was. That is a narrower reading than
the design's words and it is the one the free data supports.

Three modes, each small enough to read the output of before running the next.

    python experiments/b41_fullness.py --params commodity_desc
    python experiments/b41_fullness.py --probe
    python experiments/b41_fullness.py --split --report 3186 3225 2886

Key resolution: NASS_API_KEY in the environment, then `../.nass_api_key` beside
the repository. The key is never written into this file and never printed.
Every response is cached and validated; a cache entry that fails to parse is
renamed aside rather than removed.
"""

from __future__ import annotations

import argparse
import io
import json
import contextlib
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b41_joint as J  # noqa: E402
import b41_known_answer as K  # noqa: E402
import b41_persistence as P  # noqa: E402

BASE = "https://quickstats.nass.usda.gov/api"
REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "data" / "b41" / "nass_cache"
OUT = REPO / "data" / "b41"

STATES = {3186: "SD", 3225: "NE", 2851: "OH", 2886: "KS",
          3878: "ND", 2932: "MO", 3100: "OK", 3192: "IL"}


def api_key() -> str:
    env = os.environ.get("NASS_API_KEY")
    if env:
        return env.strip()
    for c in (REPO.parent / ".nass_api_key", REPO / "data" / ".nass_api_key"):
        if c.exists():
            return c.read_text(encoding="utf-8").strip()
    sys.exit("No API key. Set NASS_API_KEY, or put the key in a file named "
             ".nass_api_key beside the repository. It is free from "
             "quickstats.nass.usda.gov/api and never goes in a tracked file.")


def slug(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s)[:150]


def get(endpoint: str, params: dict, key: str, pause: float = 0.5):
    CACHE.mkdir(parents=True, exist_ok=True)
    tag = "&".join(f"{k}={params[k]}" for k in sorted(params))
    hit = CACHE / f"{slug(endpoint)}__{slug(tag)}.json"
    if hit.exists():
        try:
            return json.loads(hit.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            aside = hit.with_suffix(f".corrupt.{int(time.time())}.json")
            hit.rename(aside)
            print(f"    cache entry did not parse, set aside as {aside.name}")
    q = dict(params); q["key"] = key
    url = f"{BASE}/{endpoint}/?" + urllib.parse.urlencode(q)
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                payload = json.loads(r.read().decode("utf-8"))
            tmp = hit.with_suffix(".part")
            tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, hit)
            time.sleep(pause)
            return payload
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:300]
            if exc.code in (401, 403):
                sys.exit(f"HTTP {exc.code}: the key was rejected. {body}")
            if exc.code == 400:
                return {"error": [body]}          # the API says why in the body
            last = exc
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
            last = exc
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{endpoint} failed four times: {last}")


# ------------------------------------------------------------ mode: params

def mode_params(field: str, filters: list[str], key: str) -> None:
    """Enumerate a parameter's values before selecting from it."""
    params = {"param": field}
    for f in filters:
        k, _, v = f.partition("=")
        params[k] = v
    payload = get("get_param_values", params, key)
    vals = payload.get(field) or payload.get("error") or payload
    if isinstance(vals, list):
        print(f"{field}: {len(vals)} values")
        for v in vals:
            print("   ", v)
    else:
        print(json.dumps(payload, ensure_ascii=False)[:2000])


# ------------------------------------------------------------- mode: probe

# Enumerated on 2026-09-02 rather than guessed. Corn stocks come back as three
# short descriptions, "CORN, GRAIN", "CORN, ON FARM, GRAIN" and "CORN, OFF FARM,
# GRAIN", so the on-farm and off-farm split does not live in prodn_practice_desc,
# which was the first guess and was wrong. Rather than work out which parameter
# holds it and guess again for each commodity, the query asks for the whole
# statistic and the split is made here on the short description. Capacity is its
# own commodity, GRAIN STORAGE CAPACITY, which the same enumeration confirmed.
STOCK_COMMODITIES = ["CORN", "SOYBEANS", "WHEAT", "SORGHUM", "OATS", "BARLEY"]
CAPACITY_COMMODITY = "GRAIN STORAGE CAPACITY"


def is_off_farm(row: dict) -> bool:
    """OFF FARM has to be the token straight after the commodity.

    North Dakota also reports "WHEAT, SPRING, DURUM, OFF FARM", which is a
    subset of "WHEAT, OFF FARM"; a plain substring test would add it a second
    time and inflate that state's numerator."""
    d = row.get("short_desc") or ""
    c = row.get("commodity_desc") or ""
    return d.startswith(f"{c}, OFF FARM")


def pull(key: str, state: str, y0: int, commodity: str, cat: str) -> list[dict]:
    payload = get("api_GET", dict(source_desc="SURVEY", agg_level_desc="STATE",
                                  state_alpha=state, commodity_desc=commodity,
                                  statisticcat_desc=cat, year__GE=str(y0),
                                  format="JSON"), key)
    return payload.get("data") or []


def mode_probe(key: str, states: list[str], y0: int) -> None:
    """Pull the superset and print what came back, including every short
    description, so the selection is made against a printed list."""
    seen_desc: dict[str, int] = defaultdict(int)
    print(f"{'state':<7}{'commodity':<22}{'rows':>7}{'off-farm':>10}{'years':>16}")
    print("-" * 64)
    for st in states:
        for com in STOCK_COMMODITIES:
            rows = pull(key, st, y0, com, "STOCKS")
            off = [r for r in rows if is_off_farm(r)]
            for r in rows:
                seen_desc[r.get("short_desc") or ""] += 1
            yrs = sorted({r.get("year") for r in off})
            span = f"{yrs[0]}..{yrs[-1]}" if yrs else ""
            print(f"{st:<7}{com:<22}{len(rows):>7}{len(off):>10}{span:>16}")
        rows = pull(key, st, y0, CAPACITY_COMMODITY, "CAPACITY")
        off = [r for r in rows if is_off_farm(r)]
        for r in rows:
            seen_desc[r.get("short_desc") or ""] += 1
        yrs = sorted({r.get("year") for r in off})
        span = f"{yrs[0]}..{yrs[-1]}" if yrs else ""
        print(f"{st:<7}{'GRAIN STORAGE CAPACITY':<22}{len(rows):>7}{len(off):>10}{span:>16}")
    print("\nevery short description that came back, with its row count:")
    for d, n in sorted(seen_desc.items()):
        mark = "  <- off farm" if "OFF FARM" in d else ""
        print(f"  {n:>6}  {d}{mark}")
    print("\nreference periods present:")
    per = defaultdict(int)
    for f in sorted(CACHE.glob("api_GET__*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")).get("data") or []:
            per[r.get("reference_period_desc")] += 1
    for k, v in sorted(per.items(), key=lambda kv: -kv[1]):
        print(f"  {v:>6}  {k}")


# ------------------------------------------------------------- mode: split

def fullness_table(verbose: bool = True) -> dict:
    """(state, year, reference period) -> off-farm stocks / off-farm capacity.

    Stocks are summed over whichever grains the state reports; capacity is a
    single all-grain figure. The contributing commodities are printed so the
    denominator and the numerator can be seen to cover the same thing."""
    stocks: dict = defaultdict(float)
    parts: dict = defaultdict(set)
    cap: dict = {}
    for f in sorted(CACHE.glob("api_GET__*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")).get("data") or []:
            if not is_off_farm(r):
                continue
            try:
                v = float(str(r.get("Value", "")).replace(",", ""))
            except ValueError:
                continue
            k = (r.get("state_alpha"), r.get("year"), r.get("reference_period_desc"))
            if r.get("statisticcat_desc") == "STOCKS":
                stocks[k] += v
                parts[k].add(r.get("commodity_desc"))
            elif "CAPACITY" in (r.get("statisticcat_desc") or ""):
                cap[(k[0], k[1])] = v
    # Capacity is annual and the last year published is 2025, so a day in 2026
    # is matched to the most recent capacity the state has. That is an
    # assumption about a slow moving quantity and it is printed, not hidden.
    out, carried = {}, 0
    for k, s in stocks.items():
        c = cap.get((k[0], k[1]))
        if c is None:
            yrs = sorted(y for (st, y) in cap if st == k[0] and y <= k[1])
            if yrs:
                c = cap[(k[0], yrs[-1])]
                carried += 1
        if c:
            out[k] = s / c
    if verbose and carried:
        print(f"  {carried} state-quarters used the most recent earlier "
              f"capacity because the year they fall in is not published yet")
    if verbose and out:
        n = defaultdict(int)
        for k in out:
            n[k[0]] += 1
        print("  fullness points per state:",
              "  ".join(f"{a}:{b}" for a, b in sorted(n.items())))
        any_k = next(iter(out))
        print(f"  commodities summed into the numerator, e.g. {any_k}: "
              f"{sorted(parts[any_k])}")
    return out


def mode_split(reports: list[int]) -> None:
    full = fullness_table()
    if not full:
        sys.exit("No fullness numbers cached yet. Run --probe first, and check "
                 "that both the stocks and the capacity series came back.")
    print(f"{len(full)} state-quarter fullness values on disk")
    for rid in reports:
        st = STATES.get(rid, "?")
        with contextlib.redirect_stdout(io.StringIO()):
            by_day = P.load_all(rid)
        per = {d: J.day_cells(r) for d, r in by_day.items()}
        per = {d: c for d, c in per.items() if c}
        got = K.rectangle(per, 0.60)
        if got is None:
            print(f"{st}: no rectangle"); continue
        _, coms, poss = got
        need = {(c, p) for c in coms for p in poss}
        df = (len(poss) - 1) * (len(coms) - 1)
        groups = defaultdict(list)
        for d, cells in per.items():
            if not need <= set(cells):
                continue
            mat = np.array([[cells[(c, p)] for p in poss] for c in coms])
            r, _, _ = J.additive_residual(mat, np.ones_like(mat, dtype=bool))
            # the most recent quarterly reading as of that day
            m, y = int(d[:2]), int(d[6:])
            # the strings are FIRST OF MAR and so on, read off the probe
            if m == 12:
                ref, yr = "FIRST OF DEC", y
            elif m in (1, 2):
                ref, yr = "FIRST OF DEC", y - 1
            elif m in (3, 4, 5):
                ref, yr = "FIRST OF MAR", y
            elif m in (6, 7, 8):
                ref, yr = "FIRST OF JUN", y
            else:
                ref, yr = "FIRST OF SEP", y
            # the API returns year as an integer, so the key is an integer
            f = full.get((st, yr, ref))
            if f is None:
                groups["unmatched"].append(r)
            else:
                groups[f].append(r)
        vals = [k for k in groups if k != "unmatched"]
        if not vals:
            print(f"{st}: no day matched a fullness value"); continue
        med = float(np.median(vals))
        hi = np.stack([x for k in vals if k >= med for x in groups[k]])
        lo = np.stack([x for k in vals if k < med for x in groups[k]])
        f_hi = float(np.linalg.norm(hi.mean(0)) / np.sqrt(df))
        f_lo = float(np.linalg.norm(lo.mean(0)) / np.sqrt(df))
        print(f"\n{st}: fullness median {med:.3f}; "
              f"{len(hi)} days at or above it, {len(lo)} below, "
              f"{len(groups['unmatched'])} unmatched")
        print(f"   persistent residual, full quarters  : {f_hi:6.2f} cents per cycle")
        print(f"   persistent residual, slack quarters : {f_lo:6.2f} cents per cycle")
        print("   two groups, printed separately, not merged")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--params", metavar="FIELD")
    ap.add_argument("--filters", nargs="*", default=[], metavar="K=V")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--split", action="store_true")
    ap.add_argument("--report", type=int, nargs="+",
                    default=[3186, 3225, 2851, 2886, 3878, 2932, 3100])
    ap.add_argument("--states", nargs="+",
                    default=["SD", "NE", "OH", "KS", "ND", "MO", "OK", "IL"])
    ap.add_argument("--from-year", type=int, default=2019)
    a = ap.parse_args()
    if a.split:
        return mode_split(a.report)
    key = api_key()
    if a.params:
        return mode_params(a.params, a.filters, key)
    if a.probe:
        return mode_probe(key, a.states, a.from_year)
    ap.print_help()


if __name__ == "__main__":
    main()
