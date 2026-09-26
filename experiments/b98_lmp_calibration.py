"""B98 arms A to C: a zero whose answer the publisher already printed.

The tariff (Section 17.1.1) writes the price at a bus as

    gamma_i = lambda_R + gamma_i^L + gamma_i^C

with lambda_R the system marginal price at the reference bus, **one number for the whole
network in a given interval**. So the residual left after taking the two components off a
published price has to be the same at every node, which makes it a constant field, which makes
every cycle sum of it zero. The answer is fixed by the publisher's own pricing rule rather than
by an argument of ours about what must cancel.

Three arms, in order, and the second gates the third:

    A  the identity          is the residual the same at every node, to the published grid
    B  the zero calibration  fed that field, does the repository's own cycle machinery return
                             zero, and is what it returns bounded by the grid times the cycle
                             length as rounding alone would give
    C  the cross-check       does the cycle sum read off the price agree with the one read off
                             the components

**Arm B is not a mathematical claim.** A field built from node values has vanishing cycle sums
by construction, and so does the out-and-back that calibrates the loan stage. What the arm tests
is the pipeline: orientation, a repeated edge counted twice rather than cancelled, an
accumulation that should have been a difference, and arithmetic over hundreds of nodes. Fed a
real field with real timestamps, real gaps and real rounding whose true cycle sum is known, it
says whether the machinery that reports non-zero elsewhere can be trusted to report zero here.

    python experiments/b98_lmp_calibration.py --identity
    python experiments/b98_lmp_calibration.py --cycles
    python experiments/b98_lmp_calibration.py --record
"""
import argparse
import collections
import csv
import io
import json
import pathlib
import sys
import zipfile

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "nyiso"
sys.path.insert(0, str(ROOT / "src"))
from monetary_topology.product_graph import cycle_matrix, spanning_tree_cycles  # noqa: E402

#: The archives on disk, and what each one is.
CARRIERS = (
    ("day-ahead, zones", "probe_damlbmp_zone_zip.zip"),
    ("day-ahead, generators", "probe_damlbmp_gen_zip.zip"),
    ("real time, zones", "probe_rtlbmp_zone_zip.zip"),
)
#: Every value is printed to the cent, so one residual, being a sum of three of them, carries
#: up to three half-ticks of rounding. Measured rather than assumed: `grid_of` checks that
#: every value sits on the tick.
#:
#: **The statistic is a spread across nodes, which is a difference of two residuals, so its
#: bound is twice a residual's.** Judging a max-minus-min against one residual's resolution is
#: the sixth category error, the bound and the statistic living on different scales, and it
#: reads as 574 of 720 rather than as 720 of 720.
TICK = 0.01
RESIDUAL_GRID = 3 * (TICK / 2)
SPREAD_GRID = 2 * RESIDUAL_GRID
#: The four ways the two published component columns can enter. The tariff says both are added;
#: which sign the published columns carry is a fact about the file and not about the tariff, so
#: it is identified here by which choice makes the residual constant rather than looked up.
SIGNS = ((-1, -1), (-1, +1), (+1, -1), (+1, +1))
SIGN_NAMES = {(-1, -1): "LBMP - losses - congestion", (-1, +1): "LBMP - losses + congestion",
              (+1, -1): "LBMP + losses - congestion", (+1, +1): "LBMP + losses + congestion"}
ZONE_CYCLE_NODES = 15          # the zones, taken complete
GEN_CYCLE_NODES = 30           # a subset of the generators, taken complete, seeded
SEED = 98


def load(zip_name):
    """{timestamp: {node: (price, losses, congestion)}} from one monthly archive."""
    z = zipfile.ZipFile(RAW / zip_name)
    by_ts, raw_values = collections.defaultdict(dict), []
    for member in sorted(z.namelist()):
        with z.open(member) as f:
            for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
                cols = list(row)
                try:
                    vals = [row[k].strip() for k in cols[3:6]]
                    trio = tuple(float(v) for v in vals)
                except (ValueError, KeyError, IndexError):
                    continue
                by_ts[row["Time Stamp"]][row["Name"]] = trio
                raw_values += vals
    return by_ts, raw_values


