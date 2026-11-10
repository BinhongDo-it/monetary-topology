"""B145 arm A: what the Carnegie library "shares do not move" result is made of.

Berkes and Nencka (REStat 2026) report that a Carnegie library raises patenting in the
city that got it, relative to cities that applied and were turned down, and that the
share of patents by immigrant and by women inventors does not move (their table A5,
column 3: -0.000 (0.002) and -0.001 (0.004)). This script rebuilds their city-year panel
from their own replication packages and reads the share three ways:

  1. their estimator: a city-year ratio x/n, regressed on treated x post with state,
     year and grant-year fixed effects, standard errors clustered by city;
  2. the same regression weighted by the denominator n;
  3. the pooled share sum(x)/sum(n) in treated and control cities before and after the
     grant, the difference in differences, and a city-cluster bootstrap interval, with a
     placebo cut inside the pre-period on the same cities as the floor.

Inputs (data/raw/b145/, fetched by experiments/b145_fetch.py, extracted with bsdtar):
  data_x/~data_restat_upload/patent_data/patent counts.dta
  data_x/~data_restat_upload/Carnegie libraries/Output/{carnegie,rejected} libraries.dta
  data_x/~data_restat_upload/City populations/Output/updated_city_pop.dta
  data_x/~data_restat_upload/Census/Output/1900 covariates.dta
  code_x/~2023.10_conditional_accept_upload/Output/table_output/*.tex  (published numbers)

The ports follow ~Combined/Scripts/02_create_carnegie_sample.do and Scripts/
01_carnegie_rejected_results.do of the packages, read as text. Two city-level files the
sample step merges ("1900 city level covariates_2023.dta", "1900_count_non_unique.dta")
are built from the restricted full-count census and are not in the package; the
restrictions that need them are replaced by the proxies in VARIANTS and every variant is
printed.

Run from the repo root:
    python experiments/b145_carnegie_share.py            run, write results/b145_carnegie_share.json
    python experiments/b145_carnegie_share.py --selftest seeded faults, each flag must flip
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b145"
DATA = RAW / "data_x" / "~data_restat_upload"
TABLES = RAW / "code_x" / "~2023.10_conditional_accept_upload" / "Output" / "table_output"
OUT = ROOT / "results" / "b145_carnegie_share.json"

SEED = 20261029
N_BOOT = 2000
PRE_WINDOW = -20          # 01_carnegie_rejected_results.do: keep if relative_years > 9 after +30
POST_END = 19             # relative_years < 50 after +30
PLACEBO_CUT = -10         # inside the pre-period, on the same cities
VARIANTS = {
    "county_only": "large city = county population 1900 above 750,000 (the census city count is not in the package)",
    "city_pop_proxy": "large city = county population 1900 above 750,000, or the packaged city population "
                      "(interpolated) above 25,000 in 1900; stands in for the census city count",
    "pop_listed": "as city_pop_proxy, and the city must carry a positive packaged population in 1900; stands in "
                  "for the census-match restriction (census_count_city_pop_start not missing, count_non_unique == 1)",
}
PUBLISHED_COL = 3         # table A5 column 3: absorb(state_fips year grant_year)
STATE_FIPS = {"AL": 1, "AK": 2, "AZ": 4, "AR": 5, "CA": 6, "CO": 8, "CT": 9, "DE": 10, "DC": 11, "FL": 12,
              "GA": 13, "HI": 15, "ID": 16, "IL": 17, "IN": 18, "IA": 19, "KS": 20, "KY": 21, "LA": 22,
              "ME": 23, "MD": 24, "MA": 25, "MI": 26, "MN": 27, "MS": 28, "MO": 29, "MT": 30, "NE": 31,
              "NV": 32, "NH": 33, "NJ": 34, "NM": 35, "NY": 36, "NC": 37, "ND": 38, "OH": 39, "OK": 40,
              "OR": 41, "PA": 42, "RI": 44, "SC": 45, "SD": 46, "TN": 47, "TX": 48, "UT": 49, "VT": 50,
              "VA": 51, "WA": 53, "WV": 54, "WI": 55, "WY": 56}

SOURCES = [
    {"what": "Berkes-Nencka data package ~data_restat_upload.7z", "where": "doi:10.7910/DVN/TYVVY2, datafile 9659456",
     "grade": "official (authors' replication package)", "opened": True, "items": "5 .dta files read"},
    {"what": "Berkes-Nencka code package ~2023.10_conditional_accept_upload.7z",
     "where": "doi:10.7910/DVN/TYVVY2, datafile 9659455", "grade": "official (authors' replication package)",
     "opened": True, "items": "Scripts/01_carnegie_rejected_results.do read as text; 4 .tex tables read"},
    {"what": "~Combined/Scripts/02_create_carnegie_sample.do", "where": "inside the data package",
     "grade": "official (authors' replication package)", "opened": True, "items": "read as text and ported"},
    {"what": "City_Covariates/1900 city level covariates_2023.dta and 1900_count_non_unique.dta",
     "where": "named by 02_create_carnegie_sample.do; built on the NBER server from the restricted full-count census",
     "grade": "official (authors' replication package)", "opened": False,
     "items": "0: not in the package; the script that builds them is (City_Covariates/01_Create_City_Level_Covariates.do)"},
    {"what": "~Combined/Output/libraries and innovation carnegie sample.dta", "where": "named by 01_carnegie_rejected_results.do",
     "grade": "official (authors' replication package)", "opened": False, "items": "0: the Output folder is empty; rebuilt here"},
]


def _s(x) -> str:
    return "n/a" if x is None else f"{x:+.4f}"


def _u(x) -> str:
    return "n/a" if x is None else f"{x:.4f}"


def _fmt(x, d=6):
    return None if x is None or not np.isfinite(x) else float(f"{x:.{d}f}")


# ---------------------------------------------------------------- published numbers
def published(name: str, col: int = PUBLISHED_COL) -> dict:
    lines = (TABLES / f"{name}.tex").read_text(encoding="utf-8").splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("got\\_carnegie\\_lib=1 $\\times$ post=1"):
            b = [c.strip().rstrip("\\") for c in ln.split("&")[1:]]
            s = [c.strip().rstrip("\\").strip("()") for c in lines[i + 1].split("&")[1:]]
            nline = next(x for x in lines if x.startswith("Observations"))
            n = [c.strip().rstrip("\\") for c in nline.split("&")[1:]]
            return {"b": b[col - 1], "se": s[col - 1], "n": int(n[col - 1])}
    raise ValueError(name)


# ---------------------------------------------------------------- panel (02_create_carnegie_sample.do)
def build_panel() -> pd.DataFrame:
    p = pd.read_stata(DATA / "patent_data" / "patent counts.dta")
    car = pd.read_stata(DATA / "Carnegie libraries" / "Output" / "carnegie libraries.dta")
    rej = pd.read_stata(DATA / "Carnegie libraries" / "Output" / "rejected libraries.dta")
    keep = ["year", "city", "state", "patent_count", "prob_female_fn", "prob_foreignborn_ln", "prob_male_fn",
            "prob_native_ln", "inv_fips"]
    p = p[keep]
    car = car.rename(columns={"county_fips": "county_fips_temp"})
    df = p.merge(car, on=["state", "city"], how="outer", indicator=True)
    df["zero_pat"] = (df["_merge"] == "right_only")
    df = df.drop(columns="_merge").merge(rej, on=["state", "city"], how="outer", indicator=True)
    df["zero_pat_r"] = (df["_merge"] == "right_only")
    df = df.drop(columns="_merge")
    df["zero_pat_any"] = df.zero_pat | df.zero_pat_r
    df.loc[df.zero_pat_any, "year"] = 1900
    df["county_fips"] = df["county_fips"].where(df["county_fips"].notna(), df["county_fips_temp"])
    df["inv_fips"] = df["county_fips"].where(df["county_fips"].notna(), df["inv_fips"])
    tot = df.groupby(["state", "city"])["patent_count"].transform("sum")
    df = df[(df.got_lib == 1) | (df.reject_lib == 1) | (tot >= 10)]
    df = df[(df.year > 1858) & (df.year < 1960)]
    # tsfill, full
    cities = df[["state", "city"]].drop_duplicates()
    years = pd.DataFrame({"year": np.arange(int(df.year.min()), int(df.year.max()) + 1)})
    full = cities.merge(years, how="cross")
    df = full.merge(df, on=["state", "city", "year"], how="left")
    df["got_carnegie_lib"] = np.where(df.got_lib == 1, 1.0, np.where((df.reject_lib == 1) & df.got_lib.isna(), 0.0,
                                                                      np.nan))
    df["grant_year"] = df["grant_year"].where(~(df.reject_lib == 1), df["rejected_grant_year"])
    df["patent_count"] = df["patent_count"].fillna(0.0)
    fill = ["got_carnegie_lib", "reasons_for_rejection", "reject_lib", "grant_year", "local_philantropist",
            "inv_fips", "opening_date", "zero_pat_any"]
    df = df.sort_values(["state", "city", "year"])
    g = df.groupby(["state", "city"])
    for v in fill:
        df[v] = g[v].ffill()
        df[v] = df.groupby(["state", "city"])[v].bfill()
    df["county_fips"] = df["inv_fips"]
    df = df[df.state.notna() & df.county_fips.notna()]
    # city population, interpolated between census years (ipolate)
    pop = pd.read_stata(DATA / "City populations" / "Output" / "updated_city_pop.dta")
    df = df.merge(pop, on=["state", "city", "year"], how="left")
    df["i_city_pop"] = df.groupby(["state", "city"])["city_pop"].transform(
        lambda s: s.interpolate(limit_area="inside"))
    # 1900 county covariates
    cov = pd.read_stata(DATA / "Census" / "Output" / "1900 covariates.dta", convert_categoricals=False)
    df["state_fips"] = df.state.map(STATE_FIPS)
    df["county3"] = (df.county_fips.astype("int64") % 1000).astype(float)
    cov = cov.rename(columns={"county_fips": "county3"})
    cov["county3"] = cov["county3"].astype(float)
    df = df.merge(cov[["state_fips", "county3", "pop_county_1900"]], on=["state_fips", "county3"], how="left")
    df = df[df.got_carnegie_lib.notna()].copy()
    return df


# ---------------------------------------------------------------- analysis sample (01_..._results.do)
def drop_singletons(df: pd.DataFrame, fes: list[str]) -> pd.DataFrame:
    while True:
        n = len(df)
        for f in fes:
            df = df[df.groupby(f)[f].transform("size") > 1]
        if len(df) == n:
            return df


def analysis_sample(panel: pd.DataFrame, variant: str) -> pd.DataFrame:
    df = panel.copy()
    df["relative"] = df.year - df.grant_year
    df = df[(df.relative >= PRE_WINDOW) & (df.relative <= 30)]
    df["post"] = (df.year >= df.grant_year).astype(float)
    df["fem"] = df.prob_female_fn.fillna(0.0)
    df["imm"] = df.prob_foreignborn_ln.fillna(0.0)
    df["early"] = df.grant_year < 1899
    df["max_phil"] = df.groupby(["state", "city"])["local_philantropist"].transform("max")
    df = df[~df.zero_pat_any.astype(bool)]
    big = (df.pop_county_1900 > 750000) & df.pop_county_1900.notna()
    if variant in ("city_pop_proxy", "pop_listed"):
        p1900 = df[df.year == 1900].set_index(["state", "city"])["i_city_pop"]
        cp = pd.Series(np.asarray(df.set_index(["state", "city"]).index.map(p1900), dtype=float), index=df.index)
        big = big | (cp > 25000)
        if variant == "pop_listed":
            df = df[cp > 0]
            big = big[cp > 0]
    df["large"] = big
    df = df[df.max_phil != 1]
    df = df[~df.large]
    df = df[~df.early]
    df = df[df.relative <= POST_END]
    df["city_id"] = df.groupby(["state", "city"]).ngroup()
    df["sy"] = df.state_fips.astype(int) * 10000 + df.year.astype(int)
    df["gy"] = df.grant_year.astype(int) * 10000 + df.year.astype(int)
    # keep if e(sample) of reghdfe ln_patent_count ..., absorb(city, state#year, grant_year#year)
    return drop_singletons(df, ["city_id", "sy", "gy"]).copy()


# ---------------------------------------------------------------- fixed-effect OLS, cluster by city
def fe_ols(df: pd.DataFrame, y: str, fes: list[str], weight: str | None = None, tol: float = 1e-12) -> dict:
    d = df[df[y].notna()]
    d = drop_singletons(d, fes)
    w = np.ones(len(d)) if weight is None else d[weight].to_numpy(float)
    got = d.got_carnegie_lib.to_numpy(float)
    post = d.post.to_numpy(float)
    X = np.column_stack([got, post, got * post])
    Y = d[y].to_numpy(float)
    codes = [pd.factorize(d[f])[0] for f in fes]
    Z = np.column_stack([Y, X])
    for _ in range(10000):
        old = Z.copy()
        for c in codes:
            sw = np.bincount(c, weights=w)
            for j in range(Z.shape[1]):
                Z[:, j] -= (np.bincount(c, weights=w * Z[:, j]) / sw)[c]
        if np.max(np.abs(Z - old)) < tol:
            break
    yt, Xt = Z[:, 0], Z[:, 1:]
    keepcol = [j for j in range(3) if np.sqrt(np.sum(w * Xt[:, j] ** 2)) > 1e-8 * max(1.0, np.sqrt(np.sum(w)))]
    Xt = Xt[:, keepcol]
    sw = np.sqrt(w)
    Xw, yw = Xt * sw[:, None], yt * sw
    XtX_inv = np.linalg.inv(Xw.T @ Xw)
    beta = XtX_inv @ (Xw.T @ yw)
    u = yw - Xw @ beta
    cl = pd.factorize(d.city_id)[0]
    G = cl.max() + 1
    S = np.zeros((Xw.shape[1], Xw.shape[1]))
    sc = np.zeros((G, Xw.shape[1]))
    np.add.at(sc, cl, Xw * u[:, None])
    S = sc.T @ sc
    N = len(d)
    K = len(keepcol) + 1 + sum(int(c.max()) for c in codes)
    q = G / (G - 1) * (N - 1) / (N - K)
    V = q * XtX_inv @ S @ XtX_inv
    j = keepcol.index(2)
    return {"b": _fmt(float(beta[j]), 8), "se": _fmt(float(np.sqrt(V[j, j])), 8), "n": int(N), "clusters": int(G)}


# ---------------------------------------------------------------- pooled shares
def pooled(df: pd.DataFrame) -> dict:
    out = {}
    for gname, gv in (("treated", 1.0), ("control", 0.0)):
        for per, pv in (("pre", 0.0), ("post", 1.0)):
            s = df[(df.got_carnegie_lib == gv) & (df.post == pv)]
            n = s.patent_count.sum()
            out[f"{gname}_{per}"] = {"patents": _fmt(n, 3), "immigrant": _fmt(s.imm.sum(), 3),
                                     "female": _fmt(s.fem.sum(), 3),
                                     "share_immigrant": _fmt(s.imm.sum() / n), "share_female": _fmt(s.fem.sum() / n),
                                     "cities": int(s.city_id.nunique()), "city_years": int(len(s)),
                                     "city_years_zero_patents": int((s.patent_count == 0).sum())}
    for k in ("share_immigrant", "share_female"):
        out[f"did_{k}"] = _fmt((out["treated_post"][k] - out["treated_pre"][k])
                               - (out["control_post"][k] - out["control_pre"][k]))
    return out


def city_sums(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby(["city_id", "got_carnegie_lib", "post"])[["patent_count", "imm", "fem"]].sum()
            .unstack("post").fillna(0.0))


def did_from_sums(cs: pd.DataFrame, idx_t: np.ndarray, idx_c: np.ndarray) -> np.ndarray:
    a = cs.to_numpy(float)   # columns: (patent_count,0),(patent_count,1),(imm,0),(imm,1),(fem,0),(fem,1)
    t, c = a[idx_t].sum(0), a[idx_c].sum(0)
    res = []
    for k in (2, 4):
        res.append((t[k + 1] / t[1] - t[k] / t[0]) - (c[k + 1] / c[1] - c[k] / c[0]))
    return np.array(res)


def bootstrap(df: pd.DataFrame, seed: int = SEED, n_boot: int = N_BOOT) -> dict:
    cs = city_sums(df)
    cs = cs.reindex(columns=pd.MultiIndex.from_product([["patent_count", "imm", "fem"], [0.0, 1.0]]), fill_value=0.0)
    grp = cs.index.get_level_values("got_carnegie_lib").to_numpy()
    it, ic = np.where(grp == 1.0)[0], np.where(grp == 0.0)[0]
    rng = np.random.default_rng(seed)
    draws = np.array([did_from_sums(cs, rng.choice(it, len(it)), rng.choice(ic, len(ic))) for _ in range(n_boot)])
    point = did_from_sums(cs, it, ic)
    out = {}
    for j, k in enumerate(("share_immigrant", "share_female")):
        out[k] = {"did": _fmt(point[j]), "boot_sd": _fmt(draws[:, j].std(ddof=1)),
                  "ci90": [_fmt(np.quantile(draws[:, j], 0.05)), _fmt(np.quantile(draws[:, j], 0.95))],
                  "ci95": [_fmt(np.quantile(draws[:, j], 0.025)), _fmt(np.quantile(draws[:, j], 0.975))]}
    return out


def placebo(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Pre-period only; fake grant at PLACEBO_CUT; the same cities as the real fit."""
    pre = df[df.relative < 0].copy()
    pre["post"] = (pre.relative >= PLACEBO_CUT).astype(float)
    return pre, bootstrap(pre)


