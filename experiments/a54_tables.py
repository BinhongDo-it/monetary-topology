"""A54: the record, as tables.

Reads ``results/a54_penalty.json`` and prints Markdown tables. Nothing is run
and nothing is written: every number printed here is a count or a median of
values already in the record, so the tables in the ledger can be regenerated
from the file instead of retyped.

    python experiments/a54_tables.py            # every table
    python experiments/a54_tables.py cap cut    # only the named ones

Tables: carrier, side, linear, incidence, size, cap, cut, blocks, totals.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results" / "a54_penalty.json"

TARGETS = ("financial", "production")
LAYERS = ("fin", "mid", "hhw")


def load() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def table(t: dict) -> list:
    """A table of the record as a list of records, dotted names kept."""
    return [dict(zip(t["fields"], row)) for row in t["rows"]]


def med(values, digits: int = 4) -> str:
    vals = [float(v) for v in values if v is not None and np.isfinite(v)]
    if not vals:
        return "-"
    return "%.*f" % (digits, float(np.median(vals)))


def rng(values, digits: int = 4) -> str:
    vals = [float(v) for v in values if v is not None and np.isfinite(v)]
    if not vals:
        return "-"
    return "%.*f to %.*f" % (digits, min(vals), digits, max(vals))


def count(rows, test) -> int:
    return sum(1 for x in rows if test(x))


def tally(items) -> str:
    out = {}
    for it in items:
        key = "none" if it is None else str(it)
        out[key] = out.get(key, 0) + 1
    return ", ".join("%s %d" % kv for kv in sorted(out.items())) or "-"


def md(head: list, rows: list) -> None:
    print("| " + " | ".join(head) + " |")
    print("|" + "|".join("---" for _ in head) + "|")
    for r in rows:
        print("| " + " | ".join(str(v) for v in r) + " |")
    print()


def carrier(doc: dict) -> None:
    twins = table(doc["sections"]["run"]["rows"]["twin"])
    print("### carrier: the twins and the two targets (medians over seeds, "
          "then over the cells of a row)\n")
    rows = []
    for block, stress, auth in sorted({(x["block"], x["stress"], x["authority"])
                                       for x in twins}):
        xs = [x for x in twins if (x["block"], x["stress"], x["authority"])
              == (block, stress, auth)]
        row = [block, stress, auth, len(xs),
               med((x["circulating_at_penalty"] for x in xs), 2),
               med((x["circulating_close"] for x in xs), 2),
               rng((x["below_close"] for x in xs), 0)]
        for kind in TARGETS:
            p = "targets.%s." % kind
            row += [med(x[p + "share_at_penalty"] for x in xs),
                    med((x[p + "held_at_penalty"] / x[p + "inflow_per_round"]
                         for x in xs if x[p + "inflow_per_round"]), 2),
                    med(x[p + "jitter"] for x in xs),
                    "%s/%s" % (med((x[p + "routing_in_edges"] for x in xs), 0),
                               med((x[p + "routing_out_edges"] for x in xs), 0)),
                    med((x[p + "in_edges_carrying_flow"] for x in xs), 0)]
        rows.append(row)
    md(["block", "strain", "authority", "twins", "circulating at penalty",
        "at close", "below floor at close",
        "fin share", "fin balance in rounds of inflow", "fin jitter",
        "fin edges in/out", "fin in-edges carrying flow",
        "prod share", "prod balance in rounds of inflow", "prod jitter",
        "prod edges in/out", "prod in-edges carrying flow"],
       rows)
    ties = [(x["seed"], kind) for x in twins for kind in TARGETS
            if x["targets.%s.tied_first" % kind] > 1]
    print("targets tied for the most in-edges (seed, target): %s\n"
          % sorted(set(ties)))
    print("financial target is the issuance entry in %d of %d twins; "
          "production target is on the payroll payers' list in %d of %d\n"
          % (count(twins, lambda x: x["targets.financial.is_issuance_entry"]),
             len(twins),
             count(twins, lambda x: x["targets.production.on_payroll_list"]),
             len(twins)))


FAMILIES = (
    ("fine, leaves the graph", lambda x: x["kind"] == "fine"
     and x["sink"] == "destroy"),
    ("fine, returned", lambda x: x["kind"] == "fine" and x["sink"] == "return"),
    ("cap below the balance (0.5, 0.8)", lambda x: x["kind"] == "cap"
     and x["size"] < 1.0),
    ("cap at the balance, not growing", lambda x: x["kind"] == "cap"
     and x["size"] == 1.0 and x["block"] == "main"),
    ("cap at or above, growing", lambda x: x["kind"] == "cap"
     and x["block"] == "growth"),
    ("cut in-edges", lambda x: x["kind"] == "cut" and x["side"] == "in"
     and not x.get("restore")),
    ("cut in-edges, put back", lambda x: x["kind"] == "cut"
     and bool(x.get("restore"))),
    ("cut out-edges", lambda x: x["kind"] == "cut" and x["side"] == "out"),
)


def arm_rows(doc: dict) -> list:
    run = doc["sections"]["run"]["rows"]
    return table(run["fine"]) + table(run["cap"]) + table(run["cut"])


def side(doc: dict) -> None:
    rows = arm_rows(doc)
    print("### side: the three penalties side by side (all cells)\n")
    out = []
    for kind in TARGETS:
        for label, pick in FAMILIES:
            xs = [x for x in rows if x["target"] == kind and pick(x)]
            if not xs:
                continue
            out.append([
                kind, label, len(xs),
                med(x["first_round"] for x in xs),
                med(x["deviation_at.5"] for x in xs),
                med(x["deviation_at.20"] for x in xs),
                med(x["tail"] for x in xs),
                med((x["permanence_unbanded"] for x in xs), 3),
                tally(x["permanence_state"] for x in xs)])
    md(["target", "penalty", "cells", "first round", "after 5", "after 20",
        "tail", "tail over first round", "states"], out)


def linear(doc: dict) -> None:
    fines = table(doc["sections"]["run"]["rows"]["fine"])
    once = [x for x in fines if x["mode"] == "once" and x["sink"] == "destroy"
            and x["block"] == "main"]
    print("### linear: one-off fines that leave the graph, by size\n")
    out = []
    for auth in ("none", "endogenous"):
        for kind in TARGETS:
            for size in sorted({x["size"] for x in once}):
                xs = [x for x in once if x["authority"] == auth
                      and x["target"] == kind and x["size"] == size]
                stable = [x for x in xs if x["switches_as_twin"]]
                out.append([
                    auth, kind, "%g" % size, len(xs),
                    med(x["fine_over_circulating"] for x in xs),
                    med((x["fine_in_rounds_of_inflow"] for x in xs), 2),
                    med(x["impact"] for x in xs),
                    med(x["first_round"] for x in xs),
                    med(x["deviation_at.5"] for x in xs),
                    med((x["tail"] for x in xs), 5),
                    med(x["band"] for x in xs),
                    len(stable),
                    med(x["target_loss_over_fine_tail"] for x in stable),
                    med(x["share_at_penalty"] for x in stable),
                    med((x["extra_issued_share_of_fine"] for x in xs), 3)])
    md(["authority", "target", "share of balance", "cells",
        "fine over circulating claims", "fine in rounds of inflow",
        "share at the yield", "first round", "after 5", "tail", "band",
        "cells with no switch flipped", "there: target's lasting loss per "
        "unit taken", "there: its share", "issued back, share of fine"], out)
    gaps = [x for x in fines if x.get("proportional_gap") is not None
            and x["size"] != x["proportional_reference"]]
    stable = [x for x in gaps if x["switches_as_twin"]
              and x["reference_switches_as_twin"]]
    moved = [x for x in gaps if x not in stable]
    print("proportionality, one-off fines against the smallest on the same "
          "target: %d cells with every switch as the twin's, largest gap "
          "%.3g; %d with a switch flipped, gaps %.3g to %.3g, %d above 1e-9\n"
          % (len(stable), max(x["proportional_gap"] for x in stable),
             len(moved), min(x["proportional_gap"] for x in moved),
             max(x["proportional_gap"] for x in moved),
             count(moved, lambda x: x["proportional_gap"] > 1e-9)))
    print("first switch to flip, one-off fines, all cells: %s\n"
          % tally(x["first_switch"] for x in fines
                  if x["mode"] == "once" and x["sink"] == "destroy"
                  and x["block"] == "main"))


def incidence(doc: dict) -> None:
    fines = table(doc["sections"]["run"]["rows"]["fine"])
    once = [x for x in fines if x["mode"] == "once" and x["sink"] == "destroy"
            and x["block"] == "main"]
    print("### incidence: who carries a one-off fine over the tail, as a "
          "multiple of pro rata\n")
    out = []
    for auth in ("none", "endogenous"):
        for stress in ("healthy", "leak_recycled", "leak"):
            for e in sorted({x["elasticity"] for x in once}):
                xs = [x for x in once if x["authority"] == auth
                      and x["stress"] == stress and x["elasticity"] == e
                      and x["switches_as_twin"]]
                row = [auth, stress, "%.1f" % e, len(xs)]
                for L in LAYERS:
                    vals = [(1.0 - x["incidence.tail_layer." + L])
                            / x["fine_over_circulating"] for x in xs
                            if x.get("incidence.tail_layer." + L) is not None
                            and x["fine_over_circulating"] > 0]
                    row.append("%s (%d)" % (med(vals, 3), len(vals)))
                row.append(med((x["extra_issued_share_of_fine"] for x in xs),
                               3))
                out.append(row)
    md(["authority", "strain", "wage elasticity",
        "cells with no switch flipped", "financial layer (cells)",
        "intermediate layer (cells)", "households on a payroll (cells)",
        "issued back, share of fine"], out)
    print("### incidence: by steps down from the target, median balance "
          "against the twin's, one-off fines, authority off\n")
    out = []
    for kind in TARGETS:
        xs = [x for x in once if x["target"] == kind
              and x["authority"] == "none"]
        for when, key in (("after 1", "incidence.at.1.down."),
                          ("after 5", "incidence.at.5.down."),
                          ("after 20", "incidence.at.20.down.")):
            out.append([kind, when] + [
                med((x.get(key + s) for x in xs), 4) for s in ("1", "2", "3+")])
        out.append([kind, "tail (ratio less one)"] + [
            med(((x["incidence.tail_down." + s] - 1.0) for x in xs
                 if x.get("incidence.tail_down." + s) is not None), 4)
            for s in ("1", "2", "3+")])
    md(["target", "when", "one step down", "two steps", "three or more"], out)
    back = [x for x in fines if x["sink"] == "return"]
    print("returned fines, %d cells: median node's balance against its "
          "twin's over the tail %s; the target's tail %s; largest absolute "
          "tail of the target %.3g\n"
          % (len(back), rng(x["incidence.tail_all.median"] for x in back),
             rng((x["tail"] for x in back), 6),
             max(abs(x["tail"]) for x in back if x["tail"] is not None)))


def size(doc: dict) -> None:
    fines = [x for x in table(doc["sections"]["run"]["rows"]["fine"])
             if x["sink"] == "destroy" and x["block"] == "main"]
    print("### size: fines that leave the graph, by mode and size\n")
    out = []
    for auth in ("none", "endogenous"):
        for kind in TARGETS:
            for mode in ("once", "instalments", "garnish"):
                for sz in sorted({x["size"] for x in fines
                                  if x["mode"] == mode}):
                    xs = [x for x in fines if x["authority"] == auth
                          and x["target"] == kind and x["mode"] == mode
                          and x["size"] == sz]
                    out.append([
                        auth, kind, mode, "%g" % sz, len(xs),
                        med((x["fine_in_rounds_of_inflow"] for x in xs), 2),
                        med(x["fine_over_circulating"] for x in xs),
                        med((x["rounds_to_collect"] for x in xs), 0),
                        med(x["first_round"] for x in xs),
                        med((x["tail"] for x in xs), 5),
                        count(xs, lambda x: x["tail_state"].startswith(
                            "outside")),
                        count(xs, lambda x: not x["switches_as_twin"]),
                        count(xs, lambda x: x["rounds_block_under"] > 0),
                        count(xs, lambda x: x["flip"] == "block under")])
    md(["authority", "target", "mode", "size", "cells",
        "fine in rounds of inflow", "fine over circulating claims",
        "closes to collect", "first round", "tail", "tail outside band",
        "a switch flipped", "block below floor in some round",
        "block below at close"], out)


def cap(doc: dict) -> None:
    caps = table(doc["sections"]["run"]["rows"]["cap"])
    print("### cap\n")
    out = []
    for block in ("main", "growth"):
        for kind in TARGETS:
            for level in sorted({x["size"] for x in caps
                                 if x["block"] == block}):
                xs = [x for x in caps if x["block"] == block
                      and x["target"] == kind and x["size"] == level]
                read = [x for x in xs if x["cap_state"] not in (
                    "never bit", "above its cap to the end")]
                out.append([
                    block, kind, "%g" % level, len(xs),
                    tally(x["cap_state"] for x in xs),
                    med(x["deviation_at.20"] for x in read),
                    med(x["deviation_at.50"] for x in read),
                    med(x["deviation_at.100"] for x in read),
                    med(x["tail"] for x in read),
                    med((x["blocked_share_of_inflow_tail"] for x in read), 3),
                    med((x["log_slope_tail"] for x in read), 5),
                    med((x["twin_log_slope_tail"] for x in read), 5),
                    med((x["diverted_to_layer.fin"] for x in read), 3),
                    med((x["diverted_to_layer.mid"] for x in read), 3),
                    med((x["diverted_to_payers_of_target"] for x in read), 3),
                    count(read, lambda x: x["flip"] == "block under")])
    md(["block", "target", "cap", "cells", "states", "after 20", "after 50",
        "after 100", "tail", "inflow turned away, tail",
        "slope of log balance", "twin's slope", "turned away to fin",
        "to mid", "to payers of the target", "block below at close"], out)
    up = [x for x in caps if x["cap_state"] == "above its cap to the end"]
    print("above its cap to the end, %d cells: %s; balance over cap at the "
          "close, %s; extra issued after the penalty against the twin, "
          "median %s\n"
          % (len(up), tally("%s %s cap %g %s" % (
              x["target"], x["stress"], x["size"], x["authority"])
              for x in up),
             rng((x["held_close"] / x["cap_level"] for x in up), 1),
             med((x["extra_issued_after"] for x in up), 1)))
    fines = [x for x in table(doc["sections"]["run"]["rows"]["fine"])
             if x["block"] == "growth"]
    out = []
    for kind in TARGETS:
        for sz in sorted({x["size"] for x in fines}):
            xs = [x for x in fines if x["target"] == kind and x["size"] == sz]
            out.append([kind, "%g" % sz, len(xs),
                        med(x["first_round"] for x in xs),
                        med((x["tail"] for x in xs), 5),
                        med((x["log_slope_tail"] for x in xs), 5),
                        med((x["twin_log_slope_tail"] for x in xs), 5)])
    print("growing block, one-off fines beside the caps\n")
    md(["target", "share of balance", "cells", "first round", "tail",
        "slope of log balance", "twin's slope"], out)


def cut(doc: dict) -> None:
    cuts = table(doc["sections"]["run"]["rows"]["cut"])
    print("### cut: in-edges, never put back\n")
    out = []
    for kind in TARGETS:
        for sz in sorted({x["size"] for x in cuts}):
            for pick in ("flow", "random"):
                xs = [x for x in cuts if x["target"] == kind
                      and x["side"] == "in" and x["size"] == sz
                      and x["pick"] == pick and not x.get("restore")]
                out.append([
                    kind, "%g" % sz, pick, len(xs),
                    "%s of %s" % (med((x["cut"] for x in xs), 0),
                                  med((x["edges"] for x in xs), 0)),
                    med((x["flow_share"] for x in xs), 3),
                    med((-x["first_round"] for x in xs
                         if x["first_round"] is not None), 3),
                    med((-x["tail"] for x in xs if x["tail"] is not None), 3),
                    med((x["permanence_unbanded"] for x in xs), 2),
                    tally(x["permanence_state"] for x in xs),
                    count(xs, lambda x: x["flip"] == "block under")])
    md(["target", "share of edges", "pick", "cells", "edges cut",
        "share of inflow on them", "share lost, first round",
        "share lost, tail", "tail over first round", "states",
        "block below at close"], out)
    pairs = table(doc["sections"]["run"]["cut_pairs"])
    sets = table(doc["sections"]["run"]["cut_sets"])
    out = []
    for kind in TARGETS:
        for side_ in ("in", "out"):
            ps = [p for p in pairs if p["target"] == kind
                  and p["side"] == side_]
            ss = [s for s in sets if s["target"] == kind and s["side"] == side_]
            out.append([
                kind, side_, len(ps), tally(p["state"] for p in ps), len(ss),
                med((s["rank_loss_with_flow_share"] for s in ss), 3),
                med((s["rank_loss_with_edge_share"] for s in ss), 3),
                count(ss, lambda s: s["rank_loss_with_flow_share"] is not None
                      and s["rank_loss_with_edge_share"] is not None
                      and s["rank_loss_with_flow_share"]
                      > s["rank_loss_with_edge_share"]),
                med((s["loss_over_flow_share_median"] for s in ss), 3)])
    print("pairs (flow against random at the same share) and sets (the six "
          "cuts on one side of one target)\n")
    md(["target", "side", "pairs", "pair states", "sets",
        "rank corr. of loss with flow share, median",
        "with edge share, median", "sets where flow share ranks better",
        "loss over flow share, median"], out)
    odd = [p for p in pairs if p["state"] == "random pick loses more"]
    print("pairs where the random pick loses more, %d: %s\n" % (
        len(odd), tally("%s %s %g, floor %.2f, %s %s" % (
            p["target"], p["side"], p["size"], p["need"], p["stress"],
            p["authority"]) for p in odd)))
    print("### cut: out-edges, and in-edges put back\n")
    out = []
    for kind in TARGETS:
        for sz in sorted({x["size"] for x in cuts}):
            xs = [x for x in cuts if x["target"] == kind
                  and x["side"] == "out" and x["size"] == sz]
            out.append([
                kind, "out, both picks", "%g" % sz, len(xs),
                "%s of %s" % (med((x["cut"] for x in xs), 0),
                              med((x["edges"] for x in xs), 0)),
                med(x["tail"] for x in xs), rng(x["tail"] for x in xs),
                tally(x["tail_state"] for x in xs),
                med((x["other_end_cut_tail"] for x in xs), 3),
                med((x["other_end_kept_tail"] for x in xs), 3),
                count(xs, lambda x: x["flip"] == "block under")])
        for sz in sorted({x["size"] for x in cuts if x.get("restore")}):
            xs = [x for x in cuts if x["target"] == kind and x.get("restore")
                  and x["size"] == sz]
            out.append([
                kind, "in, by flow, put back", "%g" % sz, len(xs),
                "%s of %s" % (med((x["cut"] for x in xs), 0),
                              med((x["edges"] for x in xs), 0)),
                med((x["tail"] for x in xs), 6),
                rng((x["tail"] for x in xs), 6),
                tally(x["permanence_state"] for x in xs),
                med((x["peak"] for x in xs), 3), "-",
                count(xs, lambda x: x["flip"] == "block under")])
    md(["target", "arm", "share", "cells", "edges cut", "tail of own share",
        "range", "states", "other end of a cut edge (or deepest point)",
        "other end of a kept edge", "block below at close"], out)


def blocks(doc: dict) -> None:
    rows = arm_rows(doc)
    print("### blocks: fifty or more nodes more below the floor than the "
          "twin at the close\n")
    under = [x for x in rows if x["flip"] == "block under"]
    lifted = [x for x in rows if x["flip"] == "block lifted"]
    out = []
    keys = sorted({(x["need"], x["stress"], x["authority"]) for x in under})
    for need, stress, auth in keys:
        xs = [x for x in under if (x["need"], x["stress"], x["authority"])
              == (need, stress, auth)]
        cells = [x for x in rows if (x["need"], x["stress"], x["authority"])
                 == (need, stress, auth)]
        fam = []
        for label, pick in FAMILIES:
            n = count(xs, pick)
            if n:
                fam.append("%s %d of %d" % (label, n, count(cells, pick)))
        out.append(["%.2f" % need, stress, auth, len(xs), len(cells),
                    "; ".join(fam)])
    md(["floor", "strain", "authority", "cells with a block under",
        "of", "by penalty"], out)
    print("blocks lifted at the close: %d (%s)\n" % (len(lifted), tally(
        "%s, %s %s floor %.2f" % (x["arm"], x["stress"], x["authority"],
                                  x["need"]) for x in lifted)))
    print("where the nodes that went below the floor in a round their twin "
          "did not are, by penalty (cells): \n")
    out = []
    for label, pick in FAMILIES:
        xs = [x for x in rows if pick(x)]
        out.append([label, len(xs), tally(x["trigger"] for x in xs)])
    md(["penalty", "cells", "trigger"], out)


#: The arms the totals table sets side by side: one of each kind of penalty,
#: at a size where each has moved the target as far as it moves it.
TOTAL_ARMS = (
    ("fine, 0.9 of the balance, once, leaves the graph",
     lambda x: x["kind"] == "fine" and x["mode"] == "once"
     and x["size"] == 0.9 and x["sink"] == "destroy"),
    ("fine, 0.9 of the balance, once, returned",
     lambda x: x["kind"] == "fine" and x["mode"] == "once"
     and x["size"] == 0.9 and x["sink"] == "return"),
    ("cap at 0.5 of the balance", lambda x: x["kind"] == "cap"
     and x["size"] == 0.5),
    ("cap at 0.8 of the balance", lambda x: x["kind"] == "cap"
     and x["size"] == 0.8),
    ("cap at the balance", lambda x: x["kind"] == "cap" and x["size"] == 1.0),
    ("cut 0.3 of in-edges, by flow", lambda x: x["kind"] == "cut"
     and x["side"] == "in" and x["pick"] == "flow" and x["size"] == 0.3
     and not x.get("restore")),
    ("cut 0.3 of out-edges, by flow", lambda x: x["kind"] == "cut"
     and x["side"] == "out" and x["pick"] == "flow" and x["size"] == 0.3),
)


def totals(doc: dict) -> None:
    """What each penalty does to the two totals of the graph.

    The claims in trading accounts and the flow they carry, each as a ratio to
    the twin's over the tail. Two settings in which nothing issued refills a
    total in answer to the penalty: the main block with the authority off, and
    the growing block, where the issue per round is fixed. The strain whose
    twin is itself running down is left out, and so are the cells in which the
    capped node ends above its cap.
    """
    rows = [x for x in arm_rows(doc)
            if x.get("cap_state") != "above its cap to the end"]
    print("### totals: claims in trading accounts and total flow against the "
          "twin, over the tail\n")
    out = []
    for block, keep in (
            ("main", lambda x: x["authority"] == "none"
             and x["stress"] != "leak"),
            ("growth", lambda x: True)):
        for kind in TARGETS:
            for label, pick in TOTAL_ARMS:
                xs = [x for x in rows if x["block"] == block and keep(x)
                      and x["target"] == kind and pick(x)]
                if not xs:
                    continue
                out.append([
                    block, kind, label, len(xs),
                    med(x.get("fine_over_circulating") for x in xs),
                    med(x["circulating_tail_ratio"] for x in xs),
                    med(x["flow_tail_ratio"] for x in xs),
                    rng(x["flow_tail_ratio"] for x in xs),
                    med(x["tail"] for x in xs)])
    md(["block", "target", "penalty", "cells",
        "claims taken, share of trading accounts",
        "claims in trading accounts", "total flow", "range of total flow",
        "target's share, tail"], out)


TABLES = {"carrier": carrier, "side": side, "linear": linear,
          "incidence": incidence, "size": size, "cap": cap, "cut": cut,
          "blocks": blocks, "totals": totals}


def main() -> int:
    want = sys.argv[1:] or list(TABLES)
    unknown = [w for w in want if w not in TABLES]
    if unknown:
        print("unknown table %s; one of %s" % (unknown, list(TABLES)))
        return 2
    doc = load()
    crit = doc["sections"]["run"]["criteria"]
    print("record %s, stage %s, seeds %s; criteria: %s\n" % (
        RECORD.name, doc["stage"], doc["sections"]["run"]["seeds_run"],
        ", ".join("%s %s" % (c["name"].split()[0],
                             "PASS" if c["passed"] else "FAIL") for c in crit)))
    for name in want:
        TABLES[name](doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
