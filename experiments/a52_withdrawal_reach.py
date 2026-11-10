"""A52: claims taken out of the financial layer, and which nodes the loss reaches first.

Ruled 2026-09-27. The CES policy station read industries closer to finance going into
crisis less often after a tightening, and the sign it had registered, positive, came from
reading A44/A45/B114 (claims settle where they enter) across to a withdrawal the A track had
never run. A31 read withdrawal on closing states: whose accounts the claims come out of does
not change who ends below the floor, because trade mixes the shape back within rounds. What
no station has read is the path: in the rounds right after a withdrawal starts, are the
nodes near the financial layer hit first and hardest, or buffered?

**The treatment.** From round ``START`` for ``LENGTH`` rounds, a fixed amount is taken out of
the financial layer's live accounts (or, in the production arms, out of every live account outside
it) each round, pro rata to what each holds and never below
zero, and destroyed. The amount is ``RATE`` times the layer's holdings when the episode
opens. The mirror arm adds the same amount instead. The treatment reads no random number,
so a treated run and its control (the same class with an amount of zero) share every draw.

**Distance.** Hops along the carrier's graph from any financial node, the direction money
moves; a node the financial layer cannot reach is its own band.

**Readouts, per cell.** For every node outside the financial layer, its holdings against the
control at 1, 5 and 20 rounds after the episode opens (short and long, read as trend rather
than calendar), and whether it has left the market by the episode's end when the control's
twin has not. Printed by distance band, and as the rank correlation of closeness
``1/(1+d)`` with the change among the nodes the financial layer reaches.

Steps, one at a time:

    python experiments/a52_withdrawal_reach.py --gate       # A52-0
    python experiments/a52_withdrawal_reach.py --selftest   # seeded faults
    python experiments/a52_withdrawal_reach.py --smoke      # seed 0, nothing written
    python experiments/a52_withdrawal_reach.py --run        # the grid, writes the record

The criteria are written in this file and the record carries their text, so every quantity a
run produces is reported.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from monetary_topology.network import Network, NetworkConfig  # noqa: E402

from a41_same_ticket import ROUNDS, SEEDS, WALLS, base_config, classes_of  # noqa: E402

START = 150
LENGTH = 20
RATES = (0.01, 0.05)
ARMS = ("withdraw", "inject", "withdraw_production", "inject_production", "transfer")
# The two production arms were added after the CES reading came back with the sign opposite to the
# one the financial-layer arms reproduce: a tightening need not take claims out of the financial
# layer at all, since what a rate rise tightens is the borrowers' side. So the same amount is taken
# from (or added to) every live account outside the financial layer, pro rata to holdings, the
# position A31 calls "production".
# The transfer arm is what a rate rise does to the ledger rather than to the stock: the borrowers pay
# more interest and the lenders receive it. The same amount is taken from every live account outside
# the financial layer, pro rata to holdings and never below zero, and what was taken is added to the
# financial layer's live accounts, pro rata to their holdings. The claim total does not move.
#: Every round of the episode is kept. The first, fifth and twentieth alone do not show in which
#: round a sign turns.
HORIZONS = tuple(range(1, LENGTH + 1))
PRINTED = (1, 2, 3, 4, 5, 20)
RECORD = RESULTS / "a52_withdrawal_reach.json"
TOL = 1e-9


class EpisodeNetwork(Network):
    """The carrier with claims taken from (or added to) the financial layer for one episode.

    ``_pre_round`` runs before the round's issuance, outside the round's own stock-flow
    assertion, the zone A41's ticket and injection use. The amount is fixed when the episode
    opens: ``rate`` times the financial layer's holdings then. Taken pro rata to holdings and
    capped at each account; added pro rata to holdings (to the live nodes equally when the
    layer holds nothing). Destroyed or created claims move the claim total and nothing else.
    Every round records who is still trading, so exits can be read per node.
    """

    def __init__(self, config: NetworkConfig, arm: str = "withdraw", rate: float = 0.0,
                 start: int = START, length: int = LENGTH) -> None:
        super().__init__(config)
        if arm not in ARMS:
            raise ValueError(f"arm must be one of {ARMS}")
        if not rate >= 0.0:
            raise ValueError("rate must be non-negative")
        self.arm, self.rate, self.start, self.length = arm, float(rate), int(start), int(length)
        self._l1_ix = classes_of(self)["l1"]
        self._prod_ix = np.setdiff1d(np.arange(self._n), self._l1_ix)
        self._amount: float | None = None
        self.alive_rows: list[np.ndarray] = []
        self.moved: list[float] = []
        self.asked: list[float] = []

    def _targets(self) -> np.ndarray:
        ix = self._prod_ix if self.arm.endswith("_production") else self._l1_ix
        return ix[self._alive[ix]]

    def _book_total(self, amount: float) -> None:
        self._total_claims += amount

    def _pre_round(self, t: int) -> None:
        super()._pre_round(t)
        self.alive_rows.append(np.array(self._alive, dtype=bool, copy=True))
        if not (self.start <= t < self.start + self.length):
            return
        ix = self._targets()
        h0 = np.array(self.holdings, dtype=float, copy=True)
        if self._amount is None:
            self._amount = self.rate * float(np.maximum(h0[self._l1_ix], 0.0).sum())
        a = self._amount
        h = h0.copy()
        pos = np.maximum(h0[ix], 0.0)
        if self.arm == "transfer":
            src = self._prod_ix[self._alive[self._prod_ix]]
            ps = np.maximum(h0[src], 0.0)
            ts = float(ps.sum())
            take = np.minimum(ps, a * ps / ts) if ts > 0 else np.zeros_like(ps)
            got = float(take.sum())
            dst = self._l1_ix[self._alive[self._l1_ix]]
            pd = np.maximum(h0[dst], 0.0)
            tdd = float(pd.sum())
            add = got * pd / tdd if tdd > 0 else np.full(dst.size, got / max(dst.size, 1))
            h[src] = h0[src] - take
            h[dst] = h[dst] + add
            delta = 0.0
        elif self.arm.startswith("withdraw"):
            tot = float(pos.sum())
            take = np.minimum(pos, a * pos / tot) if tot > 0 else np.zeros_like(pos)
            h[ix] = h0[ix] - take
            delta = -float(take.sum())
        else:
            tot = float(pos.sum())
            add = a * pos / tot if tot > 0 else np.full(ix.size, a / max(ix.size, 1))
            h[ix] = h0[ix] + add
            delta = float(add.sum()) if ix.size else 0.0
        moved = float(h.sum() - h0.sum())
        if abs(moved - delta) > TOL * max(1.0, abs(float(h0.sum()))):
            raise AssertionError(f"episode ledger does not close at round {t}: {moved!r} vs {delta!r}")
        self.holdings = h
        self._book_total(delta)
        self.moved.append(delta)
        self.asked.append(0.0 if self.arm == "transfer" else (-a if self.arm.startswith("withdraw") else a))


def total_closes(net: Network, hist) -> tuple[bool, float]:
    """The tracked claim total against holdings plus parked claims at the close, as A41-1 reads it."""
    held = float(np.asarray(hist.holdings, float)[-1].sum())
    parked = float(np.asarray(hist.parked, float)[-1]) if hist.parked is not None else 0.0
    gap = abs(float(net._total_claims) - (held + parked))
    return gap <= 1e-9 * max(1.0, held + parked), gap


def distances(net: Network) -> np.ndarray:
    """Hops from any financial node along the graph (row pays column); inf where unreached."""
    A = np.asarray(net.adjacency) > 0
    n = A.shape[0]
    d = np.full(n, np.inf)
    q = deque()
    for s in classes_of(net)["l1"]:
        d[s] = 0.0
        q.append(int(s))
    while q:
        u = q.popleft()
        for v in np.flatnonzero(A[u]):
            if d[v] == np.inf:
                d[v] = d[u] + 1.0
                q.append(int(v))
    return d


def _rank(x):
    o = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    r[o] = np.arange(1, len(x) + 1)
    _, inv, c = np.unique(x, return_inverse=True, return_counts=True)
    return (np.bincount(inv, weights=r) / c)[inv]


def spearman(a, b):
    if len(a) < 3:
        return float("nan")
    ra, rb = _rank(np.asarray(a, float)), _rank(np.asarray(b, float))
    ra, rb = ra - ra.mean(), rb - rb.mean()
    den = math.sqrt(float((ra ** 2).sum() * (rb ** 2).sum()))
    return float((ra * rb).sum() / den) if den > 0 else float("nan")


def band(d):
    return "unreached" if not np.isfinite(d) else ("1" if d <= 1 else ("2" if d <= 2 else "3+"))


def readout(treat, ctrl, h_t, h_c, dist, l1):
    others = np.setdiff1d(np.arange(len(dist)), l1)
    H_t, H_c = np.asarray(h_t.holdings, float), np.asarray(h_c.holdings, float)
    out = {"by_band": {}, "spearman": {}, "exits": {}}
    close = np.where(np.isfinite(dist), 1.0 / (1.0 + dist), 0.0)
    for tau in HORIZONS:
        row = min(START + tau - 1, H_t.shape[0] - 1)
        base = H_c[row, others]
        rel = (H_t[row, others] - base) / np.maximum(np.abs(base), 1e-12)
        keep = np.abs(base) > 1e-12
        # the rank correlation is read on the nodes the financial layer reaches: an unreached node has
        # closeness 0 by construction and, holding next to nothing, a change of 0 whatever the arm, so
        # including it would rank a construction rather than a response
        reached = np.isfinite(dist[others])
        out["spearman"][str(tau)] = spearman(close[others][keep & reached], rel[keep & reached])
        for b in ("1", "2", "3+", "unreached"):
            m = np.array([band(dist[i]) == b for i in others]) & keep
            out["by_band"].setdefault(b, {})[str(tau)] = (float(np.median(rel[m])) if m.any() else None)
    end = min(START + LENGTH, len(treat.alive_rows) - 1)
    a_t, a_c = treat.alive_rows[end], ctrl.alive_rows[end]
    for b in ("1", "2", "3+", "unreached"):
        m = np.array([band(dist[i]) == b for i in others])
        idx = others[m]
        out["exits"][b] = {"nodes": int(idx.size), "extra_exits": int(np.sum(a_c[idx] & ~a_t[idx])),
                           "saved": int(np.sum(~a_c[idx] & a_t[idx]))}
    out["band_sizes"] = {b: int(sum(band(dist[i]) == b for i in others)) for b in ("1", "2", "3+", "unreached")}
    return out


def one_cell(seed, wall, arm, rate, ctrl=None):
    cfg = base_config(seed, need=wall)
    if ctrl is None:
        cn = EpisodeNetwork(cfg, arm, 0.0)
        ctrl = (cn, cn.run())
    tn = EpisodeNetwork(cfg, arm, rate)
    th = tn.run()
    cn, ch = ctrl
    dist = distances(tn)
    r = readout(tn, cn, th, ch, dist, classes_of(tn)["l1"])
    r.update({"seed": seed, "wall": wall, "arm": arm, "rate": rate,
              "moved": float(sum(tn.moved)), "asked": float(sum(tn.asked)),
              "ledger_ok": bool(total_closes(tn, th)[0]), "ledger_gap": total_closes(tn, th)[1],
              "shortfall": float(sum(tn.asked) - sum(tn.moved))})
    return r, ctrl


def run_gate() -> bool:
    """A52-0: an amount of zero is the plain network, bit for bit, on every floor and two seeds."""
    ok = True
    for seed in (0, 1):
        for wall in WALLS:
            a = Network(base_config(seed, need=wall)).run()
            for arm in ARMS:
                b = EpisodeNetwork(base_config(seed, need=wall), arm, 0.0).run()
                same = np.array_equal(np.asarray(a.holdings), np.asarray(b.holdings)) and \
                    np.array_equal(np.asarray(a.total_volume), np.asarray(b.total_volume))
                ok &= bool(same)
                print(f"  seed {seed} floor {wall} {arm}: {'bitwise' if same else 'DIFFERS'}")
    print(f"A52-0 {'PASS' if ok else 'FAIL'}")
    return ok


def selftest() -> bool:
    """Seeded faults (11f): an episode that takes from the wrong class, and one that does not
    book the claim total, must each be caught."""
    ok = []

    class WrongClass(EpisodeNetwork):
        def _targets(self):
            return classes_of(self)["mid"]

    class NoBook(EpisodeNetwork):
        def _book_total(self, amount):
            pass

    cfg = base_config(0, need=0.03)
    ctrl = EpisodeNetwork(cfg, "withdraw", 0.0)
    ch = ctrl.run()
    good = EpisodeNetwork(cfg, "withdraw", 0.05)
    gh = good.run()
    l1 = classes_of(good)["l1"]
    H_g, H_c = np.asarray(gh.holdings), np.asarray(ch.holdings)
    fell_l1 = float(H_g[START, l1].sum() - H_c[START, l1].sum()) < 0
    ok.append(fell_l1)
    print(f"  the financial layer falls on the episode's first round: {fell_l1}")
    w = WrongClass(cfg, "withdraw", 0.05)
    wh = w.run()
    mid = classes_of(w)["mid"]
    caught = float(np.asarray(wh.holdings)[START, mid].sum() - H_c[START, mid].sum()) < float(
        H_g[START, mid].sum() - H_c[START, mid].sum())
    ok.append(caught)
    print(f"  a withdrawal from the wrong class is seen in that class's holdings: {caught}")
    ok_good = total_closes(good, gh)[0]
    nb = NoBook(cfg, "withdraw", 0.05)
    nbh = nb.run()
    caught_nb = not total_closes(nb, nbh)[0]
    ok += [ok_good, caught_nb]
    print(f"  the claim total closes on a correct episode: {ok_good}")
    print(f"  an unbooked claim total is caught at the close: {caught_nb} (gap {total_closes(nb, nbh)[1]:.3g})")
    t1 = turn([-0.3, -0.1, 0.0, 0.2] + [0.3] * (len(HORIZONS) - 4))
    t2 = turn([-0.3, 0.1, -0.1] + [0.2] * (len(HORIZONS) - 4) + [-0.01])
    ok_turn = (t1 == {"negative_rounds": [1, 2], "first_positive": 4, "positive_from": 4}
               and t2["first_positive"] == 2 and t2["positive_from"] is None)
    ok.append(ok_turn)
    print(f"  a path's turn is read off every round, and one that ends negative has no round it stays positive from: {ok_turn}")
    print(f"selftest {'PASS' if all(ok) else 'FAIL'}")
    return all(ok)


def criteria(rows, gate_ok):
    fin = []
    for r in rows:
        fin += [v for v in r["spearman"].values()]
        fin += [v for b in r["by_band"].values() for v in b.values() if v is not None]
    finite = [isinstance(v, float) and math.isfinite(v) for v in fin]
    ledger = all(r["ledger_ok"] for r in rows)
    return [
        {"name": "A52-0", "kind": "instrument", "passed": bool(gate_ok),
         "statement": "an amount of zero is the plain network, bit for bit, on every floor and two seeds",
         "detail": "run by --gate"},
        {"name": "A52-1", "kind": "instrument", "passed": bool(ledger),
         "statement": "the tracked claim total equals holdings plus parked claims at the close of every "
                      "treated run (A41-1's reading)",
         "detail": f"{len(rows)} cells; largest gap {max(r['ledger_gap'] for r in rows):.2e}"},
        {"name": "A52-2", "kind": "bookkeeping", "passed": bool(finite) and all(finite),
         "statement": "every printed median and rank correlation is finite",
         "detail": f"{sum(finite)} of {len(finite)} finite"},
    ]


def turn(path) -> dict:
    """Where a per-round path changes sign: the rounds it is negative, the first round it is
    positive, and the round from which it stays positive to the end (None if it does not)."""
    neg = [HORIZONS[k] for k, v in enumerate(path) if v < 0]
    pos = [HORIZONS[k] for k, v in enumerate(path) if v > 0]
    stays = None
    for k in range(len(path)):
        if all(v > 0 for v in path[k:]):
            stays = HORIZONS[k]
            break
    return {"negative_rounds": neg, "first_positive": pos[0] if pos else None, "positive_from": stays}


def summarise(rows):
    out = {}
    for arm in ARMS:
        for rate in RATES:
            for wall in WALLS:
                cell = [r for r in rows if r["arm"] == arm and r["rate"] == rate and r["wall"] == wall]
                if not cell:
                    continue
                key = f"{arm} {rate} floor {wall}"
                out[key] = {
                    "spearman": {str(t): float(np.median([r["spearman"][str(t)] for r in cell])) for t in HORIZONS},
                    "spearman_turn": turn([float(np.median([r["spearman"][str(t)] for r in cell])) for t in HORIZONS]),
                    "spearman_last_by_seed": [round(r["spearman"][str(HORIZONS[-1])], 6) for r in cell],
                    "by_band": {b: {str(t): float(np.median([r["by_band"][b][str(t)] for r in cell
                                                             if r["by_band"][b][str(t)] is not None]))
                                    if any(r["by_band"][b][str(t)] is not None for r in cell) else None
                                    for t in HORIZONS} for b in ("1", "2", "3+", "unreached")},
                    "extra_exits": {b: int(sum(r["exits"][b]["extra_exits"] for r in cell)) for b in ("1", "2", "3+", "unreached")},
                    "saved": {b: int(sum(r["exits"][b]["saved"] for r in cell)) for b in ("1", "2", "3+", "unreached")},
                    "band_sizes": cell[0]["band_sizes"]}
    return out


def render(summ, crit):
    L = ["## A52: claims taken out of the financial layer, and which nodes the loss reaches first\n"]
    for key, s in summ.items():
        L.append(f"### {key}: band sizes {s['band_sizes']}")
        L.append("| band | median change at 1 | at 5 | at 20 | extra exits by episode end | exits avoided |")
        L.append("|---|---|---|---|---|---|")
        for b in ("1", "2", "3+", "unreached"):
            v = s["by_band"][b]
            f = lambda x: "-" if x is None else f"{x:+.4f}"
            L.append(f"| {b} | {f(v['1'])} | {f(v['5'])} | {f(v['20'])} | {s['extra_exits'][b]} | {s['saved'][b]} |")
        tn = s["spearman_turn"]
        L.append("rank correlation of closeness with the change among reached nodes, median over seeds: "
                 + ", ".join(f"at {t} {s['spearman'][str(t)]:+.3f}" for t in PRINTED)
                 + f"; negative in rounds {tn['negative_rounds']}, positive from round {tn['positive_from']} on"
                 + f"; at round {HORIZONS[-1]} by seed {s['spearman_last_by_seed']}\n")
    for c in crit:
        L.append(f"- {c['name']} ({c['kind']}): {'PASS' if c['passed'] else 'FAIL'}. {c['detail']}")
    return "\n".join(L)


def run_grid(seeds):
    rows = []
    for seed in seeds:
        for wall in WALLS:
            ctrl = None
            for arm in ARMS:
                for rate in RATES:
                    r, ctrl = one_cell(seed, wall, arm, rate, ctrl)
                    rows.append(r)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.gate:
        return 0 if run_gate() else 1
    if a.selftest:
        return 0 if selftest() else 1
    if a.smoke or a.run:
        t0 = time.time()
        rows = run_grid((0,) if a.smoke else SEEDS)
        gate_ok = run_gate() if a.run else True
        crit = criteria(rows, gate_ok)
        summ = summarise(rows)
        print(render(summ, crit))
        print(f"\n{len(rows)} cells in {time.time() - t0:.1f} s")
        if a.run:
            rec = {"stage": "A52", "config": {"start": START, "length": LENGTH, "rates": list(RATES),
                                              "arms": list(ARMS), "horizons": list(HORIZONS),
                                              "walls": list(WALLS), "seeds": list(SEEDS), "rounds": ROUNDS,
                                              "carrier": "A41's, from a41_same_ticket.base_config"},
                   "criteria": crit, "summary": summ, "rows": rows}
            RECORD.write_text(json.dumps(rec, sort_keys=True, indent=1, default=lambda o: None) + "\n",
                              encoding="utf-8", newline="\n")
            print(f"written {RECORD.name}")
        return 0 if all(c["passed"] for c in crit) else 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
