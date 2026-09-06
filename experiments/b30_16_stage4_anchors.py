"""B30-16 stage 4, re-read without a null.

Stage 4 asked whether carriers' fare-time subspaces are shared and answered it
with a shuffled null and a "below the null minimum over ten draws" line. That
line is a threshold anchored on what one run happened to produce, which is a
banned criterion shape, and the null it used did not carry the interpolation
that the observed matrix carries. Zero of 10,021 route series are observed in
all 120 quarters, so every block in stage 4 is 8 to 13 per cent filled.

This file replaces the pass/fail with three measured anchors on one scale, and
prints the object.

  ceiling   two random halves of ONE carrier's own routes. Same pricing
            procedure by construction, same T, same missingness, same fill.
            This is what the instrument reads when sharing is total.
  observed  cross-carrier angles, unchanged from stage 4.
  floor     the same instrument run on blocks whose route-to-time association
            has been destroyed while the missingness mask and the fill are
            preserved exactly. This is what the fill alone delivers.

A reading between floor and ceiling is then a fraction, not a verdict, and it
needs no distributional assumption. The floor is measured rather than declared,
which is what the resolution gate asks for.

    python experiments/b30_16_stage4_anchors.py --cov 0.6 0.8 0.95
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import b30_16_rank as B  # noqa: E402

K = 3
OUT = os.path.join(ROOT, "results", "b30_16")


def topk(M, kk):
    _, _, vt = np.linalg.svd(M, full_matrices=False)
    return vt[:kk].T


def angles(Vi, Vj):
    sv = np.linalg.svd(Vi.T @ Vj, compute_uv=False)
    return np.degrees(np.arccos(np.clip(sv, -1, 1)))


def fill_demean(piv):
    p = piv.interpolate(axis=1, limit_direction="both")
    return p.sub(p.mean(axis=1), axis=0).values


def load_long():
    t6 = B.t6_prepare(B.t6_fetch()).copy()
    t6["per"] = t6["year"].astype(int) * 4 + t6["quarter"].astype(int) - 1
    a = t6[["route", "per", "carrier_lg", "fare_lg"]].rename(
        columns={"carrier_lg": "carrier", "fare_lg": "fare"})
    b = t6[["route", "per", "carrier_low", "fare_low"]].rename(
        columns={"carrier_low": "carrier", "fare_low": "fare"})
    long = pd.concat([a, b], ignore_index=True).dropna()
    long["lf"] = np.log(long["fare"].clip(lower=1))
    return long.groupby(["carrier", "route", "per"], as_index=False)["lf"].mean()


def blocks_at(long, pers, min_cov, min_routes=30):
    out = {}
    for c, gc in long.groupby("carrier"):
        piv = gc.pivot_table(index="route", columns="per", values="lf")
        piv = piv.reindex(columns=pers)
        piv = piv[piv.notna().mean(axis=1) >= min_cov]
        if len(piv) >= min_routes:
            out[c] = piv
    return out


def ceiling(raw, rng, n_rep=5, min_routes=60):
    """Split one carrier's own routes in two. Sharing is total by construction."""
    rows = []
    for c, piv in sorted(raw.items()):
        if len(piv) < min_routes:
            continue
        for r in range(n_rep):
            idx = rng.permutation(len(piv))
            h = len(idx) // 2
            V1 = topk(fill_demean(piv.iloc[idx[:h]]), K)
            V2 = topk(fill_demean(piv.iloc[idx[h:2 * h]]), K)
            ang = angles(V1, V2)
            rows.append(dict(carrier=c, rep=r, n_half=h,
                             a1=float(ang[0]), a2=float(ang[1]),
                             a3=float(ang[2])))
    return pd.DataFrame(rows)


