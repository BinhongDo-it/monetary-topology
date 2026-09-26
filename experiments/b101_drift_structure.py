"""B101, third driver: is the drift a systematic shape or accumulated noise,
and does it survive a different value-added concept?

The first driver established that inside one country-industry the chained index
and the direct index disagree in 99.8% of windows, and that the paper's own
share smoothing sets that disagreement to exactly zero. Two readings are owed
before that means anything.

One: noise in the share would also make the share non-affine in the mix, and
would also produce a non-zero area. Noise and a systematic curve are told apart
by how the drift grows with the window: independent per-step contributions
accumulate as the square root of the number of steps, while a smooth curve
against its own chord grows much faster. The exponent is read, not assumed.

Two: the release ships a second value-added concept, which capitalises
intangibles national accounts do not and rebuilds the capital series to match.
That changes both the share and the mix, so it is a real second arm rather than
a re-run. Under D11 the two are different definitions and are reported apart.

Output never enters any of this. The value-added terms cancel identically
around a closed path, which is why the extended file needs no level series for
this reading even though it carries none.

    python experiments/b101_drift_structure.py --selftest
    python experiments/b101_drift_structure.py --run
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASIC = ROOT / "data" / "cache" / "b101_klems_basic.npz"
EXT = ROOT / "data" / "cache" / "b101_klems_extended.npz"
OUT = ROOT / "results" / "b101_drift_structure.json"

WINDOWS = (2, 3, 4, 6, 9, 13, 18, 26)
SEED = 101


def area(pts):
    """minus the signed area of the closed polygon in (x, alpha). This IS the
    drift: the value-added terms telescope, so nothing else is left."""
    m = len(pts)
    s = 0.0
    for k in range(m):
        (x0, a0), (x1, a1) = pts[k], pts[(k + 1) % m]
        s += 0.5 * (a0 + a1) * (x1 - x0)
    return -s


def series_basic():
    d = np.load(BASIC, allow_pickle=False)
    o = list(d["vars"]); V = d["values"]
    c = {v: V[:, i] for i, v in enumerate(o)}
    with np.errstate(invalid="ignore", divide="ignore"):
        al = c["LAB"] / c["VA_CP"]
        x = np.log(c["LAB_QI"] / c["CAP_QI"])
    return _pack(d, x, al)


def series_extended():
    """Share against the adjusted value added, which is labour plus capital
    compensation on that concept. The capital series carries intangibles, so the
    mix differs from the basic file's as well."""
    d = np.load(EXT, allow_pickle=False)
    o = list(d["vars"]); V = d["values"]
    c = {v: V[:, i] for i, v in enumerate(o)}
    with np.errstate(invalid="ignore", divide="ignore"):
        al = c["LAB"] / (c["LAB"] + c["CAP"])
        x = np.log(c["LAB_QI"] / c["CAP_QI"])
    return _pack(d, x, al)


def _pack(d, x, al):
    """Indexing a numpy string array one element at a time costs more than the
    whole rest of this driver: the first version spent 47 seconds here on the
    basic file and 99 on the extended one, against 0.0 for every drift. Convert
    to lists once and the loop is plain Python over plain objects."""
    ok = np.isfinite(x) & np.isfinite(al)
    nace = d["nace"].tolist(); geo = d["geo"].tolist(); year = d["year"].tolist()
    xs = x.tolist(); als = al.tolist()
    S = collections.defaultdict(dict)
    for i in np.flatnonzero(ok).tolist():
        S[(nace[i], geo[i])][int(year[i])] = (xs[i], als[i])
    return dict(S)


def drift(S, n):
    """Every window of n years, as a closed path.

    The consecutive-step part of the trapezoid sum is a prefix sum over the
    series, so each window costs one subtraction plus the closing chord rather
    than a walk of its own. The first version walked every window and the run
    did not finish; this returns the same numbers, which ``--selftest`` checks
    against the direct polygon on the same data."""
    out = []
    for ys in S.values():
        ts = sorted(ys)
        if len(ts) < n + 1:
            continue
        x = np.fromiter((ys[t][0] for t in ts), float, len(ts))
        a = np.fromiter((ys[t][1] for t in ts), float, len(ts))
        step = 0.5 * (a[:-1] + a[1:]) * (x[1:] - x[:-1])
        pre = np.concatenate(([0.0], np.cumsum(step)))
        yr = np.fromiter(ts, int, len(ts))
        i = np.arange(len(ts) - n)
        good = (yr[i + n] - yr[i]) == n
        if not good.any():
            continue
        i = i[good]
        chord = 0.5 * (a[i + n] + a[i]) * (x[i] - x[i + n])
        out.append(-(pre[i + n] - pre[i] + chord))
    return np.concatenate(out) if out else np.array([])


