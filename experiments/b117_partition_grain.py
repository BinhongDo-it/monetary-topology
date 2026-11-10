"""B117: how coarse the classes of a chain can be before it stops reading back how long new money
stays in the area it enters.

What this is for. B114 (experiments/b114_sarafu.py) follows each month's new Sarafu by the area it
entered and reads the share still in that area week by week. A chain in which every wallet spends
at its own quarterly speed and pays its own counterparts reads that share back; the same chain run
on whole areas reads it low, at 52 weeks by up to about 62 points. This script runs the chain on
classes between those two ends. A wallet's spending speed, and where its payments land, are taken
from its class: what a class pays on lands across classes by the class's own payment mix, and
within a class by what each wallet of it receives. With each wallet's own speed, or classes that
cross areas, the state is kept wallet by wallet; with the class's speed and classes inside areas
every wallet of a class moves alike, so the chain runs on class balances as a sparse K x K step,
which the wallet state summed into classes equals (block 0 checks it). With areas as
the classes the chain is B114's area chain; with single wallets it is B114's wallet chain; both are
checked against B114 to the last digit before anything else is read.

Blocks:
  0  the two ends and the lumping: classes = areas against B114's area chains, classes = single
     wallets against B114's wallet chain, and a chain run on class balances against the same chain
     run wallet by wallet and summed into classes
  1  the first partitions, each with the class's spending speed and with each wallet's own:
     area x business type; random classes within each area with the same class sizes; within-area
     strata of each wallet's own spending speed with the same class count per area, and random
     classes of those equal sizes; within each area, the wallets that received new money and the
     wallets that did not
  2  payment circles: the connected parts of the payments inside each area, then Louvain classes at
     rising resolution, each level read against random classes of the same sizes, own-speed strata and
     random classes of equal size with the same class counts; and each circle cut into its slower and
     faster half, against partitions matched to that

    python experiments/b117_partition_grain.py              # blocks 0 to 2
    python experiments/b117_partition_grain.py --block 1 --jobs 2   # chains not yet cached, two at a time
    python experiments/b117_partition_grain.py --criteria   # blocks 0 to 2, then the criteria
    python experiments/b117_partition_grain.py --write      # the criteria, and the record written to results/
    python experiments/b117_partition_grain.py --selftest   # seeded faults on synthetic archives and panels

Three criteria follow the objects (B117-1 to B117-3). B117-2 and B117-3 read B114's 55 cells at the 18 settings of
B114's three knobs and three Louvain seeds; the chains are cached, and with --jobs the ones not yet cached run in parallel.

Only aggregates are printed: areas, class counts by area, months and ages. No wallet address or
account id leaves the reading. Chain results are cached under data/cache/b117/, keyed on the archive,
on experiments/b114_sarafu.py, on the source of the chain functions here, on the partition and on
the setting; a change to any of them misses the cache.
"""
from __future__ import annotations

import argparse
import bisect
import datetime as dt
import hashlib
import inspect
import json
import multiprocessing
import os
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b114_sarafu as S  # noqa: E402  the archive reader, tag pass and wallet panel, imported not copied

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache" / "b117"
RANDOM_SEEDS = (0, 1, 2, 3, 4)
SPEEDS = ("class", "own")      # a wallet's spending speed taken from its class, or from itself
PRINT_MIN_COHORTS = 10         # the areas B114's block 8 prints


# ---------------------------------------------------------------------------
# Partitions: an integer class for each wallet in circulation, in the order of B114's wallet panel
# ---------------------------------------------------------------------------

def circulation_order(a, res):
    """The wallets in circulation, in the order of B114's wallet panel."""
    cls = {k: S.class_of(v) for k, v in a.users.items()}
    ci = {c: i for i, c in enumerate(res["classes"])}
    return [w for w in sorted(a.users) if cls[w] in ci]


def from_keys(keys):
    """Classes numbered by the sorted distinct keys: the class of each wallet, the class count, the keys."""
    import numpy as np
    distinct = sorted(set(keys))
    idx = {k: i for i, k in enumerate(distinct)}
    return np.fromiter((idx[k] for k in keys), dtype=np.int64, count=len(keys)), len(distinct), distinct


def renumber(part):
    import numpy as np
    _, inv = np.unique(part, return_inverse=True)
    return inv.astype(np.int64).ravel()


def refines(part, wclass):
    """True when no class holds wallets of two areas."""
    import numpy as np
    if part.size == 0:
        return True
    K = int(part.max()) + 1
    lo = np.full(K, np.iinfo(np.int64).max, dtype=np.int64)
    hi = np.full(K, -1, dtype=np.int64)
    np.minimum.at(lo, part, wclass)
    np.maximum.at(hi, part, wclass)
    used = hi >= 0
    return bool(np.all(lo[used] == hi[used]))


def class_sizes_by_area(part, wclass):
    """For each area, the sorted sizes of the classes inside it; the partition must not mix areas."""
    import numpy as np
    if not refines(part, wclass):
        raise ValueError("the partition mixes areas")
    sizes = np.bincount(part)
    area_of = np.full(sizes.size, -1, dtype=np.int64)
    area_of[part] = wclass
    return {int(c): sorted(int(s) for s in sizes[area_of == c] if s > 0) for c in np.unique(wclass)}


def random_like(part, wclass, seed):
    """Random classes within each area with exactly the class sizes `part` has in that area."""
    import numpy as np
    if not refines(part, wclass):
        raise ValueError("the reference partition mixes areas")
    rng = np.random.default_rng(seed)
    out = np.empty_like(part)
    for c in np.unique(wclass):
        idx = np.flatnonzero(wclass == c)
        out[idx] = part[idx][rng.permutation(idx.size)]
    return renumber(out)


def split_in_order(wclass, counts, key):
    """Within each area, the wallets sorted by (key, position) cut into counts[area] runs whose sizes
    differ by at most one."""
    import numpy as np
    part = np.full(wclass.size, -1, dtype=np.int64)
    base = 0
    for c in np.unique(wclass):
        idx = np.flatnonzero(wclass == c)
        if int(c) not in counts:
            raise ValueError(f"no class count for area {int(c)}")
        k = min(int(counts[int(c)]), idx.size)
        order = idx[np.lexsort((idx, key[idx]))]
        for j, run in enumerate(np.array_split(order, k)):
            part[run] = base + j
        base += k
    return part