def floor(raw, pairs, rng, n_rep=10):
    """Destroy route-to-time association, keep the mask and the fill."""
    rows = []
    for r in range(n_rep):
        V = {}
        for c, piv in raw.items():
            A = piv.values.copy()
            for t in range(A.shape[1]):
                col = A[:, t]
                ok = ~np.isnan(col)
                if ok.sum() > 1:
                    col[ok] = rng.permutation(col[ok])
            V[c] = topk(fill_demean(pd.DataFrame(A, columns=piv.columns)), K)
        for x, y in pairs:
            ang = angles(V[x], V[y])
            rows.append(dict(rep=r, a=x, b=y, a1=float(ang[0]),
                             a2=float(ang[1]), a3=float(ang[2])))
    return pd.DataFrame(rows)


def name_the_direction(obsV, pers, n_show=6):
    """Print the shared leading factor as a time series, not as an angle."""
    names = sorted(obsV)
    M = np.column_stack([obsV[c][:, 0] for c in names])
    ref = M[:, 0]
    for j in range(M.shape[1]):
        if float(M[:, j] @ ref) < 0:
            M[:, j] = -M[:, j]
    u, sv, _ = np.linalg.svd(M, full_matrices=False)
    v = u[:, 0]
    if float(v @ M.mean(axis=1)) < 0:
        v = -v
    share = float(sv[0] ** 2 / (sv ** 2).sum())
    lab = [f"{p // 4}Q{p % 4 + 1}" for p in pers]
    order = np.argsort(v)
    return v, share, lab, [lab[i] for i in order[::-1][:n_show]], \
        [lab[i] for i in order[:n_show]]


def r2_on(subspace, M):
    """Share of M's row variance captured by projecting each row on `subspace`."""
    P = M @ subspace                       # rows x k
    num = float((P ** 2).sum())
    den = float((M ** 2).sum())
    return num / den if den else float("nan")


def leave_one_out(raw, obsV, floV, seed=0):
    """Out of sample: build the shared subspace WITHOUT a carrier, then read it.

    The shared subspace is the top-k eigenvectors of the average projector over
    every carrier except one. That subspace has never seen the held-out
    carrier's routes. How much of that carrier's own variation it captures is a
    prediction and not a fit, and it needs no null: a k-dimensional subspace
    drawn at random captures k/T by construction, the carrier's own top-k
    captures the most any k dimensions can, and the two bracket the reading.
    """
    names = sorted(raw)
    T = obsV[names[0]].shape[0]
    rng = np.random.default_rng(seed)
    rows = []
    for c in names:
        M = fill_demean(raw[c])
        others = [x for x in names if x != c]

        def shared(V_by):
            P = np.zeros((T, T))
            for o in others:
                P += V_by[o] @ V_by[o].T
            w, U = np.linalg.eigh(P / len(others))
            return U[:, np.argsort(w)[::-1][:K]]

        rr = np.linalg.qr(rng.standard_normal((T, K)))[0]
        rows.append(dict(
            held_out=c, n_routes=int(M.shape[0]),
            own=r2_on(obsV[c], M),                 # ceiling, in sample
            shared_others=r2_on(shared(obsV), M),  # out of sample
            floor_others=r2_on(shared(floV), M),   # what the fill alone predicts
            random=r2_on(rr, M)))                  # k/T by construction
    return pd.DataFrame(rows)

def shared_spectrum(V_by_name):
    """Eigenvalues of the average projector, on a scale fixed by construction.

    P = mean over carriers of V_c V_c^T. Its eigenvalues lie in [0, 1]: one
    means the direction lies in every carrier's subspace, 1/C means it lies in
    exactly one, and they sum to k. So "how many dimensions are shared" is read
    off a scale that no run and no shuffle supplies.
    """
    names = sorted(V_by_name)
    T = V_by_name[names[0]].shape[0]
    P = np.zeros((T, T))
    for c in names:
        P += V_by_name[c] @ V_by_name[c].T
    P /= len(names)
    w, U = np.linalg.eigh(P)
    o = np.argsort(w)[::-1]
    w, U = w[o][:K], U[:, o][:, :K]
    for j in range(U.shape[1]):
        if U[np.argmax(np.abs(U[:, j])), j] < 0:
            U[:, j] = -U[:, j]
    return w, U


