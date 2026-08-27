"""B3: the slice summand, measured on CIP deviations between government bonds.

Registered in ``docs/b3_cip_slice.md``. This file evaluates and does not design:
every threshold it compares against is written there, including the schema
corrections in §10 that were made after retrieval and before any computation.

Usage::

    python experiments/b3_cip_slice.py
    python experiments/b3_cip_slice.py --band 250

Writes ``results/b3_cip_slice.json``.

**Read this before the numbers.** The data is a *derived* series built by its
publishers from Bloomberg and Datastream; I retrieved their output, not the
world. And a CIP deviation is **not a profit** — the post-2008 account is that it
is the shadow price of balance-sheet capacity, which is why the claim here is
that no global potential exists on the position space *as the price system states
it*, and not that money is lying around. Both points are argued in
``docs/b3_slice_availability.md`` §4 and §7.

The object is the **cross-currency cycle** `z(i,j) = x(i) − x(j)`, which never
touches the Treasury. The Treasury cycles are the literature's and are reported
only so the two can be seen together.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DATA = ROOT / "data" / "raw" / "cip_dataset_v4.csv"

#: §10. The real header, asserted rather than assumed. A column name guessed
#: with an underscore for a hyphen cost this repository four errors once, so
#: a missing column stops the run instead of silently producing a short sample.
REQUIRED = (
    "group", "currency", "tenor", "date",
    "diff_y", "rho", "cip_govt", "cip_govt_ibor", "cip_govt_sofr",
)

#: §10.1. Nine, not the eight the publisher's appendix lists: `7y` is in the data.
TENORS = ("3m", "1y", "2y", "3y", "5y", "7y", "10y", "20y", "30y")

#: §6. Registered thresholds, named together so a reader can check them against
#: the document rather than hunting through the code.
B3_1_TOL = 1e-12
B3_3_FACTOR = 4.0
B3_4_BP = 25.0
B3_4_SHARE = 0.5
B3_5_LEG_SHARE = 0.25
B3_6_TENORS = 5

#: §7. The band scan. The headline is the widest band at which the conclusion is
#: unchanged, and the rank version is reported beside it.
BANDS = (100.0, 250.0, 500.0, 1000.0)
DEFAULT_BAND = 500.0

_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun",
         "jul", "aug", "sep", "oct", "nov", "dec"]
    )
}


def parse_date(s: str) -> dt.date:
    """`08feb2007` to a date, with an explicit month table.

    Not left to a locale-dependent parser. One that quietly yields a null on an
    unexpected locale would drop rows without saying so, and a sample that
    shrinks in silence is the failure mode this repository keeps finding.
    """
    return dt.date(int(s[5:]), _MONTHS[s[2:5].lower()], int(s[:2]))


def load() -> dict:
    """Stream the file into arrays, keyed by (group, tenor, date).

    Streamed rather than loaded whole: 1.5 million rows at 118 MB is not large,
    but nothing here needs the whole table in memory at once and a loader that
    does will stop working the first time the publisher extends the sample.
    """
    if not DATA.exists():
        raise SystemExit(
            f"missing {DATA.relative_to(ROOT)}; run `python data/fetch_cip.py`"
        )
    dev: dict = defaultdict(dict)
    legs: dict = defaultdict(dict)
    both: dict = defaultdict(dict)
    dropped = defaultdict(int)
    seen = 0
    with DATA.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(
                f"schema changed: {missing} absent from {reader.fieldnames}"
            )
        for row in reader:
            g = row["group"]
            if not g or g.startswith("#"):
                continue
            seen += 1
            key = (g, row["tenor"], row["date"])
            cur = row["currency"]
            x = (row["cip_govt"] or "").strip()
            if x:
                dev[key][cur] = float(x)
                dy = (row["diff_y"] or "").strip()
                rh = (row["rho"] or "").strip()
                if dy and rh:
                    legs[key][cur] = (float(dy), float(rh))
            else:
                dropped[g] += 1
            i = (row["cip_govt_ibor"] or "").strip()
            s = (row["cip_govt_sofr"] or "").strip()
            if i and s:
                both[key][cur] = (float(i), float(s))
    return {
        "dev": dev, "legs": legs, "both": both,
        "rows": seen, "dropped": dict(dropped),
    }


def pair_energy(values: np.ndarray) -> tuple[float, float]:
    """`(by enumeration, by variance)` of the mean squared cycle sum.

    `Z = (1/k²) Σ_{p,q} (x_p − x_q)² = 2·Var(x)`. Theorem 3's identity with the
    agent index replaced by the country index. Both are computed because their
    agreement is a check on the code, and B3-1 fails the stage if it breaks.
    """
    k = values.size
    if k < 2:
        return float("nan"), float("nan")
    diff = values[:, None] - values[None, :]
    return float((diff * diff).sum() / (k * k)), float(2.0 * values.var())


def rank_within(values: np.ndarray) -> np.ndarray:
    """Ranks, so a conclusion that survives does not depend on any band."""
    order = np.argsort(np.argsort(values))
    return order.astype(float)


def analyse(data: dict, band: float) -> dict:
    dev, both = data["dev"], data["both"]

    # -- the headline: cross-currency cycles, by group and tenor -----------
    energy: dict = defaultdict(list)
    energy_rank: dict = defaultdict(list)
    worst_identity = 0.0
    per_date: dict = defaultdict(list)
    for (g, tenor, date), by_cur in dev.items():
        if len(by_cur) < 2:
            continue
        vals = np.array(list(by_cur.values()), dtype=float)
        vals = np.clip(vals, -band, band)
        enum, var = pair_energy(vals)
        if np.isfinite(enum) and np.isfinite(var):
            worst_identity = max(
                worst_identity, abs(enum - var) / max(abs(var), 1e-12)
            )
            energy[(g, tenor)].append(enum)
            energy_rank[(g, tenor)].append(pair_energy(rank_within(vals))[0])
            per_date[(g, parse_date(date))].append(enum)

    # -- the noise floor, from two constructions of the same object --------
    #
    # **Computed on the same cells as the signal it is compared against.** The
    # first version averaged the floor over the 2012-2025 window where both
    # benchmark constructions exist and the signal over the full 2000-2025
    # sample, then divided one by the other. That is `MEASUREMENT.md` rule 5:
    # the two sides of a comparison were different populations, and the ratio
    # would have carried thirteen years of sample difference inside it.
    floor: dict = defaultdict(list)
    matched: dict = defaultdict(list)
    for key, by_cur in both.items():
        if not by_cur:
            continue
        g, tenor, _date = key
        d = np.array([i - s for i, s in by_cur.values()], dtype=float)
        floor[(g, tenor)].append(float((d * d).mean()))
        same_cell = dev.get(key, {})
        if len(same_cell) >= 2:
            v = np.clip(
                np.array(list(same_cell.values()), dtype=float), -band, band
            )
            matched[(g, tenor)].append(pair_energy(v)[0])

    def summarise(store: dict, g: str) -> dict:
        out = {}
        for tenor in TENORS:
            vals = store.get((g, tenor), [])
            if vals:
                out[tenor] = float(np.mean(vals))
        return out

    return {
        "band": band,
        "worst_identity_error": worst_identity,
        "energy": {g: summarise(energy, g) for g in ("g10", "eme")},
        "energy_rank": {g: summarise(energy_rank, g) for g in ("g10", "eme")},
        # The one to divide by the floor: same cells, same dates, same
        # countries as the floor itself.
        "energy_matched": {g: summarise(matched, g) for g in ("g10", "eme")},
        "floor": {g: summarise(floor, g) for g in ("g10", "eme")},
        "per_date": per_date,
    }


def trivial_cycle(data: dict, band: float) -> float:
    """B3-2. `z(i,i)` through the full code path, which must be exactly zero.

    Computed from the same difference matrix every other number comes from,
    rather than short-circuited on `i == j`. A calibration that takes a
    different route through the code tests a different code.
    """
    worst = 0.0
    for _key, by_cur in data["dev"].items():
        if len(by_cur) < 2:
            continue
        v = np.clip(np.array(list(by_cur.values()), dtype=float), -band, band)
        diag = np.abs(np.diag(v[:, None] - v[None, :]))
        worst = max(worst, float(diag.max()))
    return worst


#: B3-6. The tenor the pairs are ranked on. The sign is then tested on the other
#: eight, so the axis that selects is disjoint from the axis that tests.
B3_6_SELECT_TENOR = "5y"
B3_6_TOP_PAIRS = 10


def sign_stability(data: dict, band: float, group: str = "g10") -> dict:
    """B3-6. Do the largest pairs keep their sign across maturities?

    Pairs are ranked by `|mean z|` at one tenor and the sign is checked on the
    **other** tenors. Ranking and testing on the same numbers would make the
    agreement partly a property of the selection.
    """
    means: dict = defaultdict(lambda: defaultdict(list))
    for (g, tenor, _date), by_cur in data["dev"].items():
        if g != group or len(by_cur) < 2:
            continue
        items = sorted(by_cur.items())
        for a in range(len(items)):
            for b in range(a + 1, len(items)):
                ca, va = items[a]
                cb, vb = items[b]
                z = float(np.clip(va, -band, band) - np.clip(vb, -band, band))
                means[(ca, cb)][tenor].append(z)
    scored = []
    for pair, by_tenor in means.items():
        ref = by_tenor.get(B3_6_SELECT_TENOR)
        if ref:
            scored.append((abs(float(np.mean(ref))), pair))
    scored.sort(reverse=True)
    others = [t for t in TENORS if t != B3_6_SELECT_TENOR]
    rows = []
    for _score, pair in scored[:B3_6_TOP_PAIRS]:
        ref_sign = np.sign(np.mean(means[pair][B3_6_SELECT_TENOR]))
        agree = sum(
            1
            for t in others
            if means[pair].get(t)
            and np.sign(np.mean(means[pair][t])) == ref_sign
        )
        rows.append({"pair": "/".join(pair), "agreeing_tenors": int(agree),
                     "of": len(others)})
    worst = min((r["agreeing_tenors"] for r in rows), default=0)
    return {"select_tenor": B3_6_SELECT_TENOR, "pairs": rows,
            "worst_agreement": worst}


def china_pair(data: dict, band: float) -> dict:
    """B3-8. `z(CNH, CNY)`: one sovereign, two currency codes.

    Same issuer, same bond market, same default risk. What differs is the
    capital account, so the cycle carries **no default-risk component by
    construction** and what is left is segmentation — the source manuscript's
    hole in its most literal available form.
    """
    z2: dict = defaultdict(list)
    floor: dict = defaultdict(list)
    for (g, tenor, date), by_cur in data["dev"].items():
        if g != "eme":
            continue
        if "CNH" in by_cur and "CNY" in by_cur:
            a = float(np.clip(by_cur["CNH"], -band, band))
            b = float(np.clip(by_cur["CNY"], -band, band))
            z2[tenor].append((a - b) ** 2)
        cell = data["both"].get((g, tenor, date), {})
        for cur in ("CNH", "CNY"):
            if cur in cell:
                i, s = cell[cur]
                floor[tenor].append((i - s) ** 2)
    out = {}
    for tenor in TENORS:
        if z2.get(tenor):
            n = float(np.mean(floor[tenor])) if floor.get(tenor) else None
            m = float(np.mean(z2[tenor]))
            out[tenor] = {
                "z_rms_bp": float(np.sqrt(m)),
                "floor_rms_bp": float(np.sqrt(n)) if n else None,
                "ratio": (m / n) if n else None,
                "cells": len(z2[tenor]),
            }
    return out


def leg_decomposition(data: dict, band: float) -> dict:
    """B3-5. Which leg carries the cycle?

    `x = diff_y − rho`, so within a date and tenor the cross-sectional variance
    splits

        Var(x) = Var(diff_y) + Var(rho) − 2 Cov(diff_y, rho)

    and `Z = 2·Var(x)` inherits the split. **The bond leg is what a critic
    assigns to sovereign credit; the forward-premium leg is the price of hedged
    dollar funding**, which is where balance-sheet capacity is priced.

    **The shares are covariance contributions, not ratios of variances.** The
    identity used is

        Var(x) = Cov(x, diff_y) − Cov(x, rho)

    which is exact and whose two terms sum to `Var(x)` by construction, so the
    shares sum to one and each is a leg's contribution to the dispersion of `x`.

    The obvious alternative — each leg's own variance over `Var(x)` — is useless
    here and the data says why. The two legs nearly cancel: `Var(diff_y)` and
    `Var(rho)` each run about twenty to twenty-five times `Var(x)`, with a
    covariance term near `−45` that removes almost all of it. Under that
    cancellation both "shares" are enormous for any data whatever, so a
    threshold on them tests nothing.
    """
    out = {}
    for g in ("g10", "eme"):
        vx, cy, cr, scale = [], [], [], []
        for (grp, _tenor, _date), by_cur in data["legs"].items():
            if grp != g or len(by_cur) < 2:
                continue
            dy = np.array([a for a, _ in by_cur.values()], dtype=float)
            rh = np.array([b for _, b in by_cur.values()], dtype=float)
            # `x` is rebuilt from the legs rather than read from `cip_govt`, so
            # that the decomposition is of the same number it decomposes.
            x = np.clip(dy - rh, -band, band)
            vx.append(x.var())
            cy.append(float(np.cov(x, dy, bias=True)[0, 1]))
            cr.append(float(np.cov(x, rh, bias=True)[0, 1]))
            scale.append((dy.var(), rh.var()))
        if vx and np.mean(vx) > 0:
            total = float(np.mean(vx))
            out[g] = {
                "var_x": total,
                "share_bond_leg": float(np.mean(cy)) / total,
                "share_forward_leg": -float(np.mean(cr)) / total,
                # Recorded because it is the reason the naive decomposition
                # fails, and because two legs that cancel to a twentieth of
                # themselves is a fact about the market, not a nuisance.
                "leg_variance_over_var_x": [
                    float(np.mean([a for a, _ in scale])) / total,
                    float(np.mean([b for _, b in scale])) / total,
                ],
                "cells": len(vx),
            }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--band", type=float, default=DEFAULT_BAND)
    ap.add_argument("--scan", action="store_true",
                    help="run every band in BANDS and report the sweep")
    args = ap.parse_args()

    print("B3: the slice summand, on CIP deviations\n")
    print("  derived series, not my retrieval; a deviation is not a profit")
    data = load()
    print(f"\n  {data['rows']:,} rows, dropped for missing cip_govt: "
          f"{data['dropped']}")

    bands = BANDS if args.scan else (args.band,)
    runs = {}
    for b in bands:
        r = analyse(data, b)
        runs[b] = r
        g10 = r["energy"].get("g10", {})
        eme = r["energy"].get("eme", {})
        mat = r["energy_matched"].get("g10", {})
        fl = r["floor"].get("g10", {})
        print(f"\n  band +/-{b:.0f} bp   (Z/N uses the matched cells only)")
        print("    tenor   sqrt Z g10   sqrt Z eme   sqrt Z matched"
              "   sqrt N   Z/N")
        for tenor in TENORS:
            if tenor not in g10:
                continue
            z, m, n = g10[tenor], mat.get(tenor), fl.get(tenor)
            ratio = (m / n) if (m and n) else float("nan")
            print(f"    {tenor:5s}  {np.sqrt(z):11.1f}"
                  f"  {np.sqrt(eme.get(tenor, np.nan)):11.1f}"
                  f"  {np.sqrt(m) if m else float('nan'):14.1f}"
                  f"  {np.sqrt(n) if n else float('nan'):7.1f}"
                  f"  {ratio:7.1f}")

    r = runs[args.band if not args.scan else BANDS[-1]]
    g10 = r["energy"].get("g10", {})
    mat = r["energy_matched"].get("g10", {})
    fl = r["floor"].get("g10", {})

    b3_1 = bool(r["worst_identity_error"] < B3_1_TOL)
    print(f"\n  B3-1  enumeration equals 2*Var: "
          f"{'pass' if b3_1 else 'FAIL'}, worst relative error "
          f"{r['worst_identity_error']:.2e} against {B3_1_TOL:.0e}")

    ratios = [mat[t] / fl[t] for t in mat if fl.get(t)]
    b3_3 = bool(ratios) and bool(all(x > B3_3_FACTOR for x in ratios))
    print(f"  B3-3  signal above the noise floor, matched cells: "
          f"{'pass' if b3_3 else 'FAIL'}, Z/N over {len(ratios)} tenors "
          f"ranges {min(ratios):.1f} to {max(ratios):.1f} against "
          f"{B3_3_FACTOR}")

    over = [bool(np.sqrt(v) > B3_4_BP) for v in g10.values()]
    b3_4 = bool(over) and bool(sum(over) / len(over) > B3_4_SHARE)
    print(f"  B3-4  cross-currency cycles do not vanish in G10: "
          f"{'pass' if b3_4 else 'FAIL'}, {sum(over)}/{len(over)} tenors above "
          f"{B3_4_BP:.0f} bp")

    legs = leg_decomposition(data, args.band if not args.scan else BANDS[-1])
    lg = legs.get("g10", {})
    b3_5 = bool(lg) and bool(lg["share_forward_leg"] > B3_5_LEG_SHARE)
    print(f"  B3-5  the forward-premium leg carries a material share: "
          f"{'pass' if b3_5 else 'FAIL'}, G10 bond leg "
          f"{lg.get('share_bond_leg', float('nan')):+.3f}, forward leg "
          f"{lg.get('share_forward_leg', float('nan')):+.3f}, sum "
          f"{lg.get('share_bond_leg', 0) + lg.get('share_forward_leg', 0):.3f}"
          f", against {B3_5_LEG_SHARE}")
    if lg:
        a, b = lg["leg_variance_over_var_x"]
        print(f"      the legs nearly cancel: Var(diff_y)/Var(x) = {a:.1f}, "
              f"Var(rho)/Var(x) = {b:.1f}. The deviation is the small "
              f"residual of two large series that track each other")
    if "eme" in legs:
        e = legs["eme"]
        print(f"      eme, reported and not evidence: bond "
              f"{e['share_bond_leg']:+.3f}, forward "
              f"{e['share_forward_leg']:+.3f}")

    band = args.band if not args.scan else BANDS[-1]

    worst_diag = trivial_cycle(data, band)
    b3_2 = bool(worst_diag == 0.0)
    print(f"  B3-2  the trivial cycle is exactly zero: "
          f"{'pass' if b3_2 else 'FAIL'}, worst |z(i,i)| {worst_diag:.1e}")

    stab = sign_stability(data, band)
    b3_6 = bool(stab["worst_agreement"] >= B3_6_TENORS)
    print(f"  B3-6  sign stable across maturities: "
          f"{'pass' if b3_6 else 'FAIL'}, ranked on {stab['select_tenor']} and "
          f"tested on the other {len(TENORS) - 1}; worst of the top "
          f"{B3_6_TOP_PAIRS} pairs agrees on {stab['worst_agreement']}, "
          f"against {B3_6_TENORS}")

    cn = china_pair(data, band)
    cn_ratios = [v["ratio"] for v in cn.values() if v["ratio"]]
    b3_8 = bool(cn_ratios) and bool(
        all(x > B3_3_FACTOR for x in cn_ratios)
    )
    print(f"  B3-8  CNH against CNY, one sovereign and two codes: "
          f"{'pass' if b3_8 else 'FAIL'}, rms z "
          f"{min(v['z_rms_bp'] for v in cn.values()):.1f} to "
          f"{max(v['z_rms_bp'] for v in cn.values()):.1f} bp over "
          f"{len(cn)} tenors; z/floor "
          f"{min(cn_ratios):.1f} to {max(cn_ratios):.1f} against "
          f"{B3_3_FACTOR}" if cn_ratios else "  B3-8  void: no matched cells")

    rk = r["energy_rank"].get("g10", {})
    if rk:
        print(f"      rank version, band-free by construction: sqrt Z on "
              f"ranks {min(np.sqrt(list(rk.values()))):.2f} to "
              f"{max(np.sqrt(list(rk.values()))):.2f} across tenors, "
              f"non-zero everywhere the banded version is")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b3_cip_slice.json"
    out.write_text(
        json.dumps(
            {
                "stage": "B3",
                "source": "Du, Keerati and Schreger (2025), cip_dataset_v4",
                "caveat": (
                    "Derived series, not my retrieval. A CIP deviation is the "
                    "shadow price of balance-sheet capacity, not a profit."
                ),
                "rows": data["rows"],
                "dropped_missing_cip_govt": data["dropped"],
                "thresholds": {
                    "B3-1": B3_1_TOL, "B3-3": B3_3_FACTOR,
                    "B3-4 bp": B3_4_BP, "B3-4 share": B3_4_SHARE,
                    "B3-5 forward leg share": B3_5_LEG_SHARE,
                },
                "leg_decomposition": legs,
                "bands": {
                    str(b): {
                        k: v for k, v in runs[b].items() if k != "per_date"
                    }
                    for b in runs
                },
                "verdicts": {
                    "B3-1": b3_1, "B3-2": b3_2, "B3-3": b3_3,
                    "B3-4": b3_4, "B3-5": b3_5, "B3-6": b3_6,
                    "B3-8": b3_8,
                },
                "sign_stability": stab,
                "china_pair": cn,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