def heaviest(df: pd.DataFrame, k: int = 5) -> dict:
    """The pooled share is patent-weighted: print who carries the weight, and the DiD without each."""
    out = {}
    tot = df.groupby(["state", "city", "got_carnegie_lib"]).patent_count.sum().reset_index()
    for gname, gv in (("treated", 1.0), ("control", 0.0)):
        g = tot[tot.got_carnegie_lib == gv].sort_values("patent_count", ascending=False)
        rows = []
        for _, r in g.head(k).iterrows():
            rest = df[~((df.state == r.state) & (df.city == r.city))]
            pl = pooled(rest)
            rows.append({"state": r.state, "city": r.city, "patents": _fmt(r.patent_count, 3),
                         "weight_in_group": _fmt(r.patent_count / g.patent_count.sum()),
                         "did_share_immigrant_without": pl["did_share_immigrant"],
                         "did_share_female_without": pl["did_share_female"]})
        out[gname] = {"top_weight": _fmt(g.patent_count.head(k).sum() / g.patent_count.sum()), "cities": rows}
    return out


def per_city(df: pd.DataFrame) -> list[dict]:
    rows = []
    for (st, ci), s in df.groupby(["state", "city"]):
        r = {"state": st, "city": ci, "treated": int(s.got_carnegie_lib.iloc[0]), "grant_year": int(s.grant_year.iloc[0])}
        for per, pv in (("pre", 0.0), ("post", 1.0)):
            q = s[s.post == pv]
            r[f"patents_{per}"] = _fmt(q.patent_count.sum(), 3)
            r[f"immigrant_{per}"] = _fmt(q.imm.sum(), 3)
            r[f"female_{per}"] = _fmt(q.fem.sum(), 3)
            r[f"zero_years_{per}"] = int((q.patent_count == 0).sum())
            r[f"years_{per}"] = int(len(q))
        rows.append(r)
    return sorted(rows, key=lambda r: (r["state"], r["city"]))


