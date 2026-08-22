"""B16 step B: rho, the placebo band, and the arm's three-way reading.

The criteria below were registered before the run, and none was changed after it.
Upstream: b16_bbo_probe.py established that every one of 17,322,270 records is
two-sided, that nothing is crossed or locked, and that the pre window carries
1,357,797 paired seconds across the 63 symbols.

WHAT IS COMPUTED

    S - S'  =  2 log(mid_b / mid_a)                      the index half
    S + S'  =  log(bid_a/ask_a) + log(bid_b/ask_b)       the friction half
    rho     =  |S - S'| / -(S + S')                      in [0,1] by Theorem 6(4)

per paired second, then the median over a symbol's seconds in a window, then the
median across symbols. log R = log(rho_post / rho_pre) is the arm's one number.

THE BAND IS PRINTED BEFORE THE READING

Twenty placebo sub-windows, ten with a boundary at offsets -19..-10 and ten at
+10..+19, each a 10+10 pair entirely inside the 29+29 that was bought. No
sampling, no permutation, no seed: "how many draws" is not a question this design
has. The band is the [10%, 90%] of those twenty numbers.

The band is printed first and the real reading second, so that whoever reads the
output sees the null before the number it is judged against. Nothing about the
band depends on the real reading, so this is presentation, not protection.

THE DOMAIN, AND WHY SECONDS ARE DROPPED BY A REGISTERED RULE

Theorem 6(4) bounds rho by 1 only where P(w) is non-empty, that is, where no
cross-venue arbitrage is available at that instant. A second with rho > 1 is
outside the framework's own domain, not a bad observation. Those seconds are
excluded, the count and rate are printed for every window, and the SAME rule runs
on the placebo sub-windows. An exclusion applied to the reading but not to the
null would manufacture the answer.

    python experiments/b16_rho.py --selftest    no data
    python experiments/b16_rho.py --run         reads 4.7 GB, prints band then reading
"""
import argparse
import ast
import bisect
import datetime
import gzip
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
RAW = os.path.join(ROOT, "data", "raw", "b16_bbo")
CAL_CACHE = os.path.join(RESULTS, "b16_trading_calendar.json")
UNIVERSE = os.path.join(RESULTS, "b16_universe.json")
OUT = os.path.join(RESULTS, "b16_e5_rho.json")

ARM = 5
BOUNDARY = "2023-02-23"
DR = -14.90e-6                       # registered, e5
VENUE_A = "XNAS.ITCH"
VENUE_B = "ARCX.PILLAR"
UTC = datetime.timezone.utc

RTH_OPEN = datetime.time(9, 30)
RTH_CLOSE = datetime.time(16, 0)
RTH_SECONDS = 6 * 3600 + 30 * 60

#: Registered. The boundary day opens the post side.
HALF = 10
BOUGHT_EACH_SIDE = 29
REF_WINDOW = (-20, -11)
#: Registered: twenty sub-windows, ten a side, each 10+10 inside the 29+29.
#: -19..-10 and +10..+19 are the only offsets for which both halves fit.
PLACEBO_PRE = tuple(range(-19, -9))
PLACEBO_POST = tuple(range(10, 20))
BAND_LO, BAND_HI = 10.0, 90.0

UNDEF = 9223372036854775807
PX_SCALE = 1e-9


# ---------------------------------------------------------------- calendar

def load_calendar():
    if not os.path.exists(CAL_CACHE):
        raise SystemExit("no %s." % os.path.relpath(CAL_CACHE, ROOT))
    return json.load(open(CAL_CACHE, encoding="utf-8"))["days"]


def load_universe():
    if not os.path.exists(UNIVERSE):
        raise SystemExit("no %s." % os.path.relpath(UNIVERSE, ROOT))
    return json.load(open(UNIVERSE, encoding="utf-8"))


def arm_symbols(ev):
    out = []
    for r in ev["symbols"]:
        t = r[0] if isinstance(r, (list, tuple)) else r
        if not isinstance(t, str) or not t:
            raise SystemExit("bad ticker %r" % (r,))
        out.append(t)
    return out