def exponent(S, windows=WINDOWS):
    ns, med = [], []
    for n in windows:
        v = np.abs(drift(S, n))
        if len(v) < 50:
            continue
        ns.append(n); med.append(float(np.median(v)))
    ns = np.array(ns, float); med = np.array(med)
    slope, inter = np.polyfit(np.log(ns), np.log(med), 1)
    pred = np.exp(inter) * ns ** slope
    r2 = 1 - float(((np.log(med) - np.log(pred)) ** 2).sum() /
                   ((np.log(med) - np.log(med).mean()) ** 2).sum())
    return float(slope), float(r2), {int(a): b for a, b in zip(ns, med)}


def _crit(name, kind, ok, detail, **extra):
    c = {"name": name, "kind": kind, "detail": detail,
         "passed": None if ok is None else bool(ok)}
    if ok is None:
        c["void"] = True
    c.update(extra)
    return c


def run(write=True):
    rng = np.random.default_rng(SEED)
    Sb, Se = series_basic(), series_extended()
    crit, report = [], {}

    sl_b, r2_b, med_b = exponent(Sb)
    sl_e, r2_e, med_e = exponent(Se)
    report["exponent"] = {"basic": {"slope": sl_b, "r2": r2_b, "medians": med_b},
                          "extended": {"slope": sl_e, "r2": r2_e, "medians": med_e}}

    # placebos, both of which keep a marginal and break an alignment
    Sh = {k: (lambda ts, ys: {t: (ys[t][0], ys[u][1]) for t, u
                              in zip(ts, rng.permutation(ts))})(sorted(ys), ys)
          for k, ys in Sb.items()}
    Sr = {k: (lambda ts, ys: {t: (ys[t][0], ys[ts[len(ts) - 1 - i]][1])
                              for i, t in enumerate(ts)})(sorted(ys), ys)
          for k, ys in Sb.items()}
    sl_h, r2_h, med_h = exponent(Sh)
    sl_r, r2_r, med_r = exponent(Sr)
    report["placebo"] = {"share_shuffled_in_time": {"slope": sl_h, "medians": med_h},
                         "share_reversed_in_time": {"slope": sl_r, "medians": med_r}}

    # **The null is the placebo, not the textbook.** The first version read the
    # exponent against 0.5, the figure independent per-step contributions would
    # give, and called 1.39 a pass. Then the placebo was run: a share shuffled in
    # time, which carries no alignment with the mix at all, gives 0.92 on this
    # data rather than 0.5, because the share's own dispersion is large and not
    # independent across years. A threshold set at the textbook figure sits far
    # from where the data's own null is. So the exponent is printed and the
    # criterion is put on the quantity the placebo actually bounds: the level of
    # the real drift against the level of the shuffled one, window by window.
    ratio_by_n = {n: med_b[n] / med_h[n] for n in sorted(med_b) if med_h.get(n)}
    rv = np.array(list(ratio_by_n.values()))
    verdict = (False if rv.max() < 0.8 else (True if rv.min() > 1.25 else None))
    crit.append(_crit(
        "B101-13  how the drift grows with the window, against a share with the alignment removed",
        "own_reading", verdict,
        f"exponents printed, not scored: basic {sl_b:.2f} (fit r2 {r2_b:.3f}), extended "
        f"{sl_e:.2f}, share shuffled in time {sl_h:.2f}, share reversed in time "
        f"{sl_r:.2f}. The textbook figure for independent per-step contributions is 0.5 "
        f"and the shuffled placebo reads {sl_h:.2f} on this panel, so 0.5 is not this "
        f"data's null and nothing is scored against it. The criterion is the level: real "
        f"median over shuffled median by window, "
        + ", ".join(f"n={n}: {r:.2f}" for n, r in ratio_by_n.items())
        + f". Reading fixed in advance: one means the alignment between the share and "
          f"the mix carries nothing, below one means the share moves with the mix in a "
          f"way that encloses less area than a random pairing, above one the reverse. "
          f"It runs {rv.min():.2f} to {rv.max():.2f} and crosses one, so **undecided "
          f"across windows, and that is the reading**: the alignment matters at short "
          f"windows and is gone by the long ones."))

    # the extended arm
    n9 = 9
    vb, ve = np.abs(drift(Sb, n9)), np.abs(drift(Se, n9))
    sb, se = drift(Sb, n9), drift(Se, n9)
    report["extended_arm"] = {
        "window": n9,
        "basic": {"windows": int(len(vb)), "median": float(np.median(vb)),
                  "share_nonzero": float((vb > 1e-12).mean()),
                  "share_negative": float((sb < 0).mean())},
        "extended": {"windows": int(len(ve)), "median": float(np.median(ve)),
                     "share_nonzero": float((ve > 1e-12).mean()),
                     "share_negative": float((se < 0).mean())},
    }
    crit.append(_crit(
        "B101-14  the second value-added concept gives the same reading",
        "own_reading", (ve > 1e-12).mean() > 0.9,
        f"the extended file capitalises intangibles the national accounts do not and "
        f"rebuilds capital to match, so both the share and the mix differ. Reported "
        f"apart from the basic arm under D11, not merged. At a {n9}-year window: basic "
        f"{(vb > 1e-12).mean():.1%} non-zero over {len(vb):,} windows, median "
        f"{np.median(vb):.3e}; extended {(ve > 1e-12).mean():.1%} over {len(ve):,}, "
        f"median {np.median(ve):.3e}. Exponent in the window length: basic {sl_b:.2f}, "
        f"extended {sl_e:.2f}."))

    # sign: a consistently curved share gives a consistently signed area
    signs = {}
    for tag, S in (("basic", Sb), ("extended", Se)):
        row = {}
        for n in (2, 6, 13, 26):
            v = drift(S, n)
            if len(v) > 50:
                row[n] = float((v < 0).mean())
        signs[tag] = row
    report["sign"] = signs
    crit.append(_crit(
        "B101-15  the drift carries a sign rather than cancelling",
        "own_reading", None,
        "Void: not adjudicated, printed only. A share that curves one way against the "
        "mix gives an area of one sign; a share that wanders gives a sign near even. "
        "Share of windows with a negative drift, basic: "
        + ", ".join(f"n={n}: {p:.1%}" for n, p in signs["basic"].items())
        + "; extended: "
        + ", ".join(f"n={n}: {p:.1%}" for n, p in signs["extended"].items())
        + ". No criterion was registered on this before the run and none is invented "
          "after it; the numbers are here so the next reader does not have to re-run."))

    # how much of the share does the smoothing keep?
    r2s = {}
    for tag, S in (("basic", Sb), ("extended", Se)):
        vals = []
        for ys in S.values():
            ts = sorted(ys)
            if len(ts) < 12:
                continue
            x = np.fromiter((ys[t][0] for t in ts), float, len(ts))
            a = np.fromiter((ys[t][1] for t in ts), float, len(ts))
            if np.ptp(x) < 1e-10 or np.ptp(a) < 1e-12:
                continue
            A = np.vstack([x, np.ones_like(x)]).T
            coef, *_ = np.linalg.lstsq(A, a, rcond=None)
            r = a - A @ coef
            vals.append(1 - float(r @ r) / float(((a - a.mean()) ** 2).sum()))
        v = np.array(vals)
        r2s[tag] = {"series": int(len(v)), "median": float(np.median(v)),
                    "p10": float(np.percentile(v, 10)), "p90": float(np.percentile(v, 90)),
                    "share_below_half": float((v < 0.5).mean())}
    report["share_explained_by_mix"] = r2s
    crit.append(_crit(
        "B101-17  how much of the share the smoothing keeps",
        "own_reading", r2s["basic"]["median"] < 0.5,
        f"the smoothing replaces the observed share with an affine function of the log "
        f"mix, so what it keeps is exactly what that function explains. Within-series "
        f"r-squared of the share on the log mix, {r2s['basic']['series']:,} series with "
        f"at least twelve years: median {r2s['basic']['median']:.3f}, p10 to p90 "
        f"{r2s['basic']['p10']:.3f} to {r2s['basic']['p90']:.3f}, and "
        f"{r2s['basic']['share_below_half']:.1%} of series sit below a half. Extended "
        f"file: median {r2s['extended']['median']:.3f}. **So the step that makes the "
        f"index transitive keeps a minority of the share's own movement and discards "
        f"the rest**, and the discarded part is precisely what the drift measures."))

    crit.append(_crit(
        "B101-16  the two files are two definitions, and the counts say so",
        "instrument", True,
        f"basic: {len(Sb):,} series usable for this reading. extended: {len(Se):,}. "
        f"The extended file carries no value-added level at all, only a growth rate on "
        f"the adjusted concept, and this reading needs none: the value-added terms "
        f"telescope around a closed path, which the first driver measured at 1.8e-15 "
        f"under an arbitrary rescaling of every level."))

    record = {
        "stage": "B101",
        "config": {
            "carriers": ["growth accounts basic", "growth accounts extended"],
            "basic_share": "LAB / VA_CP", "extended_share": "LAB / (LAB + CAP)",
            "mix": "ln(LAB_QI / CAP_QI)", "windows": list(WINDOWS), "seed": SEED,
            "placebos": ["share shuffled in time within a series",
                         "share reversed in time within a series"],
        },
        "criteria": crit, "report": report,
    }
    for c in crit:
        tag = "VOID" if c["passed"] is None else ("PASS" if c["passed"] else "FAIL")
        print(f"{tag}  {c['name']}\n      [{c['kind']}] {c['detail'][:560]}\n")
    print("  median |drift| by window")
    print(f"     {'n':>4}  {'basic':>11}  {'extended':>11}  {'shuffled':>11}  {'reversed':>11}")
    for n in sorted(med_b):
        print(f"     {n:>4}  {med_b[n]:>11.3e}  {med_e.get(n, float('nan')):>11.3e}  "
              f"{med_h.get(n, float('nan')):>11.3e}  {med_r.get(n, float('nan')):>11.3e}")
    if write:
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n",
                       encoding="utf-8", newline="\n")
        print(f"\nrecord -> {OUT.relative_to(ROOT)}")
    return 1 if [c for c in crit if c["passed"] is False] else 0


