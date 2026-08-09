"""B2 loop B: the vintage wedge, measured as a bound and labelled as H-zero.

Pre-registered in ``docs/b2_loop_b.md``. Run the retrieval first::

    python data/fetch_nmdb.py

Then::

    python experiments/b2_loop_b.py
    python experiments/b2_loop_b.py --weight VALUE2   # UPB-weighted robustness

Writes ``figures/b2_fig14_*.png`` and ``results/b2_loop_b.json``.

What this stage does and does not claim
---------------------------------------
Loop A's within share is a **holonomy**: a dwelling transfers at one market price,
so the agent edge exists with weight zero, the four-cycle closes, and Theorem 3
makes the measured variance half the mean squared cycle sum.

Loop B's dispersion is **not**. A below-market mortgage cannot be assumed, so the
agent edge is missing, the enlarged graph disconnects, and the square is not a
cycle. Whatever comes out here is the separation between components, an `H⁰`
quantity, and it is not evidence of non-integrability however large it is.

Reporting the larger number as the stronger evidence would be the error this
project exists to avoid, so the criteria below never call it one.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from monetary_topology.binned_dispersion import (
    RATE_BUCKETS,
    shares_are_usable,
    variance_lower_bound,
)
from monetary_topology.plotting import (
    COLOR_ACCENT,
    COLOR_INSTRUMENT,
    COLOR_LAYER1,
    COLOR_LAYER2,
    annotate,
    apply_style,
    save,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "nmdb"
FIGURES = ROOT / "figures"
RESULTS = ROOT / "results"

BUCKET_SERIES = [name for name, _, _ in RATE_BUCKETS]

#: Files written by ``data/fetch_nmdb.py``. Names not in this list are skipped and
#: reported rather than silently read, the same discipline as the loop A loader,
#: so a stray file cannot enter the sample and nothing needs deleting to keep it
#: out.
EXPECTED_FILES = (
    "nmdb_outstanding_national.csv",
    "nmdb_outstanding_states.csv",
    "nmdb_new_national.csv",
)

HEADLINE_MARKET = "All Mortgages"
COMPARISON_MARKET = "Conventional Market"

#: Loop A's size-weighted mean within-cell variance, read from its own result
#: record rather than copied here, so the comparison cannot drift out of date.
LOOP_A_FALLBACK = 0.3362666361898446


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.name}\n         {self.detail}"


def loop_a_within() -> tuple[float, str]:
    """Loop A's within-cell variance, and where the number came from."""
    path = RESULTS / "b2_loop_a.json"
    if path.exists():
        record = json.loads(path.read_text())
        block = record.get("variance_restricted") or record.get("variance")
        if block and "within" in block:
            return float(block["within"]), "read from results/b2_loop_a.json"
    return LOOP_A_FALLBACK, "loop A record absent; using the recorded fallback"


def load() -> tuple[dict, dict[str, int]]:
    """Read the retrieved NMDB files into ``{key: {series: value}}``.

    The key is ``(geolevel, geoid, geoname, market, period)``. Suppressed rows are
    dropped and counted; FHFA suppresses cells built on fewer than three sample
    loans, and a suppressed cell is missing rather than zero.
    """
    if not RAW.exists():
        raise SystemExit(
            f"no data directory at {RAW.relative_to(ROOT)}.\n"
            "Run:  python data/fetch_nmdb.py"
        )

    present = {p.name for p in RAW.glob("*.csv")}
    missing = [n for n in EXPECTED_FILES if n not in present]
    if missing:
        raise SystemExit(
            f"missing retrieved files: {missing}\nRun:  python data/fetch_nmdb.py"
        )
    stray = sorted(present - set(EXPECTED_FILES))
    if stray:
        print(f"  skipped {len(stray)} file(s) off-convention: {', '.join(stray[:5])}")

    counts = {"rows": 0, "suppressed": 0, "unparsable": 0}
    table: dict = defaultdict(dict)
    for name in EXPECTED_FILES:
        # Series are namespaced by source. Both the outstanding and the new
        # files publish AVE_INTRATE for the same geography, market and quarter,
        # so an unnamespaced key silently lets whichever file loads last
        # overwrite the other. That put the new-origination rate in the slot
        # labelled "outstanding average" on the first run of this loader.
        source = "new" if name.startswith("nmdb_new") else "outstanding"
        with (RAW / name).open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if (row.get("SERIESID") or "").startswith("#"):
                    continue
                counts["rows"] += 1
                if (row.get("SUPPRESSED") or "0").strip() == "1":
                    counts["suppressed"] += 1
                    continue
                key = (
                    row["GEOLEVEL"],
                    row["GEOID"],
                    row["GEONAME"],
                    row["MARKET"],
                    row["PERIOD"],
                )
                for weight in ("VALUE1", "VALUE2"):
                    slot = f"{source}::{row['SERIESID']}::{weight}"
                    try:
                        table[key][slot] = float(row[weight])
                    except (KeyError, TypeError, ValueError):
                        counts["unparsable"] += 1
    print(
        f"  loaded {len(EXPECTED_FILES)} files, {counts['rows']:,} rows, "
        f"{counts['suppressed']:,} suppressed"
    )
    return table, counts