def _nth_sunday(year, month, n):
    first = datetime.date(year, month, 1)
    return datetime.date(year, month, 1 + (6 - first.weekday()) % 7 + 7 * (n - 1))


def et_offset_hours(day):
    d = datetime.date(int(day[:4]), int(day[4:6]), int(day[6:]))
    return -4 if _nth_sunday(d.year, 3, 2) <= d < _nth_sunday(d.year, 11, 1) else -5


def rth_bounds_ns(day):
    d = datetime.date(int(day[:4]), int(day[4:6]), int(day[6:]))
    out = []
    for t in (RTH_OPEN, RTH_CLOSE):
        naive = datetime.datetime.combine(d, t, UTC)
        out.append(int((naive - datetime.timedelta(
            hours=et_offset_hours(day))).timestamp()) * 10**9)
    return out[0], out[1]


def offsets_to_days(days, boundary, lo, hi):
    b = boundary.replace("-", "")
    before = [d for d in days if d < b]
    after = [d for d in days if d >= b]
    out = []
    for k in range(lo, hi + 1):
        out.append(after[k] if k >= 0 else before[k])
    return out


def window_for(days, boundary, k):
    """The 10+10 pair whose boundary sits at offset k. Returns (pre, post)."""
    return (offsets_to_days(days, boundary, k - HALF, k - 1),
            offsets_to_days(days, boundary, k, k + HALF - 1))


# ---------------------------------------------------------------- the scan

def month_of(day):
    return "%s-%s" % (day[:4], day[4:6])


def batch_path(venue, month):
    return os.path.join(RAW, "bbo-1s_%s_e%d_%s.csv.gz"
                        % (venue.replace(".", "_"), ARM, month.replace("-", "")))


def scan(days, want):
    """rho per paired second, kept per (symbol, day). One month at a time, so the
    venue-A side never holds more than one month of arrays."""
    span = offsets_to_days(days, BOUNDARY, -BOUGHT_EACH_SIDE, BOUGHT_EACH_SIDE - 1)
    months = sorted({month_of(d) for d in span})
    rho = {}
    denom = {}
    #: (symbol, day, venue) -> [sum of relative spread, count]. Consumed by
    #: b16_xsec.py for the first segment's cross-sectional regression. It lives
    #: here rather than in a second scanner so there is one reader of the gz and
    #: one place to fix when it is wrong.
    relsum = {}
    n_pair = n_viol = 0

    for mm in months:
        mdays = [d for d in span if month_of(d) == mm]
        if not mdays:
            continue
        bounds = {d: rth_bounds_ns(d)[0] for d in mdays}
        dayset = set(mdays)

        # ---- venue A into dense per (symbol, day) arrays
        mid_a, spr_a = {}, {}
        pa = batch_path(VENUE_A, mm)
        if not os.path.exists(pa):
            raise SystemExit("missing %s" % os.path.relpath(pa, ROOT))
        los = sorted(bounds.values())
        lo2day = {v: k for k, v in bounds.items()}
        for path, venue in ((pa, VENUE_A), (batch_path(VENUE_B, mm), VENUE_B)):
            if not os.path.exists(path):
                raise SystemExit("missing %s" % os.path.relpath(path, ROOT))
            with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
                head = fh.readline().rstrip("\n").split(",")
                ix = {c: i for i, c in enumerate(head)}
                i_ts, i_b, i_a, i_s = (ix["ts_recv"], ix["bid_px_00"],
                                       ix["ask_px_00"], ix["symbol"])
                for line in fh:
                    f = line.rstrip("\n").split(",")
                    sym = f[i_s]
                    if sym not in want:
                        continue
                    b, a = int(f[i_b]), int(f[i_a])
                    if b == UNDEF or a == UNDEF or a <= b:
                        continue
                    ts = int(f[i_ts])
                    j = bisect.bisect_right(los, ts) - 1
                    if j < 0:
                        continue
                    lo = los[j]
                    off = (ts - lo) // 10**9
                    if off < 0 or off >= RTH_SECONDS:
                        continue
                    day = lo2day[lo]
                    if day not in dayset:
                        continue
                    bp, ap = b * PX_SCALE, a * PX_SCALE
                    mid = 0.5 * (bp + ap)
                    lsp = math.log(ap / bp)          # -log(bid/ask), positive
                    key = (sym, day)
                    rk = (sym, day, venue)
                    rr = relsum.get(rk)
                    if rr is None:
                        rr = relsum[rk] = [0.0, 0]
                    rr[0] += (ap - bp) / mid
                    rr[1] += 1
                    if venue == VENUE_A:
                        arr = mid_a.get(key)
                        if arr is None:
                            arr = mid_a[key] = np.full(RTH_SECONDS, np.nan, np.float64)
                            spr_a[key] = np.full(RTH_SECONDS, np.nan, np.float64)
                        arr[off] = mid
                        spr_a[key][off] = lsp
                    else:
                        ma = mid_a.get(key)
                        if ma is None:
                            continue
                        m_a = ma[off]
                        if m_a != m_a:                 # NaN, venue A silent here
                            continue
                        num = abs(2.0 * math.log(mid / m_a))
                        den = spr_a[key][off] + lsp
                        n_pair += 1
                        r_ = num / den
                        if r_ > 1.0:
                            n_viol += 1
                            continue                   # outside the domain
                        rho.setdefault(key, []).append(r_)
                        denom.setdefault(key, []).append(den)
            print("  %-12s %s" % (venue, os.path.basename(path)))
        del mid_a, spr_a

    rho = {k: np.asarray(v, np.float64) for k, v in rho.items()}
    denom = {k: np.asarray(v, np.float64) for k, v in denom.items()}
    return rho, denom, relsum, n_pair, n_viol