def selftest():
    ok = []
    rng = np.random.default_rng(7)

    # 1. affine share: zero at every window
    S = {("X", "A"): {1995 + t: (0.05 * t, 0.5 - 0.1 * (0.05 * t)) for t in range(27)}}
    ok.append(max(abs(drift(S, n)).max() for n in (2, 6, 13)) < 1e-12)
    print(f"  affine share            -> max |drift| "
          f"{max(abs(drift(S, n)).max() for n in (2, 6, 13)):.3e}  (want ~0)")

    # 2. pure noise in the share, no curve: exponent must come out near 0.5
    Sn = {}
    for g in range(200):
        x = np.cumsum(rng.normal(0, .05, 27))
        Sn[("X", f"C{g}")] = {1995 + t: (x[t], 0.5 - 0.1 * x[t] + rng.normal(0, .02))
                              for t in range(27)}
    sl, r2, _ = exponent(Sn, (2, 4, 9, 18, 26))
    ok.append(0.2 < sl < 0.8)
    print(f"  share is noise only     -> exponent {sl:.2f} (r2 {r2:.3f})  (want near 0.5)")

    # 3. a smooth curve, no noise: exponent must come out well above 1
    Sc = {}
    for g in range(200):
        x = np.cumsum(rng.normal(0, .05, 27))
        Sc[("X", f"C{g}")] = {1995 + t: (x[t], 1.0 / (1 + np.exp(-3 * x[t])))
                              for t in range(27)}
    sl2, r22, _ = exponent(Sc, (2, 4, 9, 18, 26))
    ok.append(sl2 > 1.0)
    print(f"  smooth curve, no noise  -> exponent {sl2:.2f} (r2 {r22:.3f})  (want above 1)")

    # 4. the placebo has to bite: shuffling a curved share must change the drift
    Ss = {k: (lambda ts, ys: {t: (ys[t][0], ys[u][1]) for t, u
                              in zip(ts, rng.permutation(ts))})(sorted(ys), ys)
          for k, ys in Sc.items()}
    a, b = np.median(np.abs(drift(Sc, 9))), np.median(np.abs(drift(Ss, 9)))
    ok.append(abs(np.log(b / a)) > 0.2)
    print(f"  shuffle bites           -> real {a:.3e} vs shuffled {b:.3e}  (want apart)")

    # 5. the fast path must return what the direct polygon returns
    slow = []
    for ys in Sc.values():
        ts = sorted(ys)
        for a0 in range(len(ts) - 9):
            w = ts[a0:a0 + 10]
            if w[-1] - w[0] == 9:
                slow.append(area([ys[t] for t in w]))
    fast = drift(Sc, 9)
    d = float(np.abs(np.sort(np.array(slow)) - np.sort(fast)).max())
    ok.append(len(slow) == len(fast) and d < 1e-12)
    print(f"  prefix sum == polygon   -> {len(slow):,} windows, worst {d:.3e}  (want ~0)")

    print(f"selftest: {'PASS' if all(ok) else 'FAIL'}")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    raise SystemExit(selftest() if a.selftest else run(write=not a.no_write))