def panel(
    table: dict, geolevel: str, market: str, weight: str
) -> tuple[list[str], list[str], np.ndarray]:
    """Bucket shares as ``(rows, buckets)``, with the row labels.

    Rows failing the share-sum check are dropped here and counted by the caller,
    never rescaled: a set of shares that does not sum to 100 is a set whose
    provenance is unclear, and patching it would hide that.
    """
    labels, geos, rows = [], [], []
    for (level, geoid, _name, mkt, period), values in sorted(table.items()):
        if level != geolevel or mkt != market:
            continue
        share = [values.get(f"outstanding::{s}::{weight}") for s in BUCKET_SERIES]
        if any(v is None for v in share):
            continue
        labels.append(period)
        geos.append(geoid)
        rows.append(share)
    if not rows:
        return [], [], np.zeros((0, len(BUCKET_SERIES)))
    arr = np.asarray(rows, dtype=np.float64)
    keep = shares_are_usable(arr)
    return (
        [x for x, k in zip(labels, keep, strict=True) if k],
        [g for g, k in zip(geos, keep, strict=True) if k],
        arr[keep],
    )


def series_value(
    table: dict, geolevel: str, market: str, series: str, weight: str, source: str
):
    """One series as ``{period: value}``, from a named source file.

    ``source`` is not optional because the two source files publish a series of
    the same name for the same cell; see the note in ``load``.
    """
    out = {}
    for (level, _geoid, _name, mkt, period), values in table.items():
        if level == geolevel and mkt == market:
            v = values.get(f"{source}::{series}::{weight}")
            if v is not None:
                out[period] = v
    return out


def evaluate(national: dict, states: dict, a_within: float, a_source: str) -> list:
    periods, bounds = national["periods"], national["bounds"]
    latest = periods[-1] if periods else "none"
    latest_bound = float(bounds[-1]) if len(bounds) else 0.0
    positive = bool(len(bounds)) and bool(np.all(bounds > 0.0))
    worst = float(bounds.min()) if len(bounds) else 0.0
    pre2022 = np.array(
        [b for p, b in zip(periods, bounds, strict=True) if p < "2022"], dtype=float
    )

    one_bucket = float(variance_lower_bound(np.array([[0, 100, 0, 0, 0]], float))[0])
    split_ends = float(variance_lower_bound(np.array([[50, 0, 0, 0, 50]], float))[0])

    return [
        Criterion(
            "L1  the vintage bound exceeds loop A's within-cell variance",
            latest_bound > a_within,
            f"{latest}: bound {latest_bound:.4f} (sd {latest_bound**0.5:.4f}) "
            f"against loop A's {a_within:.4f} (sd {a_within**0.5:.4f}), "
            f"{a_source}. Ratio {latest_bound / max(a_within, 1e-12):.2f}. "
            "The bound understates loop B and the spread-versus-APR gap "
            "understates loop A, so the comparison is not clean in one direction",
        ),
        Criterion(
            "L2  it is positive in every quarter, not only after 2022",
            positive and (pre2022.size > 0 and bool(np.all(pre2022 > 0.0))),
            f"{len(bounds)} quarters from {periods[0] if periods else '?'}; "
            f"smallest {worst:.4f}. Before 2022: {pre2022.size} quarters, "
            f"smallest {pre2022.min() if pre2022.size else float('nan'):.4f}. "
            "A wedge present only after the repricing would be an episode rather "
            "than a structural feature",
        ),
        Criterion(
            "L3  it is positive in every state",
            states["n_geos"] > 0 and states["n_positive"] == states["n_geos"],
            f"{states['n_positive']}/{states['n_geos']} state geographies "
            f"positive at {states['period']}; smallest {states['min']:.4f} "
            f"({states['argmin']}), largest {states['max']:.4f} "
            f"({states['argmax']})",
        ),
        Criterion(
            "L4  the null calibration is exact",
            abs(one_bucket) < 1e-15 and abs(split_ends - 2.25) < 1e-12,
            f"all mass in one bucket gives {one_bucket:.1e} (registered 0); "
            f"half below 3% and half at or above 6% gives {split_ends:.6f} "
            "(registered 2.25)",
        ),
    ]