# ---------------------------------------------------------------- statistics

def window_median_per_symbol(store, syms, wdays):
    out = {}
    for s in syms:
        parts = [store[(s, d)] for d in wdays if (s, d) in store]
        if not parts:
            continue
        out[s] = float(np.median(np.concatenate(parts)))
    return out


def reading(store, syms, days, k):
    """(cross-sectional median pre, post, log ratio, n symbols) at boundary k."""
    pre, post = window_for(days, BOUNDARY, k)
    a = window_median_per_symbol(store, syms, pre)
    b = window_median_per_symbol(store, syms, post)
    common = sorted(set(a) & set(b))
    if not common:
        return None
    va = float(np.median([a[s] for s in common]))
    vb = float(np.median([b[s] for s in common]))
    if va <= 0 or vb <= 0:
        return None
    return va, vb, math.log(vb / va), len(common)


def band(vals):
    lo, hi = np.percentile(np.asarray(vals, np.float64), [BAND_LO, BAND_HI],
                           method="linear")
    return float(lo), float(hi)


def run():
    days = load_calendar()
    uni = load_universe()
    syms = sorted(arm_symbols(uni["events"][str(ARM)]))
    print("B16 arm e%d   boundary %s   dr %+.2fe-6   %d symbols"
          % (ARM, BOUNDARY, DR * 1e6, len(syms)))
    print("venues %s / %s   schema bbo-1s   session 09:30-16:00 ET\n"
          % (VENUE_A, VENUE_B))
    rho, denom, _relsum, n_pair, n_viol = scan(days, set(syms))
    print("\n  paired seconds %d   outside the Theorem 6(4) domain (rho > 1)"
          " %d, %.4f%%" % (n_pair, n_viol, 100.0 * n_viol / max(1, n_pair)))
    print("  the same exclusion runs on the placebo sub-windows.")

    # ---- the band, printed first
    print("\n=== PLACEBO BAND (printed before the reading) ===")
    rows = []
    for k in list(PLACEBO_PRE) + list(PLACEBO_POST):
        r = reading(rho, syms, days, k)
        if r is None:
            print("  offset %+3d   no reading" % k)
            continue
        rows.append((k, r))
        print("  offset %+3d   rho_pre %.6f  rho_post %.6f  log R %+.6f  n %d"
              % (k, r[0], r[1], r[2], r[3]))
    vals = [r[2] for _, r in rows]
    blo, bhi = band(vals)
    half = 0.5 * (bhi - blo)
    print("\n  %d sub-windows   band [%.0f%%, %.0f%%] = [%+.6f, %+.6f]"
          % (len(vals), BAND_LO, BAND_HI, blo, bhi))
    print("  half width %.6f   min %+.6f   max %+.6f"
          % (half, min(vals), max(vals)))

    # ---- the denominator, gate one's statistic for this arm
    print("\n=== GATE ONE, the friction half ===")
    drows = []
    for k in list(PLACEBO_PRE) + list(PLACEBO_POST):
        r = reading(denom, syms, days, k)
        if r is not None:
            drows.append(r[2])
    dlo, dhi = band(drows)
    dreal = reading(denom, syms, days, 0)
    if dreal is None:
        raise SystemExit("the friction half has no reading at the real boundary")
    print("  placebo band on log[-(S+S')] = [%+.6f, %+.6f], half width %.6f"
          % (dlo, dhi, 0.5 * (dhi - dlo)))
    print("  real: pre %.6f  post %.6f  log move %+.6f"
          % (dreal[0], dreal[1], dreal[2]))
    out_d = not (dlo <= dreal[2] <= dhi)
    print("  the friction half moved outside its band: %s" % ("YES" if out_d else "no"))
    print("  predicted move if theta = 1:  2*dr/(s/M) with s/M = %.6f  ->  %+.6f"
          % (dreal[0] / 2.0, 2.0 * DR / (dreal[0] / 2.0)))

    # ---- the reading
    print("\n=== READING ===")
    real = reading(rho, syms, days, 0)
    print("  rho_pre %.6f   rho_post %.6f   log R %+.6f   n %d"
          % (real[0], real[1], real[2], real[3]))
    framework_side = -1 if DR > 0 else +1
    inside = blo <= real[2] <= bhi
    if inside:
        cell = "B  the arm is not adjudicable (inside the band, no power)"
    elif (real[2] > 0) == (framework_side > 0):
        cell = "A  the arm is consistent with the framework"
    else:
        cell = "C  the arm is consistent with the opponent"
    print("  band [%+.6f, %+.6f]   framework side: %s"
          % (blo, bhi, "positive" if framework_side > 0 else "negative"))
    print("\n  CELL %s" % cell)
    print("\n  This is one arm of six. Cell A here is not a station result:")
    print("  the registration reports the six-tuple, and does not fold it into a rate.")
    print("\n  PROVISIONAL. Gate three, the transmission-symmetry correction")
    print("  C_e = (theta_b - theta_a) * dr * M / (s_b - s_a), is NOT computed")
    print("  here: it needs the first segment's per-venue regression, which is a")
    print("  separate step. The cell above can move when it runs.")

    json.dump({"arm": ARM, "boundary": BOUNDARY, "dr": DR,
               "venues": [VENUE_A, VENUE_B], "n_symbols": len(syms),
               "paired_seconds": n_pair, "domain_excluded": n_viol,
               "placebo": [{"offset": k, "rho_pre": r[0], "rho_post": r[1],
                            "log_R": r[2], "n": r[3]} for k, r in rows],
               "band": [blo, bhi], "band_half_width": half,
               "reading": {"rho_pre": real[0], "rho_post": real[1],
                           "log_R": real[2], "n": real[3]},
               "cell": cell[0],
               "friction": {"band": [dlo, dhi], "pre": dreal[0],
                            "post": dreal[1], "log_move": dreal[2],
                            "outside": bool(out_d)}},
              open(OUT, "w", encoding="utf-8", newline="\n"),
              indent=2, sort_keys=True)
    print("\n  wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


# ---------------------------------------------------------------- selftest

def selftest():
    fails = []

    def chk(label, cond):
        print(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            fails.append(label)

    # the decomposition, on numbers a reader can check by hand
    ba, aa, bb, ab = 100.00, 100.10, 100.02, 100.14
    mid_a, mid_b = (ba + aa) / 2, (bb + ab) / 2
    num = abs(2 * math.log(mid_b / mid_a))
    den = math.log(aa / ba) + math.log(ab / bb)
    chk("1  S - S' is 2 log(mid_b/mid_a) and is positive when b sits above a",
        abs(num - 2 * math.log(mid_b / mid_a)) < 1e-15 and mid_b > mid_a)
    chk("2  -(S + S') is the sum of the two log spreads and is positive",
        den > 0 and abs(den - (math.log(aa / ba) + math.log(ab / bb))) < 1e-15)
    chk("3  rho lands in [0,1] on this pair (%.4f)" % (num / den), 0 <= num / den <= 1)
    # the bound is tight: push the mids apart until rho crosses 1
    far = 100.0 * math.exp(den / 2.0)
    chk("4  Theorem 6(4) is tight: rho == 1 exactly when the mid gap equals half"
        " the summed spread",
        abs(abs(2 * math.log(far / 100.0)) / den - 1.0) < 1e-12)

    days = load_calendar() if os.path.exists(CAL_CACHE) else None
    if days:
        pre, post = window_for(days, BOUNDARY, 0)
        chk("5  the real windows are 10 + 10 and the boundary opens the post side",
            len(pre) == len(post) == HALF and post[0] == BOUNDARY.replace("-", ""))
        chk("6  twenty placebo sub-windows, ten a side",
            len(PLACEBO_PRE) == 10 and len(PLACEBO_POST) == 10)
        bought = set(offsets_to_days(days, BOUNDARY, -BOUGHT_EACH_SIDE,
                                     BOUGHT_EACH_SIDE - 1))
        allin = True
        for k in list(PLACEBO_PRE) + list(PLACEBO_POST):
            a, b = window_for(days, BOUNDARY, k)
            allin = allin and set(a + b) <= bought
        chk("7  every placebo sub-window sits inside the 29+29 that was bought",
            allin)
        chk("8  no placebo sub-window straddles the real boundary",
            all(max(window_for(days, BOUNDARY, k)[1]) < BOUNDARY.replace("-", "")
                for k in PLACEBO_PRE)
            and all(min(window_for(days, BOUNDARY, k)[0]) >= BOUNDARY.replace("-", "")
                    for k in PLACEBO_POST))
        chk("9  the reference window is untouched by this file: it belongs to the"
            " transmission segment, which does not score",
            REF_WINDOW == (-20, -11))

    chk("10 dr for e5 is the registered -14.90e-6, so the framework side is"
        " positive log R", abs(DR - (-14.90e-6)) < 1e-12 and (-1 if DR > 0 else 1) > 0)
    chk("11 the band is the registered [10%, 90%] with a stated method",
        (BAND_LO, BAND_HI) == (10.0, 90.0))

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = ast.parse(src)
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            mods.add(n.module.split(".")[0])
    chk("12 no randomness is imported: this design has no draw count and no seed",
        "random" not in mods)
    calls = {getattr(c.func, "attr", None) for c in ast.walk(tree)
             if isinstance(c, ast.Call)}
    chk("13 nothing here deletes anything (AST walk)",
        not ({"remove", "unlink", "rmtree", "rmdir"} & calls))
    #: AST, scoped to scan(). A substring count would find its own text here,
    #: which is the self-check pitfall this repository has paid for eight times.
    scan_fn = next(n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "scan")
    bumps = sum(1 for n in ast.walk(scan_fn)
                if isinstance(n, ast.AugAssign)
                and isinstance(n.target, ast.Name) and n.target.id == "n_viol")
    chk("14 the domain exclusion is incremented in exactly one place inside"
        " scan(), so it cannot differ between the reading and the null (found %d)"
        % bumps, bumps == 1)

    v = [float(x) for x in range(20)]
    lo, hi = band(v)
    chk("15 the band on 0..19 is deterministic and reproducible (%.3f, %.3f)"
        % (lo, hi), abs(lo - 1.9) < 1e-9 and abs(hi - 17.1) < 1e-9)

    print("\nselftest: %s" % ("PASS" if not fails else "FAIL (%d)" % len(fails)))
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.run:
        return run()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
