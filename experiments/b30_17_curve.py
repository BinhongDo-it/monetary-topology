"""B30-17 Treasury CMT curve: how many numbers do fourteen quotes carry.

Pre-registered: the criteria for this arm are registered
and this file does not restate or change them.

Discriminator one (design file 1e): if N parties quote M numbers and the shared
procedure has K free parameters, the quotes lie on a K-dimensional manifold.
Count the rank.

Why this carrier and not another: the shared procedure is PUBLISHED. CMT is
Treasury interpolating from a small set of on-the-run securities, so unlike the
airline arm there is a named, documented shared formula. And the publication
precision gives a real noise floor rather than an assumed one: rates print to
two decimals in percent, so the grid is one basis point.

    levels   uniform rounding to 1bp        sd = 1/sqrt(12)        = 0.2887 bp
    changes  difference of two roundings    sd = sqrt(2)/sqrt(12)  = 0.4082 bp

Those two numbers are D24's resolution floor for this station, measured rather
than assumed, and they differ, so the right one has to be used for the right
quantity.

Stages:
  --stage 1  fetch, cache, build the day-by-maturity matrix, print coverage, stop
  --stage 2  PCA on levels and on daily changes, variance explained, residual RMS
             against the floor, and the shuffled baseline the design requires
  --stage 3  the column-addition test, written after stage 2 is read

Caching:
  raw   data/b30_17/raw/treasury_<year>.csv     never rebuilt
  mat   results/b30_17/mat_<first>_<last>.csv.gz
"""
import argparse, io, json, os, re, sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "b30_17", "raw")
OUT = os.path.join(ROOT, "results", "b30_17")
os.makedirs(RAW, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
       "daily-treasury-rates.csv/{y}/all?type=daily_treasury_yield_curve"
       "&field_tdr_date_value={y}&page&_format=csv")

GRID_BP = 1.0                       # rates print to two decimals in percent
FLOOR_LEVEL_BP = GRID_BP / np.sqrt(12)
FLOOR_CHANGE_BP = GRID_BP * np.sqrt(2) / np.sqrt(12)

MAT_RE = re.compile(r"^\s*([\d.]+)\s*(mo|month|months|yr|year|years)\b", re.I)


def log(*a):
    print(*a, flush=True)


def _json_write(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2, default=lambda o: float(o))
    os.replace(tmp, path)


def parse_maturity(name):
    """'1 Mo' -> 1/12 years, '1.5 Month' -> 0.125, '10 Yr' -> 10.0, else None.
    Column labels have drifted across years, so match on shape not on a list."""
    m = MAT_RE.match(str(name))
    if not m:
        return None
    v, unit = float(m.group(1)), m.group(2).lower()
    return v / 12.0 if unit.startswith("mo") else v


def fetch_year(y):
    p = os.path.join(RAW, f"treasury_{y}.csv")
    if os.path.exists(p) and os.path.getsize(p) > 200:
        return p
    import urllib.request
    url = URL.format(y=y)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
    except Exception as e:
        log(f"  {y}: FAILED {e}")
        log(f"      fetch by hand and save as {p}")
        log(f"      {url}")
        return None
    with open(p, "wb") as f:
        f.write(body)
    log(f"  {y}: {len(body)/1000:.0f} kB")
    return p


def build(years):
    frames = []
    for y in years:
        p = fetch_year(y)
        if p is None:
            continue
        d = pd.read_csv(p)
        datecol = [c for c in d.columns if c.strip().lower() == "date"][0]
        keep = {}
        for c in d.columns:
            t = parse_maturity(c)
            if t is not None:
                keep[c] = t
        if not keep:
            log(f"  {y}: no maturity columns, header was {list(d.columns)[:8]}")
            continue
        sub = d[[datecol] + list(keep)].copy()
        sub[datecol] = pd.to_datetime(sub[datecol], errors="coerce")
        sub = sub.dropna(subset=[datecol]).set_index(datecol)
        sub.columns = [keep[c] for c in sub.columns]
        sub = sub.apply(pd.to_numeric, errors="coerce")
        frames.append(sub)
    if not frames:
        return None
    m = pd.concat(frames).sort_index()
    m = m.groupby(level=0).first()
    m = m.reindex(sorted(m.columns), axis=1)
    return m