def extremes(vec, pers, n_show=5):
    lab = [f"{p // 4}Q{p % 4 + 1}" for p in pers]
    o = np.argsort(vec)
    return [lab[i] for i in o[::-1][:n_show]], [lab[i] for i in o[:n_show]]


def ceiling_subspaces(raw, n_groups, rng, min_per_group=30):
    """One carrier's own routes cut into n_groups. Sharing total by construction."""
    out = []
    for c, piv in sorted(raw.items()):
        if len(piv) < n_groups * min_per_group:
            continue
        idx = rng.permutation(len(piv))
        parts = np.array_split(idx, n_groups)
        out.append((c, {f"{c}#{i}": topk(fill_demean(piv.iloc[g]), K)
                        for i, g in enumerate(parts)}))
    return out


def floor_subspaces(raw, rng):
    V = {}
    for c, piv in raw.items():
        A = piv.values.copy()
        for t in range(A.shape[1]):
            col = A[:, t]
            ok = ~np.isnan(col)
            if ok.sum() > 1:
                col[ok] = rng.permutation(col[ok])
        V[c] = topk(fill_demean(pd.DataFrame(A, columns=piv.columns)), K)
    return V


def run(min_cov, seed=0, n_rep_ceiling=5, n_rep_floor=10):
    long = load_long()
    pers = sorted(long["per"].unique())
    raw = blocks_at(long, pers, min_cov)
    names = sorted(raw)
    if len(names) < 3:
        print(f"  cov {min_cov}: only {len(names)} carriers, skipped")
        return None
    rng = np.random.default_rng(seed)

    obsV = {c: topk(fill_demean(raw[c]), K) for c in names}
    pairs = [(names[i], names[j])
             for i in range(len(names)) for j in range(i + 1, len(names))]
    obs = pd.DataFrame([dict(a=x, b=y, **dict(zip(
        ("a1", "a2", "a3"), map(float, angles(obsV[x], obsV[y])))))
        for x, y in pairs])

    cei = ceiling(raw, rng, n_rep=n_rep_ceiling)
    flo = floor(raw, pairs, rng, n_rep=n_rep_floor)

    print(f"\n=== min_cov {min_cov} | carriers {names} | pairs {len(pairs)} ===")
    fillfrac = {c: round(float(1 - raw[c].notna().mean(axis=1).mean()), 4)
                for c in names}
    print(f"  fraction of each block that is interpolated: {fillfrac}")
    print(f"  ceiling from {cei['carrier'].nunique()} carriers x "
          f"{n_rep_ceiling} splits = {len(cei)} readings; "
          f"floor from {n_rep_floor} x {len(pairs)} = {len(flo)} readings")
    print("\n  angle |  ceiling  |  observed  |   floor   |  position")
    pos = {}
    for i, col in enumerate(("a1", "a2", "a3")):
        cl, ob, fl = cei[col].median(), obs[col].median(), flo[col].median()
        frac = (fl - ob) / (fl - cl) if fl > cl else float("nan")
        pos[col] = float(frac)
        print(f"    {i+1}   |  {cl:6.2f}   |   {ob:6.2f}   |  {fl:6.2f}   |"
              f"  {frac*100:5.1f}% of the way from floor to ceiling")
    print(f"\n  ceiling spread (max - min over splits): "
          f"{ {c: round(float(cei[cei.carrier==c]['a2'].max()-cei[cei.carrier==c]['a2'].min()),2) for c in sorted(cei.carrier.unique())} }")



    # ---- out of sample: the shared subspace applied to a carrier it never saw
    floV = floor_subspaces(raw, np.random.default_rng(seed + 3))
    loo = leave_one_out(raw, obsV, floV, seed=seed)
    print("\n  leave one carrier out. share of the held-out carrier's own")
    print("  variation captured by a subspace built without it")
    print("   held out   routes    own (in sample)   shared, out of sample"
          "   fill only    random")
    for _, r in loo.iterrows():
        print(f"     {r['held_out']:>4}     {int(r['n_routes']):5d}      "
              f"{r['own']:11.4f}       {r['shared_others']:14.4f}   "
              f"{r['floor_others']:9.4f}  {r['random']:8.4f}")
    print(f"     median            {loo['own'].median():11.4f}       "
          f"{loo['shared_others'].median():14.4f}   "
          f"{loo['floor_others'].median():9.4f}  {loo['random'].median():8.4f}")
    print(f"     out of sample recovers "
          f"{loo['shared_others'].median()/loo['own'].median()*100:.1f} % of what "
          f"the carrier's own factors capture in sample")

    # ---- how many dimensions are shared, on a scale fixed by construction
    w_obs, U_obs = shared_spectrum(obsV)
    w_flo, _ = shared_spectrum(floor_subspaces(raw, np.random.default_rng(seed + 1)))
    cei_sets = ceiling_subspaces(raw, len(names), np.random.default_rng(seed + 2))
    w_cei = ({c: shared_spectrum(d)[0] for c, d in cei_sets} if cei_sets else {})
    print("\n  eigenvalues of the average projector "
          "(1 = in every carrier's subspace, 1/C = in one only, sum = k)")
    print(f"    1/C for C={len(names)} is {1/len(names):.4f}")
    print(f"    observed : {np.round(w_obs, 4).tolist()}")
    print(f"    floor    : {np.round(w_flo, 4).tolist()}")
    for c, w in sorted(w_cei.items()):
        print(f"    ceiling {c}: {np.round(w, 4).tolist()}")

    print("\n  the shared directions, printed rather than scored")
    dir_rec = []
    for j in range(K):
        hi, lo = extremes(U_obs[:, j], pers)
        print(f"    direction {j+1} (eigenvalue {w_obs[j]:.4f})")
        print(f"      highest: {hi}")
        print(f"      lowest:  {lo}")
        dir_rec.append(dict(rank=j + 1, eigenvalue=float(w_obs[j]),
                            high=hi, low=lo,
                            vector=[float(x) for x in U_obs[:, j]]))

    v, share, lab, hi, lo = name_the_direction(obsV, pers)
    print(f"\n  the shared leading direction, printed rather than scored")
    print(f"    one direction carries {share:.4f} of the variance across the "
          f"{len(names)} carriers' own first factors")
    print(f"    six quarters where it is highest: {hi}")
    print(f"    six quarters where it is lowest:  {lo}")

    rec = dict(min_cov=min_cov, carriers=names, k=K,
               fill_fraction=fillfrac,
               n_rep_ceiling=n_rep_ceiling, n_rep_floor=n_rep_floor,
               observed_median={c: float(obs[c].median()) for c in ("a1", "a2", "a3")},
               ceiling_median={c: float(cei[c].median()) for c in ("a1", "a2", "a3")},
               floor_median={c: float(flo[c].median()) for c in ("a1", "a2", "a3")},
               position_floor_to_ceiling=pos,
               leading_direction_share=share,
               leading_direction_high=hi, leading_direction_low=lo,
               leading_direction=[float(x) for x in v],
               shared_spectrum_observed=[float(x) for x in w_obs],
               shared_spectrum_floor=[float(x) for x in w_flo],
               shared_spectrum_ceiling={c: [float(x) for x in w]
                                        for c, w in w_cei.items()},
               shared_directions=dir_rec,
               leave_one_out=loo.to_dict('records'),
               quarters=lab)
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"stage4_anchors_cov{int(min_cov*100)}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"\n  written {os.path.relpath(p, ROOT)}")
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cov", type=float, nargs="+", default=[0.6, 0.8, 0.95])
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    for mc in a.cov:
        run(mc, seed=a.seed)
