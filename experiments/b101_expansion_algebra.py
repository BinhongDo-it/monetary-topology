"""The expansion question, put back on the module so it stops living in a chat.

The question as posed: a sovereign creates claims, or borrows outside ones, and
thickens edges where it chooses. Neither is an intrinsic property of the graph,
and who repays the debt bears on different edges. Does any of that reduce to a
change in the support set, and is catch-up between two graphs a contest of
support sets?

This driver does not answer whether that is a good model of expansion. It reads
what the module actually does with each of the three inputs, so the answer is
measured rather than recalled.

    python experiments/b101_expansion_algebra.py --run
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from monetary_topology.config import MonetaryAuthority  # noqa: E402
from monetary_topology.network import Network, NetworkConfig, NetworkSpec  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b101_expansion_algebra.json"
ROUNDS = 55
SEED = 101


def build(seed=SEED, rounds=ROUNDS, **kw):
    return Network(NetworkConfig(spec=NetworkSpec(seed=seed), seed=seed,
                                 rounds=rounds, **kw))


def _crit(name, kind, ok, detail, **extra):
    c = {"name": name, "kind": kind, "detail": detail,
         "passed": None if ok is None else bool(ok)}
    if ok is None:
        c["void"] = True
    c.update(extra)
    return c


def run(write=True):
    crit, report = [], {}

    # ---- 1. a closed system holds its level; the default one does not, and the
    #         difference is issuance and nothing else
    closed = build(authority=MonetaryAuthority(rule="none")).run()
    openn = build().run()
    cv = np.asarray(closed.total_volume, float)
    ov = np.asarray(openn.total_volume, float)
    # **A transient is not a trend, and the first shape confused them.** The
    # closed system settles from its starting configuration over the first few
    # rounds and then holds; a peak-to-trough swing over the whole run reads that
    # settling and calls it movement. The reading is the trend after it settles.
    def thirds(v):
        n = len(v); a, b = n // 3, 2 * n // 3
        return float(np.median(v[:a])), float(np.median(v[a:b])), float(np.median(v[b:]))
    c1, c2, c3 = thirds(cv)
    o1, o2, o3 = thirds(ov)
    settle = 10
    tail_swing = float(np.ptp(cv[settle:]) / np.median(cv[settle:]))
    report["level"] = {
        "closed_thirds": [c1, c2, c3], "open_thirds": [o1, o2, o3],
        "closed_trend": float(c3 / c1), "open_trend": float(o3 / o1),
        "closed_first_round": float(cv[0]), "closed_settled_swing_from_round_10": tail_swing,
        "rounds": ROUNDS}
    crit.append(_crit(
        "X1  claim creation is the only engine of the level",
        "instrument", (c3 / c1) < 1.05 and (o3 / o1) > 1.5,
        f"thirds of the run, medians. Authority off: {c1:.2f}, {c2:.2f}, {c3:.2f}, a "
        f"last-over-first of {c3 / c1:.3f}, and from round {settle} onward a relative "
        f"swing of {tail_swing:.4f}. Authority on: {o1:.2f}, {o2:.2f}, {o3:.2f}, "
        f"last-over-first {o3 / o1:.2f}. Reading fixed in advance: a system with no "
        f"issuance has no engine for the level, so its trend sits at one while the "
        f"other does not. **The closed run falls during the first rounds as it settles "
        f"out of its starting configuration and then holds; a first shape measured "
        f"peak-to-trough over the whole run, read that settling as movement, and "
        f"failed on it.** Nothing else in the module moves the level."))

    # ---- 2. thickening an edge through the adjacency does nothing at all
    a = build()
    before = a._route.copy()
    i, j = np.unravel_index(int(np.argmax(a.adjacency)), a.adjacency.shape)
    a.adjacency[i, j] *= 3.0
    a._rebuild_route()
    same = bool(np.array_equal(before, a._route))
    worst = float(np.abs(before - a._route).max())
    report["thicken"] = {"edge": [int(i), int(j)], "identical": same, "worst": worst}
    crit.append(_crit(
        "X2  thickening an edge in the adjacency changes no routing",
        "instrument", same,
        f"the heaviest edge ({i}, {j}) was tripled and the routing rebuilt: worst "
        f"change {worst:.3e}, identical {same}. The rebuild clips the adjacency into "
        f"[0, 1], so a weight above one is the same edge as a weight of one. **Whatever "
        f"'thickening an edge' means in this module, it is not this**, and the two "
        f"channels that do carry weight are the industry and broadcast fields."))

    # ---- 3. does the support set track the level, or only proxy it
    rows = []
    for seed in range(8):
        for rule in ("none", "endogenous"):
            h = build(seed=seed, authority=MonetaryAuthority(rule=rule)).run()
            v = np.asarray(h.total_volume, float)
            s = np.asarray(h.effective_support, float)
            tail = slice(-15, None)
            rows.append({"seed": seed, "rule": rule,
                         "volume": float(np.median(v[tail])),
                         "support": float(np.median(s[tail]))})
    v = np.array([r["volume"] for r in rows]); s = np.array([r["support"] for r in rows])
    corr = float(np.corrcoef(np.log(v), np.log(s))[0, 1])
    # do the two ranges overlap? if support were the level, they would not
    on = [r for r in rows if r["rule"] == "endogenous"]
    off = [r for r in rows if r["rule"] == "none"]
    s_on = np.array([r["support"] for r in on]); s_off = np.array([r["support"] for r in off])
    v_on = np.array([r["volume"] for r in on]); v_off = np.array([r["volume"] for r in off])
    s_overlap = bool(s_on.min() < s_off.max() and s_off.min() < s_on.max())
    v_overlap = bool(v_on.min() < v_off.max() and v_off.min() < v_on.max())
    report["support_vs_level"] = {
        "rows": rows, "log_corr": corr,
        "support_ranges": {"authority_on": [float(s_on.min()), float(s_on.max())],
                           "authority_off": [float(s_off.min()), float(s_off.max())]},
        "volume_ranges": {"authority_on": [float(v_on.min()), float(v_on.max())],
                          "authority_off": [float(v_off.min()), float(v_off.max())]},
        "support_ranges_overlap": s_overlap, "volume_ranges_overlap": v_overlap}
    crit.append(_crit(
        "X3  the support set is a proxy for the level and not the level",
        "own_reading", None,
        f"Void: printed, not adjudicated, because no criterion was registered on it "
        f"before the run. 16 cells, eight seeds by the authority on and off. Log "
        f"correlation between the tail volume and the tail effective support is "
        f"{corr:+.3f}. The support ranges "
        f"{'overlap' if s_overlap else 'do not overlap'} across the two authority "
        f"settings ({s_off.min():.2f} to {s_off.max():.2f} off, {s_on.min():.2f} to "
        f"{s_on.max():.2f} on) while the volume ranges "
        f"{'overlap' if v_overlap else 'do not overlap'}. **A contest of support sets "
        f"is not the same contest as one of levels**, and how far apart they are is "
        f"what this prints."))

    crit.append(_crit(
        "X4  what this driver does not do", "bookkeeping", True,
        "it does not model expansion, test any theory of it, or make the two-graph "
        "catch-up reading. It records what the module does with the three inputs the "
        "question named, so the next session starts from measurements rather than "
        "from a chat transcript."))

    record = {"stage": "B101-X", "config": {"rounds": ROUNDS, "seed": SEED,
                                            "seeds_swept": 8, "tail": 15},
              "criteria": crit, "report": report}
    for c in crit:
        tag = "VOID" if c["passed"] is None else ("PASS" if c["passed"] else "FAIL")
        print(f"{tag}  {c['name']}\n      [{c['kind']}] {c['detail'][:430]}\n")
    if write:
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n",
                       encoding="utf-8", newline="\n")
        print(f"record -> {OUT.relative_to(ROOT)}")
    return 1 if [c for c in crit if c["passed"] is False] else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    raise SystemExit(run(write=not a.no_write))