def figure_14(national: dict, comparison: dict, market_rate: dict, a_within: float):
    periods, bounds = national["periods"], national["bounds"]
    x = np.arange(len(periods))
    ticks = [i for i, p in enumerate(periods) if p.endswith("Q1")][::2]

    fig, (ax_b, ax_s) = plt.subplots(1, 2, figsize=(11.4, 4.4))

    ax_b.plot(x, bounds, color=COLOR_LAYER1, linewidth=1.8, label="all mortgages")
    if comparison["periods"]:
        cx = [periods.index(p) for p in comparison["periods"] if p in periods]
        cy = [
            b
            for p, b in zip(comparison["periods"], comparison["bounds"], strict=True)
            if p in periods
        ]
        ax_b.plot(cx, cy, color=COLOR_LAYER2, linewidth=1.4, label="conventional")
    ax_b.axhline(
        a_within,
        color=COLOR_ACCENT,
        linestyle="--",
        linewidth=1.4,
        label="loop A within-cell variance",
    )
    ax_b.axhline(0.0, color=COLOR_INSTRUMENT, linewidth=1.0, linestyle=":")
    ax_b.set_xticks(ticks)
    ax_b.set_xticklabels(
        [periods[i] for i in ticks], rotation=45, ha="right", fontsize=7
    )
    ax_b.set_ylabel("lower bound on variance, squared points")
    ax_b.legend(fontsize=8, loc="upper left")
    ax_b.set_title("Vintage separation, bounded from below")
    annotate(
        ax_b,
        "Solid: what the outstanding stock's rate distribution guarantees.\n"
        "Dashed: loop A, which is a holonomy. This one is not: a below-market\n"
        "mortgage cannot be transferred, so there is no cycle to sum around.",
        loc="lower right",
    )

    shares = national["shares"]
    ax_s.stackplot(
        x,
        shares.T,
        labels=["< 3%", "3-4%", "4-5%", "5-6%", ">= 6%"],
        colors=[COLOR_LAYER1, COLOR_LAYER2, COLOR_ACCENT, "#8a8a8a", COLOR_INSTRUMENT],
    )
    if market_rate:
        mx = [i for i, p in enumerate(periods) if p in market_rate]
        my = [market_rate[periods[i]] for i in mx]
        ax_r = ax_s.twinx()
        ax_r.plot(mx, my, color="white", linewidth=1.6)
        ax_r.set_ylabel("new-origination rate, %", fontsize=8)
    ax_s.set_xticks(ticks)
    ax_s.set_xticklabels(
        [periods[i] for i in ticks], rotation=45, ha="right", fontsize=7
    )
    ax_s.set_ylabel("share of outstanding mortgages, %")
    ax_s.legend(fontsize=7, loc="lower left", ncol=5)
    ax_s.set_title("What the stock is actually paying")

    fig.suptitle(
        "Same position, different entry date: components, not cycles",
        fontsize=11.5,
        y=1.02,
    )
    fig.tight_layout()
    return save(fig, FIGURES / "b2_fig14_vintage_components.png")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weight", choices=("VALUE1", "VALUE2"), default="VALUE1")
    args = ap.parse_args()

    apply_style()
    print("B2 loop B: vintage separation in the outstanding stock\n")
    table, counts = load()

    periods, _, shares = panel(table, "National", HEADLINE_MARKET, args.weight)
    if not periods:
        raise SystemExit("no usable national quarters; check the retrieved files")
    bounds = variance_lower_bound(shares)
    national = {"periods": periods, "shares": shares, "bounds": bounds}
    print(f"  national: {len(periods)} usable quarters, {periods[0]} to {periods[-1]}")

    cp, _, cs = panel(table, "National", COMPARISON_MARKET, args.weight)
    comparison = {"periods": cp, "bounds": variance_lower_bound(cs) if len(cs) else []}

    latest = periods[-1]
    sp, sg, ss = panel(table, "State", HEADLINE_MARKET, args.weight)
    sel = [i for i, p in enumerate(sp) if p == latest]
    sb = variance_lower_bound(ss[sel]) if sel else np.zeros(0)
    states = {
        "period": latest,
        "n_geos": len(sel),
        "n_positive": int((sb > 0).sum()),
        "min": float(sb.min()) if sb.size else 0.0,
        "max": float(sb.max()) if sb.size else 0.0,
        "argmin": sg[sel[int(sb.argmin())]] if sb.size else "n/a",
        "argmax": sg[sel[int(sb.argmax())]] if sb.size else "n/a",
    }
    print(f"  states:   {states['n_geos']} geographies at {latest}")

    market_rate = series_value(
        table, "National", HEADLINE_MARKET, "AVE_INTRATE", "VALUE1", "new"
    )
    stock_rate = {
        p: v
        for p, v in series_value(
            table,
            "National",
            HEADLINE_MARKET,
            "AVE_INTRATE",
            args.weight,
            "outstanding",
        ).items()
        if p in periods
    }

    a_within, a_source = loop_a_within()
    path = figure_14(national, comparison, market_rate, a_within)
    print(f"  wrote {path.relative_to(ROOT)}\n")

    criteria = evaluate(national, states, a_within, a_source)
    print("criteria")
    for c in criteria:
        print(c.line())

    print("\nreported and not interpreted")
    print("  a stock's average rate differs from the current market rate whenever")
    print("  rates move. That is arithmetic, not an obstruction, so no criterion")
    print("  rests on it.")
    if latest in stock_rate:
        line = f"    {latest}: outstanding average {stock_rate[latest]:.3f}%"
        if latest in market_rate:
            gap = market_rate[latest] - stock_rate[latest]
            line += f", new originations {market_rate[latest]:.3f}%, gap {gap:+.3f}"
        print(line)

    n_pass = sum(c.passed for c in criteria)
    print(f"\n  {n_pass}/{len(criteria)} criteria passed")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b2_loop_b.json"
    out.write_text(
        json.dumps(
            {
                "stage": "B2B",
                "weight": args.weight,
                "rows_read": counts["rows"],
                "rows_suppressed": counts["suppressed"],
                "loop_a_within_cell_variance": a_within,
                "loop_a_source": a_source,
                "cohomological_note": (
                    "this bound is an H0 quantity: the mortgage cannot be "
                    "transferred, so the agent edge is absent, the enlarged graph "
                    "disconnects, and the four-cycle is not a cycle. It is not "
                    "evidence of non-integrability however large it is"
                ),
                "national": {
                    "periods": periods,
                    "bounds": [float(b) for b in bounds],
                    "shares": shares.tolist(),
                },
                "states_latest": states,
                "stock_average_rate": stock_rate,
                "new_origination_rate": market_rate,
                "criteria": [
                    {"name": c.name, "passed": bool(c.passed), "detail": c.detail}
                    for c in criteria
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(f"  wrote {out.relative_to(ROOT)}")
    return 0 if n_pass == len(criteria) else 1


if __name__ == "__main__":
    raise SystemExit(main())