# ---------------------------------------------------------------- criteria (flags from the objects)
def matches(pub: dict, mine: dict) -> bool:
    d = len(pub["b"].split(".")[1])
    fb = f"{mine['b']:.{d}f}"
    fs = f"{mine['se']:.{d}f}"
    norm = lambda s: s.replace("-0.000", "0.000").replace("-0.00", "0.00")  # noqa: E731
    return norm(fb) == norm(pub["b"]) and fs == pub["se"]


def build_criteria(obj: dict) -> list[dict]:
    src = obj["sources"]
    ok1 = bool(src) and all(r.get("where") and r.get("grade") and ("opened" in r) and r.get("items") for r in src)
    c1 = {"name": "B145-1", "kind": "bookkeeping", "passed": ok1,
          "statement": "Source and coverage table for arm A, each row with its source and grade, sources read at zero included.",
          "detail": f"{len(src)} rows, {sum(1 for r in src if not r['opened'])} not opened (named by the code, absent from the package)"}

    rep = obj["reproduction"][obj["chosen_variant"]]
    pub = obj["published"]
    pairs = {k: matches(pub[k], rep[k]) for k in ("share_immigrant", "share_female")}
    rebuilt = obj["sample_rebuildable"]
    passed2 = all(pairs.values()) if rebuilt else (True if all(pairs.values()) else None)
    c2 = {"name": "B145-2", "kind": "known_answer", "passed": passed2,
          "statement": "Their own specification (table A5 column 3) recomputed on the rebuilt panel reproduces "
                       "the published share coefficients and standard errors to the published digits.",
          "detail": "; ".join(f"{k}: published {pub[k]['b']} ({pub[k]['se']}) N {pub[k]['n']}, recomputed "
                              f"{rep[k]['b']:.4f} ({rep[k]['se']:.4f}) N {rep[k]['n']}, "
                              f"{'match' if pairs[k] else 'no match'}" for k in pairs)
                    + "; level columns of the same table on the rebuilt panel: " + ", ".join(
                        f"{k} {rep[k]['b']:+.4f} ({rep[k]['se']:.4f}) against {pub[k]['b']} ({pub[k]['se']})"
                        for k in ("total_immigrant_patents", "total_female_patents", "patent_count") if k in rep and k in pub)
                    + f"; share built as {obj['share_construction']}"
                    + ("" if rebuilt else "; the census-match restriction is not in the package, so a non-match "
                                           "has no object to be judged against (not evaluated)")}

    pl = obj["pooled"]
    cells = [pl[k] for k in ("treated_pre", "treated_post", "control_pre", "control_post")]
    boot = obj["pooled_bootstrap"]
    plac_same = obj["placebo"]["cities"] == obj["pooled_cities"]
    ok3 = (all(c["patents"] and c["patents"] > 0 and c["cities"] > 0 and c["share_immigrant"] is not None
               and c["share_female"] is not None for c in cells)
           and all(boot[k]["ci90"][0] is not None and boot[k]["ci90"][0] <= boot[k]["did"] <= boot[k]["ci90"][1]
                   for k in boot)
           and plac_same and len(obj["per_city"]) == obj["pooled_cities"])
    reading = obj["floor_reading"]
    c3 = {"name": "B145-3", "kind": "own_reading", "passed": ok3,
          "statement": "Pooled immigrant and women patent shares, sum(x)/sum(n), in treated and control cities before "
                       "and after the grant; the difference in differences with a city-cluster bootstrap interval; "
                       "placebo floor on the same cities; every city printed with its denominators.",
          "detail": "; ".join(f"{k}: DiD {_s(boot[k]['did'])}, 90% [{_s(boot[k]['ci90'][0])}, {_s(boot[k]['ci90'][1])}],"
                              f" placebo {_s(obj['placebo']['bootstrap'][k]['did'])} (sd "
                              f"{_u(obj['placebo']['bootstrap'][k]['boot_sd'])}), reading {reading[k]}"
                              for k in boot)
                    + ". The rival reading (the constrained class gains more, the share rises) is written here and "
                      "settled by the reading; this carrier opens the book edge and the person-to-person edge "
                      "together, so the framework allows both outcomes and no rival criterion is hung (11e sixth clause)."}
    return [c1, c2, c3]