def mat_path(years):
    return os.path.join(OUT, f"mat_{min(years)}_{max(years)}.csv.gz")


def stage1(years):
    log(f"\nB30-17 stage 1.  years {min(years)} to {max(years)}")
    log(f"publication grid {GRID_BP:.2f} bp -> floor sd: "
        f"levels {FLOOR_LEVEL_BP:.4f} bp, changes {FLOOR_CHANGE_BP:.4f} bp")
    p = mat_path(years)
    if os.path.exists(p):
        m = pd.read_csv(p, index_col=0, parse_dates=True)
        m.columns = [float(c) for c in m.columns]
        log(f"  cached matrix {os.path.basename(p)}")
    else:
        m = build(years)
        if m is None:
            log("  nothing built")
            return
        m.to_csv(p, compression="gzip")
        log(f"  built {os.path.basename(p)}")
    log(f"\n{m.shape[0]} trading days x {m.shape[1]} maturities")
    cov = pd.DataFrame({
        "maturity_yr": m.columns,
        "n_obs": [int(m[c].notna().sum()) for c in m.columns],
        "first": [str(m[c].first_valid_index())[:10] for c in m.columns],
        "last": [str(m[c].last_valid_index())[:10] for c in m.columns],
    })
    log(cov.to_string(index=False))
    full = [c for c in m.columns if m[c].notna().all()]
    log(f"\ncomplete over the whole window: {len(full)} maturities -> "
        f"{[round(c, 4) for c in full]}")
    log("\nStage 1 ends here. Criteria are in design file 4.9.")


def _pca_report(X, label, floor_bp, rng, n_shuffle):
    """X in percent. Returns variance shares and residual RMS in basis points."""
    Xc = X - X.mean(axis=0, keepdims=True)
    u, sv, vt = np.linalg.svd(Xc, full_matrices=False)
    var = sv ** 2
    share = var / var.sum()
    cum = np.cumsum(share)
    n, p = Xc.shape
    rows = []
    for k in range(1, p + 1):   # all the way to p: the floor crossing is the point
        rec = (u[:, :k] * sv[:k]) @ vt[:k]
        resid_bp = (Xc - rec) * 100.0
        rows.append(dict(k=k, cum_share=float(cum[k - 1]),
                         resid_rms_bp=float(np.sqrt((resid_bp ** 2).mean())),
                         over_floor=float(np.sqrt((resid_bp ** 2).mean()) / floor_bp)))
    nulls = []
    for _ in range(n_shuffle):
        Z = np.column_stack([rng.permutation(Xc[:, j]) for j in range(p)])
        s2 = np.linalg.svd(Z - Z.mean(axis=0, keepdims=True), compute_uv=False) ** 2
        nulls.append(float(np.cumsum(s2 / s2.sum())[min(2, p - 1)]))
    log(f"\n{label}: {n} rows x {p} maturities, floor {floor_bp:.4f} bp")
    log("   k   cum var    resid RMS bp   x floor")
    for r in rows:
        log(f"  {r['k']:2d}   {r['cum_share']:.6f}   {r['resid_rms_bp']:10.4f}   "
            f"{r['over_floor']:8.2f}")
    log(f"  shuffled null, 3 factors: mean {np.mean(nulls):.4f} "
        f"max {np.max(nulls):.4f}")
    return dict(label=label, n=int(n), p=int(p), floor_bp=float(floor_bp),
                table=rows, null_3f_mean=float(np.mean(nulls)),
                null_3f_max=float(np.max(nulls)))


