"""A22: force ``w = d phi`` on A3's live carrier and read what survives.

**Numbered A22 on 2026-09-01.** It ran under a placeholder token from
2026-08-30 to 2026-09-01. The station token lives in ``STATION`` below and every
criterion name, the record path and the printed headings are derived from it, so
the renumbering was one edit here plus two file renames. It was free because no
other document cited a criterion of this station by name, which is the condition
discipline 20 sets: criterion names are what other stations cite, so the number
has to be settled before anything cites one.

What this asks
--------------
A3's four-cycle is ``(a, cash) -> (a, q) -> (b, q) -> (b, cash)``, one tier and
two classes, and ``docs/a3_asset_channel.md`` states its value::

    w_a - w_b = log( gamma[b,q] / gamma[a,q] )

The price cancels entirely. Substituting the terms function
``gamma[i,q] = gbar[q] * (1 + kappa (1 - c_i))`` gives::

    w_a - w_b = log[ (1 + kappa (1 - c_b)) / (1 + kappa (1 - c_a)) ]

so ``kappa = 0`` makes the field exact: every class faces one function of
position, which is ``exact_field``'s ``W[a,i,j] = phi[j] - phi[i]``.

**Half of this station cannot fail and is labelled as such.** The treated arm's
holonomy is zero by that algebra, so A22-2 is a structural check on the code and
not a finding. Under D25 the treated square is degenerate outright: the first
term is flattened by the treatment and the two agent edges are zero by
``cochain_from_field``, so all three terms vanish, and a zero read on a
degenerate square carries no claim.

**The information is in A22-3 and A22-4**, which ask whether the support-set
readings survive the treatment. They are computed from realized flows and not
from the field, so the model has to be re-run rather than the statistic
recomputed, and both outcomes are reachable. If they collapse alongside the
holonomy, the executable form of the embedding corollary is refuted on this
carrier: the graph readings were being carried by the field.

Three knobs, and all three are needed
-------------------------------------
``terms_spread = 0``   flattens what is paid. This is the treatment.

``hold_mean_cost``     kappa = 0 also lowers the mean acquisition cost, from
                       1.5577 to 1.0667 on the registered profile, so without
                       this the flat cell is also the cheap cell and the reading
                       is a level effect. Held at ``mean_cost_reference``, which
                       defaults to the registered kappa, so the control arm is
                       the reference and is unchanged bitwise.

``gate_spread = 1.0``  pinned, because ``None`` ties admission to what is paid
                       and one switch would then move both H1 and H0. That is
                       the failure this project has already paid for twice.

Usage::

    python experiments/a22_exact_field.py
    python experiments/a22_exact_field.py --seeds 5 --rounds 300
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
# Both paths, and in this order, matching a1c_household_order.py. Without the
# second one the sibling import below fails depending on how this is launched,
# and the failure is at import time rather than in the run.
for _p in (ROOT / "src", ROOT / "experiments"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from a3_asset_channel import loop_sum_from_graph, terms_pair  # noqa: E402
from monetary_topology.asset import A3Config, A3Model, AssetSpec  # noqa: E402
from monetary_topology.network import NetworkConfig, NetworkSpec  # noqa: E402

#: The station token. Everything below derives from it, so a rename is one edit
#: here plus renaming this file and its record.
STATION = "A22"

OUT = ROOT / "results" / f"{STATION.lower()}_exact_field.json"

#: The registered kappa. Read from the dataclass rather than typed here, so the
#: control arm cannot drift away from the registered configuration silently.
KAPPA_REF = AssetSpec().terms_spread

#: The treatment. Not a tuned value: it is the only kappa at which the field is
#: exact, which is the whole content of the arm.
KAPPA_FLAT = 0.0

SEEDS = 5
ROUNDS = 300


@dataclass
class Criterion:
    name: str
    passed: bool
    detail: str
    #: Printed, never counted. A structural check or an identity.
    structural: bool = False

    def line(self) -> str:
        mark = "chk " if self.structural else ("pass" if self.passed else "FAIL")
        return f"  {mark}  {self.name}\n        {self.detail}"


def go(seed: int, rounds: int, **asset_kw):
    """Build, run, and keep BOTH the model and the history.

    ``a3_asset_channel.run`` is not reusable here: it returns the model and
    discards what ``Network.run`` returns, and this station needs both. The
    holonomy is read off the model's terms and the support set is read off the
    history, which is the whole point of the arm. Same two lines A3 uses, so the
    control arm is its configuration.
    """
    model = A3Model(
        A3Config(
            asset=AssetSpec(**asset_kw),
            network=NetworkConfig(
                spec=NetworkSpec(seed=seed), seed=seed, rounds=rounds
            ),
        )
    )
    history = model.run()
    return model, history


def arm(seed: int, rounds: int, *, treated: bool) -> dict:
    """One run, and the quantities read off it."""
    kw: dict = {}
    if treated:
        kw = {
            "terms_spread": KAPPA_FLAT,
            "hold_mean_cost": True,
            "mean_cost_reference": KAPPA_REF,
            # Pinned so the treatment moves what is paid and not who may enter.
            "gate_spread": KAPPA_REF,
        }
    model, h = go(seed, rounds, **kw)

    better, worse = terms_pair(model)
    delta, holonomy, price_free = loop_sum_from_graph(model, better, worse)

    vol_ratio, sup_ratio = h.divergence
    return {
        "seed": seed,
        "treated": treated,
        "holonomy": float(holonomy),
        "delta": float(delta),
        "price_free": float(price_free),
        "support_open": float(h.effective_support[0]),
        "support_close": float(h.effective_support[-1]),
        "support_ratio": float(sup_ratio),
        "volume_ratio": float(vol_ratio),
        "n_better": int(better.size),
        "n_worse": int(worse.size),
    }


def fixed(obj):
    """Round every float so two builds write the same bytes."""
    if isinstance(obj, float):
        return round(obj, 10)
    if isinstance(obj, dict):
        return {k: fixed(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [fixed(v) for v in obj]
    return obj


def criteria(control: list[dict], treated: list[dict]) -> list[Criterion]:
    out: list[Criterion] = []

    # -- A22-1 --------------------------------------------------------------
    # The control arm is `go(seed)` with no asset keywords, so it is A3's
    # registered configuration by construction. What is worth checking is the
    # thing that is NOT obvious: that the mean-cost control is a bitwise no-op
    # at the reference kappa, which is what lets the control arm stand as the
    # reference the treated arm is moved onto.
    probe = arm(control[0]["seed"], 30, treated=False)
    probe_held = arm_with(control[0]["seed"], 30,
                          terms_spread=KAPPA_REF, hold_mean_cost=True,
                          mean_cost_reference=KAPPA_REF, gate_spread=KAPPA_REF)
    same = all(
        probe[k] == probe_held[k]
        for k in ("holonomy", "delta", "support_close", "volume_ratio")
    )
    out.append(Criterion(
        f"{STATION}-1  the mean-cost control is a no-op at the reference kappa",
        same,
        "holonomy %.12e vs %.12e, support_close %.12f vs %.12f (30 rounds)"
        % (probe["holonomy"], probe_held["holonomy"],
           probe["support_close"], probe_held["support_close"]),
        structural=True,
    ))

    # -- A22-2 --------------------------------------------------------------
    # Zero by the algebra in the module docstring. Reported against the control
    # arm's own magnitude, which is the measured floor this zero is read at.
    hol_t = [r["holonomy"] for r in treated]
    hol_c = [r["holonomy"] for r in control]
    out.append(Criterion(
        f"{STATION}-2  the treated holonomy is zero  [STRUCTURAL, not a finding]",
        max(abs(v) for v in hol_t) < 1e-12,
        "treated max |holonomy| %.3e against control mean |holonomy| %.6f "
        "(control per seed: %s)"
        % (max(abs(v) for v in hol_t),
           float(np.mean([abs(v) for v in hol_c])),
           ", ".join("%.6f" % v for v in hol_c)),
        structural=True,
    ))

    # -- A22-3 --------------------------------------------------------------
    # The first reading with content. Three states, and the third exists.
    sup_c = [r["support_ratio"] for r in control]
    sup_t = [r["support_ratio"] for r in treated]
    contracts_c = sum(1 for v in sup_c if v < 1.0)
    contracts_t = sum(1 for v in sup_t if v < 1.0)
    out.append(Criterion(
        f"{STATION}-3  support-set contraction under the exact field",
        contracts_t == len(sup_t),
        "control contracts in %d/%d seeds (ratios %s); treated in %d/%d "
        "(ratios %s)"
        % (contracts_c, len(sup_c), ", ".join("%.4f" % v for v in sup_c),
           contracts_t, len(sup_t), ", ".join("%.4f" % v for v in sup_t)),
    ))

    # -- A22-4 --------------------------------------------------------------
    # Volume up while support down: the pair that carries the differential
    # claim, per NetworkHistory.divergence's own docstring.
    def both(r: dict) -> bool:
        return r["volume_ratio"] > 1.0 and r["support_ratio"] < 1.0

    n_c = sum(1 for r in control if both(r))
    n_t = sum(1 for r in treated if both(r))
    out.append(Criterion(
        f"{STATION}-4  volume rises while support falls, under the exact field",
        n_t == len(treated),
        "control %d/%d, treated %d/%d; treated (volume, support) = %s"
        % (n_c, len(control), n_t, len(treated),
           ", ".join("(%.3f, %.4f)" % (r["volume_ratio"], r["support_ratio"])
                     for r in treated)),
    ))
    return out


def arm_with(seed: int, rounds: int, **kw) -> dict:
    """``arm`` with explicit keywords, for the no-op probe."""
    model, h = go(seed, rounds, **kw)
    better, worse = terms_pair(model)
    delta, holonomy, price_free = loop_sum_from_graph(model, better, worse)
    vol_ratio, sup_ratio = h.divergence
    return {
        "holonomy": float(holonomy), "delta": float(delta),
        "support_close": float(h.effective_support[-1]),
        "volume_ratio": float(vol_ratio), "support_ratio": float(sup_ratio),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=SEEDS)
    ap.add_argument("--rounds", type=int, default=ROUNDS)
    args = ap.parse_args()

    print(f"\n{STATION}: forcing w = d phi on A3's carrier")
    print(f"  control  kappa = {KAPPA_REF}   (registered)")
    print(f"  treated  kappa = {KAPPA_FLAT}  + mean held at {KAPPA_REF}"
          f" + gate pinned at {KAPPA_REF}\n")

    control, treated = [], []
    # Print the stream rather than the summary: twenty lines returning the same
    # integer say stop at the third, and only a stream shows that.
    print("  seed   arm       holonomy      support 0 -> T        volume x")
    for seed in range(args.seeds):
        for flag, bucket in ((False, control), (True, treated)):
            r = arm(seed, args.rounds, treated=flag)
            bucket.append(r)
            print("  %4d   %-8s  %+.6f    %8.3f -> %8.3f   %6.3f"
                  % (seed, "treated" if flag else "control", r["holonomy"],
                     r["support_open"], r["support_close"], r["volume_ratio"]))

    crits = criteria(control, treated)
    print("\n  criteria\n")
    for c in crits:
        print(c.line())

    live = [c for c in crits if not c.structural]
    print("\n  %d/%d live criteria passed  (%d structural checks printed, "
          "never counted)\n" % (sum(c.passed for c in live), len(live),
                                len(crits) - len(live)))

    record = {
        "stage": STATION,
        "criteria": [
            {"name": c.name, "passed": c.passed, "detail": c.detail,
             "structural": c.structural} for c in crits
        ],
        "control": control,
        "treated": treated,
        "kappa_reference": KAPPA_REF,
        "kappa_flat": KAPPA_FLAT,
        "rounds": args.rounds,
        "seeds": args.seeds,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(
        json.dumps(fixed(record), indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8", newline="\n",
    )
    print(f"  wrote {OUT.relative_to(ROOT)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