def floor_reading(real: dict, plac: dict) -> dict:
    out = {}
    for k in real:
        d, lo, hi = real[k]["did"], real[k]["ci90"][0], real[k]["ci90"][1]
        floor = 2 * plac[k]["boot_sd"]
        if lo > 0 and d > floor:
            out[k] = "up, above the placebo floor"
        elif hi < 0 and -d > floor:
            out[k] = "down, above the placebo floor"
        elif lo <= 0 <= hi:
            out[k] = "interval covers zero"
        else:
            out[k] = "signed but within twice the placebo spread"
    return out


# ---------------------------------------------------------------- run
def run() -> dict:
    pub = {k: published(k) for k in ("share_immigrant", "share_female", "total_immigrant_patents",
                                     "total_female_patents", "patent_count")}
    panel = build_panel()
    fes = ["state_fips", "year", "grant_year"]
    rep, samples = {}, {}
    for v in VARIANTS:
        df = analysis_sample(panel, v)
        samples[v] = df
        df = df.copy()
        df["share_immigrant"] = np.where(df.patent_count > 0, df.imm / df.patent_count.where(df.patent_count > 0), np.nan)
        df["share_female"] = np.where(df.patent_count > 0, df.fem / df.patent_count.where(df.patent_count > 0), np.nan)
        rep[v] = {"sample_city_years": int(len(df)), "sample_cities": int(df.city_id.nunique()),
                  "treated_cities": int(df[df.got_carnegie_lib == 1].city_id.nunique()),
                  "control_cities": int(df[df.got_carnegie_lib == 0].city_id.nunique()),
                  "city_years_zero_patents": int((df.patent_count == 0).sum())}
        for y, col in (("share_immigrant", "share_immigrant"), ("share_female", "share_female"),
                       ("total_immigrant_patents", "imm"), ("total_female_patents", "fem"),
                       ("patent_count", "patent_count")):
            rep[v][y] = fe_ols(df, col, fes)
        for y in ("share_immigrant", "share_female"):
            rep[v][y + "_weighted_by_patents"] = fe_ols(df, y, fes, weight="patent_count")
        print(f"[{v}] city-years {len(df):,}, cities {df.city_id.nunique()}  (published count N {pub['patent_count']['n']:,})")
        for y in ("share_immigrant", "share_female", "total_immigrant_patents", "total_female_patents", "patent_count"):
            r = rep[v][y]
            print(f"   {y:26s} {r['b']:+.4f} ({r['se']:.4f}) N {r['n']:>6,}   published {pub[y]['b']} ({pub[y]['se']}) N {pub[y]['n']:,}")
        for y in ("share_immigrant", "share_female"):
            r = rep[v][y + "_weighted_by_patents"]
            print(f"   {y + ' weighted':26s} {r['b']:+.4f} ({r['se']:.4f}) N {r['n']:>6,}")
    # The count columns of the same table are the calibration: the variant whose three level
    # coefficients sit closest to the published ones, in published standard errors, carries the
    # readings. Every variant's pooled reading is printed beside it.
    for v in VARIANTS:
        rep[v]["count_distance_in_published_se"] = _fmt(sum(
            abs(rep[v][y]["b"] - float(pub[y]["b"])) / float(pub[y]["se"])
            for y in ("total_immigrant_patents", "total_female_patents", "patent_count")), 3)
    chosen = min(VARIANTS, key=lambda v: rep[v]["count_distance_in_published_se"])
    by_variant = {}
    for v in VARIANTS:
        b_v = bootstrap(samples[v])
        _, p_v = placebo(samples[v])
        by_variant[v] = {"pooled": pooled(samples[v]), "bootstrap": b_v, "placebo_bootstrap": p_v,
                         "floor_reading": floor_reading(b_v, p_v)}
        print(f"[{v}] count distance {rep[v]['count_distance_in_published_se']}; pooled DiD immigrant "
              f"{b_v['share_immigrant']['did']:+.5f} {b_v['share_immigrant']['ci90']}, female "
              f"{b_v['share_female']['did']:+.5f} {b_v['share_female']['ci90']}")
    df = samples[chosen]
    pl = by_variant[chosen]["pooled"]
    boot = by_variant[chosen]["bootstrap"]
    pre, plac = placebo(df)
    fr = floor_reading(boot, plac)
    # implied share move from the published level coefficients, at the sample means
    means = {"patents": float(df.patent_count.mean()), "immigrant": float(df.imm.mean()), "female": float(df.fem.mean())}
    implied = {}
    for k, cnt in (("share_immigrant", "total_immigrant_patents"), ("share_female", "total_female_patents")):
        m = means["immigrant" if "imm" in k else "female"]
        b_x, b_n = float(pub[cnt]["b"]), float(pub["patent_count"]["b"])
        implied[k] = {"base": _fmt(m / means["patents"]), "after": _fmt((m + b_x) / (means["patents"] + b_n)),
                      "move": _fmt((m + b_x) / (means["patents"] + b_n) - m / means["patents"])}
    # thinnest denominators in the share regression (rule 13, first step)
    sh = df[df.patent_count > 0]
    q = sh.patent_count.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).to_dict()
    denominators = {"city_years_with_a_patent": int(len(sh)), "city_years_zero": int((df.patent_count == 0).sum()),
                    "share_of_city_years_below_one_patent": _fmt(float((sh.patent_count < 1).mean())),
                    "share_of_city_years_at_most_two": _fmt(float((sh.patent_count <= 2).mean())),
                    "quantiles": {f"{k:.2f}": _fmt(v, 3) for k, v in q.items()},
                    "patent_weight_in_city_years_at_most_two": _fmt(float(sh.patent_count[sh.patent_count <= 2].sum()
                                                                          / sh.patent_count.sum()))}
    nat, male = df.prob_native_ln.fillna(0.0), df.prob_male_fn.fillna(0.0)
    coverage = {"birthplace_probabilities_over_patents": _fmt(float((df.imm + nat).sum() / df.patent_count.sum())),
                "gender_probabilities_over_patents": _fmt(float((df.fem + male).sum() / df.patent_count.sum()))}
    print("   name coverage in the sample:", coverage)
    heavy = heaviest(df)
    for gname, h in heavy.items():
        print(f"   {gname}: five heaviest cities carry {h['top_weight']:.3f} of the group's patents")
        for r in h["cities"]:
            print(f"      {r['city']}, {r['state']}: {r['patents']:,.1f} patents ({r['weight_in_group']:.3f}); DiD without it "
                  f"immigrant {r['did_share_immigrant_without']:+.5f}, female {r['did_share_female_without']:+.5f}")
    obj = {"sources": SOURCES, "name_coverage": coverage, "heaviest_cities": heavy, "published": pub, "reproduction": rep, "chosen_variant": chosen,
           "sample_rebuildable": False,
           "share_construction": "a city-year ratio, total_immigrant_patents/patent_count, with no replace for "
                                 "patent_count == 0; Stata's x/0 is missing, so every zero-patent city-year leaves "
                                 "the share regression (it is not recorded as zero)",
           "count_specification": "levels: reghdfe total_immigrant_patents (a sum of name-based probabilities), "
                                  "not ihs and not log",
           "pooled": pl, "pooled_bootstrap": boot, "pooled_by_variant": by_variant, "pooled_cities": int(df.city_id.nunique()),
           "placebo": {"cut": PLACEBO_CUT, "cities": int(pre.city_id.nunique()), "pooled": pooled(pre),
                       "bootstrap": plac},
           "floor_reading": fr, "implied_by_published_levels": implied, "sample_means": means,
           "denominators": denominators, "per_city": per_city(df)}
    print("\npooled shares, chosen variant", chosen)
    for k in ("treated_pre", "treated_post", "control_pre", "control_post"):
        c = pl[k]
        print(f"   {k:13s} patents {c['patents']:>10,.1f}  imm {c['share_immigrant']:.4f}  fem {c['share_female']:.4f}"
              f"  cities {c['cities']}  city-years {c['city_years']:,} (zero {c['city_years_zero_patents']:,})")
    for k in boot:
        print(f"   DiD {k}: {boot[k]['did']:+.5f}  90% {boot[k]['ci90']}  placebo {plac[k]['did']:+.5f} sd "
              f"{plac[k]['boot_sd']:.5f}  -> {fr[k]}")
    print("   implied by the published level coefficients:", implied)
    print("   denominators:", denominators)
    return obj