def balanced(m, min_coverage=0.99, maturities=None):
    """Columns by coverage, then rows with no gap among them.

    Requiring a column to be complete is too strict: ONE missing day in the
    whole window killed eleven otherwise-complete maturities and left a panel of
    width zero. Coverage threshold first, then drop the offending rows.
    """
    if maturities:
        keep = [c for c in m.columns if any(abs(c - t) < 1e-6 for t in maturities)]
    else:
        n = len(m)
        keep = [c for c in m.columns if m[c].notna().sum() >= min_coverage * n]
    dropped = [(round(c, 4), int(m[c].notna().sum()),
                str(m[c].first_valid_index())[:10])
               for c in m.columns if c not in keep]
    sub = m[keep]
    bad = sub.isna().any(axis=1)
    return sub[~bad], keep, dropped, int(bad.sum())


def stage2(years, n_shuffle=10, seed=0, min_coverage=0.99, maturities=None):
    p = mat_path(years)
    if not os.path.exists(p):
        log("run stage 1 first")
        return
    m = pd.read_csv(p, index_col=0, parse_dates=True)
    m.columns = [float(c) for c in m.columns]
    m, full, dropped, n_bad_rows = balanced(m, min_coverage, maturities)
    log(f"\nB30-17 stage 2.  balanced panel: {m.shape[0]} days x {m.shape[1]} "
        f"maturities {[round(c, 4) for c in full]}")
    if dropped:
        log(f"  maturities dropped below {min_coverage:.0%} coverage "
            f"(maturity, obs, first date): {dropped}")
    if n_bad_rows:
        log(f"  {n_bad_rows} day(s) dropped for a gap in a kept maturity")
    if m.shape[1] < 3 or m.shape[0] < 100:
        log("  panel too small to read. Widen --min-coverage or pick --maturities.")
        return
    rng = np.random.default_rng(seed)
    out = []
    out.append(_pca_report(m.values, "LEVELS", FLOOR_LEVEL_BP, rng, n_shuffle))
    dm = m.diff().dropna()
    out.append(_pca_report(dm.values, "DAILY CHANGES", FLOOR_CHANGE_BP, rng,
                           n_shuffle))
    f = os.path.join(OUT, f"stage2_{min(years)}_{max(years)}.json")
    _json_write(dict(years=[min(years), max(years)],
                     maturities=[float(c) for c in full], results=out), f)
    log(f"\nwritten {f}")
    log("Read against design file 4.9. Do not restate the criteria here.")



BASE11 = [1/12, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]


def _pick(m, mats):
    return [c for c in m.columns if any(abs(c - t) < 1e-6 for t in mats)]


def _k_for(X, target=0.99):
    Xc = X - X.mean(axis=0, keepdims=True)
    sv = np.linalg.svd(Xc, compute_uv=False) ** 2
    cum = np.cumsum(sv / sv.sum())
    return int(np.searchsorted(cum, target) + 1), float(cum[min(2, len(cum) - 1)])


def _loo_predict(m, col, floor_bp, folds=5, seed=0):
    """Predict one maturity from the others and report the residual in bp.

    The direct form of the column-addition question: if a maturity is a linear
    function of the rest to within the printed grid, it carries nothing that the
    rest do not already carry. Split-sample so the answer is not a fit.
    """
    others = [c for c in m.columns if c != col]
    X = m[others].values
    y = m[col].values
    n = len(y)
    rng = np.random.default_rng(seed)
    fold = rng.integers(0, folds, n)
    resid = np.empty(n)
    for f in range(folds):
        tr, te = fold != f, fold == f
        A = np.hstack([np.ones((tr.sum(), 1)), X[tr]])
        beta, *_ = np.linalg.lstsq(A, y[tr], rcond=None)
        B = np.hstack([np.ones((te.sum(), 1)), X[te]])
        resid[te] = y[te] - B @ beta
    rms_bp = float(np.sqrt((resid ** 2).mean()) * 100.0)
    return rms_bp, rms_bp / floor_bp