def own_speed(panel):
    """Each wallet's spending speed over the whole panel: value paid on or out of circulation per unit
    of balance-days (a wallet that pays out without holding a balance at any day's end is infinitely fast)."""
    import numpy as np
    out = np.zeros(panel["N"])
    for src, _, val in panel["edges"]:
        out += np.bincount(src, weights=val, minlength=panel["N"])
    tot = out + panel["sink"].sum(axis=0)
    bd = panel["balday"].sum(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(bd > 0, tot / np.where(bd > 0, bd, 1.0), np.where(tot > 0, np.inf, 0.0))


def received_new_money(panel):
    """The wallets that received new money in any month (B114's disbursements after the conversion)."""
    import numpy as np
    got = np.zeros(panel["N"], dtype=bool)
    for js, ws in panel["new_money"].values():
        got[js[ws > 0]] = True
    return got


def first_partitions(a, res, panel):
    """name -> (class of each wallet, class count), in the order of the printed tables."""
    import numpy as np
    wclass, N = panel["wclass"], panel["N"]
    circ = circulation_order(a, res)
    if len(circ) != N:
        raise AssertionError(f"{len(circ)} wallets in circulation against {N} in the panel")
    parts = {"area": (wclass.astype(np.int64).copy(), len(res["classes"]))}
    bt, k_bt = business_type_partition(a, res, panel)
    parts["area x business type"] = (bt, k_bt)
    for seed in RANDOM_SEEDS:
        r = random_like(bt, wclass, seed)
        parts[f"random, business-type sizes, seed {seed}"] = (r, int(r.max()) + 1)
    counts = {c: len(v) for c, v in class_sizes_by_area(bt, wclass).items()}
    sp = split_in_order(wclass, counts, own_speed(panel))
    parts["own-speed strata"] = (sp, int(sp.max()) + 1)
    for seed in RANDOM_SEEDS:
        key = np.random.default_rng(1000 + seed).permutation(N).astype(float)
        eq = split_in_order(wclass, counts, key)
        parts[f"random, equal sizes, seed {seed}"] = (eq, int(eq.max()) + 1)
    got = received_new_money(panel)
    en, k_en, _ = from_keys([(int(wclass[i]), bool(got[i])) for i in range(N)])
    parts["received new money or not"] = (en, k_en)
    parts["single wallets"] = (np.arange(N, dtype=np.int64), N)
    return parts


# ---------------------------------------------------------------------------
# Payment circles: modularity classes of the payments inside each area
# ---------------------------------------------------------------------------

def _adjacency(N, u, v, w):
    """Both directions of each undirected pair, sorted by node then neighbour, as compressed rows."""
    import numpy as np
    uu, vv, ww = np.concatenate([u, v]), np.concatenate([v, u]), np.concatenate([w, w])
    order = np.lexsort((vv, uu))
    uu, vv, ww = uu[order], vv[order], ww[order]
    return np.searchsorted(uu, np.arange(N + 1)), vv, ww


def louvain(n, u, v, w, resolution=1.0, seed=0):
    """Weighted undirected Louvain on n nodes with unique pairs (u, v, weight), u != v. Each node moves to the
    neighbouring class with the largest gain in modularity with this resolution, in a seeded order, until
    no move gains; classes then become nodes and the moves repeat, until nothing moves. Returns a class per node."""
    import numpy as np
    membership = np.arange(n, dtype=np.int64)
    eu, ev, ew = np.asarray(u, dtype=np.int64), np.asarray(v, dtype=np.int64), np.asarray(w, dtype=float)
    if n == 0 or ew.size == 0 or ew.sum() <= 0:
        return membership
    if np.any(eu == ev):
        raise ValueError("pairs must join two different nodes")
    rng = np.random.default_rng(seed)
    m2 = 2.0 * float(ew.sum())
    N, inner = n, np.zeros(n)          # inner: twice the weight of the pairs already inside each node
    while True:
        indptr, nbr, wt = _adjacency(N, eu, ev, ew)
        k = np.bincount(eu, weights=ew, minlength=N) + np.bincount(ev, weights=ew, minlength=N) + inner
        ip, nb, wl, kl = indptr.tolist(), nbr.tolist(), wt.tolist(), k.tolist()
        comm, tot = list(range(N)), list(kl)
        order = rng.permutation(N).tolist()
        moved, again, passes = False, True, 0
        while again:
            again, passes = False, passes + 1
            if passes > 1000:
                raise RuntimeError("Louvain made moves on a thousand passes of one level; each move must gain, so this is a fault")
            for i in order:
                ci, ki = comm[i], kl[i]
                links = {}
                for p in range(ip[i], ip[i + 1]):
                    cj = comm[nb[p]]
                    links[cj] = links.get(cj, 0.0) + wl[p]
                tot[ci] -= ki
                best_c, best = ci, links.get(ci, 0.0) - resolution * ki * tot[ci] / m2
                for c, lw in links.items():
                    gain = lw - resolution * ki * tot[c] / m2
                    if gain > best + 1e-12 * max(1.0, abs(best)):
                        best_c, best = c, gain
                tot[best_c] += ki
                if best_c != ci:
                    comm[i] = best_c
                    moved = again = True
        if not moved:
            return membership
        comm = renumber(np.array(comm, dtype=np.int64))
        membership = comm[membership]
        K = int(comm.max()) + 1
        cu, cv = comm[eu], comm[ev]
        same = cu == cv
        inner = np.bincount(comm, weights=inner, minlength=K) + 2.0 * np.bincount(cu[same], weights=ew[same], minlength=K)
        lo, hi = np.minimum(cu[~same], cv[~same]), np.maximum(cu[~same], cv[~same])
        keys, inv = np.unique(lo * K + hi, return_inverse=True)
        ew = np.bincount(inv.ravel(), weights=ew[~same], minlength=keys.size)
        eu, ev, N = keys // K, keys % K, K
        if ew.size == 0:
            return membership


def modularity(n, u, v, w, part, resolution=1.0):
    """Newman modularity with a resolution, for unique undirected pairs without self-pairs."""
    import numpy as np
    w = np.asarray(w, dtype=float)
    m2 = 2.0 * w.sum()
    if m2 <= 0:
        return 0.0
    k = np.bincount(u, weights=w, minlength=n) + np.bincount(v, weights=w, minlength=n)
    K = int(part.max()) + 1
    inside = part[u] == part[v]
    e_in = np.bincount(part[u][inside], weights=w[inside], minlength=K)
    d = np.bincount(part, weights=k, minlength=K)
    return float(((2.0 * e_in) / m2 - resolution * (d / m2) ** 2).sum())


def area_graph(panel, c):
    """The payments between two different wallets of area c over the whole panel, either way, as unique pairs
    in the area's own wallet numbering: the area's wallets, then the pairs and their value."""
    import numpy as np
    wc, N = panel["wclass"], panel["N"]
    src = np.concatenate([e[0] for e in panel["edges"]])
    dst = np.concatenate([e[1] for e in panel["edges"]])
    val = np.concatenate([e[2] for e in panel["edges"]])
    idx = np.flatnonzero(wc == c)
    local = np.full(N, -1, dtype=np.int64)
    local[idx] = np.arange(idx.size)
    keep = (wc[src] == c) & (wc[dst] == c) & (src != dst) & (val > 0)
    a, b = local[src[keep]], local[dst[keep]]
    n = idx.size
    keys, inv = np.unique(np.minimum(a, b) * n + np.maximum(a, b), return_inverse=True)
    w = np.bincount(inv.ravel(), weights=val[keep], minlength=keys.size)
    return idx, keys // n, keys % n, w


def connected_parts(n, u, v):
    """The connected parts of an undirected graph on n nodes, numbered by their lowest node."""
    import numpy as np
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a_, b_ in zip(u.tolist(), v.tolist()):
        ra, rb = find(a_), find(b_)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    return renumber(np.array([find(x) for x in range(n)], dtype=np.int64))


def paid_anything(panel):
    """The wallets that paid anything over the whole panel, to a wallet in circulation or out of it."""
    import numpy as np
    paid = np.zeros(panel["N"])
    for e_src, _, e_val in panel["edges"]:
        paid += np.bincount(e_src, weights=e_val, minlength=panel["N"])
    return (paid + panel["sink"].sum(axis=0)) > 0


def paid_a_wallet(panel):
    """The wallets that paid any wallet in circulation over the whole panel."""
    import numpy as np
    paid = np.zeros(panel["N"])
    for e_src, _, e_val in panel["edges"]:
        paid += np.bincount(e_src, weights=e_val, minlength=panel["N"])
    return paid > 0


def circle_partition(panel, level, seed=0, cache_dir=None, idle="one class"):
    """Classes of the payments inside each area: level "components" gives the connected parts, a number gives
    the Louvain classes at that resolution. The wallets that made or received no payment inside their area are
    one class of that area (idle="one class"), each a class of its own (idle="singletons"), or two classes of that
    area, the ones that paid anything to another area or out of circulation and the ones that paid nothing (idle="spent or not"),
    or the ones that paid a wallet in circulation (so in another area) and the ones that paid none (idle="paid a wallet or not").
    Louvain classes are cached per area on the graph, the resolution, the seed and the code."""
    import numpy as np
    wc, N = panel["wclass"], panel["N"]
    part = np.full(N, -1, dtype=np.int64)
    base = 0
    src_key = hashlib.sha256((inspect.getsource(louvain) + inspect.getsource(_adjacency)).encode("utf-8")).hexdigest()
    spent = paid_anything(panel) if idle == "spent or not" else paid_a_wallet(panel) if idle == "paid a wallet or not" else None
    for c in np.unique(wc):
        idx, u, v, w = area_graph(panel, c)
        n = idx.size
        if level == "components":
            memb = connected_parts(n, u, v)
        else:
            memb, path = None, None
            if cache_dir is not None:
                h = hashlib.sha256()
                h.update(json.dumps([src_key, float(level), int(seed), int(n)]).encode("utf-8"))
                for arr in (u.astype("<i8"), v.astype("<i8"), w.astype("<f8")):
                    h.update(np.ascontiguousarray(arr).tobytes())
                path = Path(cache_dir) / "circles" / f"{h.hexdigest()[:32]}.json"
                if path.exists():
                    memb = np.array(json.loads(path.read_text(encoding="utf-8")), dtype=np.int64)
            if memb is None:
                memb = louvain(n, u, v, w, float(level), seed)
                if path is not None:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    tmp = path.with_name(path.name + ".partial.expired")
                    tmp.write_text(json.dumps(memb.tolist()) + "\n", encoding="utf-8", newline="\n")
                    os.replace(tmp, path)
        paying = np.zeros(n, dtype=bool)
        paying[u] = True
        paying[v] = True
        labels = np.full(n, -1, dtype=np.int64)
        if paying.any():
            labels[paying] = renumber(memb[paying])
        n_circ = int(labels.max()) + 1 if paying.any() else 0
        n_idle = int((~paying).sum())
        if idle == "one class":
            labels[~paying] = n_circ
            base_add = n_circ + int(n_idle > 0)
        elif idle == "singletons":
            labels[~paying] = n_circ + np.arange(n_idle)
            base_add = n_circ + n_idle
        elif idle in ("spent or not", "paid a wallet or not"):
            groups = [g for g in (~paying & spent[idx], ~paying & ~spent[idx]) if g.any()]
            for j, g in enumerate(groups):
                labels[g] = n_circ + j
            base_add = n_circ + len(groups)
        else:
            raise ValueError(idle)
        part[idx] = base + labels
        base += base_add
    return part


def split_within(part, key, s):
    """Each class of `part` cut into min(s, its size) runs of near-equal size in order of key."""
    return split_in_order(part, {int(c): s for c in set(part.tolist())}, key)


# ---------------------------------------------------------------------------
# The chain on classes: the state wallet by wallet, or on class balances where the two are equal
# ---------------------------------------------------------------------------

def partition_operator(panel, k, part, K, speed):
    """One day's step for flow window k. speed "class": every wallet leaves at its class's rate, and
    pays on or out of circulation in its class's proportion; speed "own": at its own. Money paid on
    lands across classes by the paying class's mix of destination classes, and within a class by
    what each wallet of that class receives."""
    import numpy as np
    N = panel["N"]
    lo, hi = panel["qdays"][k]
    days = hi - lo
    if days <= 0:
        return None
    src, dst, val = panel["edges"][k]
    avg = panel["balday"][k] / days
    out = np.bincount(src, weights=val, minlength=N) / days
    snk = panel["sink"][k] / days
    rec = np.bincount(dst, weights=val, minlength=N) / days
    if speed == "own":
        hold, paid, sunk = avg, out, snk
    elif speed == "class":
        hold = np.bincount(part, weights=avg, minlength=K)
        paid = np.bincount(part, weights=out, minlength=K)
        sunk = np.bincount(part, weights=snk, minlength=K)
    else:
        raise ValueError(speed)
    tot = paid + sunk
    with np.errstate(divide="ignore", invalid="ignore"):
        rate = np.where(hold > 0, tot / np.where(hold > 0, hold, 1.0), np.where(tot > 0, np.inf, 0.0))
        share = np.where(tot > 0, paid / np.where(tot > 0, tot, 1.0), 0.0)
    leave = np.where(np.isinf(rate), 1.0, np.minimum(rate, 1.0))
    op = {"part": part, "K": K}
    if speed == "class":
        op["stay_k"], op["circ_k"] = 1.0 - leave, leave * share
        leave, share = leave[part], share[part]
    op["stay"], op["circ"] = 1.0 - leave, leave * share
    pair = part[src] * K + part[dst]
    keys, inv = np.unique(pair, return_inverse=True)
    flow = np.bincount(inv.ravel(), weights=val, minlength=keys.size)
    ea, eb = keys // K, keys % K
    out_k = np.bincount(ea, weights=flow, minlength=K)
    keep = flow > 0
    op["ea"], op["eb"] = ea[keep], eb[keep]
    op["d"] = flow[keep] / out_k[op["ea"]]
    rec_k = np.bincount(part, weights=rec, minlength=K)
    with np.errstate(divide="ignore", invalid="ignore"):
        op["rho"] = np.where(rec_k[part] > 0, rec / np.where(rec_k[part] > 0, rec_k[part], 1.0), 0.0)
    return op


def partition_step(V, op):
    """V: rows of wallet balances. One day: each wallet keeps `stay` of its balance; `circ` of it is
    paid on, summed into its class, spread over destination classes, and spread within each by receipts."""
    import numpy as np
    n, N = V.shape
    part, K = op["part"], op["K"]
    new = V * op["stay"][None, :]
    if op["d"].size:
        flat = (np.arange(n)[:, None] * K + part[None, :]).ravel()
        paid = np.bincount(flat, weights=(V * op["circ"][None, :]).ravel(), minlength=n * K).reshape(n, K)
        flat = (np.arange(n)[:, None] * K + op["eb"][None, :]).ravel()
        land = np.bincount(flat, weights=(paid[:, op["ea"]] * op["d"][None, :]).ravel(), minlength=n * K).reshape(n, K)
        new += land[:, part] * op["rho"][None, :]
    return new


def cohort_starts(res, pw, min_cohort):
    """For each entry month with a cohort: the entry areas, the new money by wallet, the chain's end date."""
    import numpy as np
    C, M, wclass = len(res["classes"]), len(res["months"]), pw["wclass"]
    out = []
    for m, key in enumerate(res["months"]):
        rows = [c for c in range(C) if res["disbursed"][c * M + m] >= min_cohort]
        if not rows or m not in pw["new_money"]:
            continue
        js, ws = pw["new_money"][m]
        V0 = np.zeros((len(rows), pw["N"]))
        for r, c in enumerate(rows):
            mask = wclass[js] == c
            np.add.at(V0[r], js[mask], ws[mask])
            want = res["disbursed"][c * M + m]
            if abs(V0[r].sum() - want) > 1e-6 * max(1.0, want):
                raise AssertionError(f"new money by wallet does not add up to the cohort: {V0[r].sum():.6g} against {want:.6g}")
        out.append((rows, V0, S.month_end(key)))
    return out


def chain_rows_one(res, panel, part, K, speed, min_cohort=S.MIN_COHORT, start_at="mid", window="quarter", state="auto"):
    """For one partition and speed, and each entry area: the share of the cohorts' chain mass still in
    the entry area among the mass in circulation, pooled over cohorts as B114 pools them, at each age.
    state "auto": with the class's speed and classes inside areas the chain runs on class balances
    (class_chain_rows); otherwise, or with state "wallet", wallet by wallet."""
    import numpy as np
    classes, times = res["classes"], res["snap_times"]
    pw = S.panel_window(res, panel, window)
    C, wclass = len(classes), pw["wclass"]
    if part.shape != (pw["N"],) or (part.size and (part.min() < 0 or part.max() >= K)):
        raise ValueError("the partition does not number every wallet with a class below K")
    if state not in ("auto", "wallet"):
        raise ValueError(state)
    if state == "auto" and speed == "class" and refines(part, wclass):
        return class_chain_rows(res, panel, part, K, min_cohort, start_at, window, with_masses=True)
    qk = {q: k for k, q in enumerate(pw["quarters"])}
    acc = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    ops = {}
    for rows, V0, end in cohort_starts(res, pw, min_cohort):
        first = bisect.bisect_left(times, end)
        flat = (np.arange(len(rows))[:, None] * C + wclass[None, :]).ravel()
        V, day = V0.copy(), S.chain_start(end, start_at)
        ages_left = sorted(S.AGES)
        while ages_left and first + ages_left[0] < len(times):
            target = times[first + ages_left[0]]
            while day < target:
                k = qk.get(S.period_key(day, window))
                if k is None:
                    break
                if k not in ops:
                    ops[k] = partition_operator(pw, k, part, K, speed)
                if ops[k] is None:
                    break
                V = partition_step(V, ops[k])
                day += dt.timedelta(days=1)
            age = ages_left.pop(0)
            tot = np.bincount(flat, weights=V.ravel(), minlength=len(rows) * C).reshape(len(rows), C)
            for r, c in enumerate(rows):
                if tot[r].sum() > 0:
                    acc[classes[c]][age][0] += tot[r, c]
                    acc[classes[c]][age][1] += tot[r].sum()
    shares = {cl: {g: v[0] / v[1] for g, v in by.items() if v[1] > 0} for cl, by in acc.items()}
    masses = {cl: {g: v[1] for g, v in by.items()} for cl, by in acc.items()}
    return shares, masses


def class_step(op):
    """The class-speed day step of partition_operator as a K x K sparse matrix on class balances (one
    column per cohort): class a keeps stay_k[a] of its balance and pays circ_k[a] of it on, spread
    over destination classes by its payment mix d. What leaves circulation is in neither term."""
    from scipy import sparse
    K = op["K"]
    pay = sparse.coo_matrix((op["circ_k"][op["ea"]] * op["d"], (op["eb"], op["ea"])), shape=(K, K))
    return (pay + sparse.diags(op["stay_k"])).tocsr()


def class_chain_rows(res, panel, part, K, min_cohort=S.MIN_COHORT, start_at="mid", window="quarter", with_masses=False):
    """The class-speed chain run on K class balances instead of wallet balances, for classes that do not
    mix areas (so the entry area's share can be read off the classes). With the class's speed every
    wallet of a class keeps and pays on the same fractions, so the class balances follow a closed K x K
    step; it must equal chain_rows_one with state "wallet" summed into classes."""
    import numpy as np
    from scipy import sparse
    classes, times = res["classes"], res["snap_times"]
    pw = S.panel_window(res, panel, window)
    C, wclass = len(classes), pw["wclass"]
    if not refines(part, wclass):
        raise ValueError("the partition mixes areas")
    area_of = np.zeros(K, dtype=np.int64)
    area_of[part] = wclass
    to_area = sparse.csr_matrix((np.ones(K), (area_of, np.arange(K))), shape=(C, K))
    qk = {q: k for k, q in enumerate(pw["quarters"])}
    acc = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    steps = {}
    for rows, V0, end in cohort_starts(res, pw, min_cohort):
        n = len(rows)
        x = np.bincount((part[:, None] * n + np.arange(n)[None, :]).ravel(), weights=V0.T.ravel(),
                        minlength=K * n).reshape(K, n)
        first = bisect.bisect_left(times, end)
        day = S.chain_start(end, start_at)
        ages_left = sorted(S.AGES)
        while ages_left and first + ages_left[0] < len(times):
            target = times[first + ages_left[0]]
            while day < target:
                k = qk.get(S.period_key(day, window))
                if k is None:
                    break
                if k not in steps:
                    op = partition_operator(pw, k, part, K, "class")
                    steps[k] = None if op is None else class_step(op)
                if steps[k] is None:
                    break
                x = steps[k] @ x
                day += dt.timedelta(days=1)
            age = ages_left.pop(0)
            tot = to_area @ x
            for r, c in enumerate(rows):
                if tot[:, r].sum() > 0:
                    acc[classes[c]][age][0] += tot[c, r]
                    acc[classes[c]][age][1] += tot[:, r].sum()
    shares = {cl: {g: v[0] / v[1] for g, v in by.items() if v[1] > 0} for cl, by in acc.items()}
    if not with_masses:
        return shares
    return shares, {cl: {g: v[1] for g, v in by.items()} for cl, by in acc.items()}


def lump_gap(res, panel, part, K, cache_dir=None, archive_digest=None, log=None):
    """The chain on class balances against the class-speed chain kept wallet by wallet and summed into
    classes: (largest difference, same cells). The wallet side is forced, so the two are two paths."""
    on_wallets = chain_rows(res, panel, [("wallets", part, K, "class")], cache_dir=cache_dir, archive_digest=archive_digest,
                            log=log, state="wallet")["wallets"]
    return worst_gap(on_wallets, class_chain_rows(res, panel, part, K))


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def code_key() -> str:
    """The source of everything a chain result depends on in this file, and all of B114's."""
    h = hashlib.sha256()
    for fn in (partition_operator, partition_step, cohort_starts, chain_rows_one, class_step, class_chain_rows):
        h.update(inspect.getsource(fn).encode("utf-8"))
    h.update(Path(S.__file__).read_bytes())
    return h.hexdigest()


def cache_key(archive_digest, part, K, speed, min_cohort, start_at, window, state="auto") -> str:
    import numpy as np
    h = hashlib.sha256()
    h.update(json.dumps([archive_digest, code_key(), int(K), speed, float(min_cohort), start_at, window, state]).encode("utf-8"))
    h.update(np.ascontiguousarray(part, dtype="<i8").tobytes())
    return h.hexdigest()


_SHARED: dict = {}      # the tag pass and the panel, handed to forked workers without pickling


def _write_cache(path, shares, masses):
    """Write the file whole or not at all: a run cut off mid-write leaves a .partial.expired file, never a torn cache."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".partial.expired")
    tmp.write_text(json.dumps({"shares": shares, "masses": masses}, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _run_one(job):
    name, part, K, speed, min_cohort, start_at, window, state, path = job
    t0 = time.time()
    shares, masses = chain_rows_one(_SHARED["res"], _SHARED["panel"], part, K, speed, min_cohort, start_at, window, state)
    if path is not None:
        _write_cache(path, shares, masses)
    return name, shares, time.time() - t0


def chain_rows(res, panel, variants, cache_dir=None, archive_digest=None, min_cohort=S.MIN_COHORT,
               start_at="mid", window="quarter", log=None, jobs=1, state="auto"):
    """variants: [(name, part, K, speed)] -> {name: shares}. Cached when cache_dir and archive_digest are given;
    with jobs > 1 the variants not in the cache run in forked worker processes where the platform forks.
    state "wallet" keeps every variant wallet by wallet (the check the class-balance chain is read against)."""
    out, todo = {}, []
    for name, part, K, speed in variants:
        path = None
        if cache_dir is not None and archive_digest is not None:
            path = Path(cache_dir) / f"{cache_key(archive_digest, part, K, speed, min_cohort, start_at, window, state)[:32]}.json"
            if path.exists():
                raw = json.loads(path.read_text(encoding="utf-8"))
                out[name] = {cl: {int(g): v for g, v in by.items()} for cl, by in raw["shares"].items()}
                if log:
                    log(f"   {name} ({speed} speed): cached")
                continue
        todo.append((name, part, K, speed, min_cohort, start_at, window, state, path))
    _SHARED.update(res=res, panel=panel)
    try:
        if jobs > 1 and len(todo) > 1 and "fork" in multiprocessing.get_all_start_methods():
            with multiprocessing.get_context("fork").Pool(jobs) as pool:
                for name, shares, secs in pool.imap_unordered(_run_one, todo):
                    out[name] = shares
                    if log:
                        log(f"   {name}: {secs:.1f} s")
        else:
            for job in todo:
                name, shares, secs = _run_one(job)
                out[name] = shares
                if log:
                    log(f"   {name}: {secs:.1f} s")
    finally:
        _SHARED.clear()
    return {name: out[name] for name, *_ in variants}


# ---------------------------------------------------------------------------
# Reading the chains against the cohorts
# ---------------------------------------------------------------------------

def cells_of(rows):
    """B114's cells: (area, age) that at least CELL_MIN_COHORTS cohorts reach, areas only."""
    return [(name, g) for name, r in sorted(rows.items()) if name not in S.NOT_AREAS
            for g in S.AGES if r["cohorts_at"].get(g, 0) >= S.CELL_MIN_COHORTS]


def placement(rows, shares, cells):
    """How many cells the chain lands inside the cohorts' lowest-to-highest range, below it, above it."""
    out = {"inside": 0, "below": 0, "above": 0, "no object": 0}
    for name, g in cells:
        r, v = rows.get(name, {}), shares.get(name, {}).get(g)
        if v is None or g not in r.get("cohort_min", {}):
            out["no object"] += 1
            continue
        lo, hi = r["cohort_min"][g], r["cohort_max"][g]
        out["inside" if lo <= v <= hi else "below" if v < lo else "above"] += 1
    return out


def worst_gap(a_shares, b_shares):
    """The largest difference between two sets of shares, and whether they cover the same (area, age)."""
    keys_a = {(cl, g) for cl, by in a_shares.items() for g in by}
    keys_b = {(cl, g) for cl, by in b_shares.items() for g in by}
    common = keys_a & keys_b
    gap = max((abs(a_shares[cl][g] - b_shares[cl][g]) for cl, g in common), default=0.0)
    return gap, keys_a == keys_b


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------

def block0(a, res, rows, panel, digest, log=print, jobs=1):
    import numpy as np
    print("\n== 0. the two ends and the lumping: classes = areas must give B114's area chains, classes = single"
          "\n   wallets B114's wallet chain, and the chain on class balances the wallet chain summed into classes")
    wc, N, C = panel["wclass"].astype(np.int64), panel["N"], len(res["classes"])
    b114, _ = S.wallet_chain_rows(res, panel, variants=[v for v in S.WALLET_VARIANTS if v[0] in
                                  ("area speed, area payees", "own speed, area payees", "own speed, own payees")])
    ours = chain_rows(res, panel, [("areas, class speed", wc, C, "class"), ("areas, own speed", wc, C, "own"),
                                   ("single wallets, class speed", np.arange(N, dtype=np.int64), N, "class"),
                                   ("single wallets, own speed", np.arange(N, dtype=np.int64), N, "own")],
                      cache_dir=CACHE, archive_digest=digest, log=log, jobs=jobs)
    for mine, theirs in (("areas, class speed", "area speed, area payees"), ("areas, own speed", "own speed, area payees"),
                         ("single wallets, class speed", "own speed, own payees"), ("single wallets, own speed", "own speed, own payees")):
        gap, same = worst_gap(ours[mine], b114[theirs])
        print(f"   {mine:30s} against B114 '{theirs}': largest difference {gap:.1e}, same cells {same}")
    gap, same = worst_gap(ours["areas, class speed"], {cl: r["network"] for cl, r in rows.items()})
    print(f"   {'areas, class speed':30s} against B114's block-5 area chain: largest difference {gap:.1e}, same cells {same}")
    parts = first_partitions(a, res, panel)
    bt, k_bt = parts["area x business type"]
    t0 = time.time()
    gap, same = lump_gap(res, panel, bt, k_bt, cache_dir=CACHE, archive_digest=digest, log=log)
    print(f"   area x business type ({k_bt} classes), class speed: on class balances against wallet by wallet summed"
          f" ({time.time() - t0:.1f} s): largest difference {gap:.1e}, same cells {same}")


FAMILIES = (("area", "area"), ("area x business type", "area x business type"),
            ("random, business-type sizes", "random, business-type sizes, seed "), ("own-speed strata", "own-speed strata"),
            ("random, equal sizes", "random, equal sizes, seed "), ("received new money or not", "received new money or not"),
            ("single wallets", "single wallets"))


def family_members(parts, prefix):
    return [n for n in parts if n == prefix or (prefix.endswith("seed ") and n.startswith(prefix))]


def block1_data(a, res, rows, panel, digest, log=None, jobs=1):
    """The first partitions and their chains, with both speeds."""
    parts = first_partitions(a, res, panel)
    variants = [(f"{n} | {sp}", p, K, sp) for n, (p, K) in parts.items() for sp in SPEEDS]
    return {"parts": parts, "got": chain_rows(res, panel, variants, cache_dir=CACHE, archive_digest=digest, log=log, jobs=jobs)}


def block1(a, res, rows, panel, digest, log=print, jobs=1):
    import numpy as np
    print("\n== 1. the first partitions. Each row is the chain with that partition's classes, with the class's spending"
          "\n   speed (class) or each wallet's own (own). Look at: where each row sits against the cohorts' low and high,"
          "\n   and whether the business types beat random classes of the same sizes")
    data = block1_data(a, res, rows, panel, digest, log=log, jobs=jobs)
    parts, got = data["parts"], data["got"]
    wc = panel["wclass"]
    names = res["classes"]
    bt, k_bt = parts["area x business type"]
    sizes = class_sizes_by_area(bt, wc)
    print(f"   {panel['N']:,d} wallets in circulation; classes by area (area x business type): "
          + ", ".join(f"{names[c]} {len(v)}" for c, v in sorted(sizes.items())))
    cells = cells_of(rows)
    print(f"\n   {len(cells)} cells (area, age) that at least {S.CELL_MIN_COHORTS} cohorts reach; where each chain lands against"
          " the cohorts' range")
    print(f"   {'partition':34s} {'classes':>8s} {'speed':>6s} {'inside':>7s} {'below':>6s} {'above':>6s}")
    for label, prefix in FAMILIES:
        members = family_members(parts, prefix)
        for sp in SPEEDS:
            pl = [placement(rows, got[f"{n} | {sp}"], cells) for n in members]
            ks = sorted({parts[n][1] for n in members})
            kk = f"{ks[0]:,d}" if len(ks) == 1 else f"{ks[0]:,d}-{ks[-1]:,d}"
            if len(pl) == 1:
                q = pl[0]
                print(f"   {label:34s} {kk:>8s} {sp:>6s} {q['inside']:>7d} {q['below']:>6d} {q['above']:>6d}")
            else:
                rng_ = {x: (min(p[x] for p in pl), max(p[x] for p in pl)) for x in ("inside", "below", "above")}
                print(f"   {label + f' ({len(pl)} seeds)':34s} {kk:>8s} {sp:>6s} "
                      + " ".join(f"{f'{lo}-{hi}' if lo != hi else str(lo):>{w}s}" for (lo, hi), w in
                                 ((rng_['inside'], 7), (rng_['below'], 6), (rng_['above'], 6))))
    shown = [name for name, r in sorted(rows.items(), key=lambda kv: -kv[1]["disbursed"])
             if r["cohorts"] >= PRINT_MIN_COHORTS and name not in S.NOT_AREAS]
    for age in (13, 52):
        print(f"\n   the part of the gap between the area chain and the single-wallet chain that each partition closes, at {age} weeks"
              "\n   (chain minus area chain, over single-wallet chain minus area chain, same speed; random rows: mean over seeds, lowest, highest)")
        print(f"   {'partition':34s} {'speed':>6s}" + "".join(f"{nm[:16]:>18s}" for nm in shown))
        for label, prefix in FAMILIES[1:-1]:
            members = family_members(parts, prefix)
            for sp in SPEEDS:
                cols = []
                for nm in shown:
                    base = got[f"area | {sp}"].get(nm, {}).get(age)
                    top = got[f"single wallets | {sp}"].get(nm, {}).get(age)
                    vals = [got[f"{n} | {sp}"].get(nm, {}).get(age) for n in members]
                    if base is None or top is None or top == base or any(v is None for v in vals):
                        cols.append(f"{'.':>18s}")
                        continue
                    fr = [(v - base) / (top - base) for v in vals]
                    cols.append(f"{100 * fr[0]:>17.0f}%" if len(fr) == 1 else
                                f"{f'{100 * float(np.mean(fr)):.0f}% [{100 * min(fr):.0f},{100 * max(fr):.0f}]':>18s}")
                print(f"   {label:34s} {sp:>6s}" + "".join(cols))
    for name in shown:
        r = rows[name]
        print(f"\n   {name}: {r['cohorts']} cohorts; share of the new money in circulation still in the area, %")
        print(f"   {'age (weeks)':44s}" + "".join(f"{x:>7d}" for x in S.AGES))
        for lab, src in (("observed", r["observed"]), ("cohort low", r["cohort_min"]), ("cohort high", r["cohort_max"])):
            print(f"   {lab:44s}" + "".join(f"{100 * src[x]:>7.1f}" if x in src else f"{'.':>7s}" for x in S.AGES))
        for label, prefix in FAMILIES:
            members = family_members(parts, prefix)
            for sp in SPEEDS:
                vals = {x: [got[f"{n} | {sp}"].get(name, {}).get(x) for n in members] for x in S.AGES}
                mean = {x: float(np.mean(v)) for x, v in vals.items() if v and all(y is not None for y in v)}
                tag = f"{label}, {sp}" + (" (mean)" if len(members) > 1 else "")
                print(f"   {tag:44s}" + "".join(f"{100 * mean[x]:>7.1f}" if x in mean else f"{'.':>7s}" for x in S.AGES))
                if len(members) > 1:
                    spread = {x: 100 * (max(v) - min(v)) for x, v in vals.items() if v and all(y is not None for y in v)}
                    print(f"   {'   spread over seeds (points)':44s}" + "".join(f"{spread[x]:>7.1f}" if x in spread else f"{'.':>7s}" for x in S.AGES))


LEVELS = ("components", 1.0, 10.0, 30.0, 100.0, 300.0)   # the circles: connected parts, then Louvain resolutions
IDLE_LEVELS = (10.0, 300.0)                                # where the class of wallets with no payment inside the area is split
IDLE_RULES = ("one class", "spent or not", "paid a wallet or not", "singletons")
SWEEP_SEEDS = (0, 1, 2)
SWEEP_FAMILIES = (("C", "circles", "circles"),
                  ("Cr", "random, circle sizes", "random, circle sizes, seed "),
                  ("S", "own-speed strata, circle counts", "own-speed strata, circle counts"),
                  ("Er", "random, equal sizes, circle counts", "random, equal sizes, circle counts, seed "),
                  ("CS", "own-speed halves within circles", "own-speed halves within circles"),
                  ("CSr", "random, sizes of the halves", "random, sizes of the halves, seed "),
                  ("S2", "own-speed strata, counts of the halves", "own-speed strata, counts of the halves"))


def level_label(level):
    return "connected parts" if level == "components" else f"resolution {level:g}"


def sweep_partitions(panel, level, cache_dir=None):
    """At one level of the circles: the circles, and the partitions each is read against. Every partition
    keeps the class count per area of the one it is matched to; the random ones keep its class sizes too."""
    import numpy as np
    wc, N = panel["wclass"], panel["N"]
    speed = own_speed(panel)
    circles = circle_partition(panel, level, cache_dir=cache_dir)
    out = {"circles": circles}
    for s in SWEEP_SEEDS:
        out[f"random, circle sizes, seed {s}"] = random_like(circles, wc, s)
    counts = {c: len(v) for c, v in class_sizes_by_area(circles, wc).items()}
    out["own-speed strata, circle counts"] = split_in_order(wc, counts, speed)
    for s in SWEEP_SEEDS:
        key = np.random.default_rng(2000 + s).permutation(N).astype(float)
        out[f"random, equal sizes, circle counts, seed {s}"] = split_in_order(wc, counts, key)
    halves = split_within(circles, speed, 2)
    out["own-speed halves within circles"] = halves
    for s in SWEEP_SEEDS:
        out[f"random, sizes of the halves, seed {s}"] = random_like(halves, wc, s)
    counts2 = {c: len(v) for c, v in class_sizes_by_area(halves, wc).items()}
    out["own-speed strata, counts of the halves"] = split_in_order(wc, counts2, speed)
    return {name: (part, int(part.max()) + 1) for name, part in out.items()}


def block2_data(a, res, rows, panel, digest, log=None, jobs=1):
    """The circles at every level, the partitions matched to them, the splits of the idle class, their chains,
    and what the idle wallets paid out, by area."""
    import numpy as np
    wc, N, names = panel["wclass"].astype(np.int64), panel["N"], res["classes"]
    variants = [(f"{n} | {sp}", part, K, sp) for n, part, K in (("area", wc, len(names)), ("single wallets", np.arange(N, dtype=np.int64), N))
                for sp in SPEEDS]
    parts_by_level = {}
    for level in LEVELS:
        parts = sweep_partitions(panel, level, cache_dir=CACHE)
        parts_by_level[level] = parts
        variants += [(f"{level_label(level)} | {n} | {sp}", part, K, sp) for n, (part, K) in parts.items() for sp in SPEEDS]
    top = LEVELS[-1]
    idle_single = circle_partition(panel, top, cache_dir=CACHE, idle="singletons")
    idle_name = f"{level_label(top)} | circles, idle wallets single"
    variants += [(f"{idle_name} | {sp}", idle_single, int(idle_single.max()) + 1, sp) for sp in SPEEDS]
    idle_parts = {}
    for level in IDLE_LEVELS:
        for rule in IDLE_RULES:
            part_i = parts_by_level[level]["circles"][0] if rule == "one class" else circle_partition(panel, level, cache_dir=CACHE, idle=rule)
            idle_parts[(level, rule)] = (part_i, int(part_i.max()) + 1)
            if rule != "one class":
                variants += [(f"{level_label(level)} | circles, idle {rule} | {sp}", part_i, int(part_i.max()) + 1, sp) for sp in SPEEDS]
    got = chain_rows(res, panel, variants, cache_dir=CACHE, archive_digest=digest, log=log, jobs=jobs)
    spent, to_wallet = paid_anything(panel), paid_a_wallet(panel)
    circ = circulation_order(a, res)
    idle_of = np.zeros(N, dtype=bool)
    for c in np.unique(wc):
        idx, u, v, _ = area_graph(panel, c)
        paying = np.zeros(idx.size, dtype=bool)
        paying[u] = True
        paying[v] = True
        idle_of[idx[~paying]] = True
    pos = {w: i for i, w in enumerate(circ)}
    out_kind = defaultdict(lambda: defaultdict(float))
    for t_, sub, s_, g_, w_, _ in a.txns:
        i_ = pos.get(s_)
        if i_ is None or not idle_of[i_]:
            continue
        kind = "to a wallet" if g_ in pos else ("reclaimed" if sub == "RECLAMATION" else "to the system")
        out_kind[int(wc[i_])][kind] += w_
    new_in = np.zeros(N)
    for js, ws in panel["new_money"].values():
        np.add.at(new_in, js, ws)
    idle_breakdown = {}
    for c in np.unique(wc):
        ix = np.flatnonzero((wc == c) & idle_of)
        k_ = out_kind[int(c)]
        tot_new = new_in[wc == c].sum()
        idle_breakdown[names[c]] = {"wallets": int((wc == c).sum()), "idle": int(ix.size),
                                    "paid a wallet": int(to_wallet[ix].sum()),
                                    "paid only out of circulation": int((spent[ix] & ~to_wallet[ix]).sum()),
                                    "paid nothing": int((~spent[ix]).sum()), "value to wallets": k_["to a wallet"],
                                    "value reclaimed": k_["reclaimed"], "value to the system": k_["to the system"],
                                    "share of the area new money": float(new_in[ix].sum() / tot_new) if tot_new > 0 else 0.0}
    return {"parts_by_level": parts_by_level, "idle_single": idle_single, "idle_name": idle_name, "idle_parts": idle_parts,
            "got": got, "idle_breakdown": idle_breakdown}


def block2(a, res, rows, panel, digest, log=print, jobs=1):
    import numpy as np
    print("\n== 2. payment circles. Circles are the connected parts of the payments inside each area, then Louvain classes at"
          "\n   rising resolution; wallets with no payment inside their area are one class of it. Each level is read against"
          "\n   partitions with the same class count per area: random classes of the same sizes, own-speed strata, random"
          "\n   classes of equal size; and each circle cut into its slower and faster half, against random classes and strata"
          "\n   matched to that. Look at: at which level the circles close the gap, and whether they beat what is matched to them")
    data = block2_data(a, res, rows, panel, digest, log=log, jobs=jobs)
    wc, N, names = panel["wclass"].astype(np.int64), panel["N"], res["classes"]
    parts_by_level, idle_single, idle_name = data["parts_by_level"], data["idle_single"], data["idle_name"]
    idle_parts, got, top = data["idle_parts"], data["got"], LEVELS[-1]
    cells = cells_of(rows)
    shown = [name for name, r in sorted(rows.items(), key=lambda kv: -kv[1]["disbursed"])
             if r["cohorts"] >= PRINT_MIN_COHORTS and name not in S.NOT_AREAS]
    idle_counts = []
    for c in np.unique(wc):
        idx, u, v, _ = area_graph(panel, c)
        paying = np.zeros(idx.size, dtype=bool)
        paying[u] = True
        paying[v] = True
        idle_counts.append(f"{names[c]} {int((~paying).sum()):,d} of {idx.size:,d}")
    print("   wallets with no payment inside their area: " + "; ".join(idle_counts))
    print("\n   classes at each level (circles / halves within circles):")
    for level in LEVELS:
        parts = parts_by_level[level]
        by_area = "; ".join(f"{names[c]} {len(set(parts['circles'][0][wc == c].tolist()))}" for c in np.unique(wc))
        print(f"   {level_label(level):18s} {parts['circles'][1]:>6,d} / {parts['own-speed halves within circles'][1]:>6,d}   {by_area}")
    print(f"   {'':18s} idle wallets single at {level_label(top)}: {int(idle_single.max()) + 1:,d} classes")

    def members(parts, prefix):
        return [n for n in parts if n == prefix or (prefix.endswith("seed ") and n.startswith(prefix))]

    print(f"\n   {len(cells)} cells; where each chain lands against the cohorts' range (random rows: lowest-highest over"
          f" {len(SWEEP_SEEDS)} seeds). Area: " + ", ".join(f"{sp} {placement(rows, got[f'area | {sp}'], cells)['inside']}" for sp in SPEEDS)
          + "; single wallets: " + ", ".join(f"{sp} {placement(rows, got[f'single wallets | {sp}'], cells)['inside']}" for sp in SPEEDS))
    print(f"   {'level':18s} {'partition':40s} {'classes':>8s} {'speed':>6s} {'inside':>7s} {'below':>6s} {'above':>6s}")
    for level in LEVELS:
        parts = parts_by_level[level]
        for _, label, prefix in SWEEP_FAMILIES:
            ms = members(parts, prefix)
            for sp in SPEEDS:
                pl = [placement(rows, got[f"{level_label(level)} | {n} | {sp}"], cells) for n in ms]
                ks = sorted({parts[n][1] for n in ms})
                kk = f"{ks[0]:,d}" if len(ks) == 1 else f"{ks[0]:,d}-{ks[-1]:,d}"
                col = {x: (min(q[x] for q in pl), max(q[x] for q in pl)) for x in ("inside", "below", "above")}
                cells_txt = [f"{lo}-{hi}" if lo != hi else str(lo) for lo, hi in (col["inside"], col["below"], col["above"])]
                print(f"   {level_label(level):18s} {label:40s} {kk:>8s} {sp:>6s} {cells_txt[0]:>7s} {cells_txt[1]:>6s} {cells_txt[2]:>6s}")
        if level == top:
            for sp in SPEEDS:
                q = placement(rows, got[f"{idle_name} | {sp}"], cells)
                print(f"   {level_label(level):18s} {'circles, idle wallets single':40s} {int(idle_single.max()) + 1:>8,d} {sp:>6s}"
                      f" {q['inside']:>7d} {q['below']:>6d} {q['above']:>6d}")
    print("\n   the part of the gap between the area chain and the single-wallet chain each partition closes (random: mean over seeds)."
          "\n   columns: " + "; ".join(f"{code} {label}" for code, label, _ in SWEEP_FAMILIES) + "; I circles with idle wallets single")
    for age in (13, 52):
        for sp in SPEEDS:
            for nm in shown:
                base = got[f"area | {sp}"].get(nm, {}).get(age)
                topv = got[f"single wallets | {sp}"].get(nm, {}).get(age)
                if base is None or topv is None or topv == base:
                    continue
                print(f"\n   {nm}, {age} weeks, {sp} speed")
                print(f"   {'level':18s}" + "".join(f"{code:>8s}" for code, _, _ in SWEEP_FAMILIES) + f"{'I':>8s}")
                for level in LEVELS:
                    parts = parts_by_level[level]
                    cols = []
                    for _, _, prefix in SWEEP_FAMILIES:
                        vals = [got[f"{level_label(level)} | {n} | {sp}"].get(nm, {}).get(age) for n in members(parts, prefix)]
                        cols.append(f"{'.':>8s}" if any(v is None for v in vals) else
                                    f"{100 * (float(np.mean(vals)) - base) / (topv - base):>7.0f}%")
                    extra = ""
                    if level == top:
                        v = got[f"{idle_name} | {sp}"].get(nm, {}).get(age)
                        extra = f"{'.':>8s}" if v is None else f"{100 * (v - base) / (topv - base):>7.0f}%"
                    print(f"   {level_label(level):18s}" + "".join(cols) + extra)
    print("\n   the class of wallets with no payment inside their area. By area: idle wallets that paid a wallet (in another area) /"
          "\n   paid only out of circulation / paid nothing; the value they paid to wallets, reclaimed from them, paid to the system;"
          "\n   and the share of the area's new money that was disbursed to them")
    for nm_, b_ in data["idle_breakdown"].items():
        print(f"   {nm_:22s} {b_['paid a wallet']:6,d} / {b_['paid only out of circulation']:6,d} / {b_['paid nothing']:5,d}"
              f"   to wallets {b_['value to wallets']:12,.0f}  reclaimed {b_['value reclaimed']:12,.0f}  to the system {b_['value to the system']:12,.0f}"
              f"   new money {100 * b_['share of the area new money']:5.1f}%")
    print("\n   kept as one class per area, split two ways, or each idle wallet alone")
    print(f"   {'level':16s} {'idle wallets':14s} {'classes':>8s} {'speed':>6s} {'inside':>7s}   gap closed at 13 weeks, then at 52 weeks: "
          + ", ".join(nm for nm in shown))
    for level in IDLE_LEVELS:
        for rule in IDLE_RULES:
            part_i, K_i = idle_parts[(level, rule)]
            for sp in SPEEDS:
                key = f"{level_label(level)} | circles | {sp}" if rule == "one class" else f"{level_label(level)} | circles, idle {rule} | {sp}"
                q = placement(rows, got[key], cells)
                cols = []
                for age in (13, 52):
                    for nm in shown:
                        base = got[f"area | {sp}"].get(nm, {}).get(age)
                        topv = got[f"single wallets | {sp}"].get(nm, {}).get(age)
                        v = got[key].get(nm, {}).get(age)
                        cols.append(f"{'.':>6s}" if base is None or topv is None or v is None or topv == base
                                    else f"{100 * (v - base) / (topv - base):>5.0f}%")
                print(f"   {level_label(level):16s} {rule:14s} {K_i:>8,d} {sp:>6s} {q['inside']:>7d}  " + "".join(cols[:len(shown)])
                      + "  |" + "".join(cols[len(shown):]))


BLOCKS = (block0, block1, block2)


# ---------------------------------------------------------------------------
# Criteria and the record
# ---------------------------------------------------------------------------

CRITERIA_LEVEL = 10.0      # the circles B117-2 and B117-3 read: the first level at which block 2's circles land in as many cells as single wallets
CRITERIA_SEEDS = (0, 1, 2)  # Louvain seeds for those circles; each is read against random classes with its own class sizes and the same seed
ENDS_SETTINGS = ({"min_cohort": 10_000.0, "start_at": "mid", "window": "quarter"},
                 {"min_cohort": 5_000.0, "start_at": "start", "window": "half"},
                 {"min_cohort": 20_000.0, "start_at": "end", "window": "half"})   # every value of every knob at least once
ENDS_TOLERANCE = 1e-8      # B114's record prints shares to nine significant figures
LUMP_TOLERANCE = 1e-12     # the two ways of running one chain differ only by rounding over a year of daily steps
B114_RECORD = ROOT / "results" / "b114_sarafu.json"

RIVAL_PREMISE = ("inside one area, the wallets of one business type are interchangeable: each spends at the speed of its area and"
                 " business type taken together, and what it pays lands across the area-and-business-type cells in that cell's"
                 " mix of destinations")
RIVAL_ENTAILMENT = ("the chain on area x business type cells, each at its own quarterly speed and its own mix of destination cells,"
                    " with what lands in a cell spread over its wallets by what each receives, gives the entry area's share of new"
                    " money week by week; that share is the rival's prediction in every cell")
RIVAL_MAPPING = {
    "the area x business type chain outside the cohort range at every setting": "the rival misses: counts toward PASS",
    "that chain inside at every setting, the circle chain outside at every setting and seed": "grid C: counts toward FAIL",
    "both inside at every setting and seed": "grid A: no bearing on the rival",
    "that chain inside at every setting, the circle chain moving with a knob or a seed": "not read",
    "that chain moving with a knob, or no object": "not read",
    "verdict": "PASS when the counted cells are all misses, FAIL when they are all C, no verdict when both occur, when none is"
               " counted, or when no cell can be placed in the grid",
    "chains": "the rival's: area x business type cells at each cell's speed; ours: circles of the payments inside each area"
              " (Louvain at resolution 10, seeds 0 to 2), wallets with no payment inside their area one class of it, at each"
              " class's speed",
    "grid letter": "placed only when both chains are steady over the knobs and seeds: B ours inside and the rival's outside,"
                   " A both inside, C the rival's inside and ours outside, both_unmet both outside"}
OWN_MAPPING = {"nearer circles": "the whole cohort range on the circle chain's side of the midpoint between it and the chain on random"
                                 " classes with the circles' sizes: counts toward PASS",
               "nearer random": "the whole cohort range on the random chain's side of that midpoint: counts toward FAIL",
               "straddle": "the range crosses the midpoint: not read",
               "moves with a knob": "the state changes with a knob or a seed: not read", "no object": "not read",
               "verdict": "PASS when the counted cells are all nearer circles, FAIL when all nearer random, otherwise no verdict"}


def business_type_partition(a, res, panel):
    wclass = panel["wclass"]
    bt, k_bt, _ = from_keys([(int(wclass[i]), a.users[w]["business_type"].lower()) for i, w in enumerate(circulation_order(a, res))])
    return bt, k_bt


def criteria_partitions(a, res, panel):
    """The rival's cells, and for each seed the circles at CRITERIA_LEVEL and random classes with their sizes."""
    out = {"area x business type": business_type_partition(a, res, panel)}
    for s in CRITERIA_SEEDS:
        circ = circle_partition(panel, CRITERIA_LEVEL, seed=s, cache_dir=CACHE)
        rnd = random_like(circ, panel["wclass"], s)
        out[f"circles, seed {s}"] = (circ, int(circ.max()) + 1)
        out[f"random, circle sizes, seed {s}"] = (rnd, int(rnd.max()) + 1)
    return out


def grid_letter(lo, hi, ours, rival):
    return {(True, False): "B", (True, True): "A", (False, True): "C", (False, False): "both_unmet"}[(lo <= ours <= hi, lo <= rival <= hi)]


def side_cell(lo, hi, circles, random_):
    """Which chain the whole cohort range sits nearer: on which side of the midpoint between the two chains it lies."""
    mid = (circles + random_) / 2
    if circles > random_:
        return "nearer circles" if lo > mid else "nearer random" if hi < mid else "straddle"
    if circles < random_:
        return "nearer circles" if hi < mid else "nearer random" if lo > mid else "straddle"
    return "straddle"


def criteria_cells(res, panel, parts, digest, log=None, jobs=1):
    """B114's cells, each read at every setting of the three knobs and every seed. A state is read only when it is the
    same at every setting and seed; the rival's chain has no seed, so its state is the same across seeds by construction."""
    base = S.cohort_rows(res, **S.DEFAULT_SETTING)
    cells = cells_of(base)
    out = {f"{name} | {g} weeks": {"area": name, "age": g, "settings": []} for name, g in cells}
    bt, k_bt = parts["area x business type"]
    for setting in S.settings_grid():
        rows = base if setting == S.DEFAULT_SETTING else S.cohort_rows(res, **setting)
        variants = [("rival", bt, k_bt, "class")]
        for s in CRITERIA_SEEDS:
            for nm in (f"circles, seed {s}", f"random, circle sizes, seed {s}"):
                variants.append((nm, parts[nm][0], parts[nm][1], "class"))
        got = chain_rows(res, panel, variants, cache_dir=CACHE, archive_digest=digest, log=log, jobs=jobs,
                         min_cohort=setting["min_cohort"], start_at=setting["start_at"], window=setting["window"])
        for name, g in cells:
            r = rows.get(name, {})
            rec = out[f"{name} | {g} weeks"]
            rv = got["rival"].get(name, {}).get(g)
            for s in CRITERIA_SEEDS:
                cv = got[f"circles, seed {s}"].get(name, {}).get(g)
                qv = got[f"random, circle sizes, seed {s}"].get(name, {}).get(g)
                if not r or g not in r.get("cohort_min", {}) or rv is None or cv is None or qv is None:
                    rec["settings"].append({**setting, "seed": s, "rival_in_range": "no object", "circles_in_range": "no object",
                                            "grid": "no object", "side": "no object"})
                    continue
                lo, hi = r["cohort_min"][g], r["cohort_max"][g]
                rec["settings"].append({**setting, "seed": s, "low": lo, "high": hi, "rival_chain": rv, "circle_chain": cv,
                                        "random_chain": qv, "rival_in_range": "inside" if lo <= rv <= hi else "outside",
                                        "circles_in_range": "inside" if lo <= cv <= hi else "outside",
                                        "grid": grid_letter(lo, hi, cv, rv), "side": side_cell(lo, hi, cv, qv)})
    for rec in out.values():
        for which in ("rival_in_range", "circles_in_range", "grid", "side"):
            rec[which] = S.settle(x[which] for x in rec["settings"])
    return out


def rival_reading(cell):
    """What one cell says about the rival: "miss", "C", "A", or not read."""
    rv, cv = cell["rival_in_range"], cell["circles_in_range"]
    if rv == "outside":
        return "miss"
    if rv == "inside" and cv == "outside":
        return "C"
    if rv == "inside" and cv == "inside":
        return "A"
    return "not read"


def criterion_rival(cells):
    readings = [rival_reading(c) for c in cells.values()]
    letters = [c["grid"] for c in cells.values()]
    split = {g: letters.count(g) for g in ("A", "B", "C", "both_unmet") if letters.count(g)}
    counted = [x for x in readings if x in ("miss", "C")]
    if not split:
        passed = None
    elif counted and "C" not in counted:
        passed = True
    elif counted and all(x == "C" for x in counted):
        passed = False
    else:
        passed = None
    grid = "unread" if not split else next(iter(split)) if len(split) == 1 else "mixed"
    judged = readings.count("miss") + readings.count("C") + readings.count("A")
    holds = readings.count("C") + readings.count("A")
    rec = {"name": "B117-2", "kind": "rival", "passed": passed, "grid": grid, "rival_shape": "point",
           "rival_premise": RIVAL_PREMISE, "rival_entailment": RIVAL_ENTAILMENT,
           "rival_holds_share": None if not judged else round(holds / judged, 6),
           "statement": "the rival's trajectory, the chain on area x business type cells, misses the range of the observed"
                        " entry-area share across monthly cohorts, area by area and age by age, at every setting of the station's"
                        " knobs; ours is the chain on the circles of payments inside each area",
           "detail": f"{len(readings)} cells; the rival misses in {readings.count('miss')}, holds with ours outside (C) in"
                     f" {readings.count('C')}, holds with ours inside (A) in {readings.count('A')}, not read in"
                     f" {readings.count('not read')}; placed in the grid: "
                     + (", ".join(f"{g} {n}" for g, n in split.items()) if split else "none")}
    if grid == "mixed":
        rec["grid_split"] = split
    placed = sum(split.values())
    if len(letters) > placed:
        rec["grid_note"] = {"not placed": f"{len(letters) - placed} cell(s) where a chain moves with a knob or a seed, or has no"
                                          f" object at some setting; {readings.count('miss') - split.get('B', 0) - split.get('both_unmet', 0)}"
                                          " of them still read as a miss by the rival, whose chain is steady there"}
    return rec


def criterion_own(cells):
    states = [c["side"] for c in cells.values()]
    near_c, near_r = states.count("nearer circles"), states.count("nearer random")
    passed = True if near_c and not near_r else False if near_r and not near_c else None
    return {"name": "B117-3", "kind": "own_reading", "passed": passed,
            "statement": "the observed entry-area share sits nearer the chain on the circles of payments inside each area than"
                         " the chain on random classes with the same sizes, the whole cohort range on one side of their midpoint,"
                         " at every setting and seed",
            "detail": f"{len(states)} cells; nearer circles {near_c}; nearer random {near_r}; "
                      + ", ".join(f"{x} {states.count(x)}" for x in sorted(set(states)) if x not in ("nearer circles", "nearer random"))}


def criterion_instrument(ends, lump, partitions, residual, disbursed_max):
    """ends: one entry per setting of ENDS_SETTINGS with the largest gap of each end and whether the cells agree;
    lump: the largest gap and agreement of the chain on class balances; partitions: every partition inside its areas,
    and every random partition with its reference's class sizes."""
    ends_ok = bool(ends) and all(e["same cells"] and e["areas"] <= ENDS_TOLERANCE and e["single wallets"] <= ENDS_TOLERANCE for e in ends)
    lump_ok = bool(lump["same cells"]) and lump["gap"] <= LUMP_TOLERANCE
    parts_ok = bool(partitions["inside areas"]) and bool(partitions["sizes kept"])
    conserved = residual is not None and residual <= 1e-6 * max(1.0, disbursed_max)
    passed = ends_ok and lump_ok and parts_ok and conserved
    return {"name": "B117-1", "kind": "instrument", "passed": bool(passed),
            "statement": "classes = areas and classes = single wallets give B114's recorded area and wallet chains on its cells,"
                         " the chain on class balances equals the wallet chain summed into classes, every partition stays inside"
                         " its areas and every random partition keeps its reference's class sizes, and the tag pass conserves value",
            "detail": "; ".join(f"{e['setting']}: areas {e['areas']:.1e}, single wallets {e['single wallets']:.1e}, same cells {e['same cells']}"
                                for e in ends)
                      + f"; tolerance {ENDS_TOLERANCE:.0e}; class balances against wallets {lump['gap']:.1e} (tolerance {LUMP_TOLERANCE:.0e}),"
                        f" same cells {lump['same cells']}; partitions inside their areas {partitions['inside areas']},"
                        f" random sizes kept {partitions['sizes kept']}; tagged value conserved to {residual:.2e}"}


def instrument_data(res, rows, panel, parts, digest, log=None, jobs=1):
    import numpy as np
    wc, N, C = panel["wclass"].astype(np.int64), panel["N"], len(res["classes"])
    b114 = json.loads(B114_RECORD.read_text(encoding="utf-8"))
    rec_cells, rec_wallet = b114["objects"]["cells"], b114["objects"]["wallet_cells"]
    ends = []
    for setting in ENDS_SETTINGS:
        got = chain_rows(res, panel, [("areas", wc, C, "class"), ("single wallets", np.arange(N, dtype=np.int64), N, "class")],
                         cache_dir=CACHE, archive_digest=digest, log=log, jobs=jobs, min_cohort=setting["min_cohort"],
                         start_at=setting["start_at"], window=setting["window"])
        gaps, same = {"areas": 0.0, "single wallets": 0.0}, True
        for mine, recorded, field in (("areas", rec_cells, "network"), ("single wallets", rec_wallet, "wallet_network")):
            for key, cell in recorded.items():
                entry = next(x for x in cell["settings"] if float(x["min_cohort"]) == setting["min_cohort"]
                             and x["start_at"] == setting["start_at"] and x["window"] == setting["window"])
                ours = got[mine].get(cell["area"], {}).get(int(cell["age"]))
                if (field in entry) != (ours is not None):
                    same = False
                    continue
                if ours is not None:
                    gaps[mine] = max(gaps[mine], abs(ours - entry[field]))
        ends.append({"setting": f"{setting['min_cohort']:g} / {setting['start_at']} / {setting['window']}",
                     "areas": gaps["areas"], "single wallets": gaps["single wallets"], "same cells": same})
    bt, k_bt = parts["area x business type"]
    gap, same = lump_gap(res, panel, bt, k_bt, cache_dir=CACHE, archive_digest=digest, log=log)
    inside = all(refines(p_, wc) for p_, _ in parts.values())
    sizes = all(class_sizes_by_area(parts[f"random, circle sizes, seed {s}"][0], wc) == class_sizes_by_area(parts[f"circles, seed {s}"][0], wc)
                for s in CRITERIA_SEEDS)
    return {"ends": ends, "lump": {"gap": gap, "same cells": same}, "partitions": {"inside areas": inside, "sizes kept": sizes},
            "b114_record_sha256": hashlib.sha256(B114_RECORD.read_bytes()).hexdigest()}


def _shares_and_places(rows, cells, got, key):
    return {"placement": placement(rows, got[key], cells), "shares": got[key]}


def build_record(a, res, rows, panel, digest, log=None, jobs=1):
    import numpy as np
    wc, names = panel["wclass"], res["classes"]
    S.panel_window(res, panel, "half")          # built once, before any worker forks
    d1 = block1_data(a, res, rows, panel, digest, log=log, jobs=jobs)
    d2 = block2_data(a, res, rows, panel, digest, log=log, jobs=jobs)
    parts = criteria_partitions(a, res, panel)
    inst = instrument_data(res, rows, panel, parts, digest, log=log, jobs=jobs)
    cells_crit = criteria_cells(res, panel, parts, digest, log=log, jobs=jobs)
    criteria = [criterion_instrument(inst["ends"], inst["lump"], inst["partitions"], res["conservation_residual"], float(res["disbursed"].max())),
                criterion_rival(cells_crit), criterion_own(cells_crit)]
    cells = cells_of(rows)
    block1 = {"classes by area, area x business type": {names[c]: len(v) for c, v in class_sizes_by_area(d1["parts"]["area x business type"][0], wc).items()},
              "partitions": {n: {"classes": K, "speeds": {sp: _shares_and_places(rows, cells, d1["got"], f"{n} | {sp}") for sp in SPEEDS}}
                             for n, (_, K) in d1["parts"].items()}}
    block2 = {"levels": {level_label(lv): {"classes": {n: K for n, (_, K) in d2["parts_by_level"][lv].items()},
                                           "circles by area": {names[c]: len(set(d2["parts_by_level"][lv]["circles"][0][wc == c].tolist()))
                                                               for c in np.unique(wc)}} for lv in LEVELS},
              "partitions": {f"{level_label(lv)} | {n}": {"classes": K, "speeds": {sp: _shares_and_places(rows, cells, d2["got"], f"{level_label(lv)} | {n} | {sp}")
                                                                                   for sp in SPEEDS}}
                             for lv in LEVELS for n, (_, K) in d2["parts_by_level"][lv].items()},
              "idle wallets": {"by area": d2["idle_breakdown"],
                               "splits": {f"{level_label(lv)} | {rule}": {"classes": K, "speeds": {
                                   sp: _shares_and_places(rows, cells, d2["got"], f"{level_label(lv)} | circles | {sp}" if rule == "one class"
                                                          else f"{level_label(lv)} | circles, idle {rule} | {sp}") for sp in SPEEDS}}
                                          for (lv, rule), (_, K) in d2["idle_parts"].items()},
                               f"{d2['idle_name']}": {"classes": int(d2["idle_single"].max()) + 1,
                                                      "speeds": {sp: _shares_and_places(rows, cells, d2["got"], f"{d2['idle_name']} | {sp}") for sp in SPEEDS}}}}
    cohorts = {name: {k: r[k] for k in ("cohorts", "observed", "cohort_min", "cohort_max", "cohorts_at")} for name, r in rows.items()}
    return S.clean({
        "stage": "B117",
        "config": {"archive": S.ARCHIVE_NAME, "archive_sha256": digest, "b114_record_sha256": inst["b114_record_sha256"],
                   "speeds": list(SPEEDS), "random_seeds_block1": list(RANDOM_SEEDS), "levels": [str(x) for x in LEVELS],
                   "sweep_seeds": list(SWEEP_SEEDS), "idle_levels": list(IDLE_LEVELS), "idle_rules": list(IDLE_RULES),
                   "criteria_level": CRITERIA_LEVEL, "criteria_seeds": list(CRITERIA_SEEDS), "knobs": S.SWEEP,
                   "ends_settings": [dict(x) for x in ENDS_SETTINGS], "ends_tolerance": ENDS_TOLERANCE, "lump_tolerance": LUMP_TOLERANCE,
                   "cell_min_cohorts": S.CELL_MIN_COHORTS, "not_areas": sorted(S.NOT_AREAS), "print_min_cohorts": PRINT_MIN_COHORTS,
                   "ages_weeks": list(S.AGES), "default_setting": S.DEFAULT_SETTING},
        "mapping": {"B117-2": RIVAL_MAPPING, "B117-3": OWN_MAPPING},
        "objects": {"wallets_in_circulation": panel["N"], "classes": names, "cohorts_default_setting": cohorts,
                    "instrument": inst, "block1": block1, "block2": block2, "criteria_cells": cells_crit},
        "criteria": criteria,
    })


def print_criteria(record: dict) -> None:
    print("\n== criteria")
    for name, mapping in record["mapping"].items():
        print(f"  {name} mapping: " + "; ".join(f"{k} -> {v}" for k, v in mapping.items()))
    for c in record["criteria"]:
        verdict = {True: "PASS", False: "FAIL", None: "no verdict"}[c["passed"]]
        grid = f" grid {c['grid']}" + (f" {c['grid_split']}" if "grid_split" in c else "") if "grid" in c else ""
        print(f"  {c['name']} [{c['kind']}] {verdict}{grid}: {c['statement']}\n      {c['detail']}")
    print("\n  cells (area | age): rival's chain, circle chain, grid, side; default setting and seed 0: low-high, rival's, circles, random")
    for key, rec in record["objects"]["criteria_cells"].items():
        base = next((x for x in rec["settings"] if float(x["min_cohort"]) == S.MIN_COHORT and x["start_at"] == "mid"
                     and x["window"] == "quarter" and int(x["seed"]) == 0), {})
        nums = ("" if "low" not in base else f"{100 * base['low']:.1f}-{100 * base['high']:.1f}, {100 * base['rival_chain']:.1f},"
                f" {100 * base['circle_chain']:.1f}, {100 * base['random_chain']:.1f}")
        print(f"   {key:28s} {rec['rival_in_range']:18s} {rec['circles_in_range']:18s} {rec['grid']:18s} {rec['side']:18s} {nums}")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

HEAD_T = "id,timeset,transfer_subtype,source,target,weight,token_name,token_address\n"
HEAD_U = "id,start,final_bal,gender,area_name,area_type,held_roles,business_type,xDAI_blockchain_address\n"


def _circles_toy():
    """Area Misc Nairobi: x1 and x2 sell food and pay only each other; x3 and x4 keep shops, x3 buys from
    y1 in Mukuru Nairobi, y1 buys from x4, x4 from x3. New money enters x1 in February."""
    s, x1, x2, x3, x4, y1 = "0xs", "0xx1", "0xx2", "0xx3", "0xx4", "0xy1"
    rows = [("2020-01-25 10:00", "DISBURSEMENT", s, x2, 20000), ("2020-01-25 10:05", "DISBURSEMENT", s, x3, 50000),
            ("2020-01-25 10:10", "DISBURSEMENT", s, x4, 50000), ("2020-01-25 10:15", "DISBURSEMENT", s, y1, 50000),
            ("2020-02-05 10:00", "DISBURSEMENT", s, x1, 100000), ("2020-02-10 10:00", "STANDARD", x1, x2, 30000),
            ("2020-02-12 10:00", "STANDARD", x3, y1, 20000), ("2020-02-20 10:00", "STANDARD", x2, x1, 25000),
            ("2020-02-25 10:00", "STANDARD", y1, x4, 15000), ("2020-03-05 10:00", "STANDARD", x1, x2, 20000),
            ("2020-03-10 10:00", "STANDARD", x4, x3, 15000), ("2020-03-20 10:00", "STANDARD", x2, x1, 20000),
            ("2020-04-10 10:00", "STANDARD", x1, x2, 10000), ("2020-04-15 10:00", "STANDARD", x3, y1, 10000),
            ("2020-05-01 10:00", "STANDARD", y1, x4, 5000), ("2020-05-10 10:00", "STANDARD", x2, x1, 10000),
            ("2020-06-20 10:00", "STANDARD", x4, x3, 1000), ("2020-07-15 10:00", "STANDARD", x1, x2, 1000)]
    txns = HEAD_T + "".join(f"{i + 1},{t}:00.000,{sub},{a_},{b_},{w},Sarafu,0x\n" for i, (t, sub, a_, b_, w) in enumerate(rows))
    users = (HEAD_U + f"1,2020-01-01,0,,other,other,ADMIN,system,{s}\n"
             f"2,2020-01-25,0,f,Misc Nairobi,urban,BENEFICIARY,food,{x1}\n"
             f"3,2020-01-25,0,f,Misc Nairobi,urban,BENEFICIARY,food,{x2}\n"
             f"4,2020-01-25,0,m,Misc Nairobi,urban,BENEFICIARY,shop,{x3}\n"
             f"5,2020-01-25,0,m,Misc Nairobi,urban,BENEFICIARY,shop,{x4}\n"
             f"6,2020-01-25,0,m,Mukuru Nairobi,urban,BENEFICIARY,shop,{y1}\n")
    return txns, users, (x1, x2, x3, x4, y1)


def _leaver_toy():
    """New money enters k1 in Kilifi in March and k1 pays nine tenths of it to n1 in Nyanza the next day,
    so the entry area holds less of the cohort than another area from the first week on."""
    s, k1, k2, n1, n2 = "0xs", "0xk1", "0xk2", "0xn1", "0xn2"
    rows = [("2020-01-25 10:00", "DISBURSEMENT", s, n1, 30000), ("2020-01-25 10:05", "DISBURSEMENT", s, k2, 30000),
            ("2020-03-03 10:00", "DISBURSEMENT", s, k1, 20000), ("2020-03-04 10:00", "STANDARD", k1, n1, 18000),
            ("2020-03-10 10:00", "STANDARD", n1, n2, 10000), ("2020-03-20 10:00", "STANDARD", n2, n1, 5000),
            ("2020-04-05 10:00", "STANDARD", n1, k2, 3000), ("2020-04-20 10:00", "STANDARD", k2, k1, 2000),
            ("2020-05-15 10:00", "STANDARD", k1, n1, 1000), ("2020-06-30 10:00", "STANDARD", n2, k2, 1000),
            ("2020-08-20 10:00", "STANDARD", k2, n2, 500)]
    txns = HEAD_T + "".join(f"{i + 1},{t}:00.000,{sub},{a_},{b_},{w},Sarafu,0x\n" for i, (t, sub, a_, b_, w) in enumerate(rows))
    users = (HEAD_U + f"1,2020-01-01,0,,other,other,ADMIN,system,{s}\n"
             f"2,2020-01-25,0,f,Kilifi,rural,BENEFICIARY,farming,{k1}\n"
             f"3,2020-01-25,0,f,Kilifi,rural,BENEFICIARY,farming,{k2}\n"
             f"4,2020-01-25,0,m,Nyanza,rural,BENEFICIARY,shop,{n1}\n"
             f"5,2020-01-25,0,m,Nyanza,rural,BENEFICIARY,food,{n2}\n")
    return txns, users


def _synthetic_panel(seed):
    """Forty wallets in three areas, two flow windows, random balances, sinks and payments; one wallet
    pays out without ever holding a balance at a day's end; the second window repeats pairs, as the
    half-year window does."""
    import numpy as np
    rng = np.random.default_rng(seed)
    N = 40
    wclass = np.sort(rng.integers(0, 3, N))
    balday = rng.uniform(100, 1000, (2, N)) * (rng.uniform(0, 1, (2, N)) > 0.15)
    balday[:, 7] = 0.0
    sink = rng.uniform(0, 30, (2, N)) * (rng.uniform(0, 1, (2, N)) > 0.5)
    edges = []
    for k in range(2):
        m = 160
        src, dst = rng.integers(0, N, m), rng.integers(0, N, m)
        src[:3] = 7
        val = rng.uniform(1, 50, m)
        if k == 1:
            src, dst, val = np.concatenate([src, src[:40]]), np.concatenate([dst, dst[:40]]), np.concatenate([val, val[:40]])
        edges.append((src.astype(np.int64), dst.astype(np.int64), val))
    return {"N": N, "wclass": wclass, "qdays": [(0, 30), (30, 60)], "balday": balday, "sink": sink,
            "edges": edges, "new_money": {}}


def cmd_selftest() -> int:
    import numpy as np
    checks = {}

    # One day by hand. Wallets 0 and 1 are class 0, wallet 2 class 1; each holds 100 over ten days.
    # Wallet 0 pays wallet 2 ten a day and five a day out of circulation; wallet 1 pays wallet 0 five a day.
    pan = {"N": 3, "wclass": np.array([0, 0, 0]), "qdays": [(0, 10)], "balday": np.array([[1000.0, 1000.0, 1000.0]]),
           "sink": np.array([[50.0, 0.0, 0.0]]), "edges": [(np.array([0, 1]), np.array([2, 0]), np.array([100.0, 50.0]))]}
    part3 = np.array([0, 0, 1])
    op_c = partition_operator(pan, 0, part3, 2, "class")
    op_o = partition_operator(pan, 0, part3, 2, "own")
    v_c = partition_step(np.array([[100.0, 0.0, 0.0]]), op_c)
    v_o = partition_step(np.array([[100.0, 0.0, 0.0]]), op_o)
    v_o1 = partition_step(np.array([[0.0, 100.0, 0.0]]), op_o)
    checks["one day by hand, class speed: class 0 leaves at 10%, pays on 75% of it, two thirds to class 1"] = (
        np.allclose(op_c["stay"], [0.9, 0.9, 1.0]) and np.allclose(op_c["circ"], [0.075, 0.075, 0.0])
        and np.allclose(v_c, [[92.5, 0.0, 5.0]]))
    checks["one day by hand, own speed: wallet 0 pays on 10%, landing by its class's mix, not its own payee"] = (
        np.allclose(op_o["stay"], [0.85, 0.95, 1.0]) and np.allclose(v_o, [[85.0 + 10.0 / 3, 0.0, 20.0 / 3]])
        and np.allclose(v_o1, [[5.0 / 3, 95.0, 10.0 / 3]]))

    # A wallet, or a class, that pays out more in a day than it holds leaves with all of it and no more.
    fast = {**pan, "balday": np.array([[50.0, 50.0, 1000.0]]), "sink": np.array([[0.0, 0.0, 0.0]]),
            "edges": [(np.array([0, 1]), np.array([2, 2]), np.array([200.0, 200.0]))]}
    f_c, f_o = partition_operator(fast, 0, part3, 2, "class"), partition_operator(fast, 0, part3, 2, "own")
    checks["a wallet or class paying out more than it holds in a day leaves at most all of it"] = (
        np.allclose(f_c["stay"], [0.0, 0.0, 1.0]) and np.allclose(f_o["stay"], [0.0, 0.0, 1.0])
        and np.allclose(f_c["circ"], [1.0, 1.0, 0.0]) and np.allclose(f_c["stay_k"], [0.0, 1.0]))

    # Lumping and mass on random panels: the class-speed chain on wallets, summed into classes, is the
    # chain on class balances; and each day's loss is exactly what leaves circulation.
    lump_ok, mass_ok, inf_ok = True, True, True
    for seed in range(3):
        pn = _synthetic_panel(seed)
        N = pn["N"]
        rng = np.random.default_rng(100 + seed)
        part = renumber(rng.integers(0, 7, N))
        K = int(part.max()) + 1
        V = rng.uniform(0, 100, (3, N))
        x = np.bincount((np.arange(3)[:, None] * K + part[None, :]).ravel(), weights=V.ravel(), minlength=3 * K).reshape(3, K)
        for day in range(60):
            op = partition_operator(pn, day // 30, part, K, "class")
            lost = float((V * ((1.0 - op["stay"]) - op["circ"])[None, :]).sum())
            new = partition_step(V, op)
            if abs(V.sum() - new.sum() - lost) > 1e-9 * V.sum():
                mass_ok = False
            V = new
            paid = x * op["circ_k"][None, :]
            flat = (np.arange(3)[:, None] * K + op["eb"][None, :]).ravel()
            land = np.bincount(flat, weights=(paid[:, op["ea"]] * op["d"][None, :]).ravel(), minlength=3 * K).reshape(3, K)
            x = x * op["stay_k"][None, :] + land
        summed = np.bincount((np.arange(3)[:, None] * K + part[None, :]).ravel(), weights=V.ravel(), minlength=3 * K).reshape(3, K)
        lump_ok &= bool(np.allclose(summed, x, rtol=1e-12, atol=1e-9))
        single = np.arange(N, dtype=np.int64)
        a1, a2 = partition_operator(pn, 1, single, N, "class"), partition_operator(pn, 1, single, N, "own")
        inf_ok &= bool(np.array_equal(a1["stay"], a2["stay"]) and np.array_equal(a1["circ"], a2["circ"]) and a1["stay"][7] == 0.0)
    checks["on random panels the class-speed chain on wallets sums to the chain on class balances"] = lump_ok
    checks["each day's loss of mass is exactly what leaves circulation"] = mass_ok
    checks["single wallets with class speed are own speed, down to a wallet that pays out holding nothing"] = inf_ok

    # The toy archive: the two ends against B114, the circles, and the partitions.
    txns, users, (x1, x2, x3, x4, y1) = _circles_toy()
    with tempfile.TemporaryDirectory() as d:
        pth = Path(d) / "circles.zip"
        S._archive(pth, txns, users)
        a = S.Archive(pth)
        res, rows = S.tagged(a)
        panel = S.wallet_panel(a, res)
        order = circulation_order(a, res)
        ix = {w: i for i, w in enumerate(order)}
        wc = panel["wclass"].astype(np.int64)
        N, C = panel["N"], len(res["classes"])
        b114, _ = S.wallet_chain_rows(res, panel)
        mine = chain_rows(res, panel, [("areas class", wc, C, "class"), ("areas own", wc, C, "own"),
                                       ("single class", np.arange(N, dtype=np.int64), N, "class"),
                                       ("single own", np.arange(N, dtype=np.int64), N, "own")])
        ends = [worst_gap(mine[m_], b114[t_]) for m_, t_ in (("areas class", "area speed, area payees"), ("areas own", "own speed, area payees"),
                                                          ("single class", "own speed, own payees"), ("single own", "own speed, own payees"))]
        net = worst_gap(mine["areas class"], {cl: r["network"] for cl, r in rows.items()})
        checks["toy: areas give B114's area chains and single wallets its wallet chain, to 1e-12 on the same cells"] = (
            a.problems == [] and all(g < 1e-12 and same for g, same in ends + [net]) and bool(mine["areas class"]))
        parts = first_partitions(a, res, panel)
        bt, k_bt = parts["area x business type"]
        mixed = renumber(np.array([0 if order[i] in (x1, x3) else 1 if order[i] in (x2, x4) else 2 for i in range(N)]))
        run = chain_rows(res, panel, [("bt", bt, k_bt, "class"), ("mixed", mixed, 3, "class")], state="wallet")
        whole = np.zeros(N, dtype=np.int64)
        # On a toy this small the two paths agree to the last bit, so which one ran is read off the calls.
        calls = {"step": 0, "cls": 0}
        real_step, real_cls = globals()["partition_step"], globals()["class_chain_rows"]

        def spy_step(V, op):
            calls["step"] += 1
            return real_step(V, op)

        def spy_cls(*args_, **kw_):
            calls["cls"] += 1
            return real_cls(*args_, **kw_)

        seen = {}
        globals()["partition_step"], globals()["class_chain_rows"] = spy_step, spy_cls
        try:
            for label, fn in (("auto, inside areas", lambda: chain_rows(res, panel, [("bt", bt, k_bt, "class")])),
                              ("auto, across areas", lambda: chain_rows(res, panel, [("whole", whole, 1, "class")])),
                              ("auto, own speed", lambda: chain_rows(res, panel, [("bt", bt, k_bt, "own")])),
                              ("lump", lambda: lump_gap(res, panel, bt, k_bt))):
                calls.update(step=0, cls=0)
                seen[label] = (fn(), dict(calls))
        finally:
            globals()["partition_step"], globals()["class_chain_rows"] = real_step, real_cls
        g_lump, same_lump = seen["lump"][0]
        checks["toy: class speed inside areas runs on class balances; across areas, own speed and the lump check wallet by wallet"] = (
            not refines(whole, wc)
            and seen["auto, inside areas"][1] == {"step": 0, "cls": 1}
            and seen["auto, across areas"][1]["cls"] == 0 and seen["auto, across areas"][1]["step"] > 0
            and seen["auto, own speed"][1]["cls"] == 0 and seen["auto, own speed"][1]["step"] > 0
            and seen["lump"][1]["cls"] == 1 and seen["lump"][1]["step"] > 0
            and g_lump < 1e-12 and same_lump and worst_gap(seen["auto, inside areas"][0]["bt"], run["bt"])[0] < 1e-12)
        try:
            class_chain_rows(res, panel, whole, 1)
            checks["toy: the class-balance chain refuses classes that cross areas"] = False
        except ValueError:
            checks["toy: the class-balance chain refuses classes that cross areas"] = True
        obs = rows["Misc Nairobi"]["observed"]
        bt_m, mx_m, ar_m = run["bt"]["Misc Nairobi"], run["mixed"]["Misc Nairobi"], mine["areas class"]["Misc Nairobi"]
        checks["toy: the tagged money never leaves the food circle, and the business-type classes keep all of it"] = (
            bool(obs) and all(abs(v - 1.0) < 1e-12 for v in obs.values()) and set(bt_m) == set(obs)
            and all(abs(v - 1.0) < 1e-12 for v in bt_m.values()))
        checks["toy: classes that cut across the circle, and the area, leak it to Mukuru Nairobi"] = (
            mx_m.get(13, 1.0) < 0.999 and ar_m.get(13, 1.0) < 0.999)
        on_cls = class_chain_rows(res, panel, bt, k_bt)
        g_cls, same_cls = worst_gap(run["bt"], on_cls)
        checks["toy: the chain on class balances equals the wallet chain summed, same cells"] = g_cls < 1e-12 and same_cls
        got = received_new_money(panel)
        checks["toy: only the wallet paid after the conversion counts as having received new money"] = (
            bool(got[ix[x1]]) and not any(got[ix[w]] for w in (x2, x3, x4, y1)))
        en, k_en = parts["received new money or not"]
        checks["toy: the split by new money has three classes, the paid wallet alone in its own"] = (
            k_en == 3 and sum(int(en[i] == en[ix[x1]]) for i in range(N)) == 1 and en[ix[x2]] == en[ix[x3]] == en[ix[x4]])
        sp_t, k_sp = parts["own-speed strata"]
        spd = own_speed(panel)
        checks["toy: speed strata cut Misc Nairobi in two by speed, as many classes as business types"] = (
            k_sp == 3 and sp_t[ix[y1]] not in {sp_t[ix[w]] for w in (x1, x2, x3, x4)}
            and all(spd[i] <= spd[j] for i in range(N) for j in range(N)
                    if wc[i] == wc[j] == wc[ix[x1]] and sp_t[i] < sp_t[j]))
        checks["toy: area x business type has three classes, and the area partition is B114's"] = (
            k_bt == 3 and bt[ix[x1]] == bt[ix[x2]] and bt[ix[x3]] == bt[ix[x4]] and bt[ix[x1]] != bt[ix[x3]]
            and np.array_equal(parts["area"][0], wc))

    # The same four ends where the new money leaves its area within days, so the entry area is not the
    # area holding most of the cohort: the share must be read for the entry area, not for the largest.
    txns_l, users_l = _leaver_toy()
    with tempfile.TemporaryDirectory() as d:
        pth = Path(d) / "leaver.zip"
        S._archive(pth, txns_l, users_l)
        a = S.Archive(pth)
        res, rows = S.tagged(a)
        panel = S.wallet_panel(a, res)
        wc = panel["wclass"].astype(np.int64)
        N, C = panel["N"], len(res["classes"])
        b114, _ = S.wallet_chain_rows(res, panel)
        mine = chain_rows(res, panel, [("areas class", wc, C, "class"), ("areas own", wc, C, "own"),
                                       ("single class", np.arange(N, dtype=np.int64), N, "class"),
                                       ("single own", np.arange(N, dtype=np.int64), N, "own")], jobs=2)
        ends = [worst_gap(mine[m_], b114[t_]) for m_, t_ in (("areas class", "area speed, area payees"), ("areas own", "own speed, area payees"),
                                                          ("single class", "own speed, own payees"), ("single own", "own speed, own payees"))]
        bt_l, k_l, _ = from_keys([(int(wc[i]), a.users[w]["business_type"]) for i, w in enumerate(circulation_order(a, res))])
        run_l = chain_rows(res, panel, [("bt", bt_l, k_l, "class")], state="wallet")["bt"]
        g_l, same_l = worst_gap(run_l, class_chain_rows(res, panel, bt_l, k_l))
        checks["toy where new money leaves at once: the chain on class balances equals the wallet chain summed"] = (
            k_l == 3 and g_l < 1e-12 and same_l and any(v < 0.9 for v in run_l.get("Kilifi", {}).values()))
        low = [v for v in mine["single own"].get("Kilifi", {}).values() if v < 0.5]
        checks["toy where new money leaves at once: the four ends against B114 to 1e-12, entry share below one half, two workers"] = (
            a.problems == [] and all(g < 1e-12 and same for g, same in ends) and len(low) >= 3
            and list(mine) == ["areas class", "areas own", "single class", "single own"])

    # Payment circles. Six planted groups of 25, dense inside and sparse between: Louvain at resolution 1 finds
    # exactly the six, with modularity no lower than theirs; a low resolution merges them and a high one splits
    # them; the same seed gives the same classes.
    rng = np.random.default_rng(11)
    n_pl, g_pl = 150, np.repeat(np.arange(6), 25)
    iu, ju = np.triu_indices(n_pl, 1)
    same_g = g_pl[iu] == g_pl[ju]
    pick = rng.uniform(0, 1, iu.size) < np.where(same_g, 0.5, 0.01)
    u_pl, v_pl = iu[pick], ju[pick]
    w_pl = rng.uniform(1, 2, u_pl.size)
    found = louvain(n_pl, u_pl, v_pl, w_pl, 1.0, seed=0)
    pairs = set(zip(found.tolist(), g_pl.tolist()))
    exact = len(pairs) == 6 and len({a_ for a_, _ in pairs}) == 6 and len({b_ for _, b_ in pairs}) == 6
    q_found, q_planted = modularity(n_pl, u_pl, v_pl, w_pl, found), modularity(n_pl, u_pl, v_pl, w_pl, g_pl)
    k_low = int(louvain(n_pl, u_pl, v_pl, w_pl, 0.05, seed=0).max()) + 1
    k_high = int(louvain(n_pl, u_pl, v_pl, w_pl, 30.0, seed=0).max()) + 1
    checks["circles: six planted groups found exactly at resolution 1, modularity no lower than the planted one"] = (
        exact and q_found >= q_planted - 1e-12)
    checks["circles: a low resolution merges the groups, a high one splits them"] = k_low <= 2 and k_high > 6
    checks["circles: the same seed gives the same classes"] = bool(np.array_equal(found, louvain(n_pl, u_pl, v_pl, w_pl, 1.0, seed=0)))
    # Four cliques of five in a ring, five unit payments between neighbours: joining two neighbours changes
    # modularity by (5 - 30 * 30 / 120) / 60 < 0, which a class's degree only shows if it carries twice its
    # inner weight at the second level.
    cu_, cv_ = [], []
    for q_ in range(4):
        for i_ in range(5):
            for j_ in range(i_ + 1, 5):
                cu_.append(5 * q_ + i_)
                cv_.append(5 * q_ + j_)
            cu_.append(5 * q_ + i_)
            cv_.append(5 * ((q_ + 1) % 4) + i_)
    cu_, cv_ = np.array(cu_), np.array(cv_)
    ring = louvain(20, cu_, cv_, np.ones(cu_.size), 1.0, seed=2)
    cliques = np.repeat(np.arange(4), 5)
    joined = np.where(cliques == 1, 0, cliques)
    checks["circles: four weakly joined cliques stay four classes, and joining two would lower modularity"] = (
        len(set(zip(ring.tolist(), cliques.tolist()))) == 4 and len(set(ring.tolist())) == 4
        and modularity(20, cu_, cv_, np.ones(cu_.size), cliques) > modularity(20, cu_, cv_, np.ones(cu_.size), joined))
    tri = louvain(6, np.array([0, 0, 1, 3, 3, 4, 2]), np.array([1, 2, 2, 4, 5, 5, 3]), np.ones(7), 1.0, seed=5)
    checks["circles: two triangles joined by one payment are two classes"] = (
        len(set(tri.tolist())) == 2 and tri[0] == tri[1] == tri[2] and tri[3] == tri[4] == tri[5])
    # Within areas: a triangle and a pair in area 0, a wallet of area 0 paying only area 1, a pair and two idle
    # wallets in area 1, and a payment to itself; the wallets with no payment inside their area are one class.
    pan_c = {"N": 10, "wclass": np.array([0, 0, 0, 0, 0, 0, 1, 1, 1, 1]),
             "edges": [(np.array([0, 1, 2, 3, 5, 6, 4]), np.array([1, 2, 0, 4, 6, 7, 4]), np.array([5.0, 5.0, 5.0, 3.0, 9.0, 2.0, 7.0]))]}
    idx_c, u_c, v_c, w_c = area_graph(pan_c, 0)
    checks["circles: the area graph keeps pairs inside the area, sums both ways, drops payments to oneself"] = (
        idx_c.tolist() == [0, 1, 2, 3, 4, 5] and sorted(zip(u_c.tolist(), v_c.tolist(), w_c.tolist())) == [(0, 1, 5.0), (0, 2, 5.0), (1, 2, 5.0), (3, 4, 3.0)])
    pc = circle_partition(pan_c, 1.0)
    checks["circles: classes inside each area, the idle wallets of an area in one class of their own"] = (
        refines(pc, pan_c["wclass"]) and int(pc.max()) + 1 == 5 and pc[0] == pc[1] == pc[2] and pc[3] == pc[4]
        and len({pc[0], pc[3], pc[5]}) == 3 and pc[6] == pc[7] and pc[8] == pc[9] and pc[6] != pc[8])
    pk = circle_partition(pan_c, "components")
    ps = circle_partition(pan_c, 1.0, idle="singletons")
    two_tri = (np.array([0, 0, 1, 3, 3, 4, 2]), np.array([1, 2, 2, 4, 5, 5, 3]))
    checks["circles: connected parts join what Louvain splits, and idle wallets can be classes of their own"] = (
        np.array_equal(pk, pc) and len(set(connected_parts(6, *two_tri).tolist())) == 1
        and len(set(connected_parts(7, *two_tri).tolist())) == 2
        and int(ps.max()) + 1 == 6 and ps[8] != ps[9] and refines(ps, pan_c["wclass"]) and ps[0] == ps[1] == ps[2])
    # The idle class split by spending: in area 0 wallet 2 pays only area 1 and wallet 5 pays nothing; in area 1
    # wallet 4 pays only out of circulation and wallet 3 only receives.
    pan_i = {"N": 6, "wclass": np.array([0, 0, 0, 1, 1, 0]), "edges": [(np.array([0, 2]), np.array([1, 3]), np.array([5.0, 4.0]))],
             "sink": np.array([[0.0, 0.0, 0.0, 0.0, 2.0, 0.0]])}
    one_i, two_i = circle_partition(pan_i, 1.0), circle_partition(pan_i, 1.0, idle="spent or not")
    checks["circles: the idle class splits into wallets that paid something and wallets that paid nothing, area by area"] = (
        int(one_i.max()) + 1 == 3 and one_i[2] == one_i[5] and one_i[3] == one_i[4]
        and int(two_i.max()) + 1 == 5 and two_i[0] == two_i[1] and two_i[2] != two_i[5] and two_i[3] != two_i[4]
        and refines(two_i, pan_i["wclass"]) and refines(two_i, one_i))
    wal_i = circle_partition(pan_i, 1.0, idle="paid a wallet or not")
    checks["circles: split by paying a wallet, a wallet that pays only out of circulation goes with the ones that pay nothing"] = (
        int(wal_i.max()) + 1 == 4 and wal_i[2] != wal_i[5] and wal_i[3] == wal_i[4] and refines(wal_i, one_i))
    key_c = np.array([5.0, 1.0, 3.0, 2.0, 9.0, 0.0, 4.0, 1.0, 7.0, 6.0])
    sw = split_within(pc, key_c, 2)
    checks["circles: speed within circles cuts each class in two by the key and never joins classes"] = (
        int(sw.max()) + 1 == 9 and refines(sw, pc) and sw[1] == sw[2] != sw[0]
        and all(len(set(sw[pc == c_].tolist())) == min(2, int((pc == c_).sum())) for c_ in range(5)))

    # Partition builders on a bigger random layout.
    rng = np.random.default_rng(7)
    wcl = np.sort(rng.integers(0, 4, 300)).astype(np.int64)
    ref = renumber(wcl * 10 + rng.integers(0, 6, 300))
    like_ok = True
    for seed in range(4):
        r = random_like(ref, wcl, seed)
        like_ok &= refines(r, wcl) and class_sizes_by_area(r, wcl) == class_sizes_by_area(ref, wcl)
    try:
        random_like(np.zeros(300, dtype=np.int64), wcl, 0)
        raised = False
    except ValueError:
        raised = True
    checks["random classes keep each area's class sizes, never mix areas, and refuse a reference that does"] = like_ok and raised
    counts = {c: len(v) for c, v in class_sizes_by_area(ref, wcl).items()}
    key = rng.uniform(0, 1, 300)
    sp = split_in_order(wcl, counts, key)
    runs_ok = refines(sp, wcl) and all(len(class_sizes_by_area(sp, wcl)[c]) == counts[c] for c in counts)
    for c in counts:
        cls_ = sorted(set(sp[wcl == c]))
        sz = [int((sp == j).sum()) for j in cls_]
        runs_ok &= max(sz) - min(sz) <= 1
        runs_ok &= all(key[sp == cls_[j]].max() <= key[sp == cls_[j + 1]].min() for j in range(len(cls_) - 1))
    checks["strata: each area cut into its count of runs of near-equal size, in order of the key"] = bool(runs_ok)

    # Placement against the cohort range, and the cache.
    fake_rows = {"A": {"cohorts_at": {13: 3, 26: 3, 52: 2}, "cohort_min": {13: 0.5, 26: 0.4, 52: 0.3}, "cohort_max": {13: 0.7, 26: 0.6, 52: 0.5}},
                 "other": {"cohorts_at": {13: 5}, "cohort_min": {13: 0.1}, "cohort_max": {13: 0.9}}}
    cl = cells_of(fake_rows)
    checks["cells: areas only, ages that three cohorts reach"] = cl == [("A", 13), ("A", 26)]
    checks["placement: inside, below and above the range are told apart"] = (
        placement(fake_rows, {"A": {13: 0.6, 26: 0.2}}, cl) == {"inside": 1, "below": 1, "above": 0, "no object": 0}
        and placement(fake_rows, {"A": {13: 0.71}}, cl) == {"inside": 0, "below": 0, "above": 1, "no object": 1})
    with tempfile.TemporaryDirectory() as d:
        pth = Path(d) / "circles.zip"
        S._archive(pth, txns, users)
        a = S.Archive(pth)
        res, _ = S.tagged(a)
        panel = S.wallet_panel(a, res)
        wc = panel["wclass"].astype(np.int64)
        C = len(res["classes"])
        first = chain_rows(res, panel, [("x", wc, C, "class")], cache_dir=Path(d) / "c", archive_digest="abc")
        second = chain_rows(res, panel, [("x", wc, C, "class")], cache_dir=Path(d) / "c", archive_digest="abc")
        files = sorted((Path(d) / "c").glob("*.json"))
        keys = {cache_key("abc", wc, C, "class", S.MIN_COHORT, "mid", "quarter"),
                cache_key("abd", wc, C, "class", S.MIN_COHORT, "mid", "quarter"),
                cache_key("abc", wc[::-1].copy(), C, "class", S.MIN_COHORT, "mid", "quarter"),
                cache_key("abc", wc, C, "own", S.MIN_COHORT, "mid", "quarter"),
                cache_key("abc", wc, C, "class", S.MIN_COHORT, "end", "quarter"),
                cache_key("abc", wc, C, "class", S.MIN_COHORT, "mid", "half")}
        checks["cache: a second run reads the file and gives the same shares; archive, partition, speed and setting change the key"] = (
            len(files) == 1 and first == second and len(keys) == 6)

    # Criteria. B117-1 passes on clean inputs and fails on each seeded fault.
    ends_ok = [{"setting": "a", "areas": 1e-10, "single wallets": 2e-10, "same cells": True}]
    good = {"ends": ends_ok, "lump": {"gap": 1e-14, "same cells": True}, "partitions": {"inside areas": True, "sizes kept": True},
            "residual": 1e-9, "disbursed_max": 1e5}
    faults = [dict(good, ends=[dict(ends_ok[0], areas=1e-6)]), dict(good, ends=[dict(ends_ok[0], **{"single wallets": 1e-6})]),
              dict(good, ends=[dict(ends_ok[0], **{"same cells": False})]), dict(good, ends=[]),
              dict(good, lump={"gap": 1e-9, "same cells": True}), dict(good, lump={"gap": 0.0, "same cells": False}),
              dict(good, partitions={"inside areas": False, "sizes kept": True}),
              dict(good, partitions={"inside areas": True, "sizes kept": False}), dict(good, residual=1.0)]
    checks["B117-1 passes on clean inputs and fails on each of nine seeded faults"] = (
        criterion_instrument(**good)["passed"] is True and all(criterion_instrument(**f)["passed"] is False for f in faults))

    def cell_(rv, cv, grid, side="nearer circles"):
        return {"rival_in_range": rv, "circles_in_range": cv, "grid": grid, "side": side}

    all_b = {f"x{i}": cell_("outside", "inside", "B") for i in range(4)}
    r_b, r_m = criterion_rival(all_b), criterion_rival(dict(all_b, y=cell_("inside", "outside", "C")))
    r_c = criterion_rival({f"c{i}": cell_("inside", "outside", "C") for i in range(3)})
    r_a = criterion_rival({f"a{i}": cell_("inside", "inside", "A") for i in range(3)})
    r_u = criterion_rival({f"u{i}": cell_("outside", "moves with a knob", "moves with a knob") for i in range(3)})
    checks["B117-2: misses PASS in B; one C among them no verdict, mixed with counts; all C FAIL; all A no verdict; nothing placed unread"] = (
        r_b["passed"] is True and r_b["grid"] == "B" and "grid_split" not in r_b
        and r_m["passed"] is None and r_m["grid"] == "mixed" and r_m["grid_split"] == {"B": 4, "C": 1}
        and r_c["passed"] is False and r_c["grid"] == "C" and r_a["passed"] is None and r_a["grid"] == "A"
        and r_u["passed"] is None and r_u["grid"] == "unread" and "grid_split" not in r_u
        and all(x["rival_premise"] == RIVAL_PREMISE and x["rival_entailment"] == RIVAL_ENTAILMENT and x["kind"] == "rival"
                for x in (r_b, r_m, r_c, r_a, r_u)))
    o_p = criterion_own({"a": cell_("x", "x", "x", "nearer circles"), "b": cell_("x", "x", "x", "straddle")})
    o_n = criterion_own({"a": cell_("x", "x", "x", "nearer circles"), "b": cell_("x", "x", "x", "nearer random")})
    o_f = criterion_own({"a": cell_("x", "x", "x", "nearer random")})
    o_0 = criterion_own({"a": cell_("x", "x", "x", "moves with a knob")})
    checks["B117-3: all counted nearer circles PASS, both sides no verdict, all nearer random FAIL, none counted no verdict"] = (
        o_p["passed"] is True and o_n["passed"] is None and o_f["passed"] is False and o_0["passed"] is None)
    checks["the grid letter and the side of the midpoint, case by case"] = (
        [grid_letter(0.4, 0.6, o_, r_) for o_, r_ in ((0.5, 0.7), (0.5, 0.5), (0.7, 0.5), (0.7, 0.8))] == ["B", "A", "C", "both_unmet"]
        and side_cell(0.8, 0.9, 0.85, 0.3) == "nearer circles" and side_cell(0.1, 0.2, 0.85, 0.3) == "nearer random"
        and side_cell(0.5, 0.7, 0.85, 0.3) == "straddle" and side_cell(0.1, 0.2, 0.15, 0.9) == "nearer circles"
        and side_cell(0.7, 0.8, 0.15, 0.9) == "nearer random" and side_cell(0.1, 0.2, 0.5, 0.5) == "straddle")
    saved_rows, saved_chain = S.cohort_rows, globals()["chain_rows"]

    def fake_rows(res_, min_cohort=S.MIN_COHORT, start_at="mid", window="quarter"):
        return {"Nyanza": {"cohorts_at": {13: 4, 26: 3}, "cohort_min": {13: 0.90, 26: 0.90}, "cohort_max": {13: 0.99, 26: 0.99}},
                "other": {"cohorts_at": {13: 5}, "cohort_min": {13: 0.9}, "cohort_max": {13: 0.99}}}

    def fake_chain(res_, panel_, variants, cache_dir=None, archive_digest=None, min_cohort=S.MIN_COHORT, start_at="mid",
                   window="quarter", log=None, jobs=1):
        out = {}
        for name, _, _, _ in variants:
            if name == "rival":
                out[name] = {"Nyanza": {13: 0.50, 26: 0.95 if window == "quarter" else 0.50}, "other": {13: 0.5}}
            elif name.startswith("circles"):
                out[name] = {"Nyanza": {13: 0.95, 26: 0.95 if not name.endswith("2") else 0.80}, "other": {13: 0.95}}
            else:
                out[name] = {"Nyanza": {13: 0.40, 26: 0.40}, "other": {13: 0.40}}
        return out

    fake_parts = {"area x business type": (np.zeros(3, dtype=np.int64), 1)}
    for s in CRITERIA_SEEDS:
        fake_parts[f"circles, seed {s}"] = (np.zeros(3, dtype=np.int64), 1)
        fake_parts[f"random, circle sizes, seed {s}"] = (np.zeros(3, dtype=np.int64), 1)
    S.cohort_rows, globals()["chain_rows"] = fake_rows, fake_chain
    try:
        cc = criteria_cells({}, {}, fake_parts, "d")
    except Exception as exc:
        print(f"  criteria cells raised {exc!r}")
        cc = {}
    finally:
        S.cohort_rows, globals()["chain_rows"] = saved_rows, saved_chain
    checks["criteria cells: areas only; the rival settled over settings, the circles over settings and seeds; 54 readings a cell"] = (
        sorted(cc) == ["Nyanza | 13 weeks", "Nyanza | 26 weeks"]
        and cc["Nyanza | 13 weeks"]["grid"] == "B" and cc["Nyanza | 13 weeks"]["side"] == "nearer circles"
        and cc["Nyanza | 13 weeks"]["rival_in_range"] == "outside" and cc["Nyanza | 13 weeks"]["circles_in_range"] == "inside"
        and cc["Nyanza | 26 weeks"]["rival_in_range"] == "moves with a knob"
        and cc["Nyanza | 26 weeks"]["circles_in_range"] == "moves with a knob"
        and all(len(v["settings"]) == 54 for v in cc.values()))

    failed = [k for k, ok in checks.items() if not ok]
    for k, ok in checks.items():
        print(("ok    " if ok else "FAIL  ") + k)
    print(f"\n{len(checks) - len(failed)} of {len(checks)} checks pass")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--block", type=int, action="append", help="run only these blocks (repeatable)")
    ap.add_argument("--archive", default=str(S.RAW / S.ARCHIVE_NAME))
    ap.add_argument("--jobs", type=int, default=1, help="worker processes for the chains not yet cached")
    ap.add_argument("--criteria", action="store_true", help="print the criteria after the blocks")
    ap.add_argument("--write", action="store_true", help="print the criteria and write results/b117_partition_grain.json")
    args = ap.parse_args()
    if args.selftest:
        return cmd_selftest()
    path = Path(args.archive)
    if not path.exists():
        print(f"no archive at {path}; B114 reads it from UK Data Service ReShare record 855142")
        return 1
    digest = S.sha256_of(path)
    manifest = path.parent / S.MANIFEST.name
    known = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    if known.get(path.name) != digest:
        print(f"PROBLEM the archive is not the one B114 recorded in {manifest.name}")
        return 1
    print(f"archive {path.name}, sha256 {digest}")
    a = S.Archive(path)
    if a.problems:
        print("PROBLEM " + "; ".join(a.problems))
        return 1
    res, rows = S.tagged(a)
    panel = S.wallet_panel(a, res)
    if not args.write:
        for k, fn in enumerate(BLOCKS):
            if not args.block or k in args.block:
                fn(a, res, rows, panel, digest, jobs=args.jobs)
    if args.criteria or args.write:
        record = build_record(a, res, rows, panel, digest, log=print, jobs=args.jobs)
        print_criteria(record)
        if args.write:
            out = ROOT / "results" / "b117_partition_grain.json"
            S.write_record(record, out)
            print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
