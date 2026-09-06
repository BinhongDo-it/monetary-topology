"""B30-16 rank test: how much rank is left in a carrier-by-route fare matrix.

Pre-registered: the criteria for this arm are registered and this file does not
change any of them.

Question (design file 1e, discriminator one): if N parties quote M numbers and the
shared procedure has only K free parameters, the quotes must lie on a K-dimensional
manifold. So count the rank.

The rank-one approximation here is "route level times carrier constant markup".
If it explains most of the variance, then one carrier's fare on one route is about
two numbers multiplied, and a large pile of quotes carries only r and c worth of
information.

TWO BACKENDS, because the good one is behind a form.

  --source table6   DOT Consumer Airfare Report Table 6, Socrata API, no forms,
                    works today, 1996Q1 onward. Gives exactly TWO carriers per
                    city pair per quarter: the largest carrier and the
                    lowest-fare carrier, each with its own fare.
                    Sparse, but that is enough to identify r (x) c, and it also
                    gives a second, sharper reading: if fares were route specific
                    the gap between two carriers on one route would vary by route.
                    Under rank one it depends only on WHICH two carriers.

  --source db1b     BTS TranStats DB1B Market, 1993Q1 onward, every carrier on
                    every route. Better data, but the download is a form.
                    See DOWNLOAD notes below.

Stages, each separately auditable:
  --stage 1   fetch, cache, build the matrix, print dimensions and coverage, stop
  --stage 2   rank-one fit plus the shuffled baseline the design file requires
  --stage 3   control carrier, separate file, not here

No GPU needed. Stage 1 is IO and parsing, stage 2 is one small SVD.

Caching, three layers, rerun only rebuilds the layer that changed:
  raw   data/b30_16/raw/...            never rebuilt
  mat   results/b30_16/mat_<key>.*     keyed on (source, period, filter config)
  dec   results/b30_16/dec_<hash>.json keyed on matrix hash

DOWNLOAD notes for --source db1b, checked 2026-08-30 against the live site:

  The PREZIP direct link is dead and the "Prezipped File" checkbox on the form
  returns a syntax error from BTS's own page. Neither is usable. Use the form
  and tick fields:

    https://transtats.bts.gov/DL_SelectFields.asp?gnoyr_VQ=FHK&QO_fu146_anzr=b4vtv0+n0q+Qr56v0n6v10+f748rB

    Filter Geography = Domestic, then pick Year and Period, then tick:
      Year, Quarter, Origin, Dest, OriginAirportID, DestAirportID,
      OriginCityMarketID, DestCityMarketID, TkCarrier, TkCarrierChange,
      Passengers, MktFare, MktCoupons, BulkFare, MktDistance

  Drop the download anywhere under data/b30_16/raw/. The file name does not
  matter: BTS names form downloads by year only (T_DB1B_MARKET_1995.zip) and
  one file can hold a whole year, so the script reads Year and Quarter out of
  the file and builds an index of what is actually inside.

  Two filters on this path differ from the archive path, both deliberate:
    - the route-median outlier cut runs on aggregated CELL fares, not on
      individual tickets, to avoid a second full pass over the file;
    - rows with TkCarrierChange nonzero are dropped, because a fare cannot be
      attributed to one carrier when the ticketing carrier changed inside the
      market. Report says whether that column was present.
"""
import argparse, hashlib, io, json, os, sys, zipfile
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "b30_16", "raw")
OUT = os.path.join(ROOT, "results", "b30_16")
os.makedirs(RAW, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

T6 = "https://data.transportation.gov/resource/yj5y-b2ir.csv"
PREZIP = ("https://transtats.bts.gov/PREZIP/"
          "Origin_and_Destination_Survey_DB1BMarket_{year}_{q}.zip")
DL_FORM = "https://transtats.bts.gov/DL_SelectFields.asp?gnoyr_VQ=FHK"

CFG = dict(
    min_fare=10.0,
    max_fare_mult=10.0,
    max_coupons=2,
    drop_bulk=True,
    min_carriers_per_route=3,      # db1b only; table6 always has 2
    min_pax_per_cell=20,           # db1b only
    min_routes_per_carrier=30,
    t6_min_passengers=10.0,
    carry_distance=True,   # 2026-08-30: route features were not aligned
    carry_noise=True,      # 2026-08-30: failure mode 112 needs a measured floor
)
CFG_KEY = hashlib.md5(json.dumps(CFG, sort_keys=True).encode()).hexdigest()[:8]


def _json_default(o):
    """numpy scalars are not JSON serializable and pandas hands them back from
    .values and .astype(int). Cast rather than let a cache write abort a run."""
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not JSON serializable: {type(o).__name__}")


def _json_write(obj, path):
    """Atomic. A crash mid-dump used to leave a truncated cache that then broke
    every later run at load time (rule 17: write to a temp path, then replace)."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2, default=_json_default)
    os.replace(tmp, path)


def _json_read(path):
    """A corrupt cache is a reason to rebuild, never a reason to abort the run."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        log(f"  cache unreadable, rebuilding: {os.path.basename(path)} ({e})")
        return None


def log(*a):
    print(*a, flush=True)


def http_get(url, dest=None, timeout=600):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if dest is None:
            return r.read()
        with open(dest, "wb") as f:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
    return dest


# ---------------------------------------------------------------- table6

def t6_fetch():
    """Whole table, paged. About 250k rows, a few tens of MB. Cached once."""
    p = os.path.join(RAW, "t6_raw.csv.gz")
    if os.path.exists(p):
        log(f"  cached  {os.path.basename(p)}  {os.path.getsize(p)/1e6:.1f} MB")
        return pd.read_csv(p, low_memory=False)
    frames, off, page = [], 0, 50000
    while True:
        url = f"{T6}?$limit={page}&$offset={off}"
        log(f"  GET     offset {off}")
        raw = http_get(url)
        d = pd.read_csv(io.BytesIO(raw), low_memory=False)
        if d.empty:
            break
        frames.append(d)
        off += page
        if len(d) < page:
            break
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(p, index=False, compression="gzip")
    log(f"  saved   {len(df)} rows -> {os.path.basename(p)}")
    return df


def t6_prepare(df):
    """Normalise column names across Socrata revisions, and say what was found."""
    cols = {c.lower().strip(): c for c in df.columns}
    log(f"  columns found: {sorted(cols)}")

    def pick(*cands):
        for c in cands:
            if c in cols:
                return cols[c]
        return None

    m = dict(
        year=pick("year", "tbl6pk_year"),
        quarter=pick("quarter", "tbl6pk_quarter"),
        c1=pick("city1", "citymarketid_1"),
        c2=pick("city2", "citymarketid_2"),
        pax=pick("passengers", "pax"),
        fare=pick("fare", "fare_avg"),
        carrier_lg=pick("carrier_lg", "carrierlg"),
        fare_lg=pick("fare_lg", "farelg"),
        carrier_low=pick("carrier_low", "carrierlow"),
        fare_low=pick("fare_low", "farelow"),
        miles=pick("nsmiles", "miles"),
    )
    missing = [k for k, v in m.items() if v is None]
    assert not missing, f"columns not found: {missing}; have {sorted(cols)}"
    out = df[[v for v in m.values()]].copy()
    out.columns = list(m.keys())
    for c in ("year", "quarter", "pax", "fare", "fare_lg", "fare_low", "miles"):
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out["route"] = np.where(out["c1"].astype(str) < out["c2"].astype(str),
                            out["c1"].astype(str) + "|" + out["c2"].astype(str),
                            out["c2"].astype(str) + "|" + out["c1"].astype(str))
    out = out.dropna(subset=["fare_lg", "fare_low", "year", "quarter"])
    out = out[(out["fare_lg"] >= CFG["min_fare"]) & (out["fare_low"] >= CFG["min_fare"])]
    out = out[out["pax"] >= CFG["t6_min_passengers"]]
    return out


def t6_matrix(t6, year, q):
    """Long form: one row per (carrier, route) cell, two cells per route."""
    d = t6[(t6["year"] == year) & (t6["quarter"] == q)]
    a = d[["route", "carrier_lg", "fare_lg", "miles"]].rename(
        columns={"carrier_lg": "carrier", "fare_lg": "fare"})
    a["leg"] = "lg"
    b = d[["route", "carrier_low", "fare_low", "miles"]].rename(
        columns={"carrier_low": "carrier", "fare_low": "fare"})
    b["leg"] = "low"
    cell = pd.concat([a, b], ignore_index=True)
    cell = cell.groupby(["carrier", "route"], as_index=False).agg(
        fare=("fare", "mean"), miles=("miles", "first"))
    for _ in range(10):
        n0 = len(cell)
        keep_c = cell.groupby("carrier")["route"].nunique()
        keep_c = keep_c[keep_c >= CFG["min_routes_per_carrier"]].index
        cell = cell[cell["carrier"].isin(keep_c)]
        keep_r = cell.groupby("route")["carrier"].nunique()
        keep_r = keep_r[keep_r >= 2].index
        cell = cell[cell["route"].isin(keep_r)]
        if len(cell) == n0:
            break
    return cell, d


# ---------------------------------------------------------------- db1b

def _open_table(p, **kw):
    """Read a DB1B file whether it is a zip, a csv, or a csv.gz.
    Passing chunksize through returns an iterator, which is how the big ones
    are handled: a full year of DB1BMarket does not fit comfortably in memory.
    """
    if p.lower().endswith(".zip"):
        z = zipfile.ZipFile(p)
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        fh = z.open(name)
        return pd.read_csv(fh, low_memory=False, **kw)
    return pd.read_csv(p, low_memory=False, **kw)


def _colmap(columns):
    cols = {c.lower().strip(): c for c in columns}

    def pick(*cands):
        for c in cands:
            if c in cols:
                return cols[c]
        return None
    return cols, pick


def db1b_files():
    import glob
    out = []
    for pat in ("*.zip", "*.csv", "*.csv.gz"):
        out += glob.glob(os.path.join(RAW, pat))
    return sorted(f for f in out if "t6_raw" not in os.path.basename(f).lower())


def db1b_index(rebuild=False):
    """Which file holds which (year, quarter).

    The form download names files by year only, for example
    T_DB1B_MARKET_1995.zip, and one file can hold a whole year. So do not guess
    from the file name. Read the Year and Quarter columns and record what is
    actually inside. Cached on (name, size, mtime) so this pass happens once.
    """
    idx_path = os.path.join(OUT, "db1b_index.json")
    idx = None if rebuild else (_json_read(idx_path)
                                if os.path.exists(idx_path) else None)
    if idx is None:
        idx = {}
    changed = False
    for f in db1b_files():
        st = os.stat(f)
        key = os.path.basename(f)
        sig = [int(st.st_size), int(st.st_mtime)]
        if key in idx and idx[key].get("sig") == sig:
            continue
        head = _open_table(f, nrows=0)
        cols, pick = _colmap(head.columns)
        yc, qc = pick("year"), pick("quarter")
        if yc is None or qc is None:
            log(f"  index: {key} has no Year/Quarter column, skipped. "
                f"columns: {sorted(cols)}")
            idx[key] = dict(sig=sig, periods=[], columns=sorted(cols))
            changed = True
            continue
        seen = set()
        for ch in _open_table(f, usecols=[yc, qc], chunksize=2_000_000):
            ch.columns = ["year", "quarter"]
            seen |= set(map(tuple, ch.dropna().astype(int).drop_duplicates().values))
        idx[key] = dict(sig=sig,
                        periods=sorted([[int(a), int(b)] for a, b in seen]),
                        columns=sorted(cols))
        log(f"  index: {key} covers {idx[key]['periods']}")
        changed = True
    if changed:
        _json_write(idx, idx_path)
    return idx


def db1b_file_for(year, q, idx):
    for name, rec in idx.items():
        if [int(year), int(q)] in [list(map(int, p)) for p in rec.get("periods", [])]:
            return os.path.join(RAW, name)
    return None


CARRIER_CANDIDATES = [
    "tkcarrier", "ticket_carrier", "ticketcarrier", "ticketing_carrier",
    "rpcarrier", "reporting_carrier", "reportingcarrier",
    "opcarrier", "operating_carrier", "operatingcarrier",
]
ROUTE_CITY = (["origincitymarketid", "origin_city_market_id"],
              ["destcitymarketid", "dest_city_market_id"])
ROUTE_AIRPORT = (["originairportid", "origin_airport_id", "origin"],
                 ["destairportid", "dest_airport_id", "dest"])


def db1b_cells(year, q):
    """Stream one quarter out of whatever file holds it and aggregate.

    Streamed because one file can hold a whole year. Aggregation is done per
    chunk and combined at the end, so peak memory is one chunk plus the cell
    table, not the file.

    Two filters differ from the pre-zipped path and both are recorded:
      - the route-median outlier cut is applied to the aggregated CELL fares
        rather than to individual tickets, because the ticket-level median
        needs a second pass over the file for no gain in what we use;
      - if TkCarrierChange is present, rows where the ticketing carrier changed
        inside the market are dropped, because a fare cannot be attributed to
        one carrier there. The pre-zipped path had no such filter.
    """
    idx = db1b_index()
    p = db1b_file_for(year, q, idx)
    if p is None:
        log(f"  no local file covers {year}Q{q}")
        log("")
        log("  Drop the download anywhere in " + RAW + " and rerun.")
        log("  The file name does not matter. The script reads Year and Quarter")
        log("  out of the file itself, so T_DB1B_MARKET_1995.zip is fine.")
        log("")
        log("  Form:  " + DL_FORM)
        log("    Filter Geography = Domestic")
        log(f"    Filter Year = {year}, Filter Period = Quarter {q}")
        log("    'Prezipped File' errors out on BTS's side. Tick fields instead:")
        log("      Year, Quarter, Origin, Dest, OriginAirportID, DestAirportID,")
        log("      OriginCityMarketID, DestCityMarketID, TkCarrier, TkCarrierChange,")
        log("      Passengers, MktFare, MktCoupons, BulkFare, MktDistance")
        if idx:
            log("")
            log("  Files seen and what they cover:")
            for k, v in idx.items():
                log(f"    {k}: {v.get('periods')}")
        return None
    log(f"  file    {os.path.basename(p)}")

    head = _open_table(p, nrows=0)
    cols, pick = _colmap(head.columns)
    car = next((cols[c] for c in CARRIER_CANDIDATES if c in cols), None)
    assert car, f"no carrier column; have {sorted(cols)}"
    o = pick(*ROUTE_CITY[0]) or pick(*ROUTE_AIRPORT[0])
    d = pick(*ROUTE_CITY[1]) or pick(*ROUTE_AIRPORT[1])
    assert o and d, f"no origin/dest columns; have {sorted(cols)}"
    route_basis = ("citymarket" if "citymarket" in o.lower().replace("_", "")
                   else "airport")
    yc, qc = pick("year"), pick("quarter")
    fare = pick("mktfare", "market_fare", "marketfare")
    pax = pick("passengers")
    coup = pick("mktcoupons", "market_coupons", "marketcoupons")
    bulk = pick("bulkfare", "bulk_fare")
    chg = pick("tkcarrierchange", "tk_carrier_change")
    assert fare and pax, f"missing fare or passengers; have {sorted(cols)}"
    dist = pick("mktdistance", "market_distance", "nonstopmiles", "nonstop_miles")
    use = [c for c in [yc, qc, o, d, car, fare, pax, coup, bulk, chg, dist] if c]
    log(f"  route basis: {route_basis}, carrier column: {car}, "
        f"carrier-change filter: {'on' if chg else 'ABSENT'}")

    parts, n_raw, n_kept = [], 0, 0
    for ch in _open_table(p, usecols=use, chunksize=2_000_000):
        ren = {yc: "year", qc: "quarter", o: "o", d: "dd", car: "carrier",
               fare: "fare", pax: "pax"}
        if coup:
            ren[coup] = "coupons"
        if bulk:
            ren[bulk] = "bulk"
        if chg:
            ren[chg] = "chg"
        if dist:
            ren[dist] = "dist"
        ch = ch.rename(columns=ren)
        n_raw += len(ch)
        ch = ch[(ch["year"] == year) & (ch["quarter"] == q)]
        if ch.empty:
            continue
        if "bulk" in ch.columns and CFG["drop_bulk"]:
            ch = ch[ch["bulk"] != 1]
        if "chg" in ch.columns:
            ch = ch[ch["chg"] == 0]
        if "coupons" in ch.columns:
            ch = ch[ch["coupons"] <= CFG["max_coupons"]]
        ch = ch[(ch["fare"] >= CFG["min_fare"]) & (ch["fare"] <= 10000)]
        ch = ch[ch["pax"] > 0]
        if ch.empty:
            continue
        a, b = ch["o"].astype(str), ch["dd"].astype(str)
        ch["route"] = np.where(a < b, a + "|" + b, b + "|" + a)
        ch["fp"] = ch["fare"] * ch["pax"]
        n_kept += len(ch)
        agg = dict(fp=("fp", "sum"), pax=("pax", "sum"))
        # second moment, so the cell mean gets a standard error. Failure mode 112
        # says a low-rank reading needs a floor from the carrier's own precision,
        # and for a 10 per cent ticket sample averaged into a cell that floor is
        # the sampling error of the cell mean, not a printing grid.
        ch["ffp"] = ch["fare"] * ch["fp"]
        agg["ffp"] = ("ffp", "sum")
        if "dist" in ch.columns:
            ch["dp"] = ch["dist"] * ch["pax"]
            agg["dp"] = ("dp", "sum")
        parts.append(ch.groupby(["carrier", "route"], observed=True)
                       .agg(**agg).reset_index())
    if not parts:
        log(f"  no rows for {year}Q{q} in that file")
        return None
    allp = pd.concat(parts, ignore_index=True)
    agg2 = dict(fp=("fp", "sum"), pax=("pax", "sum"), ffp=("ffp", "sum"))
    if "dp" in allp.columns:
        agg2["dp"] = ("dp", "sum")
    g = allp.groupby(["carrier", "route"], as_index=False).agg(**agg2)
    g = g[g["pax"] >= CFG["min_pax_per_cell"]]
    g["fare"] = g["fp"] / g["pax"]
    keep = ["carrier", "route", "fare", "pax"]
    var = (g["ffp"] / g["pax"] - g["fare"] ** 2).clip(lower=0.0)
    g["fare_sd"] = np.sqrt(var)
    g["se_mean"] = g["fare_sd"] / np.sqrt(g["pax"].clip(lower=1))
    g["se_log"] = g["se_mean"] / g["fare"]      # delta method
    keep += ["fare_sd", "se_mean", "se_log"]
    if "dp" in g.columns:
        g["miles"] = g["dp"] / g["pax"]
        keep.append("miles")
    cell = g[keep].copy()
    med = cell.groupby("route")["fare"].transform("median")
    cell = cell[cell["fare"] <= CFG["max_fare_mult"] * med]
    log(f"  rows scanned {n_raw}, kept {n_kept}, cells before pruning {len(cell)}")

    for _ in range(10):
        n0 = len(cell)
        keep_r = cell.groupby("route")["carrier"].nunique()
        keep_r = keep_r[keep_r >= CFG["min_carriers_per_route"]].index
        cell = cell[cell["route"].isin(keep_r)]
        keep_c = cell.groupby("carrier")["route"].nunique()
        keep_c = keep_c[keep_c >= CFG["min_routes_per_carrier"]].index
        cell = cell[cell["carrier"].isin(keep_c)]
        if len(cell) == n0:
            break
    return cell.reset_index(drop=True)


# ---------------------------------------------------------------- shared

def cell_key(source, year, q):
    return os.path.join(OUT, f"cell_{source}_{year}Q{q}_{CFG_KEY}")


def save_cell(cell, base):
    try:
        cell.to_parquet(base + ".parquet"); return base + ".parquet"
    except Exception:
        cell.to_csv(base + ".csv.gz", index=False, compression="gzip")
        return base + ".csv.gz"


def load_cell(base):
    for ext in (".parquet", ".csv.gz"):
        p = base + ext
        if os.path.exists(p):
            return pd.read_parquet(p) if ext == ".parquet" else pd.read_csv(p)
    return None


def describe(cell, source, year, q):
    d = dict(source=source, year=int(year), quarter=int(q), cfg_key=CFG_KEY,
             n_carriers=int(cell["carrier"].nunique()),
             n_routes=int(cell["route"].nunique()),
             n_cells=int(len(cell)))
    d["density"] = d["n_cells"] / max(d["n_carriers"] * d["n_routes"], 1)
    d["fare_mean"] = float(cell["fare"].mean())
    d["fare_sd"] = float(cell["fare"].std())
    d["cells_per_route"] = d["n_cells"] / max(d["n_routes"], 1)
    if "se_log" in cell.columns:
        d["floor_log_rms"] = float(np.sqrt((cell["se_log"] ** 2).mean()))
        d["floor_log_median"] = float(cell["se_log"].median())
        d["pax_median"] = float(cell["pax"].median())
    return d


def stage1(source, periods):
    log(f"\nB30-16 stage 1.  source={source}  filter key={CFG_KEY}")
    log(json.dumps(CFG))
    t6 = None
    if source == "table6":
        log("\nfetching Table 6")
        t6 = t6_prepare(t6_fetch())
        yrs = sorted(t6["year"].dropna().unique())
        log(f"  coverage {int(yrs[0])} to {int(yrs[-1])}, {len(t6)} rows after filter")
    rows = []
    for year, q in periods:
        log(f"\n{year}Q{q}")
        base = cell_key(source, year, q)
        cell = load_cell(base)
        if cell is None:
            if source == "table6":
                cell, _ = t6_matrix(t6, year, q)
            else:
                cell = db1b_cells(year, q)
            if cell is None or len(cell) == 0:
                log("  no cells, skipped")
                continue
            log(f"  built   {os.path.basename(save_cell(cell, base))}")
        else:
            log("  cached  cells")
        d = describe(cell, source, year, q)
        _json_write(d, base + "_diag.json")
        rows.append(d)
        log(f"  {d['n_carriers']} carriers x {d['n_routes']} routes, "
            f"{d['n_cells']} cells, density {d['density']:.4f}, "
            f"{d['cells_per_route']:.2f} cells/route, "
            f"fare mean {d['fare_mean']:.1f} sd {d['fare_sd']:.1f}")
        if "floor_log_rms" in d:
            log(f"  measurement floor on log fare: RMS {d['floor_log_rms']:.5f}, "
                f"median {d['floor_log_median']:.5f}, "
                f"median sampled pax per cell {d['pax_median']:.0f}")
    if rows:
        log("\nsummary")
        log(pd.DataFrame(rows).to_string(index=False))
    log("\nStage 1 ends here. Criteria are in the design file 4.8. "
        "Look at these numbers before running stage 2.")



# ---------------------------------------------------------------- stage 2

def t6_pairs(t6, year, q):
    """Pair-level rows: one per route, carrying both carriers and both fares.

    With exactly two cells per route, the two-way fixed-effect model
    log fare = a_carrier + b_route reduces EXACTLY to the within-route
    difference, so the route effect is differenced out rather than estimated.
    That removes the degrees-of-freedom inflation that two cells per route
    would otherwise cause, and it leaves the rank-one prediction bare:

        log fare_lg - log fare_low  =  c_lg - c_low

    n_carriers - 1 free parameters against n_routes observations.
    """
    d = t6[(t6["year"] == year) & (t6["quarter"] == q)].copy()
    d = d[d["carrier_lg"].astype(str) != d["carrier_low"].astype(str)]
    d = d[(d["fare_lg"] > 0) & (d["fare_low"] > 0)]
    d["gap"] = np.log(d["fare_lg"].values) - np.log(d["fare_low"].values)
    return d


def _r2(y, X):
    """R^2 of the least-squares fit of y on X. Minimum-norm solution, so a
    rank-deficient X is fine and the R^2 is still well defined."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def _rank1_design(lg, low, carriers):
    """+1 in the large carrier's column, -1 in the low-fare carrier's column."""
    idx = {c: i for i, c in enumerate(carriers)}
    X = np.zeros((len(lg), len(carriers)))
    X[np.arange(len(lg)), [idx[c] for c in lg]] += 1.0
    X[np.arange(len(low)), [idx[c] for c in low]] -= 1.0
    return np.hstack([np.ones((len(lg), 1)), X])


def _pair_design(lg, low):
    keys = [a + ">" + b for a, b in zip(lg, low)]
    uniq = sorted(set(keys))
    idx = {k: i for i, k in enumerate(uniq)}
    X = np.zeros((len(keys), len(uniq)))
    X[np.arange(len(keys)), [idx[k] for k in keys]] = 1.0
    return X, len(uniq)


def stage2(periods, n_shuffle=10, seed=0):
    log(f"\nB30-16 stage 2.  criteria are in design file 4.8 and 4.8a, not here.")
    log(f"statistic: R2 of the rank-one prediction on the within-route log fare gap")
    t6 = t6_prepare(t6_fetch())
    rng = np.random.default_rng(seed)
    rows = []
    for year, q in periods:
        d_all = t6_pairs(t6, year, q)
        if len(d_all) < 200:
            log(f"{year}Q{q}: only {len(d_all)} routes, skipped")
            continue
        # Stage 1 pruned carriers below min_routes_per_carrier and stage 2 did
        # not, so the two disagreed on the carrier count. Run both here and
        # report both, because a rise in fit could otherwise be a change in who
        # is in the sample rather than a change in how they price.
        for prune in (False, True):
            d = d_all
            if prune:
                cnt = pd.concat([d["carrier_lg"], d["carrier_low"]]).value_counts()
                keep = set(cnt[cnt >= CFG["min_routes_per_carrier"]].index)
                d = d[d["carrier_lg"].isin(keep) & d["carrier_low"].isin(keep)]
                if len(d) < 200:
                    log(f"{year}Q{q} pruned: only {len(d)} routes, skipped")
                    continue
            _one(d, year, q, prune, rng, n_shuffle, rows)
    _finish(rows)


def _one(d, year, q, prune, rng, n_shuffle, rows):
    lg = d["carrier_lg"].astype(str).values
    low = d["carrier_low"].astype(str).values
    y = d["gap"].values
    carriers = sorted(set(lg) | set(low))

    X1 = _rank1_design(lg, low, carriers)
    r2_rank1 = _r2(y, X1)

    Xp, n_pairs = _pair_design(lg, low)
    r2_pair = _r2(y, Xp)

    # route characteristics on top of the rank-one model
    extra = [np.log(np.maximum(d["miles"].values.astype(float), 1.0)),
             np.log(np.maximum(d["pax"].values.astype(float), 1.0))]
    Xr = np.hstack([X1] + [e.reshape(-1, 1) for e in extra])
    r2_rank1_route = _r2(y, Xr)

    # route characteristics ALONE, no carrier information at all
    Xonly = np.hstack([np.ones((len(y), 1))] + [e.reshape(-1, 1) for e in extra])
    r2_route_only = _r2(y, Xonly)

    # shuffled baseline: permute carrier labels, keep everything else
    nulls = []
    for _ in range(n_shuffle):
        perm = rng.permutation(len(y))
        lg_s, low_s = lg[perm], low[perm]
        nulls.append(_r2(y, _rank1_design(lg_s, low_s, carriers)))
    null_mean, null_max = float(np.mean(nulls)), float(np.max(nulls))

    r = dict(year=year, quarter=q, prune=bool(prune), n_routes=int(len(y)),
             n_carriers=len(carriers), n_pairs=int(n_pairs),
             gap_mean=float(y.mean()), gap_sd=float(y.std()),
             r2_rank1=r2_rank1, r2_pair=r2_pair,
             r2_rank1_plus_route=r2_rank1_route,
             route_increment=r2_rank1_route - r2_rank1,
             r2_route_only=r2_route_only,
             null_mean=null_mean, null_max=null_max,
             excess_over_null=r2_rank1 - null_mean)
    rows.append(r)
    tag = "pruned" if prune else "all carriers"
    log(f"\n{year}Q{q}  [{tag}]  {len(y)} routes, {len(carriers)} carriers, "
        f"{n_pairs} observed pairs")
    log(f"  mean log gap {y.mean():.4f}  sd {y.std():.4f}")
    log(f"  R2 rank one (c_lg - c_low)      {r2_rank1:.4f}")
    log(f"  R2 unrestricted carrier pair    {r2_pair:.4f}   (upper bound)")
    log(f"  R2 rank one + route features    {r2_rank1_route:.4f}")
    log(f"    increment from route features {r2_rank1_route - r2_rank1:+.4f}")
    log(f"  R2 route features alone         {r2_route_only:.4f}")
    log(f"  shuffled null: mean {null_mean:.4f}  max {null_max:.4f}  "
        f"excess {r2_rank1 - null_mean:+.4f}")
def _finish(rows):
    if rows:
        df = pd.DataFrame(rows)
        out = os.path.join(OUT, f"stage2_table6_{CFG_KEY}.json")
        _json_write(rows, out)
        log("\nsummary")
        log(df[["year", "quarter", "prune", "n_routes", "n_carriers",
                "r2_rank1", "r2_pair", "route_increment", "r2_route_only",
                "null_mean", "excess_over_null"]].to_string(index=False))
        log(f"\nwritten {out}")
    log("\nRead against design file 4.8a. Do not restate the criteria here.")



def _dummies(labels, levels):
    idx = {c: i for i, c in enumerate(levels)}
    X = np.zeros((len(labels), len(levels)))
    X[np.arange(len(labels)), [idx[c] for c in labels]] = 1.0
    return X


def stage2_db1b(periods, n_shuffle=10, seed=0):
    """Same question as the Table 6 arm, on a carrier set that is not selected.

    Table 6 gives exactly two carriers per route and picks them on the outcome
    (largest, and lowest-fare). DB1B gives every carrier on every route, about
    4.3 to 4.6 of them here, chosen by nobody. So this is the arm that removes
    limit 1 of the Table 6 chunk.

    Statistic: within-route R^2 of carrier constants on log fare. The route
    level is demeaned out exactly, so what is being asked is the rank-one
    question with no route effect left in it:

        log fare(i, j)  =  a_i + b_j     <=>     within-route variation is a_i

    Route characteristics cannot enter directly here because they are constant
    within a route and vanish under demeaning. The analogue is carrier BY route
    interactions: does a carrier's premium depend on how big the route is, or on
    how many rivals are on it. Under rank one it does not.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for year, q in periods:
        cell = load_cell(cell_key("db1b", year, q))
        if cell is None:
            log(f"{year}Q{q}: no cached cells, run stage 1 first")
            continue
        cell = cell.copy()
        cell["lf"] = np.log(cell["fare"].values)
        g = cell.groupby("route")
        cell["route_pax"] = g["pax"].transform("sum")
        cell["route_n"] = g["carrier"].transform("nunique")
        y = (cell["lf"] - g["lf"].transform("mean")).values

        carriers = sorted(cell["carrier"].unique())
        D = _dummies(cell["carrier"].values, carriers)
        rt = cell["route"].values

        def dm(M):
            """within-route demean of a matrix, aligned to the cell order"""
            f = pd.DataFrame(M)
            f["__r"] = rt
            return (f.drop(columns="__r").values
                    - f.groupby("__r").transform("mean").values)

        Dw = dm(D)
        r2_rank1 = _r2(y, Dw)

        z1 = np.log(cell["route_pax"].values.astype(float))
        z2 = cell["route_n"].values.astype(float)
        Ipax = dm(D * z1.reshape(-1, 1))
        Inum = dm(D * z2.reshape(-1, 1))
        r2_pax = _r2(y, np.hstack([Dw, Ipax]))
        r2_num = _r2(y, np.hstack([Dw, Inum]))
        r2_both = _r2(y, np.hstack([Dw, Ipax, Inum]))

        nulls = []
        for _ in range(n_shuffle):
            perm = rng.permutation(len(y))
            nulls.append(_r2(y, dm(_dummies(cell["carrier"].values[perm], carriers))))
        null_mean, null_max = float(np.mean(nulls)), float(np.max(nulls))

        r = dict(source="db1b", year=year, quarter=q,
                 n_cells=int(len(y)), n_routes=int(cell["route"].nunique()),
                 n_carriers=len(carriers),
                 cells_per_route=float(len(y) / cell["route"].nunique()),
                 within_sd=float(y.std()),
                 r2_rank1=r2_rank1,
                 r2_plus_pax_interaction=r2_pax,
                 r2_plus_ncarrier_interaction=r2_num,
                 r2_plus_both=r2_both,
                 increment_pax=r2_pax - r2_rank1,
                 increment_ncarrier=r2_num - r2_rank1,
                 increment_both=r2_both - r2_rank1,
                 null_mean=null_mean, null_max=null_max,
                 excess_over_null=r2_rank1 - null_mean)
        rows.append(r)
        log(f"\n{year}Q{q}  {len(y)} cells, {r['n_routes']} routes, "
            f"{len(carriers)} carriers, {r['cells_per_route']:.2f} per route")
        log(f"  within-route sd of log fare      {y.std():.4f}")
        log(f"  R2 carrier constants (rank one)  {r2_rank1:.4f}")
        log(f"  + carrier x log route pax        {r2_pax:.4f}  ({r2_pax - r2_rank1:+.4f})")
        log(f"  + carrier x carriers on route    {r2_num:.4f}  ({r2_num - r2_rank1:+.4f})")
        log(f"  + both                           {r2_both:.4f}  ({r2_both - r2_rank1:+.4f})")
        log(f"  shuffled null: mean {null_mean:.4f}  max {null_max:.4f}  "
            f"excess {r2_rank1 - null_mean:+.4f}")
    if rows:
        out = os.path.join(OUT, f"stage2_db1b_{CFG_KEY}.json")
        _json_write(rows, out)
        log("\nsummary")
        log(pd.DataFrame(rows)[["year", "n_cells", "n_carriers", "cells_per_route",
                                "within_sd", "r2_rank1", "increment_pax",
                                "increment_ncarrier", "null_mean"]].to_string(index=False))
        log(f"\nwritten {out}")
    log("\nRead against design file 4.8 and 4.8a.")



def stage2_db1b_mimic_t6(periods, n_shuffle=10, seed=0):
    """Compute the TABLE 6 statistic on DB1B, so the two carriers can be compared.

    The Table 6 chunk read a within-route log gap between exactly two carriers
    picked on the outcome: the largest by passengers and the lowest by fare.
    The DB1B chunk reads within-route variance across every carrier. Those are
    different quantities, so a difference between their R^2 values says nothing
    about a change in pricing until the same statistic is computed on both.

    This rebuilds Table 6's selection out of DB1B cells and runs Table 6's
    regression, on 1993 to 1995. If it lands near the Table 6 1996 value, the
    apparent time trend is the statistic. If it lands near the DB1B value, the
    trend is real and the statistic is not what separates them.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for year, q in periods:
        cell = load_cell(cell_key("db1b", year, q))
        if cell is None:
            log(f"{year}Q{q}: no cached cells, run stage 1 first")
            continue
        g = cell.sort_values(["route", "pax"])
        lg_row = g.groupby("route").tail(1).set_index("route")
        low_row = (cell.sort_values(["route", "fare"])
                       .groupby("route").head(1).set_index("route"))
        cols = {
            "carrier_lg": lg_row["carrier"], "fare_lg": lg_row["fare"],
            "carrier_low": low_row["carrier"], "fare_low": low_row["fare"],
            "pax": cell.groupby("route")["pax"].sum(),
        }
        if "miles" in cell.columns:
            cols["miles"] = cell.groupby("route")["miles"].mean()
        d = pd.DataFrame(cols).dropna()
        d = d[d["carrier_lg"].astype(str) != d["carrier_low"].astype(str)]
        y = np.log(d["fare_lg"].values) - np.log(d["fare_low"].values)
        lg = d["carrier_lg"].astype(str).values
        low = d["carrier_low"].astype(str).values
        carriers = sorted(set(lg) | set(low))
        r2_rank1 = _r2(y, _rank1_design(lg, low, carriers))
        Xp, n_pairs = _pair_design(lg, low)
        r2_pair = _r2(y, Xp)
        feats = [np.log(d["pax"].values.astype(float))]
        if "miles" in d.columns and d["miles"].notna().all():
            feats.append(np.log(np.maximum(d["miles"].values.astype(float), 1.0)))
        Xr = np.hstack([_rank1_design(lg, low, carriers)]
                       + [f.reshape(-1, 1) for f in feats])
        r2_route = _r2(y, Xr)
        r2_route_only = _r2(y, np.hstack([np.ones((len(y), 1))]
                                         + [f.reshape(-1, 1) for f in feats]))
        nulls = []
        for _ in range(n_shuffle):
            perm = rng.permutation(len(y))
            nulls.append(_r2(y, _rank1_design(lg[perm], low[perm], carriers)))
        r = dict(source="db1b_mimic_t6", year=year, quarter=q,
                 n_routes=int(len(y)), n_carriers=len(carriers),
                 n_pairs=int(n_pairs), gap_mean=float(y.mean()),
                 gap_sd=float(y.std()), r2_rank1=r2_rank1, r2_pair=r2_pair,
                 route_increment=r2_route - r2_rank1,
                 r2_route_only=r2_route_only,
                 n_route_feats=len(feats),
                 null_mean=float(np.mean(nulls)))
        rows.append(r)
        log(f"\n{year}Q{q} [Table 6 statistic rebuilt on DB1B]  {len(y)} routes, "
            f"{len(carriers)} carriers, {n_pairs} pairs")
        log(f"  mean log gap {y.mean():.4f}  sd {y.std():.4f}")
        log(f"  R2 rank one {r2_rank1:.4f}  pair {r2_pair:.4f}  "
            f"route incr {r2_route - r2_rank1:+.4f} ({len(feats)} feats)  "
            f"route alone {r2_route_only:.4f}  null {np.mean(nulls):.4f}")
    if rows:
        out = os.path.join(OUT, f"stage2_db1b_mimic_{CFG_KEY}.json")
        _json_write(rows, out)
        log("\nsummary")
        log(pd.DataFrame(rows)[["year", "n_routes", "n_carriers", "gap_mean",
                                "gap_sd", "r2_rank1", "r2_pair",
                                "route_increment", "r2_route_only",
                                "null_mean"]].to_string(index=False))
        log(f"\nwritten {out}")



def stage3_floor(periods, ks=(1, 2, 3), holdout=0.10, seed=0, n_rep=3):
    """How many carrier-space dimensions survive the measurement floor.

    Failure mode 112: a variance share is not an information content. This is
    B30-16's answer to that, using a floor measured from the carrier itself.

    The floor here is not a printing grid. MARKET_FARE is a prorated fare from a
    10 per cent ticket sample averaged into a cell, so the precision of a cell is
    the standard error of its mean, computed from the within-cell second moment
    and the sampled passenger count, then put on the log scale by the delta
    method. That is `se_log`, carried since 2026-08-30.

    Shape note that bounds what can be asked. The matrix is carriers by routes,
    11 to 15 by about 2,200, with 4.3 to 4.6 carriers observed per route. Factors
    live in CARRIER space, so a factor is 11 to 15 numbers and the route scores
    are projections, which is the same well-conditioned situation as the Treasury
    panel. But a route's score vector is estimated from its 4.3 observed cells,
    so k above about 3 is not identified per route and is not attempted.

    Overfitting guard: a held-out fraction of observed cells is masked before
    fitting and the residual is reported on those cells. In-sample residual falls
    with k by construction; the held-out one does not have to.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for year, q in periods:
        cell = load_cell(cell_key("db1b", year, q))
        if cell is None or "se_log" not in cell.columns:
            log(f"{year}Q{q}: cells missing or built before the floor was carried, "
                f"rerun stage 1")
            continue
        carriers = sorted(cell["carrier"].unique())
        routes = sorted(cell["route"].unique())
        ci = {c: i for i, c in enumerate(carriers)}
        ri = {r: j for j, r in enumerate(routes)}
        I = cell["carrier"].map(ci).values
        J = cell["route"].map(ri).values
        y = np.log(cell["fare"].values)
        se = cell["se_log"].values
        n_c, n_r = len(carriers), len(routes)

        for rep in range(n_rep):
            mask = rng.random(len(y)) >= holdout      # True = train
            for k in ks:
                M = np.full((n_c, n_r), np.nan)
                M[I[mask], J[mask]] = y[mask]
                obs = ~np.isnan(M)
                # route mean removed exactly, then EM-SVD to rank k
                rmean = np.nanmean(M, axis=0)
                rmean = np.where(np.isnan(rmean), np.nanmean(y), rmean)
                D = M - rmean
                F = np.where(obs, D, 0.0)
                for _ in range(60):
                    u, sv, vt = np.linalg.svd(F, full_matrices=False)
                    low = (u[:, :k] * sv[:k]) @ vt[:k]
                    F = np.where(obs, D, low)
                fit = low + rmean
                tr = mask
                te = ~mask
                res_tr = y[tr] - fit[I[tr], J[tr]]
                res_te = y[te] - fit[I[te], J[te]]
                rows.append(dict(year=year, quarter=q, rep=rep, k=k,
                                 n_train=int(tr.sum()), n_test=int(te.sum()),
                                 resid_train=float(np.sqrt((res_tr ** 2).mean())),
                                 resid_test=float(np.sqrt((res_te ** 2).mean())),
                                 floor_train=float(np.sqrt((se[tr] ** 2).mean())),
                                 floor_test=float(np.sqrt((se[te] ** 2).mean()))))
    if not rows:
        return
    df = pd.DataFrame(rows)
    agg = (df.groupby(["year", "k"])
             .agg(resid_train=("resid_train", "mean"),
                  resid_test=("resid_test", "mean"),
                  floor=("floor_test", "mean")).reset_index())
    agg["train_over_floor"] = agg["resid_train"] / agg["floor"]
    agg["test_over_floor"] = agg["resid_test"] / agg["floor"]
    log("\nB30-16 stage 3: residual against the measured floor")
    log(f"  {n_rep} held-out repetitions at {holdout:.0%}, ranks {list(ks)}")
    log(agg.to_string(index=False))
    out = os.path.join(OUT, f"stage3_floor_{CFG_KEY}.json")
    _json_write(rows, out)
    log(f"\nwritten {out}")
    log("Read against design file 4.8 and failure mode 112.")



def stage4_crossparty(min_cov=0.6, k=3, seed=0, holdout=0.15, n_rep=3):
    """Design file 1e-2, test A: one shared manifold, or several summing.

    Discriminator one measures how compressible a pooled quote matrix is. It
    cannot tell a shared procedure from several procedures that happen to sum to
    the same dimension. Test A does:

        pooled rank ~ max(individual ranks)  -> they share a manifold
        pooled rank ~ sum(individual ranks)  -> they do not

    And the sharper, floor-free version: take each carrier's own top-k TIME
    factor subspace and measure the principal angles between carriers. Principal
    angles need no noise floor and no variance threshold, which is why they are
    the headline here and the rank comparison is secondary (failure mode 112).

    Carrier: Table 6, quarterly 1996 onward. A row is one (carrier, route) fare
    series through time; columns are quarters. Series with less than min_cov of
    quarters present are dropped, remaining gaps are filled by time
    interpolation, and that fill is a stated approximation rather than data.
    """
    t6 = t6_prepare(t6_fetch())
    t6 = t6.copy()
    t6["per"] = t6["year"].astype(int) * 4 + t6["quarter"].astype(int) - 1
    a = t6[["route", "per", "carrier_lg", "fare_lg"]].rename(
        columns={"carrier_lg": "carrier", "fare_lg": "fare"})
    b = t6[["route", "per", "carrier_low", "fare_low"]].rename(
        columns={"carrier_low": "carrier", "fare_low": "fare"})
    long = pd.concat([a, b], ignore_index=True).dropna()
    long["lf"] = np.log(long["fare"].clip(lower=1))
    long = long.groupby(["carrier", "route", "per"], as_index=False)["lf"].mean()

    pers = sorted(long["per"].unique())
    pidx = {p: i for i, p in enumerate(pers)}
    T = len(pers)
    log(f"\nB30-16 stage 4 (design file 1e-2 test A): {T} quarters, "
        f"{long['carrier'].nunique()} carriers, {long['route'].nunique()} routes")

    blocks = {}
    for c, gc in long.groupby("carrier"):
        piv = gc.pivot_table(index="route", columns="per", values="lf")
        piv = piv.reindex(columns=pers)
        cov = piv.notna().mean(axis=1)
        piv = piv[cov >= min_cov]
        if len(piv) < 30:
            continue
        piv = piv.interpolate(axis=1, limit_direction="both")
        piv = piv.sub(piv.mean(axis=1), axis=0)      # each series demeaned in time
        blocks[c] = piv
    if len(blocks) < 3:
        log("  too few carriers survive the coverage filter")
        return
    log(f"  carriers kept: {len(blocks)}  "
        f"{ {c: len(v) for c, v in sorted(blocks.items())} }")

    def topk(M, kk):
        u, sv, vt = np.linalg.svd(M, full_matrices=False)
        return vt[:kk].T, (sv ** 2 / (sv ** 2).sum())

    subs, shares = {}, {}
    for c, piv in blocks.items():
        V, sh = topk(piv.values, k)
        subs[c], shares[c] = V, sh

    names = sorted(subs)
    log(f"\n  variance share of each carrier's own top {k} time factors:")
    for c in names:
        log(f"    {c}: {np.cumsum(shares[c])[k-1]:.4f}")

    log(f"\n  principal angles between carriers' top {k} time-factor subspaces")
    log("  (degrees; 0 means the same subspace, 90 means orthogonal)")
    rows = []
    for i, ci in enumerate(names):
        for cj in names[i + 1:]:
            sv = np.linalg.svd(subs[ci].T @ subs[cj], compute_uv=False)
            ang = np.degrees(np.arccos(np.clip(sv, -1, 1)))
            rows.append(dict(a=ci, b=cj, ang1=float(ang[0]),
                             ang2=float(ang[1]) if k > 1 else np.nan,
                             ang3=float(ang[2]) if k > 2 else np.nan))
    dfa = pd.DataFrame(rows)
    log(dfa.describe().loc[["mean", "50%", "max"]].to_string())

    # Null for EVERY angle, not just the first. Chunk four recorded only the
    # first and then compared the observed second and third against it, which is
    # not a comparison: for a random pair of k-dimensional subspaces the k angles
    # have different distributions and the later ones are much larger by
    # construction. That fault blocked two thirds of that table.
    rng = np.random.default_rng(seed)
    nul = {i: [] for i in range(k)}
    for _ in range(10):
        Vs = []
        for c in names:
            M = blocks[c].values.copy()
            M = np.column_stack([rng.permutation(M[:, t]) for t in range(M.shape[1])])
            Vs.append(topk(M, k)[0])
        for i in range(len(Vs)):
            for j in range(i + 1, len(Vs)):
                sv = np.linalg.svd(Vs[i].T @ Vs[j], compute_uv=False)
                ang = np.degrees(np.arccos(np.clip(sv, -1, 1)))
                for t in range(k):
                    nul[t].append(float(ang[t]))
    log("\n  shuffled null, matched per angle (degrees)")
    log("   angle   null mean   null min   observed median   observed below null min")
    obs_med = [float(dfa["ang1"].median()),
               float(dfa["ang2"].median()) if k > 1 else np.nan,
               float(dfa["ang3"].median()) if k > 2 else np.nan]
    null_rows = []
    for t in range(k):
        nm, nmin = float(np.mean(nul[t])), float(np.min(nul[t]))
        below = "yes" if obs_med[t] < nmin else "no"
        null_rows.append(dict(angle=t + 1, null_mean=nm, null_min=nmin,
                              obs_median=obs_med[t], below_null_min=below))
        log(f"     {t+1}      {nm:8.2f}   {nmin:8.2f}   {obs_med[t]:15.2f}   "
            f"{below:>22s}")

    pool = pd.concat(blocks.values(), axis=0)
    _, sh_pool = topk(pool.values, k)
    log(f"\n  pooled top {k} variance share: {np.cumsum(sh_pool)[k-1]:.4f}")
    log(f"  mean individual top {k} share:   "
        f"{np.mean([np.cumsum(shares[c])[k-1] for c in names]):.4f}")
    out = os.path.join(OUT, f"stage4_crossparty_cov{int(min_cov*100)}.json")
    _json_write(dict(k=k, min_cov=min_cov, carriers=names,
                     angles=rows, null_by_angle=null_rows,
                     pooled_share=float(np.cumsum(sh_pool)[k-1]),
                     individual_shares={c: float(np.cumsum(shares[c])[k-1])
                                        for c in names}), out)
    log(f"\nwritten {out}")
    log("Read against design file 1e-2. Do not restate the criteria here.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, default=1)
    ap.add_argument("--source", choices=["table6", "db1b"], default="table6")
    ap.add_argument("--periods", default="1996Q1,2005Q1,2015Q1,2024Q1")
    ap.add_argument("--shuffle", type=int, default=10)
    ap.add_argument("--covs", default="", help="stage 4: coverage thresholds")
    ap.add_argument("--mimic", action="store_true",
                    help="db1b only: rebuild the Table 6 two-carrier statistic")
    a = ap.parse_args()
    per = []
    for tok in a.periods.split(","):
        y, q = tok.strip().upper().split("Q")
        per.append((int(y), int(q)))
    if a.stage == 1:
        stage1(a.source, per)
    elif a.stage == 2:
        if a.source == "table6":
            stage2(per, n_shuffle=a.shuffle)
        elif a.mimic:
            stage2_db1b_mimic_t6(per, n_shuffle=a.shuffle)
        else:
            stage2_db1b(per, n_shuffle=a.shuffle)
    elif a.stage == 3:
        stage3_floor(per)
    elif a.stage == 4:
        for cov in [float(x) for x in (a.covs.split(",") if a.covs else ["0.6"])]:
            stage4_crossparty(min_cov=cov)
    else:
        log("Stage 4 is a separate file, the control carrier.")