def stage3(years, seed=0):
    p = mat_path(years)
    if not os.path.exists(p):
        log("run stage 1 first")
        return
    m = pd.read_csv(p, index_col=0, parse_dates=True)
    m.columns = [float(c) for c in m.columns]

    log("\nB30-17 stage 3, part A: can each maturity be predicted from the rest")
    log("  split-sample, five folds. Residual in basis points against the floor.")
    for label, tf, floor in (("LEVELS", lambda d: d, FLOOR_LEVEL_BP),
                             ("CHANGES", lambda d: d.diff().dropna(),
                              FLOOR_CHANGE_BP)):
        sub = m[_pick(m, BASE11)].dropna()
        sub = tf(sub)
        log(f"\n  {label}: {len(sub)} rows, floor {floor:.4f} bp")
        for c in sub.columns:
            rms, over = _loo_predict(sub, c, floor, seed=seed)
            log(f"    {c:8.4f} yr   resid {rms:8.3f} bp   {over:8.2f} x floor")

    log("\n\nB30-17 stage 3, part B: does adding a column raise the factor count")
    log("  registered in design file 4.9. Base set is the eleven always-present")
    log("  maturities. k is the factors needed to reach 99 per cent.")
    tests = [
        ("2 month added 2018-10-16", 2/12,
         ("2016-01-01", "2018-10-15"), ("2018-10-16", "2022-10-18")),
        ("4 month added 2022-10-19", 4/12,
         ("2018-10-16", "2022-10-18"), ("2022-10-19", "2024-12-31")),
    ]
    rows = []
    for name, newmat, (a0, a1), (b0, b1) in tests:
        base = _pick(m, BASE11)
        newc = _pick(m, [newmat])
        if not newc:
            log(f"\n  {name}: column not in the panel, skipped")
            continue
        A = m.loc[a0:a1, base].dropna()
        Bb = m.loc[b0:b1, base].dropna()
        Bp = m.loc[b0:b1, base + newc].dropna()
        for label, tf in (("levels", lambda d: d),
                          ("changes", lambda d: d.diff().dropna())):
            kA, c3A = _k_for(tf(A).values)
            kB, c3B = _k_for(tf(Bb).values)
            kBp, c3Bp = _k_for(tf(Bp).values)
            rows.append(dict(test=name, quantity=label,
                             n_before=len(A), n_after=len(Bb),
                             k_before_base=kA, k_after_base=kB,
                             k_after_with_new=kBp,
                             cum3_after_base=c3B, cum3_after_with_new=c3Bp,
                             raised=int(kBp > kB)))
        sub = m.loc[b0:b1, base + newc].dropna()
        rms, over = _loo_predict(sub, newc[0], FLOOR_LEVEL_BP, seed=seed)
        d = sub.diff().dropna()
        rms_d, over_d = _loo_predict(d, newc[0], FLOOR_CHANGE_BP, seed=seed)
        log(f"\n  {name}")
        log(f"    predicted from the other eleven, levels  "
            f"{rms:7.3f} bp = {over:6.2f} x floor")
        log(f"    predicted from the other eleven, changes "
            f"{rms_d:7.3f} bp = {over_d:6.2f} x floor")
    if rows:
        df = pd.DataFrame(rows)
        log("")
        log(df[["test", "quantity", "n_before", "n_after", "k_before_base",
                "k_after_base", "k_after_with_new", "raised"]].to_string(index=False))
        _json_write(rows, os.path.join(OUT, "stage3_column_addition.json"))
    log("\nRead against design file 4.9. Do not restate the criteria here.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, default=1)
    ap.add_argument("--years", default="2010-2024")
    ap.add_argument("--shuffle", type=int, default=10)
    ap.add_argument("--min-coverage", type=float, default=0.99,
                    dest="min_coverage")
    ap.add_argument("--maturities", default="",
                    help="comma separated years, e.g. 0.0833,0.25,0.5,1,2,3,5,7,10,20,30")
    a = ap.parse_args()
    if "-" in a.years:
        lo, hi = a.years.split("-")
        yrs = list(range(int(lo), int(hi) + 1))
    else:
        yrs = [int(x) for x in a.years.split(",")]
    if a.stage == 1:
        stage1(yrs)
    elif a.stage == 2:
        mats = [float(x) for x in a.maturities.split(",")] if a.maturities else None
        stage2(yrs, n_shuffle=a.shuffle, min_coverage=a.min_coverage,
               maturities=mats)
    elif a.stage == 3:
        stage3(yrs)
    else:
        log("no such stage")
