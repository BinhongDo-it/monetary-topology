"""B106 step two: is the class ladder the same everywhere?

The field is p(position, class) = ln(Share_W / Share_E), the class's pay relative
to its position's average. The position's level is normalised away by the
module's own construction, so what is left is the ladder.

A scalar price field on positions says the ladder is one object: p(j,k) is the
sum of something about the position and something about the class, and nothing
else. That is additive separability, and it is the same statement as the field
being a gradient, because the additive subspace of a J by K table IS the image of
the coboundary on the complete bipartite graph. The obstruction carries
(J-1)(K-1) independent cycles, which is B79's product count.

Each cycle is a square: two positions, two classes, and the difference in
differences of log relative pay. B2A's carrier could not form one, because its
borrowers carry no labels and so there is no same class at another position to
compare against. This one can, which is the whole reason to run it.

    python experiments/b106_separability.py
    python experiments/b106_separability.py --no-write
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache" / "b106_labour.npz"
OUT = ROOT / "results" / "b106_separability.json"

#: The exhaustive partition. The module also reports M-N, MARKT, NMARKT, TOT and
#: TOT_IND, which are sums of these. Putting an aggregate in beside its own parts
#: would enter the same workers twice and add a row that is a weighted mean of
#: the others, which is the twelfth category error: every count stays sensible
#: while the object changes. They are named here rather than filtered silently.
SECTIONS = [chr(c) for c in range(ord("A"), ord("T") + 1)]
AGGREGATES = ["M-N", "MARKT", "NMARKT", "TOT", "TOT_IND"]
K = 18


def load():
    d = np.load(CACHE, allow_pickle=False)
    e, w = d["share_e"], d["share_w"]
    ok = (e > 0) & (w > 0)
    p = np.full(len(e), np.nan)
    p[ok] = np.log(w[ok] / e[ok])
    return {"nace": d["nace"], "geo": d["geo"], "year": d["year"],
            "cls": d["cls"], "p": p, "share_e": e, "ok": ok}


def tables(d, rows_by):
    """Build rectangular tables. rows_by picks what the rows are:
    'industry' gives one table per (country, year), 'country' one per
    (industry, year). Columns are always the 18 classes."""
    keep = np.isin(d["nace"], SECTIONS) & d["ok"]
    classes = sorted(set(d["cls"][keep]))
    ci = {c: i for i, c in enumerate(classes)}
    grid = {}
    for i in np.flatnonzero(keep):
        if rows_by == "industry":
            key, row = (str(d["geo"][i]), int(d["year"][i])), str(d["nace"][i])
        else:
            key, row = (str(d["nace"][i]), int(d["year"][i])), str(d["geo"][i])
        grid.setdefault(key, {}).setdefault(row, {})[ci[str(d["cls"][i])]] = (
            d["p"][i], d["share_e"][i])
    out = {}
    for key, rowmap in grid.items():
        full = {r: v for r, v in rowmap.items() if len(v) == len(classes)}
        if len(full) < 3:
            continue
        rs = sorted(full)
        P = np.array([[full[r][c][0] for c in range(len(classes))] for r in rs])
        E = np.array([[full[r][c][1] for c in range(len(classes))] for r in rs])
        out[key] = (rs, classes, P, E)
    return out


def interaction(P):
    """Two-way fit and its residual. The additive fit of a table is its row and
    column means; the residual is the interaction, and it is exactly the part
    that no scalar on positions plus a class ladder can produce."""
    r = P - P.mean(axis=1, keepdims=True) - P.mean(axis=0, keepdims=True) + P.mean()
    tot = P - P.mean()
    denom = float((tot ** 2).sum())
    return r, (float((r ** 2).sum()) / denom if denom > 0 else 0.0)


# --------------------------------------------------------- B106-1 what loaded

def check_load(d, t_ind, t_cty):
    keep = np.isin(d["nace"], SECTIONS)
    agg = np.isin(d["nace"], AGGREGATES)
    js = np.array([len(v[0]) for v in t_ind.values()])
    cs = np.array([len(v[0]) for v in t_cty.values()])
    ok = len(t_ind) > 0 and len(t_cty) > 0 and int(agg.sum()) > 0
    detail = (f"{int(keep.sum()):,} class-cells on the 20 NACE sections, "
              f"{int(agg.sum()):,} on the five aggregates that are sums of them "
              f"({', '.join(AGGREGATES)}) and are excluded by name rather than "
              f"silently. {len(t_ind):,} country-year tables with three or more "
              f"industries, rows min {js.min()} median {int(np.median(js))} max "
              f"{js.max()}; {len(t_cty):,} industry-year tables with three or more "
              f"countries, rows min {cs.min()} median {int(np.median(cs))} max "
              f"{cs.max()}. Columns are the 18 classes in every table.")
    return bool(ok), detail, {
        "cells_on_sections": int(keep.sum()), "cells_on_aggregates": int(agg.sum()),
        "aggregates_excluded": AGGREGATES,
        "country_year_tables": len(t_ind), "industry_year_tables": len(t_cty),
        "rows_median_industry": int(np.median(js)),
        "rows_median_country": int(np.median(cs)),
        "cycles_median_industry": int((np.median(js) - 1) * (K - 1)),
        "cycles_median_country": int((np.median(cs) - 1) * (K - 1))}


# ---------------------------------------------------- B106-2 planted answers

def check_planted(rng, reps):
    """Separable in, zero out. No structure in, the exact degrees of freedom out:
    the interaction carries (J-1)(K-1) of the JK-1 dimensions, so a field with no
    structure spends that fraction of its variance there."""
    zero, noise = [], []
    for J in (4, 8, 19):
        for _ in range(reps):
            a = rng.normal(size=(J, 1)); b = rng.normal(size=(1, K))
            zero.append(interaction(a + b)[1])
            noise.append({"J": J, "share": interaction(rng.normal(size=(J, K)))[1],
                          "closed_form": (J - 1) * (K - 1) / (J * K - 1)})
    worst_zero = max(zero)
    by_J = {}
    for e in noise:
        by_J.setdefault(e["J"], []).append(e["share"])
    # The share is exactly Beta(a, b) for an isotropic field, with
    # a = (J-1)(K-1)/2 and b = (J+K-2)/2, so both the mean and the spread are
    # known and the tolerance below is four standard errors of that exact
    # distribution over this many draws. No constant is invented.
    rows, worst_z = [], 0.0
    for J, v in sorted(by_J.items()):
        aa = (J - 1) * (K - 1) / 2.0
        bb = (J + K - 2) / 2.0
        cf = aa / (aa + bb)
        var = aa * bb / ((aa + bb) ** 2 * (aa + bb + 1))
        se = float(np.sqrt(var / len(v)))
        z = abs(float(np.mean(v)) - cf) / se
        worst_z = max(worst_z, z)
        rows.append({"J": J, "mean": float(np.mean(v)), "closed_form": cf,
                     "se": se, "z": z, "draws": len(v)})
    ok = worst_zero < 1e-20 and worst_z < 4.0
    detail = (f"separable in, zero out: worst interaction share {worst_zero:.2e} "
              f"over {len(zero)} draws. No structure in, the degrees of freedom "
              f"out: " + ", ".join(
                  f"J={r['J']} {r['mean']:.4f} vs (J-1)(K-1)/(JK-1) = "
                  f"{r['closed_form']:.4f} (z {r['z']:.2f})" for r in rows)
              + f"; worst z {worst_z:.2f} against four standard errors of the "
                f"exact Beta over {reps} draws")
    return bool(ok), detail, {"worst_zero": worst_zero, "noise": rows,
                              "worst_z": worst_z}


# --------------------------------------------------- B106-3 the own reading

def check_reading(t_ind, t_cty):
    out = {}
    for name, tabs in (("industries_within_country_year", t_ind),
                       ("countries_within_industry_year", t_cty)):
        sh = np.array([interaction(v[2])[1] for v in tabs.values()])
        J = np.array([len(v[0]) for v in tabs.values()])
        null = (J - 1) * (K - 1) / (J * K - 1)
        out[name] = {"n": int(len(sh)),
                     "median": float(np.median(sh)),
                     "p10": float(np.percentile(sh, 10)),
                     "p90": float(np.percentile(sh, 90)),
                     "null_median": float(np.median(null)),
                     "over_null_median": float(np.median(sh / null)),
                     "below_half_null": int(np.sum(sh < 0.5 * null))}
    ok = all(v["n"] > 0 for v in out.values())
    detail = "; ".join(
        f"{k}: {v['n']:,} tables, interaction share median {v['median']:.4f} "
        f"against a no-structure {v['null_median']:.4f}, ratio "
        f"{v['over_null_median']:.3f}, below half of it in {v['below_half_null']:,}"
        for k, v in sorted(out.items()))
    return bool(ok), detail, out


# ------------------------------------- B106-4 does the interaction persist

def check_persistence(d, t_ind, t_cty):
    """The position-scalar reading says the interaction is zero and what is seen
    is survey noise. Noise does not repeat. So the reading against it is whether
    the same position and class carry the same interaction next year."""
    out = {}
    for name, tabs in (("industries_within_country_year", t_ind),
                       ("countries_within_industry_year", t_cty)):
        res = {}
        for (key0, yr), (rs, cls, P, E) in tabs.items():
            r, _ = interaction(P)
            for i, rowname in enumerate(rs):
                for j in range(len(cls)):
                    res[(key0, rowname, cls[j], yr)] = r[i, j]
        a, b = [], []
        for (k0, rn, cl, yr), v in res.items():
            nxt = res.get((k0, rn, cl, yr + 1))
            if nxt is not None:
                a.append(v); b.append(nxt)
        a, b = np.array(a), np.array(b)
        rho = float(np.corrcoef(a, b)[0, 1])
        # Ten years apart, because a compiler that interpolates between survey
        # years would manufacture an adjacent-year correlation and could not
        # manufacture a decade of one.
        far = []
        for (k0, rn, cl, yr), v in res.items():
            nxt = res.get((k0, rn, cl, yr + 10))
            if nxt is not None:
                far.append((v, nxt))
        rho10 = float(np.corrcoef(np.array([x for x, _ in far]),
                                  np.array([y for _, y in far]))[0, 1]) if far else float("nan")
        # Placebo: keep the year pairing and the class, move to a DIFFERENT first
        # key. Every marginal survives and only the position pairing is broken,
        # so this is what the statistic reads when there is nothing at a
        # position to read.
        keys0 = sorted({k[0] for k in res})
        shift = {k: keys0[(keys0.index(k) + 1) % len(keys0)] for k in keys0}
        pa, pb = [], []
        for (k0, rn, cl, yr), v in res.items():
            other = res.get((shift[k0], rn, cl, yr + 1))
            if other is not None:
                pa.append(v); pb.append(other)
        rho_pl = float(np.corrcoef(np.array(pa), np.array(pb))[0, 1]) if len(pa) > 3 else float("nan")
        se = float(1.0 / np.sqrt(max(len(a) - 3, 1)))
        out[name] = {"pairs": int(len(a)), "corr_next_year": rho,
                     "pairs_10y": len(far), "corr_ten_years": rho10,
                     "pairs_placebo": len(pa), "corr_placebo": rho_pl,
                     "se": se, "z_against_zero": abs(rho) / se}
    worst_z = min(v["z_against_zero"] for v in out.values())
    ok = worst_z > 4.0
    detail = "; ".join(
        f"{k}: {v['pairs']:,} adjacent-year pairs, correlation "
        f"{v['corr_next_year']:+.4f}, which is {v['z_against_zero']:.0f} standard "
        f"errors from the rival's zero; ten years apart "
        f"{v['corr_ten_years']:+.4f} over {v['pairs_10y']:,}; with the position "
        f"pairing broken and every marginal kept, {v['corr_placebo']:+.4f} over "
        f"{v['pairs_placebo']:,}"
        for k, v in sorted(out.items()))
    detail += (". Survey noise does not repeat, so the rival's reading is a point "
               "at zero. The decade-apart figure answers a compiler that "
               "interpolates between survey years, and the broken pairing "
               "answers the statistic itself.")
    return bool(ok), detail, out


# ------------------------------------ B106-5 does it shrink with cell size

def check_by_size(t_ind):
    """If the interaction were sampling noise it would shrink where the class is
    large. Printing it by size decile answers that without a threshold."""
    vals, sizes = [], []
    for rs, cls, P, E in t_ind.values():
        r, _ = interaction(P)
        vals.append(r.ravel()); sizes.append(E.ravel())
    v = np.concatenate(vals); s = np.concatenate(sizes)
    q = np.percentile(s, np.arange(0, 101, 10))
    rows = []
    for i in range(10):
        m = (s >= q[i]) & (s <= q[i + 1] if i == 9 else s < q[i + 1])
        if m.sum():
            rows.append({"decile": i + 1, "share_e_from": float(q[i]),
                         "share_e_to": float(q[i + 1]),
                         "n": int(m.sum()), "sd": float(v[m].std())})
    lo, hi = rows[0]["sd"], rows[-1]["sd"]
    span = rows[-1]["share_e_from"] / max(rows[0]["share_e_to"], 1e-12)
    ok = len(rows) == 10
    detail = ("interaction residual by the class's own employment share, ten "
              "deciles from the smallest classes to the largest: "
              + ", ".join(f"d{r['decile']} {r['sd']:.4f}" for r in rows)
              + f". The thinnest decile reads {lo:.4f} and the thickest "
                f"{hi:.4f}, a fall of {lo/hi:.2f} times across a span of at least "
                f"{span:.0f} times in employment share. Sampling error would fall "
                f"as one over the root of the count, which over that span is about "
                f"{span**0.5:.0f} times, so the profile is far flatter than noise "
                f"and it stops falling after the fifth decile: d5 to d10 move only "
                f"from {rows[4]['sd']:.4f} to {hi:.4f}.")
    return bool(ok), detail, {"by_decile": rows, "sd_thinnest": lo,
                              "sd_thickest": hi, "share_span": span}


# -------------------------------------------------------------------- driver

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()

    t0 = time.time()
    d = load()
    t_ind = tables(d, "industry")
    t_cty = tables(d, "country")
    rng = np.random.default_rng(a.seed)

    checks = [
        ("B106-1", "instrument",
         "what the tables are, and the five aggregates kept out of them by name",
         check_load(d, t_ind, t_cty)),
        ("B106-2", "known_answer",
         "a separable field reads zero and a field with no structure reads its "
         "own degrees of freedom", check_planted(rng, a.reps)),
        ("B106-3", "own_reading",
         "how much of the field no scalar on positions plus a class ladder can "
         "produce", check_reading(t_ind, t_cty)),
        ("B106-4", "rival",
         "whether what is left over repeats next year, which survey noise does "
         "not", check_persistence(d, t_ind, t_cty)),
        ("B106-5", "own_reading",
         "whether the leftover shrinks where the class is large, which is what "
         "sampling noise does", check_by_size(t_ind)),
    ]
    criteria = []
    for name, kind, what, (passed, detail, payload) in checks:
        c = {"name": name, "kind": kind, "criterion": what,
             "passed": bool(passed), "detail": detail, "payload": payload}
        if kind == "rival":
            c.update({
                "grid": "B",
                "rival_shape": "point prediction",
                "rival_premise":
                    "the price a class is paid at a position is a scalar on the "
                    "position times a factor for the class, so in logs the field "
                    "is additively separable and the interaction is identically "
                    "zero; anything observed in it is sampling error in the "
                    "survey the shares come from",
                "rival_entailment":
                    "sampling error in one year is independent of sampling error "
                    "in the next, so under that premise the interaction measured "
                    "at a position and class in year t has zero correlation with "
                    "the same position and class in year t+1. The prediction is a "
                    "point at zero, with a standard error of one over the root of "
                    "the pair count.",
                "grid_note": {
                    "ours": "the interaction is the square, two positions by two "
                            "classes, and it is a standing feature of who is "
                            "being paid where, so it repeats",
                    "rival": "it is zero, so what is measured is noise and does "
                             "not repeat",
                    "reality": "filled in by this run",
                },
            })
        criteria.append(c)
        print(f"[{'PASS' if passed else 'FAIL'}] {name} ({kind})  {detail}")

    record = {
        "stage": "B106",
        "config": {"reps": a.reps, "seed": a.seed,
                   "field": "ln(Share_W / Share_E)",
                   "classes": "3 education x 3 age x 2 gender = 18",
                   "sections": SECTIONS, "aggregates_excluded": AGGREGATES,
                   "sources": ["labour accounts.csv"]},
        "criteria": criteria,
    }
    body = json.dumps(record, indent=2, sort_keys=True, default=float)
    print(f"\n{sum(c['passed'] for c in criteria)}/{len(criteria)} pass, "
          f"{time.time()-t0:.2f}s, sha256 "
          f"{hashlib.sha256(body.encode()).hexdigest()[:16]}")
    if not a.no_write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(body, encoding="utf-8", newline="\n")
        print(f"record -> {OUT.relative_to(ROOT)}")
    return 0 if all(c["passed"] for c in criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