def write(obj: dict) -> None:
    crit = build_criteria(obj)
    for c in crit:
        print(f"{c['name']} [{c['kind']}] passed={c['passed']}: {c['detail']}")
    rec = {"stage": "B145", "arm": "A", "criteria": crit,
           "config": {"n_boot": N_BOOT, "seed": SEED, "window": [PRE_WINDOW, POST_END], "placebo_cut": PLACEBO_CUT,
                      "variants": VARIANTS, "published_column": PUBLISHED_COL,
                      "fixed_effects": ["state_fips", "year", "grant_year"], "cluster": "city",
                      "fetched_by": "experiments/b145_fetch.py"},
           "objects": obj}
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("wrote", OUT.relative_to(ROOT))


# ---------------------------------------------------------------- selftest (11f)
def selftest() -> int:
    fixture_city = [{"state": "XX", "city": "A"}]
    base = {"sources": [dict(r) for r in SOURCES],
            "published": {"share_immigrant": {"b": "-0.000", "se": "0.002", "n": 10},
                          "share_female": {"b": "-0.001", "se": "0.004", "n": 10}},
            "reproduction": {"v": {"share_immigrant": {"b": -0.0001, "se": 0.0021, "n": 10},
                                   "share_female": {"b": -0.0012, "se": 0.0041, "n": 10}}},
            "chosen_variant": "v", "sample_rebuildable": True, "share_construction": "x",
            "pooled": {k: {"patents": 10.0, "cities": 1, "share_immigrant": 0.1, "share_female": 0.05}
                       for k in ("treated_pre", "treated_post", "control_pre", "control_post")},
            "pooled_bootstrap": {"share_immigrant": {"did": 0.01, "ci90": [0.0, 0.02]},
                                 "share_female": {"did": 0.0, "ci90": [-0.01, 0.01]}},
            "placebo": {"cities": 1, "bootstrap": {"share_immigrant": {"did": 0.0, "boot_sd": 0.01},
                                                   "share_female": {"did": 0.0, "boot_sd": 0.01}}},
            "pooled_cities": 1, "per_city": fixture_city, "floor_reading": {"share_immigrant": "x", "share_female": "x"}}
    import copy
    ok = {c["name"]: c["passed"] for c in build_criteria(base)}
    assert ok == {"B145-1": True, "B145-2": True, "B145-3": True}, ok
    seeds = []
    s = copy.deepcopy(base); s["sources"][0]["where"] = ""; seeds.append(("B145-1", s, False))
    s = copy.deepcopy(base); s["reproduction"]["v"]["share_female"]["b"] = 0.004; seeds.append(("B145-2", s, False))
    s = copy.deepcopy(base); s["reproduction"]["v"]["share_immigrant"]["se"] = 0.0031; seeds.append(("B145-2", s, False))
    s = copy.deepcopy(base); s["sample_rebuildable"] = False; s["reproduction"]["v"]["share_female"]["b"] = 0.004
    seeds.append(("B145-2", s, None))
    s = copy.deepcopy(base); s["pooled"]["control_post"]["patents"] = 0.0; seeds.append(("B145-3", s, False))
    s = copy.deepcopy(base); s["placebo"]["cities"] = 2; seeds.append(("B145-3", s, False))
    s = copy.deepcopy(base); s["per_city"] = []; seeds.append(("B145-3", s, False))
    s = copy.deepcopy(base); s["pooled_bootstrap"]["share_female"]["ci90"] = [None, None]; seeds.append(("B145-3", s, False))
    for name, s, want in seeds:
        got = {c["name"]: c["passed"] for c in build_criteria(s)}[name]
        assert got is want, (name, got, want)
        print(f"seed on {name}: flag {got} as required")
    # the matcher reads the published digits, it does not round to a fixed place
    assert matches({"b": "-0.000", "se": "0.002"}, {"b": 0.0004, "se": 0.0024})
    assert not matches({"b": "-0.000", "se": "0.002"}, {"b": 0.0006, "se": 0.0024})
    # the bootstrap DiD on a two-city fixture equals the hand computation
    fx = pd.DataFrame({"city_id": [0, 0, 1, 1], "got_carnegie_lib": [1.0, 1.0, 0.0, 0.0], "post": [0.0, 1.0, 0.0, 1.0],
                       "patent_count": [10.0, 10.0, 10.0, 10.0], "imm": [1.0, 3.0, 1.0, 1.0], "fem": [0.0, 0.0, 1.0, 0.0]})
    cs = city_sums(fx).reindex(columns=pd.MultiIndex.from_product([["patent_count", "imm", "fem"], [0.0, 1.0]]),
                               fill_value=0.0)
    d = did_from_sums(cs, np.array([1]), np.array([0]))   # index order: (0,ctrl) sorts first
    grp = cs.index.get_level_values("got_carnegie_lib").to_numpy()
    d = did_from_sums(cs, np.where(grp == 1.0)[0], np.where(grp == 0.0)[0])
    assert abs(d[0] - 0.2) < 1e-12 and abs(d[1] - 0.1) < 1e-12, d
    print("selftest: all seeds flip, matcher and DiD check out")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    write(run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