def grid_of(values):
    """The publication tick, measured. Failure mode 165: printed digits vary because trailing
    zeros are dropped, so what separates a format from a serializer is whether every value is
    an integer multiple of one tick."""
    from decimal import Decimal
    ds = [Decimal(v) for v in values]
    places = max(-d.as_tuple().exponent for d in ds)
    unit = Decimal(1).scaleb(-places)
    off = sum(1 for d in ds if (d / unit) != (d / unit).to_integral_value())
    distinct = sorted({int(d / unit) for d in ds})
    gap = min((b - a for a, b in zip(distinct, distinct[1:])), default=1)
    return float(unit * gap), off, len(ds)


def residual_spreads(by_ts, sign):
    sl, sc = sign
    out = []
    for nodes in by_ts.values():
        v = [p + sl * lo + sc * co for p, lo, co in nodes.values()]
        out.append(max(v) - min(v))
    out.sort()
    return out


def identify_sign(by_ts):
    """The sign the published columns carry, read off the constancy the tariff requires."""
    table = {}
    for sign in SIGNS:
        sp = residual_spreads(by_ts, sign)
        table[SIGN_NAMES[sign]] = {
            "median": sp[len(sp) // 2], "p90": sp[int(0.9 * (len(sp) - 1))], "max": sp[-1],
            "within_grid": sum(1 for s in sp if s <= SPREAD_GRID + 1e-12), "n": len(sp)}
    good = [k for k, v in table.items() if v["within_grid"] == v["n"]]
    return table, good


def read_identity():
    for label, zn in CARRIERS:
        if not (RAW / zn).exists():
            print(f"=== {label}: {zn} not on disk\n")
            continue
        by_ts, raw = load(zn)
        tick, off, n = grid_of(raw)
        table, good = identify_sign(by_ts)
        counts = collections.Counter(len(v) for v in by_ts.values())
        print(f"=== {label}: {len(by_ts)} timestamps, nodes per timestamp "
              f"{dict(counts.most_common(3))}")
        print(f"    grid measured at {tick:.2f} over {n} values, {off} off it: one residual is "
              f"resolved to {RESIDUAL_GRID:.3f} and a spread between two of them to "
              f"{SPREAD_GRID:.3f}")
        for k, v in table.items():
            mark = "  <- constant" if v["within_grid"] == v["n"] else ""
            print(f"    {k:30s} median {v['median']:8.4f}  p90 {v['p90']:8.4f}  "
                  f"max {v['max']:8.4f}  within grid {v['within_grid']:5d}/{v['n']}{mark}")
        print(f"    identified: {good if good else 'none, and that is a reading'}\n")


def adjacency(k, shape):
    """Complete, or a ring with a few chords.

    **A complete graph's spanning-tree cycle basis is all triangles**, so a run on it exercises
    three-edge cycles and nothing longer, and the bugs this arm is for, an orientation flipped
    or a repeated edge counted rather than cancelled, are likelier to show on a long cycle than
    on a triangle. The ring carries one cycle through every node, and the chords add more that
    are long without making the basis triangular.
    """
    adj = np.zeros((k, k))
    if shape == "complete":
        return np.ones((k, k)) - np.eye(k)
    for i in range(k):
        adj[i, (i + 1) % k] = adj[(i + 1) % k, i] = 1.0
    for d in (k // 3, k // 2):                        # two chord families, both long
        for i in range(0, k, max(1, k // 4)):
            j = (i + d) % k
            if i != j:
                adj[i, j] = adj[j, i] = 1.0
    return adj


def cycle_report(by_ts, sign, n_nodes, shape="complete", seed=SEED):
    """Cycle sums of the residual field, through the repository's own cycle machinery."""
    sl, sc = sign
    names = sorted(next(iter(by_ts.values())))
    rng = np.random.default_rng(seed)
    take = sorted(rng.choice(len(names), size=min(n_nodes, len(names)), replace=False))
    picked = [names[i] for i in take]
    k = len(picked)
    adj = adjacency(k, shape)
    cycles = spanning_tree_cycles(adj)
    basis = cycle_matrix(adj, 1)
    # the column order `cycle_matrix` uses: undirected pairs of the position graph, m = 1
    from monetary_topology.product_graph import undirected_pairs
    cols = {pair: n for n, pair in enumerate(undirected_pairs(adj))}
    worst_energy = worst_price = worst_gap = 0.0
    lengths = []
    used = 0
    for nodes in by_ts.values():
        if any(p not in nodes for p in picked):
            continue
        used += 1
        r = np.array([nodes[p][0] + sl * nodes[p][1] + sc * nodes[p][2] for p in picked])
        price = np.array([nodes[p][0] for p in picked])
        comp = np.array([-sl * nodes[p][1] - sc * nodes[p][2] for p in picked])
        e_r = np.array([r[j] - r[i] for (i, j) in cols])
        e_p = np.array([price[j] - price[i] for (i, j) in cols])
        e_c = np.array([comp[j] - comp[i] for (i, j) in cols])
        worst_energy = max(worst_energy, float(np.abs(basis @ e_r).max()))
        worst_price = max(worst_price, float(np.abs(basis @ e_p).max()))
        worst_gap = max(worst_gap, float(np.abs(basis @ (e_p - e_c)).max()))
    lengths = [len(c) - 1 for c in cycles]
    edges = len(cols)
    return {"nodes": k, "shape": shape, "edges": edges, "cycles": int(basis.shape[0]),
            "timestamps": used, "longest_cycle": max(lengths), "b1": edges - k + 1,
            "worst_energy_cycle": worst_energy, "worst_price_cycle": worst_price,
            "worst_price_minus_components": worst_gap,
            "bound": max(lengths) * SPREAD_GRID}


def read_cycles():
    print("Cycle sums through `cycle_matrix`, the same basis every other stage uses.")
    print("A field built from node values has vanishing cycle sums by construction, so what is")
    print("read here is the pipeline and the rounding, not a claim about the world.\n")
    for label, zn in CARRIERS:
        if not (RAW / zn).exists():
            continue
        by_ts, _raw = load(zn)
        _t, good = identify_sign(by_ts)
        if not good:
            print(f"=== {label}: no sign makes the residual constant, so arm B does not run\n")
            continue
        sign = next(s for s in SIGNS if SIGN_NAMES[s] == good[0])
        n = GEN_CYCLE_NODES if "generators" in label else ZONE_CYCLE_NODES
        for shape in ("complete", "ring"):
            rep = cycle_report(by_ts, sign, n, shape)
            print(f"=== {label}, {rep['nodes']} nodes, {shape}")
            print(f"    {rep['edges']} edges, independent cycles b1 = {rep['b1']}, basis rows "
                  f"{rep['cycles']}, longest {rep['longest_cycle']} edges, over "
                  f"{rep['timestamps']} timestamps")
            print(f"    worst |cycle sum| of the residual field   "
                  f"{rep['worst_energy_cycle']:.2e}")
            print(f"    worst |cycle sum| of the published price  "
                  f"{rep['worst_price_cycle']:.2e}")
            print(f"    worst |price cycle - component cycle|     "
                  f"{rep['worst_price_minus_components']:.2e}")
            print(f"    rounding bound, longest cycle x grid      {rep['bound']:.6f}\n")


DA_ZIP, RT_ZIP = "probe_damlbmp_zone_zip.zip", "probe_rtlbmp_zone_zip.zip"
#: A square of four published prices carries four half-ticks; the identity below compares a
#: square against two more squares, so twelve of them.
SQUARE_GRID = 4 * (TICK / 2)
CHANNEL_GRID = 12 * (TICK / 2)


def hourly(rt):
    """Five-minute rows averaged onto the hour, so the two markets sit on one clock."""
    bag = collections.defaultdict(lambda: collections.defaultdict(list))
    for ts, nodes in rt.items():
        day, clock = ts.split(" ")
        for n, trio in nodes.items():
            bag[f"{day} {clock[:2]}:00"][n].append(trio)
    return {h: {n: tuple(sum(x[i] for x in v) / len(v) for i in range(3))
                for n, v in nodes.items()} for h, nodes in bag.items()}


def market_squares():
    """The same megawatt hour at one node, bought a day ahead and bought in real time.

    Two goods at the same position and the same delivery hour, differing in the contract. A
    scalar carried by each position gives both goods there the same wedge against any other
    position, so the difference of the two wedges, which is this square, is zero under it.
    """
    da, _ = load(DA_ZIP)
    rt, _ = load(RT_ZIP)
    rt_h = hourly(rt)
    names = sorted(set(next(iter(da.values()))) & set(next(iter(rt_h.values()))))
    rows = {"full": [], "loss": [], "cong": [], "residual": []}
    buckets = collections.defaultdict(list)
    worst = None
    for h in sorted(set(da) & set(rt_h)):
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if not all(n in d for d in (da[h], rt_h[h]) for n in (a, b)):
                    continue
                pa, la, ca = da[h][a]
                pb, lb, cb = da[h][b]
                qa, ma, xa = rt_h[h][a]
                qb, mb, xb = rt_h[h][b]
                full = (pa - qa) - (pb - qb)
                loss = (la - ma) - (lb - mb)
                cong = (ca - xa) - (cb - xb)
                rows["full"].append(abs(full))
                rows["loss"].append(abs(loss))
                rows["cong"].append(abs(cong))
                rows["residual"].append(abs(full - (loss - cong)))
                worst_cong = max(abs(ca), abs(cb), abs(xa), abs(xb))
                key = ("open" if worst_cong <= SQUARE_GRID else
                       "light" if worst_cong < 1.0 else "binding")
                buckets[key].append(abs(full))
                if worst is None or abs(full) > worst["square"]:
                    worst = {"square": abs(full), "hour": h, "a": a, "b": b,
                             "loss_channel": loss, "congestion_channel": cong}
    return rows, buckets, worst, len(names)


def read_squares():
    rows, buckets, worst, n_nodes = market_squares()
    n = len(rows["full"])
    print(f"Day-ahead against real time at {n_nodes} zones, {n} node pairs over the month.")
    print("A scalar carried by each position predicts every one of these is zero.\n")
    print(f"{'channel':36s} {'median':>9s} {'p90':>9s} {'max':>10s} {'over its grid':>20s}")
    for k, lab, grid in (("full", "the square itself", SQUARE_GRID),
                         ("loss", "its loss channel", SQUARE_GRID),
                         ("cong", "its congestion channel", SQUARE_GRID),
                         ("residual", "square minus (loss - congestion)", CHANNEL_GRID)):
        v = sorted(rows[k])
        over = sum(1 for x in v if x > grid)
        print(f"{lab:36s} {v[len(v)//2]:9.3f} {v[int(0.9*len(v))]:9.3f} {v[-1]:10.3f} "
              f"{over:9d}/{n:7d} at {grid:.2f}")
    print(f"\nlargest square {worst['square']:.3f} at {worst['hour']} between {worst['a']} "
          f"and {worst['b']}: congestion channel {worst['congestion_channel']:.3f}, "
          f"loss channel {worst['loss_channel']:.3f}")
    print("\nby whether a transmission constraint is in play on the pair:")
    for k in ("open", "light", "binding"):
        v = sorted(buckets[k])
        if not v:
            continue
        print(f"  {k:9s} {len(v):7d} pairs   median {v[len(v)//2]:8.3f}   "
              f"p90 {v[int(0.9*len(v))]:8.3f}   max {v[-1]:9.3f}")
    print("\n**The open bucket does not fall to the floor**, which is a fact about the carrier:")
    print("moving power always costs power, so the loss channel is never switched off and this")
    print("network has no interval in which the edge is fully open.")


def write_record():
    """Every number here is computed from the archives on disk."""
    out = ROOT / "results" / "b98_lmp_calibration.json"
    per_carrier, cyc = {}, {}
    for label, zn in CARRIERS:
        if not (RAW / zn).exists():
            continue
        by_ts, raw = load(zn)
        tick, off, n = grid_of(raw)
        table, good = identify_sign(by_ts)
        per_carrier[label] = {"archive": zn, "timestamps": len(by_ts),
                              "nodes": len(next(iter(by_ts.values()))),
                              "tick": tick, "values": n, "off_grid": off,
                              "identified": good, "spreads": table}
        if good:
            sign = next(sg for sg in SIGNS if SIGN_NAMES[sg] == good[0])
            n_nodes = GEN_CYCLE_NODES if "generators" in label else ZONE_CYCLE_NODES
            cyc[label] = {sh: cycle_report(by_ts, sign, n_nodes, sh)
                          for sh in ("complete", "ring")}

    total_off = sum(v["off_grid"] for v in per_carrier.values())
    total_vals = sum(v["values"] for v in per_carrier.values())
    held = [(k, v["spreads"][v["identified"][0]]) for k, v in per_carrier.items()
            if v["identified"]]
    unique = all(len(v["identified"]) == 1 for v in per_carrier.values())
    worst_cycle = max((r["worst_energy_cycle"] for c in cyc.values() for r in c.values()),
                      default=float("nan"))
    worst_price = max((r["worst_price_cycle"] for c in cyc.values() for r in c.values()),
                      default=float("nan"))
    longest = max((r["longest_cycle"] for c in cyc.values() for r in c.values()), default=0)
    most_cycles = max((r["b1"] for c in cyc.values() for r in c.values()), default=0)

    crit = [
        {"name": "B98-1", "kind": "instrument", "passed": total_off == 0 and bool(per_carrier),
         "statement": "Every published value sits on an integer number of one tick, which is "
                      "what makes the printed grid usable as a floor rather than an artefact "
                      "of the serializer.",
         "detail": f"{total_vals:,} values over {len(per_carrier)} archives, {total_off} off "
                   f"the grid, tick "
                   f"{sorted({v['tick'] for v in per_carrier.values()})}. Checked rather than "
                   f"counted from the printed digits, since trailing zeros are dropped."},
        {"name": "B98-2", "kind": "known_answer",
         "passed": bool(held) and all(t["within_grid"] == t["n"] for _k, t in held),
         "statement": "The tariff writes the price at a bus as a reference price plus two "
                      "components, with the reference the same everywhere in an interval, so "
                      "the residual after removing the components has to be constant across "
                      "nodes. It is, to the grid the values are published on.",
         "detail": "; ".join(
             f"{k}: {t['within_grid']}/{t['n']} intervals within {SPREAD_GRID:.3f}, "
             f"max spread {t['max']:.4f}" for k, t in held)
             + f". The bound is a spread between two residuals, each a sum of three published "
               f"values, so it is {SPREAD_GRID:.3f} and not {RESIDUAL_GRID:.3f}: judging a "
               f"max-minus-min against one residual's resolution reads as 574 of 720 rather "
               f"than 720 of 720. **This is the zero calibration, and the answer comes from "
               f"the publisher's own pricing rule rather than from an argument here about "
               f"what must cancel.**"},
        {"name": "B98-3", "kind": "instrument", "passed": unique and bool(per_carrier),
         "statement": "Exactly one of the four ways the two component columns can enter makes "
                      "the residual constant, so the sign the published columns carry is "
                      "identified by the requirement itself rather than looked up.",
         "detail": "; ".join(f"{k}: {v['identified']}" for k, v in per_carrier.items())
                   + ". The tariff adds both components; the published congestion column "
                     "carries the opposite sign, and nothing but the constancy was needed to "
                     "find that. Two conventions holding at once would leave the sign "
                     "undetermined and this criterion would not pass."},
        {"name": "B98-4", "kind": "instrument",
         "passed": bool(cyc) and worst_cycle == 0.0 and worst_price < 1e-9,
         "statement": "Fed that field, the cycle machinery every other stage uses returns "
                      "zero, on a complete graph and on a ring with chords so that long "
                      "cycles are exercised and not only triangles.",
         "detail": f"worst |cycle sum| of the residual field {worst_cycle:.2e}, of the "
                   f"published price {worst_price:.2e}, over up to {most_cycles} independent "
                   f"cycles and a longest cycle of {longest} edges. **A field built from node "
                   f"values has vanishing cycle sums by construction, so this is a check on "
                   f"the pipeline and not a claim about the world**: orientation, a repeated "
                   f"edge counted rather than cancelled, and arithmetic over hundreds of "
                   f"nodes. A complete graph's spanning-tree basis is all triangles, which is "
                   f"why the ring is here."},
    ]
    rows, buckets, worst, n_zones = market_squares()
    n_pairs = len(rows["full"])
    over = {k: sum(1 for x in rows[k] if x > SQUARE_GRID) for k in ("full", "loss", "cong")}
    resid_out = sum(1 for x in rows["residual"] if x > CHANNEL_GRID)
    med = {k: sorted(rows[k])[len(rows[k]) // 2] for k in rows}
    bmed = {k: (sorted(v)[len(v) // 2] if v else float("nan")) for k, v in buckets.items()}
    crit += [
        {"name": "B98-5", "kind": "rival", "grid": "B", "passed": over["full"] > 0,
         "rival_shape": "point prediction",
         "rival_premise": "Each position carries one scalar and every price at that position "
                          "is that scalar plus a term belonging to the contract alone.",
         "rival_entailment": "Under it the wedge between two positions is the same for every "
                             "contract, so the difference of the day-ahead wedge and the real "
                             "time wedge, a four-cycle over two positions and two contracts "
                             "for the same megawatt hour in the same delivery hour, is exactly "
                             "zero. Both legs are published per node, and the floor is the "
                             "grid they are printed on, so nothing is estimated.",
         "statement": "The rival's point prediction of zero does not hold on the day-ahead "
                      "against real time squares. Passing means the rival is wrong here.",
         "detail": f"{over['full']:,} of {n_pairs:,} node pairs stand above the published "
                   f"floor of {SQUARE_GRID:.2f}, median {med['full']:.3f}, largest "
                   f"{max(rows['full']):.3f} which is {max(rows['full']) / SQUARE_GRID:,.0f} "
                   f"times the floor, over {n_zones} zones and a month of delivery hours. "
                   f"**Neither leg is priced off a bank and there is no money in this carrier "
                   f"at all.**"},
        {"name": "B98-6", "kind": "known_answer", "passed": resid_out == 0,
         "statement": "That square is exactly its loss channel less its congestion channel, "
                      "both of which the publisher prints separately, to the grid they are "
                      "printed on.",
         "detail": f"{n_pairs - resid_out:,} of {n_pairs:,} pairs lie within {CHANNEL_GRID:.2f}, "
                   f"which is twelve published values at half a tick each; median residual "
                   f"{med['residual']:.3f}, largest {max(rows['residual']):.3f}. **So the "
                   f"non-zero cycle is not only measured, it is attributed**: the largest "
                   f"square in the month, {worst['square']:.3f} at {worst['hour']} between "
                   f"{worst['a']} and {worst['b']}, is congestion "
                   f"{worst['congestion_channel']:.3f} against losses "
                   f"{worst['loss_channel']:.3f}."},
        {"name": "B98-7", "kind": "own_reading",
         "passed": bool(buckets["binding"]) and bool(buckets["open"])
                   and bmed["binding"] > bmed["open"],
         "statement": "The two channels do not behave alike: congestion switches on and off "
                      "while losses do not, so this network has no interval in which the edge "
                      "between two nodes is fully open.",
         "detail": f"congestion stands above the floor on {over['cong'] / n_pairs:.1%} of pairs "
                   f"and losses on {over['loss'] / n_pairs:.1%}. Split by whether a constraint "
                   f"is in play: open {len(buckets['open']):,} pairs at median "
                   f"{bmed['open']:.3f}, light {len(buckets['light']):,} at "
                   f"{bmed['light']:.3f}, binding {len(buckets['binding']):,} at "
                   f"{bmed['binding']:.3f}. **The open bucket does not fall to the floor**, it "
                   f"sits at {bmed['open'] / SQUARE_GRID:.0f} times it, because moving power "
                   f"always costs power. A design that assumed an edge could be switched fully "
                   f"off and back would not find that state here, which is the same thing the "
                   f"Cyprus carrier turned out to lack in a different way."},
    ]
    for c in crit:
        if not isinstance(c["passed"], bool):
            raise SystemExit(f"{c['name']}: passed is not a bool")
    rec = {"stage": "B98",
           "config": {"archives": [z for _l, z in CARRIERS], "tick": TICK,
                      "residual_grid": RESIDUAL_GRID, "spread_grid": SPREAD_GRID,
                      "zone_nodes": ZONE_CYCLE_NODES, "gen_nodes": GEN_CYCLE_NODES,
                      "seed": SEED, "shapes": ["complete", "ring"]},
           "mapping": {
               "B98-2": "constant to the spread grid on every interval -> PASS; any interval "
                        "outside it -> FAIL, and the sign convention is re-read first",
               "B98-3": "exactly one convention constant -> PASS; none -> FAIL and the "
                        "identity does not hold here; more than one -> FAIL, undetermined"},
           "criteria": crit,
           "report": {"carriers": per_carrier, "cycles": cyc,
                      "squares": {"pairs": n_pairs, "zones": n_zones, "over_floor": over,
                                  "median": med, "residual_outside": resid_out,
                                  "largest": worst,
                                  "by_constraint": {k: {"pairs": len(v), "median": bmed[k]}
                                                    for k, v in buckets.items()}},
                      "note": "m = 1: every participant at a node faces one price, so this "
                              "station has no agent layer and reaches no reading about two "
                              "classes at one position. The rival criterion it does carry is "
                              "over two goods rather than two classes of holder, which that "
                              "limit does not exclude. "
                              "It buys instrument credibility rather than breadth, and the "
                              "two are not substitutes."}}
    out.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8")
    print(f"wrote {out}")
    for c in crit:
        print(f"  {c['name']:7s} {c['kind']:12s} {'PASS' if c['passed'] else 'FAIL'}")
    rivals = [c for c in crit if c.get("kind") == "rival"]
    print(f"\nall {len(crit)} criteria written; {len(rivals)} rival criterion, "
          f"{sum(1 for c in rivals if c['passed'])} of which pass, which is to say the rival's "
          f"point prediction of zero fails there")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--identity", action="store_true")
    ap.add_argument("--cycles", action="store_true")
    ap.add_argument("--squares", action="store_true")
    ap.add_argument("--record", action="store_true")
    a = ap.parse_args()
    if a.identity:
        read_identity()
    elif a.cycles:
        read_cycles()
    elif a.squares:
        read_squares()
    elif a.record:
        write_record()
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
