"""A27: tenure and the transfer of an industry, the slow-to-build half of an
industry's standing.

Block one, ``--part gates``. The supply switch is wired in: every member of an
industry carries a tenure ``s`` in [0, 1] that grows ``s += skill_rate (1 - s)``
each round and resets to zero when the member changes industry, and an
industry's deliverable capacity counts members at ``1 - supply_skill (1 - s)``
each. This part checks that the wiring is inert where it has to be and moves
where it has to move. No reading of the stage is taken here.

Criteria in this part, each with its kind:

* A27-0  ``IndustrySpec.replace`` lists every field. A hand written field list
  is what silently drops a new field back to its default (rule 19).
* A27-1  Every new switch at zero reproduces the build before this stage, all
  history fields bit for bit, run against the ``.expired`` copy of
  ``network.py`` taken immediately before the change.
* A27-1b The supply switch on while nobody changes industry reproduces the
  same build bit for bit. Every member then sits at tenure one, the weights
  are exact ones, and the new code path has to land on the old bytes.
* A27-1c Claims are conserved with the switch on and people moving.

Printed beside them and not scored: what the switch does when people do move
(D28, the treatment has to move something before anything it moves can be
read), per industry at the close.

Block two, ``--part jia2``, the rest of the supply side:

* A27-2a The premium form of the same switch, ``1 + b s`` with
  ``b = d / (1 - d)`` and the reference moved with it, lands on the shortfall
  form up to rounding. Run at ``d = 0.5``, where the factor between the two
  forms is a power of two, and at ``d = 0.25``, where it is four thirds.
* A27-2b The reference point does not cancel. The premium form measured from
  a newcomer (tenure starting at zero, reference the starting headcount) against
  the shortfall form measured from an established member, each against the
  switch off. Read on the delivery ratio the supply constraint applies, with
  total volume and the rest printed beside it.
* A27-8a A19-5 read again: what switching does, with the tenure switch at four
  settings. The zero setting has to reproduce A19's recorded rows.
* A27-8b A20's rank correlations read again with the tenure switch on. The zero
  setting has to reproduce A20's recorded values.

Block three, ``--part yi``, the transfer event:

* A scan of the subsistence need, printed, to find where the production layer
  is alive when the event lands (rule 13, step 1).
* A27-1d The event at its default reproduces the build before it, bit for bit.
* A27-3 The event's mechanical reach: every round before it is identical to the
  run without it, and in the round it lands the industry's capacity is exactly
  ``n - m_out + m_in (1 - d)``.
* A27-4 A membership transfer that moves no claim and keeps the headcount,
  read with switching off so the only thing separating the arms is tenure:
  every production industry, five seeds, three build rates, the shortfall form
  against the same transfer with tenure off.

Block four, ``--part yi2``, the same event with switching on, and a return:

* A27-4b The transfer with switching on, read as a double difference, tenure on
  against off by transfer on against off, so the churn switching produces on its
  own is taken out. Beside it, who leaves the transferred industry by switching
  after the event, newcomers and the members who stayed, and at what tenure.
* A27-7 The same people moved out at round 50 and moved back at round 100 or
  150, their tenure reset on each move, switching off. What is left at the
  close against the run with no transfer at all, printed beside the signal
  side's residual.
* A27-7c With no subsistence line, what is left in the transferred industry at
  the close is the rebuild clock and nothing else: the close-window delivery
  ratio against ``(n - m_out + m (1 - d (1 - eta)^(t - r))) / reference``, with
  ``r`` the round of the last move and ``m`` the people it put into the
  industry, in every cell.

Printed beside them and not scored (D28): what the relabel does to the layer's
capacity in the round it lands, with tenure off, so the only thing it moves is
headcount between industries.

Block five, ``--part bing``, the first block of the wall (A27-5): before any
tenure arm is run, a scan of the subsistence need for an environment in which
an industry weakened with tenure off comes back. The event moves a share of the
industry's live members to the rest of its layer and restaffs nothing, the
entry friction is zero, and switching is on at the base's rate, so the only way
back is people choosing to switch in. Printed, not scored: without such an
environment the tenure arms have one reachable outcome, and the design does not
open them.

Block six, ``--part bing2``: the scan found none, because switchers go only to
the layer's best-paid industry. A switch for the destination is added,
``switch_destination``, default ``"best"``; ``"proportional"`` opens every
industry of the layer that beats the mover's own by its entry threshold.

* A27-1e The destination switch at its default reproduces the build before it,
  bit for bit, with industries on, off, and under the weakening event.

Printed beside it, not scored: where the switches go under each rule, and the
weakening scan again with every better-paid industry open.

Block seven, ``--part bing3``: that scan found none either, because a payer's
channel into an industry is an edge to a person and moves with the person. A
switch for forming lost channels again at a finite rate is added,
``channel_rate``, default zero, the fixed graph.

* A27-1f Channel formation at its default reproduces the build before it, bit
  for bit, with industries on, off, and under the weakening event.

Printed beside it, not scored: the weakening scan with channels formed again at
three rates, and how much of the weakened industry's market comes back.

Block eight, ``--part bing4``, A27-5 itself, in the environment block seven
found: the weakened industry's recovery against the build rate, at each channel
rate, read against the tenure-off arm at the same rate.

* A27-5 The recovery curve over the build rate, printed with the paired signs
  cell by cell; step or slope is read off it.

Block nine, ``--part ding``, the demand side: regular customers. A buyer
splitting what it spends on an industry weighs each member there at
``1 - demand_skill (1 - s)``.

* A27-1g The demand switch at its default reproduces the build before it.
* A27-1b (demand half) The switch on while nobody moves reproduces it too.
* A27-2a (demand half) The premium form ``1 + b s`` lands on the shortfall
  form up to rounding: the split normalises within each industry.
* A27-6b The wall with the demand side alone: the weakened industry's
  recovery against the build rate, read against the tenure-off arm.

Block ten, ``--part ding2``, the rest of the demand side, no change to ``src``:

* A27-6c The transfer of block three with regular customers: exits and
  income by group, the people moved out, moved in, the stayers and the rest.
* A27-6a Of the people who move into a weakened industry, how many are
  switched out again and after how many rounds.

Each part writes its own section of ``results/a27_skill.json``. Exits non-zero
if a criterion fails.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import sys
import time
from dataclasses import fields
from importlib.machinery import SourceFileLoader
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RECORD = RESULTS / "a27_skill.json"
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from monetary_topology.config import WageChannel  # noqa: E402
from monetary_topology.industry import IndustrySpec, friction_vector  # noqa: E402
from monetary_topology.network import (  # noqa: E402
    Network,
    NetworkConfig,
    NetworkSpec,
    SubsistenceSpec,
)

# A19 is the carrier, and its constants and its comparison are imported, so
# this stage restates none of them (D5).
_a19 = SourceFileLoader("a19_for_a27", str(ROOT / "experiments" / "a19_industry.py")).load_module()
_a20 = SourceFileLoader("a20_for_a27", str(ROOT / "experiments" / "a20_formation_lag.py")).load_module()

#: The copy of ``network.py`` as it stood immediately before the tenure switch
#: was wired in. ``industry.py`` has its own copy with the same stamp; the old
#: ``network.py`` imports the current ``industry.py``, whose new fields all have
#: defaults and are never read by the old code.
BACKUP = "network.py.expired_20260910_072054_pre_A27"

#: The environment every run here uses: A19's live setting, subsistence line
#: at 0.0914 with a ten round grace, wage elasticity 0.10.
ENV = dict(_a19.LIVE)

#: A20's read point on A19's industry structure: supply constraint binding,
#: switching on, damage marked at 1.1 of the layer's mean size, entry friction
#: 1.0 and flat. The spread is A20's own treatment and this stage does not sit
#: on it.
BASE = dict(_a19.ON, supply_elasticity=1.0, switch_rate=0.2, switch_cost=0.3,
            min_share=_a19.MIN_SHARE, recovery_friction=1.0)

#: The tenure setting the gates run at. Any positive pair does for a gate; this
#: one sits inside the sweep the design registers.
SKILL = dict(supply_skill=0.5, skill_rate=0.03)

SEED = 0
DIGITS = 12

#: Part two. Five seeds (rule 12), and both of A20's environments: at 0.0914
#: most of the production layer is out by the close, at 0.06 it is neither full
#: nor empty, and a direction that holds in one and flips in the other is a
#: property of the point (D11).
SEEDS = (0, 1, 2, 3, 4)
ENVS = {label: dict(_a19.LIVE, **over) for label, over in _a20.ENVS.items()}

#: A27-2a runs the two forms at two shortfalls. At 0.5 the factor between them,
#: ``1 / (1 - d)``, is two, a power of two, so the scaling itself is exact; the
#: two forms still round their weights through different operations, so
#: agreement to the bit is not guaranteed even there. At 0.25 the factor is four
#: thirds. The criterion is agreement up to rounding at both, with no round on
#: which the two runs disagree about who is alive or where.
CANCEL_D = (0.25, 0.5)

#: The relative tolerance for "agrees up to rounding", the same constant and
#: meaning as the claim-conservation tolerance: floating point, nothing else.
REL_TOL = _a19.SFC_TOLERANCE

#: A27-2b and A27-8: one shortfall for the reference comparison, a sweep for
#: the re-reads, and one build rate throughout, the gates' own.
REF_D = 0.5
READ_D = (0.0, 0.25, 0.5, 0.75)
RATE = SKILL["skill_rate"]


@dataclasses.dataclass
class Criterion:
    name: str
    kind: str
    passed: bool
    detail: str


def _fmt(x):
    """Floats through an explicit spec, never repr (derived-file rule 5)."""
    if isinstance(x, bool) or x is None or isinstance(x, str):
        return x
    if isinstance(x, (float, np.floating)):
        return float(f"{float(x):.10f}")
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (list, tuple)):
        return [_fmt(v) for v in x]
    if isinstance(x, dict):
        return {str(k): _fmt(v) for k, v in x.items()}
    return x


def _config_diff(obj) -> dict:
    """Every dataclass field of ``obj`` that differs from its default (18d)."""
    out = {}
    for f in dataclasses.fields(obj):
        if not f.init:
            continue
        cur = getattr(obj, f.name)
        if f.default is not dataclasses.MISSING:
            dflt = f.default
        elif f.default_factory is not dataclasses.MISSING:
            dflt = f.default_factory()
        else:
            dflt = None
        if dataclasses.is_dataclass(cur) and not isinstance(cur, type):
            sub = _config_diff(cur)
            if sub:
                out[f.name] = sub
            continue
        if isinstance(cur, np.ndarray):
            continue
        try:
            same = bool(cur == dflt)
        except Exception:
            same = False
        if not same:
            out[f.name] = cur
    return out


#: The copy of ``network.py`` taken immediately before the transfer event.
BACKUP_YI = "network.py.expired_20260910_080345_pre_A27乙"


def load_backup_named(fname: str) -> object:
    """Load any ``.expired`` copy of ``network.py`` under its own module name."""
    path = SRC / "monetary_topology" / fname
    name = "monetary_topology._a27_" + str(abs(hash(fname)))
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


def load_backup() -> object:
    """The pre-A27 ``network.py`` as a module, loaded the way A19 loads its
    backups: package-qualified name so the relative imports resolve, and the
    loader named explicitly because the file extension is not one Python
    recognises."""
    path = SRC / "monetary_topology" / BACKUP
    name = "monetary_topology._a27_pre"
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod


def config_for(mod, industry: dict, seed: int = SEED, env: dict | None = None):
    env = ENV if env is None else env
    spec = mod.NetworkSpec(layer1_size=_a19.LAYER1_SIZE,
                           layer2_size=_a19.LAYER2_SIZE, seed=seed)
    return mod.NetworkConfig(
        spec=spec,
        rounds=_a19.ROUNDS,
        seed=seed,
        wages=WageChannel(elasticity=env["elasticity"]),
        subsistence=mod.SubsistenceSpec(need=env["need"], grace=env["grace"],
                                        mode=env["mode"]),
        industry=mod.IndustrySpec(**industry),
    )


def run(mod, industry: dict, seed: int = SEED):
    """One run on ``mod``'s own classes. Returns the history and the model."""
    m = mod.Network(config_for(mod, industry, seed))
    return m.run(), m


def conservation(h, initial: float) -> float:
    """Residual of claims held against claims made, over the whole run.

    ``frozen_holdings`` is left out of the held side. It is
    ``holdings[out_of_market].sum()``, a part of ``holdings`` measured on its
    own, so adding it counts the claims of every node that has left twice.
    A19's version of this function adds it, and there it is harmless: A19-3
    runs without the subsistence line, nothing is frozen, and the term is zero.
    Under the live setting this stage runs in, the same formula reports the
    frozen stock as a leak, which is why the gate uses this one and prints the
    other beside it.
    """
    held = float(np.asarray(h.holdings)[-1].sum()) + float(np.asarray(h.parked)[-1])
    made = (initial + float(np.asarray(h.issuance).sum())
            - float(np.asarray(h.written_off).sum()))
    return abs(held - made)


def capacity_ratios(m) -> dict:
    """Per industry at the close: headcount ratio and tenure-weighted ratio.

    The same two numbers ``_ration_supply`` would compute in the next round,
    read off the model's state, so the treatment's reach is printed as the
    object it acts through (rule 11)."""
    ind = m.config.industry
    g = np.asarray(m._industry_of)
    live = (g >= 0) & np.asarray(m._alive)
    ref = np.asarray(m._initial_agents, dtype=float)
    heads = np.bincount(g[live], minlength=ind.count).astype(float)
    if ind.supply_skill > 0.0:
        w = 1.0 - ind.supply_skill * (1.0 - np.asarray(m._tenure))
        cap = np.bincount(g[live], weights=w[live], minlength=ind.count)
    else:
        cap = heads.copy()
    with np.errstate(divide="ignore", invalid="ignore"):
        hr = np.where(ref > 0, heads / ref, 1.0)
        cr = np.where(ref > 0, cap / ref, 1.0)
    return dict(headcount_ratio=hr.tolist(), capacity_ratio=cr.tolist(),
                live_members=heads.astype(int).tolist())


def part_gates() -> dict:
    crit: list[Criterion] = []
    old = load_backup()
    cur = sys.modules["monetary_topology.network"]

    print("A27 block one: gates on the tenure switch (rule 19: run, do not derive)\n")

    # D38: the one-run cost is measured and printed. It stays out of the
    # record, because a wall-clock number in a checked-in file differs on
    # every run.
    t0 = time.perf_counter()
    h_cur, m_cur = run(cur, BASE)
    secs = time.perf_counter() - t0
    print(f"  one run of {_a19.ROUNDS} rounds on this machine: {secs:.1f} s\n")

    # A27-0
    declared = {f.name for f in fields(IndustrySpec)}
    listed = set(IndustrySpec(**BASE).replace().__dict__)
    ok0 = declared == listed
    crit.append(Criterion(
        "A27-0 replace() lists every field", "instrument", ok0,
        f"{len(listed)}/{len(declared)} fields carried"
        + ("" if ok0 else f"; missing {sorted(declared - listed)}")))

    # A27-1: every new switch at zero against the build before them, on two
    # configurations: the station's own, and one with the industry layer off,
    # which is what every station without industries runs through.
    h_old, _ = run(old, BASE)
    ok1, differ1, n1 = _a19.compare(h_old, h_cur)
    h_old0, _ = run(old, dict(count=0))
    h_cur0, _ = run(cur, dict(count=0))
    ok1z, differ1z, n1z = _a19.compare(h_old0, h_cur0)
    crit.append(Criterion(
        "A27-1 new switches at zero reproduce the pre-A27 build", "instrument",
        ok1 and ok1z,
        f"{n1 - len(differ1)}/{n1} history fields identical with industries on, "
        f"{n1z - len(differ1z)}/{n1z} with them off"
        + ("" if ok1 and ok1z else "; differ: " + ", ".join(differ1 + differ1z))))

    # A27-1b: the switch on, nobody changing industry.
    still = dict(BASE, switch_rate=0.0)
    h_old_still, _ = run(old, still)
    h_new_still, m_new_still = run(cur, dict(still, **SKILL))
    ok1b, differ1b, n1b = _a19.compare(h_old_still, h_new_still)
    tmin = float(np.min(m_new_still._tenure))
    crit.append(Criterion(
        "A27-1b supply switch on, nobody moves: pre-A27 build reproduced",
        "instrument", ok1b,
        f"{n1b - len(differ1b)}/{n1b} history fields identical at "
        f"supply_skill={SKILL['supply_skill']}, skill_rate={SKILL['skill_rate']}, "
        f"switch_rate=0; lowest tenure at close {tmin:.1f}"
        + ("" if ok1b else "; differ: " + ", ".join(differ1b))))

    # The switch on with people moving. Not a gate: this is the treatment
    # reaching its object, printed so a switch that moves nothing is seen.
    h_on, m_on = run(cur, dict(BASE, **SKILL))
    _, differ_on, n_on = _a19.compare(h_cur, h_on)
    ten = np.asarray(m_on._tenure)
    g_on = np.asarray(m_on._industry_of)
    live_on = (g_on >= 0) & np.asarray(m_on._alive)
    below = int(((ten < 1.0) & live_on).sum())
    vol_off = float(np.asarray(h_cur.total_volume).sum())
    vol_on = float(np.asarray(h_on.total_volume).sum())
    caps_off = capacity_ratios(m_cur)
    caps_on = capacity_ratios(m_on)
    moved = dict(
        fields_differing=len(differ_on), n_fields=n_on,
        switches_off=int(m_cur._switch_count), switches_on=int(m_on._switch_count),
        live_members_below_full_tenure=below,
        live_members=int(live_on.sum()),
        lowest_live_tenure=float(ten[live_on].min()) if live_on.any() else 1.0,
        total_volume_off=vol_off, total_volume_on=vol_on,
        total_volume_relative=(vol_on - vol_off) / vol_off if vol_off else 0.0,
        capacity_off=caps_off, capacity_on=caps_on,
    )

    # A27-1c: conservation with the switch on and people moving, and on the
    # still arm.
    initial = float(m_on.config.initial_claims)
    r_on = conservation(h_on, initial)
    r_still = conservation(h_new_still, initial)
    a19_on = _a19.conservation(h_on)
    a19_still = _a19.conservation(h_new_still)
    frozen_on = float(np.asarray(h_on.frozen_holdings)[-1])
    frozen_still = float(np.asarray(h_new_still.frozen_holdings)[-1])
    worst = max(r_on, r_still)
    crit.append(Criterion(
        "A27-1c claims conserved with the tenure switch on", "instrument",
        worst < _a19.SFC_TOLERANCE,
        f"residual below {_below(r_on)} with switching, below {_below(r_still)} without; "
        f"tolerance {_a19.SFC_TOLERANCE:.0e}"))

    for c in crit:
        print(f"  {'PASS' if c.passed else 'FAIL':4}  [{c.kind}]  {c.name}")
        print(f"        {c.detail}")

    print("\nthe switch with people moving (printed, not scored)")
    print(f"  history fields differing from the switch off: "
          f"{moved['fields_differing']}/{n_on}")
    print(f"  switches: off {moved['switches_off']}, on {moved['switches_on']}")
    print(f"  live members below full tenure at the close: {below} of "
          f"{moved['live_members']}, lowest {moved['lowest_live_tenure']:.4f}")
    print(f"  total volume: off {vol_off:,.2f}, on {vol_on:,.2f} "
          f"({moved['total_volume_relative']:+.4%})")
    print("  per industry at the close (headcount ratio / capacity ratio / live):")
    for k in range(len(caps_on["capacity_ratio"])):
        print(f"    ind {k:2d}  off {caps_off['headcount_ratio'][k]:.3f}"
              f" / {caps_off['capacity_ratio'][k]:.3f} / {caps_off['live_members'][k]:3d}"
              f"    on {caps_on['headcount_ratio'][k]:.3f}"
              f" / {caps_on['capacity_ratio'][k]:.3f} / {caps_on['live_members'][k]:3d}")

    print("\nconservation, two formulas")
    print(f"  held minus made, frozen counted once:  switching {r_on:.3e}, still {r_still:.3e}")
    print(f"  A19's formula, frozen added again:     switching {a19_on:.6f}, still {a19_still:.6f}")
    print(f"  frozen stock at the close:             switching {frozen_on:.6f}, still {frozen_still:.6f}")

    n_pass = sum(c.passed for c in crit)
    print(f"\n  {n_pass}/{len(crit)} criteria passed")
    return dict(
        criteria=[dict(name=c.name, kind=c.kind, passed=bool(c.passed),
                       detail=c.detail) for c in crit],
        backup_compared_against=BACKUP,
        gate_fields=dict(a27_1=[n1 - len(differ1), n1],
                         a27_1_industry_off=[n1z - len(differ1z), n1z],
                         a27_1b=[n1b - len(differ1b), n1b]),
        switch_with_movement=moved,
        conservation=dict(switching=r_on, still=r_still,
                          tolerance=_a19.SFC_TOLERANCE,
                          a19_formula_switching=a19_on,
                          a19_formula_still=a19_still,
                          frozen_close_switching=frozen_on,
                          frozen_close_still=frozen_still),
    )


class Recorder(Network):
    """The current model, recording what part two reads, and nothing else.

    Per round: who is alive and who is in which industry (A27-2a looks for the
    first round two runs disagree on either), and the delivery ratio the supply
    constraint applied, ``min(capacity / reference, 1)`` per industry with a
    positive reference (A27-2b reads it). The ratio is recomputed from the same
    state ``_ration_supply`` reads, just before it runs, and the call is then
    passed through, so recording moves nothing.
    """

    def __init__(self, config):
        super().__init__(config)
        self.rec_alive: list[np.ndarray] = []
        self.rec_industry: list[np.ndarray] = []
        self.rec_delivery: list[np.ndarray] = []
        self.rec_delivery_full: list[np.ndarray] = []
        self.rec_count: list[np.ndarray] = []
        self.rec_reference: np.ndarray | None = None
        self.rec_tenure: list[np.ndarray] = []

    def _ration_supply(self, matrix):
        ind = self.config.industry
        if ind.enabled and ind.supply_elasticity > 0.0:
            g = self._industry_of
            live = (g >= 0) & self._alive
            if ind.supply_skill > 0.0:
                w = self._skill_weights()
                cur = np.bincount(g[live], weights=w[live], minlength=ind.count)
            else:
                cur = np.bincount(g[live], minlength=ind.count).astype(float)
            ref = np.asarray(self._capacity_reference(), dtype=float)
            ratio = np.divide(cur, ref, out=np.ones(ind.count), where=ref > 0)
            self.rec_delivery.append(np.minimum(ratio, 1.0)[ref > 0])
            self.rec_delivery_full.append(np.minimum(ratio, 1.0))
            self.rec_count.append(np.asarray(cur, dtype=float).copy())
            self.rec_reference = ref
        return super()._ration_supply(matrix)

    def _post_round(self, t: int) -> None:
        super()._post_round(t)
        self.rec_alive.append(self._alive.copy())
        self.rec_industry.append(self._industry_of.copy())
        self.rec_tenure.append(self._tenure.copy())

    def _transfer_out(self) -> None:
        """Capture the industry's weighted count at the instant before the
        event, and the weight of the members about to leave, then pass on."""
        ind = self.config.industry
        k = int(ind.transfer_industry)
        live_k = (self._industry_of == k) & self._alive
        w = (self._skill_weights() if ind.supply_skill > 0.0
             else np.ones(self._n))
        self.rec_k_before = float(w[live_k].sum())
        members = np.flatnonzero(live_k)
        m = int(round(ind.transfer_share * members.size))
        self.rec_k_out_weight = float(w[members[:m]].sum())
        self.rec_route_before = np.array(self._route, copy=True)
        super()._transfer_out()
        self.rec_route_after = np.array(self._route, copy=True)


class PremiumEstablished(Recorder):
    """The premium form measured from an established member.

    A member weighs ``1 + b s`` with ``b = d / (1 - d)``, and the reference is
    ``1 + b`` times the starting headcount, which is the starting capacity
    because every member starts at one. The two forms then differ by the
    constant ``1 + b`` on both sides of the ratio.
    """

    def _premium(self) -> float:
        d = self.config.industry.supply_skill
        return d / (1.0 - d)

    def _skill_weights(self) -> np.ndarray:
        return 1.0 + self._premium() * self._tenure

    def _capacity_reference(self) -> np.ndarray:
        return (1.0 + self._premium()) * self._initial_agents


class PremiumFromZero(PremiumEstablished):
    """The premium form measured from a newcomer: every member starts at tenure
    zero, weighs one, and the reference is the starting headcount."""

    def __init__(self, config):
        super().__init__(config)
        self._tenure[:] = 0.0

    def _capacity_reference(self) -> np.ndarray:
        return self._initial_agents


def run_cls(cls, industry: dict, seed: int, env: dict):
    m = cls(config_for(sys.modules["monetary_topology.network"], industry, seed, env))
    return m.run(), m


def max_relative_difference(a, b) -> tuple[float, str | None]:
    """Largest relative difference over every numeric field of two histories."""
    worst, where = 0.0, None

    def one(name, x, y):
        nonlocal worst, where
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        if x.shape != y.shape:
            worst, where = float("inf"), name
            return
        if x.size == 0:
            return
        scale = max(float(np.abs(x).max()), float(np.abs(y).max()), 1e-300)
        r = float(np.abs(x - y).max()) / scale
        if r > worst:
            worst, where = r, name

    for f in fields(type(a)):
        x, y = getattr(a, f.name), getattr(b, f.name)
        if isinstance(x, dict):
            for k in x:
                one(f"{f.name}[{k}]", x[k], y[k])
        elif isinstance(x, (np.ndarray, float, int)) and not isinstance(x, bool):
            one(f.name, x, y)
    return worst, where


def first_split(m1, m2) -> int | None:
    """First round at which the two runs disagree on who is alive or where."""
    for t, (a1, a2, i1, i2) in enumerate(zip(m1.rec_alive, m2.rec_alive,
                                             m1.rec_industry, m2.rec_industry)):
        if not (np.array_equal(a1, a2) and np.array_equal(i1, i2)):
            return t
    return None


def summarize(h, m) -> dict:
    dl = np.concatenate(m.rec_delivery) if m.rec_delivery else np.zeros(0)
    g = np.asarray(m._industry_of)
    live = (g >= 0) & np.asarray(m._alive)
    return dict(
        total_volume=float(np.asarray(h.total_volume).sum()),
        mean_delivery=float(dl.mean()) if dl.size else 1.0,
        binding_share=float((dl < 1.0).mean()) if dl.size else 0.0,
        active_close=float(np.asarray(h.active_nodes)[-1]),
        l2_support_close=float(np.asarray(h.effective_support_l2)[-1]),
        live_close=int(live.sum()),
        switches=int(m._switch_count),
    )


def _signs(v) -> dict:
    pos = sum(1 for x in v if x > 0)
    neg = sum(1 for x in v if x < 0)
    return dict(positive=pos, zero=len(v) - pos - neg, negative=neg)


def _direction(s: dict) -> int:
    return (s["positive"] > s["negative"]) - (s["negative"] > s["positive"])


def part_jia2() -> dict:
    out: dict = {}
    crits: list[dict] = []
    print("A27 block two: the rest of the supply side\n")

    # ---- A27-2a: the constant cancels -----------------------------------
    print("A27-2a  premium form against shortfall form, reference moved with it")
    rows = []
    for d in CANCEL_D:
        ind = dict(BASE, supply_skill=d, skill_rate=RATE)
        for label, env in ENVS.items():
            for s_ in SEEDS:
                h1, m1 = run_cls(Recorder, ind, s_, env)
                h2, m2 = run_cls(PremiumEstablished, ind, s_, env)
                r, where = max_relative_difference(h1, h2)
                split = first_split(m1, m2)
                ok, differ, n = _a19.compare(h1, h2)
                state = ("bit-identical" if ok else
                         "within rounding" if split is None and r < REL_TOL else
                         "discrete split" if split is not None else
                         "beyond rounding")
                rows.append(dict(d=d, env=label, seed=s_, max_relative=r,
                                 worst_field=where, first_split=split,
                                 identical_fields=[n - len(differ), n], state=state))
                print(f"  d={d:<4} {label:24} seed {s_}  {state:15} "
                      f"max rel {r:.3e}  split {split}")
    states = {r["state"] for r in rows}
    if "beyond rounding" in states:
        passed, verdict = False, "FAIL: a difference beyond rounding with no discrete split"
    elif "discrete split" in states:
        passed, verdict = None, "not judged on the split cells, which are listed"
    else:
        passed, verdict = True, "PASS"
    by_d = {str(d): sorted({r["state"] for r in rows if r["d"] == d}) for d in CANCEL_D}
    crits.append(dict(
        name="A27-2a the premium form with its reference lands on the shortfall form",
        kind="instrument", passed=passed,
        detail=f"{verdict}; states by shortfall {by_d}; largest relative difference "
               f"below {_below(max(r['max_relative'] for r in rows))} over "
               f"{len(rows)} run pairs, tolerance {REL_TOL:.0e}"))
    out["A27-2a"] = dict(rows=rows, tolerance=REL_TOL)

    # ---- A27-2b: the reference point does not cancel -----------------------
    print("\nA27-2b  reference at the newcomer against reference at the established member")
    ind_on = dict(BASE, supply_skill=REF_D, skill_rate=RATE)
    keys = ("mean_delivery", "binding_share", "total_volume", "active_close",
            "l2_support_close", "live_close", "switches")
    per_env = {}
    for label, env in ENVS.items():
        table = []
        for s_ in SEEDS:
            c = summarize(*run_cls(Recorder, BASE, s_, env))
            e = summarize(*run_cls(Recorder, ind_on, s_, env))
            z = summarize(*run_cls(PremiumFromZero, ind_on, s_, env))
            table.append(dict(seed=s_, control=c,
                              established_minus_control={k: e[k] - c[k] for k in keys},
                              newcomer_minus_control={k: z[k] - c[k] for k in keys}))
        sig_e = {k: _signs([r["established_minus_control"][k] for r in table]) for k in keys}
        sig_z = {k: _signs([r["newcomer_minus_control"][k] for r in table]) for k in keys}
        de, dz = _direction(sig_e["mean_delivery"]), _direction(sig_z["mean_delivery"])
        allzero = all(r["established_minus_control"]["mean_delivery"] == 0.0
                      and r["newcomer_minus_control"]["mean_delivery"] == 0.0
                      for r in table)
        state = ("identical" if allzero else
                 "reversed" if de * dz < 0 else
                 "same sign" if de == dz and de != 0 else "mixed")
        per_env[label] = dict(rows=table, signs_established=sig_e,
                              signs_newcomer=sig_z, state=state)
        print(f"  {label}: state {state}")
        print("    seed  d(delivery) est / new     d(volume) est / new       "
              "d(active) est / new")
        for r in table:
            ee, zz = r["established_minus_control"], r["newcomer_minus_control"]
            print(f"    {r['seed']:<4}  {ee['mean_delivery']:+.5f} / {zz['mean_delivery']:+.5f}"
                  f"    {ee['total_volume']:+11.2f} / {zz['total_volume']:+11.2f}"
                  f"    {ee['active_close']:+5.0f} / {zz['active_close']:+5.0f}")
        for k in keys:
            print(f"    {k:>17}  established {sig_e[k]['positive']}+ {sig_e[k]['zero']}0 "
                  f"{sig_e[k]['negative']}-   newcomer {sig_z[k]['positive']}+ "
                  f"{sig_z[k]['zero']}0 {sig_z[k]['negative']}-")
    st = {lb: v["state"] for lb, v in per_env.items()}
    p2b = (True if all(s in ("reversed", "same sign") for s in st.values()) else None)
    crits.append(dict(
        name="A27-2b the reference point does not cancel",
        kind="own_reading", passed=p2b,
        detail=f"state on the delivery ratio by environment {st}",
        note=("printed object, no line drawn (rule 11). Mapping: reversed or same "
              "sign reads that the reference point is load-bearing; identical or "
              "mixed is not judged")))
    out["A27-2b"] = per_env

    # ---- A27-8a: A19-5 read again -----------------------------------------
    print("\nA27-8a  A19-5 again: switching on against off, tenure switch at "
          f"{list(READ_D)}")
    base5 = dict(_a19.ON, supply_elasticity=1.0)
    treat5 = dict(base5, switch_rate=0.2, switch_cost=0.3)
    rnd = lambda q: {a: round(b, DIGITS) if isinstance(b, float) else b for a, b in q.items()}
    ctrl = {s_: rnd(_a19.quantities(*_a19.run_full(base5, s_, _a19.LIVE))) for s_ in SEEDS}
    by_d = {}
    for d in READ_D:
        ind = dict(treat5, supply_skill=d, skill_rate=RATE if d > 0 else 0.0)
        rows8 = []
        for s_ in SEEDS:
            t_ = rnd(_a19.quantities(*_a19.run_full(ind, s_, _a19.LIVE)))
            rows8.append({k: round(t_[k] - ctrl[s_][k], DIGITS) for k in _a19.READ}
                         | {"seed": s_, "switches_treat": t_["switches"],
                            "switches_control": ctrl[s_]["switches"]})
        by_d[str(d)] = dict(rows=rows8,
                            signs={k: _signs([r[k] for r in rows8]) for k in _a19.READ})
        vol = [r["total_volume"] for r in rows8]
        print(f"  d={d:<5} total volume  " + " ".join(f"{v:+11.1f}" for v in vol)
              + f"   switches {[r['switches_treat'] for r in rows8]}")
    recorded = json.loads((RESULTS / "a19_directions.json").read_text(encoding="utf-8"))
    rec_rows = recorded["readings"]["A19-5 switching"]["rows"]
    mine = by_d["0.0"]["rows"]
    same = all(all(m[k] == r[k] for k in (*_a19.READ, "switches_treat", "switches_control"))
               for m, r in zip(mine, rec_rows))
    crits.append(dict(
        name="A27-8z A19-5 reproduced at tenure switch zero", kind="instrument",
        passed=same,
        detail=f"{len(mine)} seeds x {len(_a19.READ)} quantities and the switch counts, "
               f"against results/a19_directions.json"))
    crits.append(dict(
        name="A27-8a what switching does with the tenure switch on",
        kind="own_reading",
        detail={d: v["signs"] for d, v in by_d.items()},
        note="printed object, no line drawn (rule 11); the reading is how the signs "
             "and the size of the switching effect move along the sweep"))
    out["A27-8a"] = by_d

    # ---- A27-8b: A20's rank correlations read again ------------------------
    print("\nA27-8b  A20's rank correlations with the tenure switch on")
    ind20 = dict(_a20.BASE, recovery_friction=_a20.FRICTION,
                 friction_spread=_a20.SPREAD)
    fv = friction_vector(IndustrySpec(**ind20))
    rho: dict = {}
    for label, env in ENVS.items():
        rho[label] = {}
        for d in (0.0, REF_D):
            ind = dict(ind20, supply_skill=d, skill_rate=RATE if d > 0 else 0.0)
            per = {"hot": [], "damaged_rounds": [], "damaged": []}
            for s_ in SEEDS:
                h, m = _a19.run_full(ind, s_, env)
                g = np.asarray(m._industry_of)
                hot = np.asarray(m._last_inflow) > float(h.epsilon_absolute)
                dd = np.asarray(m._damaged_for, dtype=float)
                hc = np.array([int(((g == i) & hot).sum()) for i in range(int(ind["count"]))],
                              dtype=float)
                per["hot"].append(round(_a20.spearman(fv, hc), DIGITS))
                per["damaged_rounds"].append(round(_a20.spearman(fv, np.where(dd >= 0, dd, 0.0)), DIGITS))
                per["damaged"].append(round(_a20.spearman(fv, (dd >= 0).astype(float)), DIGITS))
            rho[label][str(d)] = per
            print(f"  {label:24} d={d:<4} " + "  ".join(
                f"{k} " + " ".join(f"{x:+.3f}" for x in v) for k, v in per.items()))
    rec20 = json.loads((RESULTS / "a20_formation_lag.json").read_text(encoding="utf-8"))
    rec_rho = rec20["readings"]["A20-6 rank correlation"]
    same20 = all(rho[lb]["0.0"][k] == rec_rho[lb][k] for lb in ENVS for k in rec_rho[lb])
    crits.append(dict(
        name="A27-8y A20's rank correlations reproduced at tenure switch zero",
        kind="instrument", passed=same20,
        detail="three quantities x five seeds x two environments, against "
               "results/a20_formation_lag.json"))
    crits.append(dict(
        name="A27-8b A20's rank correlations with the tenure switch on",
        kind="own_reading",
        detail={lb: {q: _signs(v[str(REF_D)][q]) for q in v[str(REF_D)]}
                for lb, v in rho.items()},
        note="printed object, no line drawn (rule 11); the reading is whether the "
             "damage correlations keep their sign and whether the member count "
             "picks up one"))
    out["A27-8b"] = rho

    print()
    for c in crits:
        tag = {True: "PASS", False: "FAIL", None: "----"}.get(c.get("passed"), "----")
        print(f"  {tag:4}  [{c['kind']}]  {c['name']}")
    return dict(criteria=crits, readings=out)


#: Part three. The scan that picks where the event lands: at 0.0914 the
#: production layer is gone by round 150 whatever else is set, so an event
#: there lands on nothing.
NEED_SCAN = (0.0914, 0.06, 0.04, 0.02, 0.0)

#: The two environments the transfer is read in, picked off the scan. At 0.06
#: the subsistence line is live, and the population has settled by round 50,
#: so an exit after the event is an exit the event caused. At zero there is no
#: line and nobody can leave, so whatever persists cannot be an exit.
YI_ENVS = {"need=0.06": dict(_a19.LIVE, need=0.06),
           "no line, need=0": dict(_a19.LIVE, need=0.0)}

#: The event: half of one production industry's live members reassigned at
#: round 50 and the industry restaffed from the rest of its layer. Every
#: production industry takes a turn, so no single one carries the reading
#: (A20's half-sum lesson).
YI_AT = 50
YI_SHARE = 0.5
YI_INDUSTRIES = tuple(range(int(_a19.ON["financial_count"]), int(_a19.ON["count"])))
YI_RATES = (0.01, 0.03, 0.1)
YI_D = 0.5

#: Windows of 25 rounds, the one before the event and ten after it.
WINDOW = 25

#: Wall-clock budget for one invocation. The runs are cached, so a part that
#: runs out of budget stops, says so, and resumes where it left off.
BUDGET_S = 140.0
CACHE = RESULTS / "a27_cache.json"


def yi_industry(k: int, d: float, eta: float, share: float = YI_SHARE,
                transfer: bool = True, switch_rate: float = 0.0,
                back_round: int = -1) -> dict:
    ind = dict(BASE, switch_rate=switch_rate, supply_skill=d,
               skill_rate=eta if d > 0 else 0.0)
    if transfer:
        ind.update(transfer_share=share, transfer_round=YI_AT,
                   transfer_industry=k, transfer_replace=True)
        if back_round >= 0:
            ind.update(transfer_back_round=back_round)
    return ind


#: Fields added to ``IndustrySpec`` after the cache was first written. At their
#: default they stay out of the key, so the summaries already on disk keep their
#: address; a gate checks that the default reproduces the build before the field
#: went in, which is what makes the old summaries still the right ones.
_KEY_NEW_DEFAULTS = {"switch_destination": "best", "channel_rate": 0.0,
                     "channel_conserve_degree": False, "demand_skill": 0.0}


def cache_key(ind: dict, seed: int, env: dict, tag: str) -> str:
    spec = IndustrySpec(**ind)
    parts = [f"{f.name}={getattr(spec, f.name)!r}" for f in fields(IndustrySpec)
             if not (f.name in _KEY_NEW_DEFAULTS
                     and getattr(spec, f.name) == _KEY_NEW_DEFAULTS[f.name])]
    parts += [f"env.{k}={env[k]!r}" for k in sorted(env)]
    parts += [f"seed={seed}", f"rounds={_a19.ROUNDS}", f"tag={tag}"]
    return "|".join(parts)


def load_cache() -> dict:
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def save_cache(c: dict) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(c, indent=1, sort_keys=True) + "\n",
                     encoding="utf-8", newline="\n")


def windows(x: np.ndarray) -> list[float]:
    """Mean of ``x`` over the window before the event and the ten after it."""
    x = np.asarray(x, dtype=float)
    out = [float(x[YI_AT - WINDOW:YI_AT].mean())]
    for i in range((len(x) - YI_AT) // WINDOW):
        a = YI_AT + i * WINDOW
        out.append(float(x[a:a + WINDOW].mean()))
    return out


def yi_summary(h, m, k: int | None) -> dict:
    alive = np.array(m.rec_alive)
    q = dict(
        vol_windows=windows(h.total_volume),
        volume_post=float(np.asarray(h.total_volume)[YI_AT:].sum()),
        alive_before=int(alive[YI_AT - 1].sum()),
        alive_close=int(alive[-1].sum()),
        moved=int(m._transfer_count),
    )
    if k is not None:
        dl = np.array(m.rec_delivery_full)
        cnt = np.array(m.rec_count)
        ind_path = np.array(m.rec_industry)
        g_before = ind_path[YI_AT - 1]
        members = int(((g_before == k) & alive[YI_AT - 1]).sum())
        hold = np.asarray(h.holdings, dtype=float)
        tot = hold.sum(axis=1)
        k_now = (ind_path == k) & alive
        share = np.where(tot > 0, (hold * k_now).sum(axis=1) / np.where(tot > 0, tot, 1.0), 0.0)
        # Who leaves after the event: the industry's members as the event left
        # them, the people it moved out, and everyone else.
        after = ind_path[YI_AT] == k
        out_nodes = (m._transfer_moved[0] if m._transfer_moved is not None
                     else np.zeros(0, dtype=int))
        moved_out = np.zeros(m._n, dtype=bool)
        moved_out[out_nodes] = True
        left = alive[YI_AT - 1] & ~alive[-1]
        q.update(
            k_delivery_windows=windows(dl[:, k]),
            k_holdings_share_windows=windows(share),
            k_count_before=float(cnt[YI_AT - 1, k]),
            k_count_at=float(cnt[YI_AT, k]),
            k_members_before=members,
            k_reference=float(np.asarray(m.rec_reference)[k]),
            exits_in_industry=int((left & after).sum()),
            exits_moved_out=int((left & moved_out).sum()),
            exits_elsewhere=int((left & ~after & ~moved_out).sum()),
        )
        if m._transfer_moved is not None:
            out_nodes, in_nodes, _ = m._transfer_moved
            q.update(m_out=int(out_nodes.size), m_in=int(in_nodes.size))
    return {a: (round(b, DIGITS) if isinstance(b, float) else
                [round(v, DIGITS) for v in b] if isinstance(b, list) else b)
            for a, b in q.items()}


def part_yi() -> dict:
    t_start = time.perf_counter()
    cache = load_cache()
    out: dict = {}
    crits: list[dict] = []
    print("A27 block three: the transfer event\n")

    def get(tag, ind, seed, env, k):
        key = cache_key(ind, seed, env, tag)
        if key not in cache:
            if time.perf_counter() - t_start > BUDGET_S:
                raise TimeoutError
            h, m = run_cls(Recorder, ind, seed, env)
            cache[key] = yi_summary(h, m, k)
        return cache[key]

    try:
        # ---- the scan ------------------------------------------------------
        scan = {}
        for sw in (0.0, 0.2):
            for need in NEED_SCAN:
                env = dict(_a19.LIVE, need=need)
                cells = []
                for s_ in SEEDS:
                    q = get("scan", dict(BASE, switch_rate=sw), s_, env, None)
                    cells.append([q["alive_before"], q["alive_close"]])
                scan[f"switch {sw} need {need}"] = cells
        # ---- the transfer grid ---------------------------------------------
        grid = {}
        for label, env in YI_ENVS.items():
            for k in YI_INDUSTRIES:
                for s_ in SEEDS:
                    grid[(label, k, s_, 0.0)] = get("yi2", yi_industry(k, 0.0, 0.0), s_, env, k)
                    for eta in YI_RATES:
                        grid[(label, k, s_, eta)] = get("yi2", yi_industry(k, YI_D, eta), s_, env, k)
            for s_ in SEEDS:
                grid[(label, "none", s_, 0.0)] = get("yi2", yi_industry(0, 0.0, 0.0, transfer=False),
                                                     s_, env, None)
    except TimeoutError:
        save_cache(cache)
        print(f"  budget of {BUDGET_S:.0f} s reached with {len(cache)} runs cached; "
              "run the same command again to continue")
        return {}
    save_cache(cache)

    print("need scan, alive before round 50 / at the close, five seeds")
    for lb, cells in scan.items():
        print(f"  {lb:22} " + "  ".join(f"{a}/{b}" for a, b in cells))
    out["need_scan"] = scan

    # ---- A27-1d: the event at its default against the build before it -----
    old = load_backup_named(BACKUP_YI)
    cur = sys.modules["monetary_topology.network"]
    h_o, _ = run(old, BASE)
    h_n, _ = run(cur, BASE)
    ok1, d1, n1 = _a19.compare(h_o, h_n)
    h_o0, _ = run(old, dict(count=0))
    h_n0, _ = run(cur, dict(count=0))
    ok2, d2, n2 = _a19.compare(h_o0, h_n0)
    crits.append(dict(
        name="A27-1d the transfer event at its default reproduces the build before it",
        kind="instrument", passed=bool(ok1 and ok2),
        detail=f"{n1 - len(d1)}/{n1} history fields with industries on, "
               f"{n2 - len(d2)}/{n2} with them off, against {BACKUP_YI}"))

    # ---- A27-3: every round before the event is identical, and the capacity
    # arithmetic in the round it lands ------------------------------------
    env = YI_ENVS["need=0.06"]
    pre_ok, arith_ok, arith_rows = True, True, []
    for k in YI_INDUSTRIES:
        ind_on = yi_industry(k, YI_D, 0.03)
        h_on, m_on = run_cls(Recorder, ind_on, SEEDS[0], env)
        h_off, m_off = run_cls(Recorder, yi_industry(k, YI_D, 0.03, transfer=False),
                               SEEDS[0], env)
        for f in fields(type(h_on)):
            x, y = getattr(h_on, f.name), getattr(h_off, f.name)
            if isinstance(x, np.ndarray) and x.ndim >= 1 and x.shape[0] == _a19.ROUNDS:
                if not np.array_equal(x[:YI_AT], y[:YI_AT]):
                    pre_ok = False
        out_nodes, in_nodes, _ = m_on._transfer_moved
        n_before = m_on.rec_k_before
        expect = n_before - m_on.rec_k_out_weight + in_nodes.size * (1.0 - YI_D)
        got = float(np.array(m_on.rec_count)[YI_AT, k])
        arith_rows.append(dict(industry=k, count_before=n_before, m_out=int(out_nodes.size),
                               m_in=int(in_nodes.size), expected=expect, got=got))
        arith_ok = arith_ok and (got == expect)
    crits.append(dict(
        name="A27-3a every round before the event is identical to the run without it",
        kind="instrument", passed=pre_ok,
        detail=f"all per-round history fields over rounds 0 to {YI_AT - 1}, "
               f"{len(YI_INDUSTRIES)} industries, seed {SEEDS[0]}, need=0.06"))
    crits.append(dict(
        name="A27-3b capacity in the round the event lands is n - m_out + m_in (1 - d)",
        kind="instrument", passed=arith_ok,
        detail=f"exact equality in {len(arith_rows)} of {len(arith_rows)} industries"
        if arith_ok else "mismatch, see rows"))
    out["A27-3"] = arith_rows
    print("\n  A27-3b  moved out / in and capacity before -> in the event round, seed 0, need=0.06")
    for r in arith_rows:
        print(f"    ind {r['industry']:2d}  {r['m_out']:2d}/{r['m_in']:2d}   "
              f"{r['count_before']:.2f} -> {r['got']:.2f}  (expected {r['expected']:.2f})")

    # ---- A27-4: the reading ---------------------------------------------
    reading = {}
    for label, env in YI_ENVS.items():
        reading[label] = {}
        for eta in YI_RATES:
            cells = []
            for k in YI_INDUSTRIES:
                for s_ in SEEDS:
                    c = grid[(label, k, s_, 0.0)]
                    tr = grid[(label, k, s_, eta)]
                    dv = [a - b for a, b in zip(tr["vol_windows"], c["vol_windows"])]
                    rel = [(a - b) / b if b else 0.0
                           for a, b in zip(tr["vol_windows"], c["vol_windows"])]
                    dk = [a - b for a, b in zip(tr["k_delivery_windows"], c["k_delivery_windows"])]
                    dh = [a - b for a, b in zip(tr["k_holdings_share_windows"],
                                                c["k_holdings_share_windows"])]
                    cells.append(dict(
                        industry=k, seed=s_,
                        d_volume_post=tr["volume_post"] - c["volume_post"],
                        rel_first=rel[1], rel_last=rel[-1], d_pre=dv[0],
                        d_k_first=dk[1], d_k_last=dk[-1],
                        d_share_first=dh[1], d_share_last=dh[-1],
                        d_exits_in_industry=tr["exits_in_industry"] - c["exits_in_industry"],
                        d_exits_moved_out=tr["exits_moved_out"] - c["exits_moved_out"],
                        d_exits_elsewhere=tr["exits_elsewhere"] - c["exits_elsewhere"],
                        d_exits=(tr["alive_before"] - tr["alive_close"])
                                - (c["alive_before"] - c["alive_close"]),
                        k_members=c["k_members_before"], m_out=tr.get("m_out", 0)))
            dvp = [x["d_volume_post"] for x in cells]
            shrink = sum(1 for x in cells if abs(x["rel_last"]) < abs(x["rel_first"]))
            grow = sum(1 for x in cells if abs(x["rel_last"]) > abs(x["rel_first"]))
            state = ("narrows" if shrink > grow else "widens" if grow > shrink
                     else "holds")
            summ = dict(
                cells=len(cells),
                pre_window_all_zero=all(x["d_pre"] == 0.0 for x in cells),
                volume_post=_signs(dvp),
                rel_first_median=float(np.median([x["rel_first"] for x in cells])),
                rel_last_median=float(np.median([x["rel_last"] for x in cells])),
                shrinking=shrink, growing=grow, state=state,
                k_delivery_first_median=float(np.median([x["d_k_first"] for x in cells])),
                k_delivery_last_median=float(np.median([x["d_k_last"] for x in cells])),
                exits=_signs([x["d_exits"] for x in cells]),
                exits_total=int(sum(x["d_exits"] for x in cells)),
                exits_split=dict(
                    in_industry=int(sum(x["d_exits_in_industry"] for x in cells)),
                    moved_out=int(sum(x["d_exits_moved_out"] for x in cells)),
                    elsewhere=int(sum(x["d_exits_elsewhere"] for x in cells))),
                share_first_median=float(np.median([x["d_share_first"] for x in cells])),
                share_last_median=float(np.median([x["d_share_last"] for x in cells])),
                share_last=_signs([x["d_share_last"] for x in cells]))
            reading[label][str(eta)] = dict(summary=summ, cells=cells)
    out["A27-4"] = reading
    print("\nA27-4  tenure's cost of a transfer: d=0.5 minus d=0, same transfer, switching off")
    for label in YI_ENVS:
        print(f"  {label}")
        print("    eta    post volume +/0/-   rel gap first -> last (median)   "
              "shrink/grow  state     k delivery first -> last    exits +/0/- (total)"
              "   exits in k / moved out / elsewhere   k holdings share first -> last (median, last +/0/-)")
        for eta in YI_RATES:
            s = reading[label][str(eta)]["summary"]
            print(f"    {eta:<5}  {s['volume_post']['positive']:2d}/{s['volume_post']['zero']:2d}/"
                  f"{s['volume_post']['negative']:2d}        "
                  f"{s['rel_first_median']:+.4f} -> {s['rel_last_median']:+.4f}          "
                  f"{s['shrinking']:2d}/{s['growing']:2d}      {s['state']:9}"
                  f"{s['k_delivery_first_median']:+.4f} -> {s['k_delivery_last_median']:+.4f}"
                  f"      {s['exits']['positive']}/{s['exits']['zero']}/{s['exits']['negative']}"
                  f" ({s['exits_total']:+d})"
                  f"      {s['exits_split']['in_industry']:+d} / {s['exits_split']['moved_out']:+d}"
                  f" / {s['exits_split']['elsewhere']:+d}"
                  f"        {s['share_first_median']:+.5f} -> {s['share_last_median']:+.5f}"
                  f" ({s['share_last']['positive']}/{s['share_last']['zero']}/{s['share_last']['negative']})")
    pre_zero = all(reading[lb][str(e)]["summary"]["pre_window_all_zero"]
                   for lb in YI_ENVS for e in YI_RATES)
    crits.append(dict(
        name="A27-4 a transfer that moves no claim and keeps the headcount, read through tenure",
        kind="own_reading",
        detail={lb: {str(e): reading[lb][str(e)]["summary"]["state"] for e in YI_RATES}
                for lb in YI_ENVS},
        pre_window_identical=pre_zero,
        note="printed object, no line drawn (rule 11). The state per build rate is "
             "the majority of cells whose relative volume gap is smaller in its last "
             "window than in its first (narrows), larger (widens), or neither "
             "(holds), whatever the gap's sign; every cell is in the record"))
    print()
    for c in crits:
        tag = {True: "PASS", False: "FAIL", None: "----"}.get(c.get("passed"), "----")
        print(f"  {tag:4}  [{c['kind']}]  {c['name']}")
    print(f"\n  {len(cache)} runs cached, {time.perf_counter() - t_start:.0f} s this call")
    return dict(criteria=crits, readings=out)


#: Part four. Switching on for A27-4b at the base's own rate, and two return
#: rounds for A27-7, fifty and a hundred rounds after the event.
YI2_SWITCH = BASE["switch_rate"]
YI2_BACK = (100, 150)

#: The signal side's residual, for the printout only: after a broadcast is
#: switched off the effect it had keeps about one and a half per cent of itself
#: (A24, the build-and-tear-down arm). Not a threshold on anything here.
SIGNAL_RESIDUAL = 0.015


def churn_summary(h, m, k: int) -> dict:
    """``yi_summary`` plus who leaves the industry by switching after the event."""
    q = yi_summary(h, m, k)
    ind_path = np.array(m.rec_industry)
    ten = np.array(m.rec_tenure)
    alive = np.array(m.rec_alive)
    out_nodes, in_nodes, _ = (m._transfer_moved if m._transfer_moved is not None
                              else (np.zeros(0, dtype=int),) * 3)
    before = (ind_path[YI_AT - 1] == k) & alive[YI_AT - 1]
    stayed = np.flatnonzero(before & ~np.isin(np.arange(m._n), out_nodes))

    def leaves(nodes):
        rounds, tenure = [], []
        for v in nodes:
            idx = np.flatnonzero(ind_path[YI_AT:, v] != k)
            if idx.size:
                t_ = YI_AT + int(idx[0])
                rounds.append(t_ - YI_AT)
                tenure.append(round(float(ten[t_ - 1, v]), DIGITS))
        return rounds, tenure

    r_in, s_in = leaves(in_nodes)
    r_st, s_st = leaves(stayed)
    q.update(newcomers=int(in_nodes.size), newcomers_left=len(r_in),
             newcomer_leave_rounds=r_in, newcomer_leave_tenure=s_in,
             incumbents=int(stayed.size), incumbents_left=len(r_st),
             incumbent_leave_tenure=s_st,
             k_live_close=int(((ind_path[-1] == k) & alive[-1]).sum()),
             k_live_before=int(before.sum()))
    return q


def base_summary(h, m, k=None) -> dict:
    """``yi_summary`` for a run with no event, plus every industry's delivery
    windows, so a transferred industry can be read against itself untouched."""
    q = yi_summary(h, m, None)
    dl = np.array(m.rec_delivery_full)
    q["all_delivery_windows"] = [[round(v, DIGITS) for v in windows(dl[:, j])]
                                 for j in range(dl.shape[1])]
    return q


def event_summary(h, m, k=None) -> dict:
    """Headcount and capped capacity over the production layer in the round
    before the event and the round it lands. With tenure off the weighted
    count is the headcount, and the capacity the supply constraint can use is
    ``min(count, reference)`` per industry: members above an industry's
    reference add nothing, members below it take capacity away."""
    cnt = np.array(m.rec_count)
    ref = np.asarray(m.rec_reference, dtype=float)
    alive = np.array(m.rec_alive)
    ind_path = np.array(m.rec_industry)
    prod = np.arange(int(_a19.ON["financial_count"]), int(_a19.ON["count"]))
    out = {}
    for tag_, t_ in (("before", YI_AT - 1), ("at", YI_AT)):
        c = cnt[t_, prod]
        out[tag_] = dict(headcount=round(float(c.sum()), DIGITS),
                         capped=round(float(np.minimum(c, ref[prod]).sum()), DIGITS),
                         above=int((c > ref[prod]).sum()),
                         below=int((c < ref[prod]).sum()))
    # Where the headcount went, and who leaves afterwards: the people the
    # event did not move, by the industry they sit in, and the people it moved.
    out["delta"] = [int(round(float(x))) for x in cnt[YI_AT, prod] - cnt[YI_AT - 1, prod]]
    left = alive[YI_AT - 1] & ~alive[-1]
    kept = ind_path[YI_AT] == ind_path[YI_AT - 1]
    out["stayer_exits"] = [int((left & kept & (ind_path[YI_AT] == j)).sum()) for j in prod]
    out["mover_exits"] = int((left & ~kept).sum())
    # The routing either side of the event. A payer gives each industry a share
    # of its intermediate spending set by what its own industry needs from that
    # industry, whatever the headcount there, and splits the share among its
    # neighbours in it; every row is normalised. Relabelling one node changes
    # how many of each of its payers' neighbours sit in the old industry and the
    # new one, so everyone else's share in those two moves with it, and the
    # node's own spending follows its new industry. A column sum is a node's
    # weight summed over the rows that pay it.
    rb = getattr(m, "rec_route_before", None)
    if rb is not None:
        ra = m.rec_route_after
        d_col = ra.sum(axis=0) - rb.sum(axis=0)
        st_live = kept & alive[YI_AT - 1] & (ind_path[YI_AT] >= int(_a19.ON["financial_count"]))
        eps = 1e-12
        out["route"] = dict(
            mass_moved=round(float(0.5 * np.abs(ra - rb).sum()), DIGITS),
            rows=int((rb.sum(axis=1) > 0).sum()),
            stayers=int(st_live.sum()),
            stayers_down=int((st_live & (d_col < -eps)).sum()),
            stayers_up=int((st_live & (d_col > eps)).sum()),
            stayer_exits_down=int((left & st_live & (d_col < -eps)).sum()),
            stayer_exits_up=int((left & st_live & (d_col > eps)).sum()),
            stayer_exits_flat=int((left & st_live & (np.abs(d_col) <= eps)).sum()))
    return out


def _below(x: float) -> str:
    """The smallest power of ten above a rounding residue, as text. A residue's
    own digits belong to the machine that ran it, so the record carries the
    bound it sits under and not the digits (derived-file rules 5 and 6)."""
    if x <= 0.0:
        return "0"
    return f"1e{int(np.ceil(np.log10(x)))}"


def _quint(v) -> list[float]:
    return [round(float(x), 4) for x in np.quantile(v, [0.0, 0.25, 0.5, 0.75, 1.0])] if len(v) else []


def part_yi2() -> dict:
    t_start = time.perf_counter()
    cache = load_cache()
    out: dict = {}
    crits: list[dict] = []
    print("A27 block four: switching on, and a return\n")

    def get(tag, ind, seed, env, k, summ):
        key = cache_key(ind, seed, env, tag)
        if key not in cache:
            if time.perf_counter() - t_start > BUDGET_S:
                raise TimeoutError
            h, m = run_cls(Recorder, ind, seed, env)
            cache[key] = summ(h, m, k)
        return cache[key]

    churn, trip, event = {}, {}, {}
    try:
        env_ev = YI_ENVS["need=0.06"]
        event["none"] = get("yi2ev3", yi_industry(0, 0.0, 0.0, transfer=False),
                            SEED, env_ev, None, event_summary)
        for k in YI_INDUSTRIES:
            event[k] = get("yi2ev3", yi_industry(k, 0.0, 0.0), SEED, env_ev, k,
                           event_summary)
        for label, env in YI_ENVS.items():
            for s_ in SEEDS:
                for d, eta in [(0.0, 0.0)] + [(YI_D, e) for e in YI_RATES]:
                    churn[(label, "none", s_, eta if d else 0.0)] = get(
                        "yi2c", yi_industry(0, d, eta, transfer=False, switch_rate=YI2_SWITCH),
                        s_, env, 0, churn_summary)
                trip[(label, "none", s_)] = get(
                    "yi2base", yi_industry(0, 0.0, 0.0, transfer=False), s_, env, None,
                    base_summary)
                for k in YI_INDUSTRIES:
                    for d, eta in [(0.0, 0.0)] + [(YI_D, e) for e in YI_RATES]:
                        churn[(label, k, s_, eta if d else 0.0)] = get(
                            "yi2c", yi_industry(k, d, eta, switch_rate=YI2_SWITCH),
                            s_, env, k, churn_summary)
                        for r2 in (-1,) + YI2_BACK:
                            trip[(label, k, s_, eta if d else 0.0, r2)] = get(
                                "yi2", yi_industry(k, d, eta, back_round=r2),
                                s_, env, k, yi_summary)
    except TimeoutError:
        save_cache(cache)
        print(f"  budget of {BUDGET_S:.0f} s reached with {len(cache)} runs cached; "
              "run the same command again to continue")
        return {}
    save_cache(cache)

    # ---- A27-4b: the double difference with switching on -------------------
    b4 = {}
    print("A27-4b  switching on: (tenure on - off) x (transfer on - off), per cell")
    for label in YI_ENVS:
        b4[label] = {}
        for eta in YI_RATES:
            cells = []
            for k in YI_INDUSTRIES:
                for s_ in SEEDS:
                    T1, N1 = churn[(label, k, s_, eta)], churn[(label, "none", s_, eta)]
                    T0, N0 = churn[(label, k, s_, 0.0)], churn[(label, "none", s_, 0.0)]
                    def ex(q):
                        return q["alive_before"] - q["alive_close"]
                    cells.append(dict(
                        industry=k, seed=s_,
                        did_volume_post=(T1["volume_post"] - N1["volume_post"])
                                        - (T0["volume_post"] - N0["volume_post"]),
                        did_exits=(ex(T1) - ex(N1)) - (ex(T0) - ex(N0)),
                        d_k_first=T1["k_delivery_windows"][1] - T0["k_delivery_windows"][1],
                        d_k_last=T1["k_delivery_windows"][-1] - T0["k_delivery_windows"][-1],
                        newcomers=T1["newcomers"],
                        newcomers_left_on=T1["newcomers_left"],
                        newcomers_left_off=T0["newcomers_left"],
                        incumbents=T1["incumbents"],
                        incumbents_left_on=T1["incumbents_left"],
                        incumbents_left_off=T0["incumbents_left"],
                        leave_tenure_newcomers=T1["newcomer_leave_tenure"],
                        leave_tenure_incumbents=T1["incumbent_leave_tenure"],
                        k_live_close_on=T1["k_live_close"], k_live_close_off=T0["k_live_close"],
                        k_live_before=T1["k_live_before"],
                        transfer_exits_on=ex(T1) - ex(N1),
                        transfer_exits_off=ex(T0) - ex(N0)))
            nl_on = sum(c["newcomers_left_on"] for c in cells)
            nl_off = sum(c["newcomers_left_off"] for c in cells)
            il_on = sum(c["incumbents_left_on"] for c in cells)
            il_off = sum(c["incumbents_left_off"] for c in cells)
            nn = sum(c["newcomers"] for c in cells)
            ni = sum(c["incumbents"] for c in cells)
            lt_n = [x for c in cells for x in c["leave_tenure_newcomers"]]
            lt_i = [x for c in cells for x in c["leave_tenure_incumbents"]]
            summ = dict(
                did_volume_post=_signs([c["did_volume_post"] for c in cells]),
                did_exits=_signs([c["did_exits"] for c in cells]),
                did_exits_total=int(sum(c["did_exits"] for c in cells)),
                k_delivery_first_median=float(np.median([c["d_k_first"] for c in cells])),
                k_delivery_last_median=float(np.median([c["d_k_last"] for c in cells])),
                newcomers=nn, newcomers_left=[nl_on, nl_off],
                incumbents=ni, incumbents_left=[il_on, il_off],
                newcomer_leave_tenure_quintiles=_quint(lt_n),
                incumbent_leave_tenure_quintiles=_quint(lt_i),
                k_live_close=[int(sum(c["k_live_close_on"] for c in cells)),
                              int(sum(c["k_live_close_off"] for c in cells)),
                              int(sum(c["k_live_before"] for c in cells))],
                k_live_on_minus_off=_signs([c["k_live_close_on"] - c["k_live_close_off"]
                                            for c in cells]),
                # The two single differences the double difference is made of:
                # what the transfer does to exits with tenure on and with it
                # off, each against the run with no transfer at the same setting.
                transfer_exits=[int(sum(c["transfer_exits_on"] for c in cells)),
                                int(sum(c["transfer_exits_off"] for c in cells))],
                transfer_exits_off=_signs([c["transfer_exits_off"] for c in cells]))
            b4[label][str(eta)] = dict(summary=summ, cells=cells)
        print(f"  {label}")
        print("    eta    DiD post volume +/0/-   DiD exits +/0/- (total)   "
              "k delivery on-off first -> last   newcomers left on/off of n   "
              "incumbents left on/off of n   k live at close on/off/before")
        for eta in YI_RATES:
            s = b4[label][str(eta)]["summary"]
            print(f"    {eta:<5}  {s['did_volume_post']['positive']:2d}/{s['did_volume_post']['zero']:2d}/"
                  f"{s['did_volume_post']['negative']:2d}              "
                  f"{s['did_exits']['positive']:2d}/{s['did_exits']['zero']:2d}/{s['did_exits']['negative']:2d}"
                  f" ({s['did_exits_total']:+d})          "
                  f"{s['k_delivery_first_median']:+.4f} -> {s['k_delivery_last_median']:+.4f}"
                  f"            {s['newcomers_left'][0]}/{s['newcomers_left'][1]} of {s['newcomers']}"
                  f"                  {s['incumbents_left'][0]}/{s['incumbents_left'][1]} of {s['incumbents']}"
                  f"               {s['k_live_close'][0]}/{s['k_live_close'][1]}/{s['k_live_close'][2]}")
            print(f"           tenure at leaving, newcomers {s['newcomer_leave_tenure_quintiles']}"
                  f"  incumbents {s['incumbent_leave_tenure_quintiles']}")
            print(f"           the transfer's own exits, tenure on/off: "
                  f"{s['transfer_exits'][0]:+d}/{s['transfer_exits'][1]:+d}"
                  f" (tenure off by cell +/0/-: {s['transfer_exits_off']['positive']}/"
                  f"{s['transfer_exits_off']['zero']}/{s['transfer_exits_off']['negative']});"
                  f"  k live at close, on-off by cell +/0/-: {s['k_live_on_minus_off']['positive']}/"
                  f"{s['k_live_on_minus_off']['zero']}/{s['k_live_on_minus_off']['negative']}")
    out["A27-4b"] = b4
    crits.append(dict(
        name="A27-4b the transfer with switching on, as a double difference",
        kind="own_reading",
        detail={lb: {str(e): dict(did_exits_total=b4[lb][str(e)]["summary"]["did_exits_total"],
                                  transfer_exits=b4[lb][str(e)]["summary"]["transfer_exits"],
                                  newcomers_left=b4[lb][str(e)]["summary"]["newcomers_left"],
                                  incumbents_left=b4[lb][str(e)]["summary"]["incumbents_left"])
                     for e in YI_RATES} for lb in YI_ENVS},
        note="printed object, no line drawn (rule 11); transfer_exits, "
             "newcomers_left and incumbents_left are [tenure on, tenure off] summed "
             "over the cells, and did_exits_total is the first transfer_exits minus "
             "the second"))

    # ---- A27-7: the round trip ---------------------------------------------
    r7 = {}
    print("\nA27-7  out at round 50, back at round 100 or 150, switching off; "
          "gaps against no transfer at all")
    for label in YI_ENVS:
        r7[label] = {}
        for r2 in (-1,) + YI2_BACK:
            r7[label][str(r2)] = {}
            for eta in (0.0,) + YI_RATES:
                cells = []
                for k in YI_INDUSTRIES:
                    for s_ in SEEDS:
                        tr, base = trip[(label, k, s_, eta, r2)], trip[(label, "none", s_)]
                        rel = [(a - b) / b if b else 0.0
                               for a, b in zip(tr["vol_windows"], base["vol_windows"])]
                        cells.append(dict(
                            industry=k, seed=s_, rel_first=rel[1], rel_close=rel[-1],
                            d_exits=(tr["alive_before"] - tr["alive_close"])
                                    - (base["alive_before"] - base["alive_close"]),
                            k_delivery_close=tr["k_delivery_windows"][-1],
                            d_k_close=tr["k_delivery_windows"][-1]
                                      - base["all_delivery_windows"][k][-1],
                            exits_in_industry=tr["exits_in_industry"],
                            exits_moved_out=tr["exits_moved_out"],
                            exits_elsewhere=tr["exits_elsewhere"],
                            base_exits=base["alive_before"] - base["alive_close"]))
                ratio = [abs(c["rel_close"]) / abs(c["rel_first"])
                         for c in cells if c["rel_first"] != 0.0]
                summ = dict(
                    rel_first_median=float(np.median([c["rel_first"] for c in cells])),
                    rel_close_median=float(np.median([c["rel_close"] for c in cells])),
                    residual_ratio_median=float(np.median(ratio)) if ratio else float("nan"),
                    exits=_signs([c["d_exits"] for c in cells]),
                    exits_total=int(sum(c["d_exits"] for c in cells)),
                    k_delivery_close_median=float(np.median([c["k_delivery_close"] for c in cells])),
                    d_k_close_median=float(np.median([c["d_k_close"] for c in cells])),
                    d_k_close=_signs([c["d_k_close"] for c in cells]),
                    # Where the exits fall, one-way only: a return clears the
                    # record of who was moved, so after one the people moved out
                    # are counted with everyone else and the split is not defined.
                    exits_split=(dict(
                        in_industry=int(sum(c["exits_in_industry"] for c in cells)),
                        moved_out=int(sum(c["exits_moved_out"] for c in cells)),
                        elsewhere=int(sum(c["exits_elsewhere"] for c in cells)),
                        untouched=int(sum(c["base_exits"] for c in cells)))
                        if r2 < 0 else None))
                r7[label][str(r2)][str(eta)] = dict(summary=summ, cells=cells)
        print(f"  {label}")
        print("    back      eta          volume gap first window -> close (median)   "
              "|close|/|first| (median)   exits vs no transfer +/0/- (total)   "
              "industry's delivery at close vs untouched (median, +/0/-)")
        for r2 in (-1,) + YI2_BACK:
            for eta in (0.0,) + YI_RATES:
                s = r7[label][str(r2)][str(eta)]["summary"]
                tag = "tenure off" if eta == 0.0 else f"{eta}"
                back = "one-way" if r2 < 0 else str(r2)
                print(f"    {back:<9} {tag:<12} {s['rel_first_median']:+.4f} -> {s['rel_close_median']:+.4f}"
                      f"                     {s['residual_ratio_median']:.3f}"
                      f"                     {s['exits']['positive']:2d}/{s['exits']['zero']:2d}/"
                      f"{s['exits']['negative']:2d} ({s['exits_total']:+d})"
                      f"                    {s['d_k_close_median']:+.4f} "
                      f"({s['d_k_close']['positive']}/{s['d_k_close']['zero']}/{s['d_k_close']['negative']})")
    print(f"\n  signal side, for comparison: a broadcast keeps about "
          f"{SIGNAL_RESIDUAL:.1%} of its effect once it is off (A24)")
    out["A27-7"] = r7
    crits.append(dict(
        name="A27-7 the round trip: what is left at the close against no transfer",
        kind="own_reading",
        detail={lb: {r2: {e: dict(
                    exits_total=r7[lb][r2][e]["summary"]["exits_total"],
                    d_k_close_median=r7[lb][r2][e]["summary"]["d_k_close_median"],
                    rel_close_median=r7[lb][r2][e]["summary"]["rel_close_median"])
                    for e in r7[lb][r2]} for r2 in r7[lb]} for lb in r7},
        note="printed object, no line drawn (rule 11); per environment, return round "
             "(-1 one-way) and build rate (0.0 tenure off): exits against no transfer "
             "summed over the cells, and the medians over cells of the transferred "
             "industry's delivery gap and of the relative volume gap in the close "
             "window. The close-over-first ratio stays in the readings and is not "
             "read: in the tenure-off rows with no line its denominator is a first-"
             "window volume gap of about two in ten thousand, and it is a ratio of "
             "volume, a different quantity from the support size A24's residual is "
             "measured on"))

    # ---- A27-7c: with no line, the residual is the rebuild clock ------------
    lab0 = "no line, need=0"
    lo = YI_AT + ((_a19.ROUNDS - YI_AT) // WINDOW - 1) * WINDOW
    tt = np.arange(lo, lo + WINDOW, dtype=float)
    clock, worst, ncell = {}, 0.0, 0
    for eta in YI_RATES:
        for r2 in (-1,) + YI2_BACK:
            diffs = []
            for k in YI_INDUSTRIES:
                for s_ in SEEDS:
                    one, tr = trip[(lab0, k, s_, eta, -1)], trip[(lab0, k, s_, eta, r2)]
                    n, ref = tr["k_members_before"], tr["k_reference"]
                    m_out, m_in = one["m_out"], one["m_in"]
                    r = YI_AT if r2 < 0 else r2
                    fresh = m_in if r2 < 0 else m_out
                    w = 1.0 - YI_D * (1.0 - eta) ** (tt - r)
                    pred = float(np.mean((n - m_out + fresh * w) / ref))
                    diffs.append(abs(tr["k_delivery_windows"][-1] - pred))
            clock[f"{r2}|{eta}"] = max(diffs)
            worst, ncell = max(worst, max(diffs)), ncell + len(diffs)
    print(f"\nA27-7c  no line: the transferred industry's close-window delivery "
          f"against the rebuild clock, {ncell} cells, largest difference {worst:.1e}")
    out["A27-7c"] = dict(largest_difference_below={a: _below(b) for a, b in clock.items()},
                         window=[int(lo), int(lo + WINDOW - 1)])
    crits.append(dict(
        name="A27-7c with no line, what is left at the close is the rebuild clock",
        kind="instrument", passed=bool(worst <= REL_TOL),
        detail=f"{ncell} cells (three build rates, one-way and two return rounds, "
               f"14 industries, 5 seeds); largest |observed - clock| below "
               f"{_below(worst)}; tolerance {REL_TOL:.0e}",
        note="clock: (n - m_out + m (1 - d (1 - eta)^(t - r))) / reference averaged "
             "over the close window, r the round of the last move and m the people "
             "it put into the industry; the observed value is rounded to 12 digits "
             "in the cache"))

    # ---- printed, not scored (D28): the relabel's reach at the event -------
    print("\nprinted, not scored (D28): the relabel alone, tenure off, need=0.06, "
          f"seed {SEED}, production layer, in the round the event lands")
    print("    industry   headcount before/at   capped capacity before/at (lost)   "
          "above/below reference   industries losing, same, gaining headcount (net)   "
          "exits of people not moved, in those three groups, transfer vs no event   "
          "exits of people moved")
    ev_rows = {}
    base_st = np.array(event["none"]["stayer_exits"])
    groups_sum = np.zeros((3, 2), dtype=int)
    mover_sum = 0
    for k in YI_INDUSTRIES:
        e_ = event[k]
        lost = e_["before"]["capped"] - e_["at"]["capped"]
        dl = np.array(e_["delta"])
        st = np.array(e_["stayer_exits"])
        grp = [dl < 0, dl == 0, dl > 0]
        g_tr = [int(st[g].sum()) for g in grp]
        g_ba = [int(base_st[g].sum()) for g in grp]
        for i_ in range(3):
            groups_sum[i_] += (g_tr[i_], g_ba[i_])
        mover_sum += e_["mover_exits"]
        ev_rows[str(k)] = dict(e_, lost=round(lost, DIGITS),
                               stayer_exits_by_group=dict(losing=[g_tr[0], g_ba[0]],
                                                          same=[g_tr[1], g_ba[1]],
                                                          gaining=[g_tr[2], g_ba[2]]))
        print(f"    {k:>8}   {e_['before']['headcount']:.0f}/{e_['at']['headcount']:.0f}"
              f"               {e_['before']['capped']:.0f}/{e_['at']['capped']:.0f} ({lost:.0f})"
              f"                    {e_['at']['above']}/{e_['at']['below']}"
              f"                   {int(grp[0].sum())}, {int(grp[1].sum())}, {int(grp[2].sum())}"
              f" ({int(dl[dl < 0].sum()):+d}/{int(dl[dl > 0].sum()):+d})"
              f"                          {g_tr[0]}/{g_ba[0]}, {g_tr[1]}/{g_ba[1]}, {g_tr[2]}/{g_ba[2]}"
              f"                               {e_['mover_exits']}")
    e_ = event["none"]
    print(f"    no event   {e_['before']['headcount']:.0f}/{e_['at']['headcount']:.0f}"
          f"               {e_['before']['capped']:.0f}/{e_['at']['capped']:.0f}"
          f"                        {e_['at']['above']}/{e_['at']['below']}")
    print(f"    summed over the 14: people not moved, losing {groups_sum[0][0]}/{groups_sum[0][1]}, "
          f"same {groups_sum[1][0]}/{groups_sum[1][1]}, gaining {groups_sum[2][0]}/{groups_sum[2][1]}; "
          f"people moved {mover_sum}")
    print("    the routing either side of the event, production-layer people not moved:")
    print("    industry   routing mass moved (of rows)   their weight down/up (of n)   "
          "exits among them: weight down / up / unchanged")
    rt_sum = np.zeros(5, dtype=int)
    for k in YI_INDUSTRIES:
        rt = event[k]["route"]
        rt_sum += (rt["stayers_down"], rt["stayers_up"], rt["stayer_exits_down"],
                   rt["stayer_exits_up"], rt["stayer_exits_flat"])
        print(f"    {k:>8}   {rt['mass_moved']:.3f} ({rt['rows']})"
              f"                   {rt['stayers_down']}/{rt['stayers_up']} ({rt['stayers']})"
              f"                   {rt['stayer_exits_down']} / {rt['stayer_exits_up']} / {rt['stayer_exits_flat']}")
    print(f"    summed: weight down {rt_sum[0]}, up {rt_sum[1]}; exits {rt_sum[2]} / {rt_sum[3]} / {rt_sum[4]}")
    out["event_capacity"] = dict(
        rows=ev_rows, untouched=e_, env="need=0.06", seed=SEED,
        stayer_exits_summed=dict(losing=groups_sum[0].tolist(), same=groups_sum[1].tolist(),
                                 gaining=groups_sum[2].tolist()),
        mover_exits_summed=int(mover_sum),
        route_summed=dict(stayers_down=int(rt_sum[0]), stayers_up=int(rt_sum[1]),
                          exits_down=int(rt_sum[2]), exits_up=int(rt_sum[3]),
                          exits_flat=int(rt_sum[4])))

    print()
    for c in crits:
        print(f"  ----  [{c['kind']}]  {c['name']}")
    print(f"\n  {len(cache)} runs cached, {time.perf_counter() - t_start:.0f} s this call")
    return dict(criteria=crits, readings=out)


#: Part five. The weakening event of A27-5: a share of one production
#: industry's live members moved to the rest of the layer at round 50 and
#: nobody moved in. Entry friction zero, so a damaged mark charges nothing extra
#: and the only barrier left is the switching rule itself: movers go to the
#: best-paid industry of their layer when the gain clears the switching cost.
BING_NEEDS = NEED_SCAN
BING_SHARES = (0.5, 0.9)
BING_BASE = dict(BASE, recovery_friction=0.0)


def bing_industry(k: int, share: float, d: float = 0.0, eta: float = 0.0,
                  weaken: bool = True) -> dict:
    ind = dict(BING_BASE, supply_skill=d, skill_rate=eta if d > 0 else 0.0)
    if weaken:
        ind.update(transfer_share=share, transfer_round=YI_AT,
                   transfer_industry=k, transfer_replace=False)
    return ind


def bing_summary(h, m, k=None) -> dict:
    """The weakened industry's path, who came into it after the event, and the
    event's own reach. With ``k`` None, every industry's path, for the run with
    no event that each weakened run is read against."""
    alive = np.array(m.rec_alive)
    ind_path = np.array(m.rec_industry)
    dl = np.array(m.rec_delivery_full)
    count = dl.shape[1]

    def live(j):
        return ((ind_path == j) & alive).sum(axis=1).astype(float)

    q = dict(alive_before=int(alive[YI_AT - 1].sum()), alive_close=int(alive[-1].sum()),
             vol_windows=windows(h.total_volume))
    if k is None:
        q.update(
            live_before=[int(live(j)[YI_AT - 1]) for j in range(count)],
            live_close=[int(live(j)[-1]) for j in range(count)],
            live_windows=[windows(live(j)) for j in range(count)],
            delivery_windows=[windows(dl[:, j]) for j in range(count)])
    else:
        lk = live(k)
        out_nodes = (m._transfer_moved[0] if m._transfer_moved is not None
                     else np.zeros(0, dtype=int))
        joined = (ind_path[YI_AT + 1:] == k).any(axis=0) & (ind_path[YI_AT] != k)
        back = joined & np.isin(np.arange(m._n), out_nodes)
        rb = getattr(m, "rec_route_before", None)
        ra = getattr(m, "rec_route_after", None)
        q.update(
            k_live_before=int(lk[YI_AT - 1]), k_live_at=int(lk[YI_AT]),
            k_live_close=int(lk[-1]), k_live_windows=windows(lk),
            k_delivery_before=float(dl[YI_AT - 1, k]), k_delivery_at=float(dl[YI_AT, k]),
            k_delivery_windows=windows(dl[:, k]),
            m_out=int(out_nodes.size), joined=int(joined.sum()),
            joined_moved_out=int(back.sum()),
            route_mass_moved=float(0.5 * np.abs(ra - rb).sum()) if rb is not None else 0.0)
    return _round_tree(q)


def _round_tree(x):
    if isinstance(x, float):
        return round(x, DIGITS)
    if isinstance(x, list):
        return [_round_tree(v) for v in x]
    if isinstance(x, dict):
        return {a: _round_tree(b) for a, b in x.items()}
    return x


class InflowRecorder(Recorder):
    """``Recorder`` that also keeps every node's inflow each round, the one
    signal the switching rule reads, so who can be moved into is printable."""

    def __init__(self, config):
        super().__init__(config)
        self.rec_inflow: list[np.ndarray] = []

    def _post_round(self, t: int) -> None:
        super()._post_round(t)
        li = self._last_inflow
        self.rec_inflow.append(np.zeros(self._n) if li is None else np.array(li, copy=True))


def mech_summary(h, m, k) -> dict:
    """Where the weakened industry stands on the switching rule's own scale:
    the mean inflow of the live members of each production industry, the
    layer's best, and in how many rounds after the event the weakened industry
    is the best (the only industry anyone can switch into)."""
    alive = np.array(m.rec_alive)
    ind_path = np.array(m.rec_industry)
    inflow = np.array(m.rec_inflow)
    lower = np.concatenate([m._mid, m._l2]).astype(int)
    rows = []
    for t in range(YI_AT - 1, _a19.ROUNDS):
        nodes = lower[alive[t, lower]]
        gs = ind_path[t, nodes]
        keep = gs >= 0
        nodes, gs = nodes[keep], gs[keep]
        uniq = np.unique(gs)
        means = {int(g): float(inflow[t, nodes[gs == g]].mean()) for g in uniq}
        best = max(means, key=means.get) if means else -1
        order = sorted(means, key=means.get, reverse=True)
        rows.append(dict(best=best, k_mean=means.get(k, float("nan")),
                         best_mean=means.get(best, float("nan")),
                         k_rank=(order.index(k) + 1) if k in means else 0,
                         live_industries=len(means)))
    after = rows[1:]
    ratio = [r["k_mean"] / r["best_mean"] if r["best_mean"] else float("nan") for r in rows]
    return _round_tree(dict(
        k_mean_before=rows[0]["k_mean"], k_mean_after=rows[2]["k_mean"],
        best_mean_before=rows[0]["best_mean"], best_mean_after=rows[2]["best_mean"],
        k_rank_before=rows[0]["k_rank"], k_rank_after=rows[2]["k_rank"],
        live_industries_before=rows[0]["live_industries"],
        rounds_k_best_after=int(sum(r["best"] == k for r in after)),
        best_industries_after=sorted({int(r["best"]) for r in after}),
        k_over_best_first=float(np.nanmean(ratio[1:1 + WINDOW])),
        k_over_best_close=float(np.nanmean(ratio[-WINDOW:]))))


#: The strength of the supply constraint, scanned for the wall's environment.
#: At one a thinned industry delivers in proportion to its headcount, so its
#: members' pay does not rise when it thins; below one it delivers more than
#: that, and the pay of those left rises, which is the pull back into it.
#: Zero is left out: there the constraint is off and tenure has no path at all.
BING_ELASTICITIES = (0.25, 0.5, 0.75)
BING_E_NEEDS = (0.06, 0.0)
BING_E_SHARE = 0.5


def _wall_rows(runs: dict, base: dict, keys: list) -> dict:
    """One printed row per key: the weakened industry against itself before the
    event and against the same industry in the run with no event."""
    cells = []
    for key in keys:
        q, b = runs[key], base[key[:-2] + (key[-1],)]
        k = key[-2]
        cells.append(dict(
            industry=k, seed=key[-1], emptied=q["k_live_at"] == 0,
            before=q["k_live_before"], at=q["k_live_at"], close=q["k_live_close"],
            base_close=b["live_close"][k],
            d_delivery_close=q["k_delivery_windows"][-1] - b["delivery_windows"][k][-1],
            delivery_drop=q["k_delivery_at"] - q["k_delivery_before"],
            joined=q["joined"], joined_moved_out=q["joined_moved_out"],
            extra_exits=(q["alive_before"] - q["alive_close"])
                        - (b["alive_before"] - b["alive_close"]),
            route_mass_moved=q["route_mass_moved"],
            live_path=[v / q["k_live_before"] if q["k_live_before"] else 0.0
                       for v in q["k_live_windows"]]))
    kept = [c for c in cells if not c["emptied"] and c["before"] > 0]

    def med(vals):
        return float(np.median(vals)) if vals else float("nan")

    summ = dict(
        cells=len(cells), emptied=sum(c["emptied"] for c in cells),
        close_over_before_median=med([c["close"] / c["before"] for c in kept]),
        close_minus_base=_signs([c["close"] - c["base_close"] for c in kept]),
        close_minus_base_median=med([c["close"] - c["base_close"] for c in kept]),
        d_delivery_close_median=med([c["d_delivery_close"] for c in kept]),
        joined_median=med([c["joined"] for c in kept]),
        joined_total=int(sum(c["joined"] for c in kept)),
        joined_moved_out_median=med([c["joined_moved_out"] for c in kept]),
        extra_exits=int(sum(c["extra_exits"] for c in cells)),
        delivery_drop_median=med([c["delivery_drop"] for c in kept]),
        route_mass_moved_median=med([c["route_mass_moved"] for c in cells]),
        live_path_median=([med([c["live_path"][i] for c in kept])
                           for i in range(len(kept[0]["live_path"]))] if kept else []))
    return dict(summary=summ, cells=cells)


def _print_wall_row(tag: str, s: dict) -> None:
    cb = s["close_minus_base"]
    kept = cb["positive"] + cb["zero"] + cb["negative"]
    print(f"  {tag:<22} {s['emptied']:2d}/{s['cells']}"
          f"    {s['close_over_before_median']:.3f}"
          f"               {s['close_minus_base_median']:+.1f}"
          f"                  {cb['positive'] + cb['zero']}/{kept}"
          f"             {s['d_delivery_close_median']:+.4f}"
          f"                      {s['joined_median']:.0f} ({s['joined_total']})"
          f"        {s['extra_exits']:+d}"
          f"        {s['delivery_drop_median']:+.4f}"
          f"                 {s['route_mass_moved_median']:.3f}")


def part_bing() -> dict:
    t_start = time.perf_counter()
    cache = load_cache()
    print("A27 block five: the wall, first block, a scan for an environment to read it in\n")

    def get(tag, ind, seed, env, k, cls=Recorder, summ=bing_summary):
        key = cache_key(ind, seed, env, tag)
        if key not in cache:
            if time.perf_counter() - t_start > BUDGET_S:
                raise TimeoutError
            h, m = run_cls(cls, ind, seed, env)
            cache[key] = summ(h, m, k)
        return cache[key]

    runs, base, eruns, ebase, mech = {}, {}, {}, {}, {}
    try:
        for need in BING_NEEDS:
            env = dict(_a19.LIVE, need=need)
            for s_ in SEEDS:
                base[(need, s_)] = get("bingscan", bing_industry(0, 0.0, weaken=False),
                                       s_, env, None)
                for share in BING_SHARES:
                    for k in YI_INDUSTRIES:
                        runs[(need, share, k, s_)] = get(
                            "bingscan", bing_industry(k, share), s_, env, k)
        # The mechanism, one seed: where the weakened industry stands on the
        # scale the switching rule reads, at the constraint's full strength and
        # at half of it.
        env6 = dict(_a19.LIVE, need=0.06)
        for e in (1.0, 0.5):
            for k in YI_INDUSTRIES:
                mech[(e, k)] = get("bingmech", dict(bing_industry(k, 0.5), supply_elasticity=e),
                                   SEED, env6, k, InflowRecorder, mech_summary)
                # The run with no event is the same run for every industry, and
                # its summary depends on which industry it is read for, so the
                # industry goes into the cache key through the tag.
                mech[(e, "none", k)] = get(
                    f"bingmech-none-{k}", dict(bing_industry(0, 0.0, weaken=False), supply_elasticity=e),
                    SEED, env6, k, InflowRecorder, mech_summary)
        for e in BING_ELASTICITIES:
            for need in BING_E_NEEDS:
                env = dict(_a19.LIVE, need=need)
                for s_ in SEEDS:
                    ebase[(e, need, s_)] = get(
                        "bingscan", dict(bing_industry(0, 0.0, weaken=False), supply_elasticity=e),
                        s_, env, None)
                    for k in YI_INDUSTRIES:
                        eruns[(e, need, k, s_)] = get(
                            "bingscan", dict(bing_industry(k, BING_E_SHARE), supply_elasticity=e),
                            s_, env, k)
    except TimeoutError:
        save_cache(cache)
        print(f"  budget of {BUDGET_S:.0f} s reached with {len(cache)} runs cached; "
              "run the same command again to continue")
        return {}
    save_cache(cache)

    head = ("  setting                emptied  k live close/before  k live close vs no event  "
            "refilled to no event  k delivery close minus no event  joined, median (total)  "
            "extra exits  delivery drop at the event  routing moved")
    print("weakening at round 50, tenure off, entry friction 0, switching at the base's rate;")
    print("each row: 14 production industries x 5 seeds\n")
    print("the need scan, supply constraint at full strength")
    print(head)
    table = {}
    for need in BING_NEEDS:
        for share in BING_SHARES:
            keys = [(need, share, k, s_) for k in YI_INDUSTRIES for s_ in SEEDS]
            b = {(need, share, s_): base[(need, s_)] for s_ in SEEDS}
            table[f"e=1.0|need={need}|share={share}"] = _wall_rows(runs, b, keys)
            _print_wall_row(f"need {need} share {share}", table[f"e=1.0|need={need}|share={share}"]["summary"])
    print("\nthe supply constraint's strength, share 0.5")
    print(head)
    for e in BING_ELASTICITIES:
        for need in BING_E_NEEDS:
            keys = [(e, need, k, s_) for k in YI_INDUSTRIES for s_ in SEEDS]
            b = {(e, need, s_): ebase[(e, need, s_)] for s_ in SEEDS}
            table[f"e={e}|need={need}|share={BING_E_SHARE}"] = _wall_rows(eruns, b, keys)
            _print_wall_row(f"e {e} need {need}", table[f"e={e}|need={need}|share={BING_E_SHARE}"]["summary"])

    print("\n  the weakened industry's live members over the run, median over cells,")
    print("  each window over its own count before the event (window 0 is rounds 25-49):")
    for lab, row in table.items():
        print(f"  {lab:<28} " + " ".join(f"{v:.2f}" for v in row["summary"]["live_path_median"]))

    print("\nprinted, not scored (D28): the switching rule's own scale, need 0.06, seed 0, share 0.5;")
    print("mean inflow of the weakened industry's live members, before the event and the round")
    print("after, the layer's best, and in how many of the 250 rounds after the event the")
    print("weakened industry is the best, which is the only industry anyone can move into")
    mech_out = {}
    for e in (1.0, 0.5):
        print(f"  supply constraint {e}")
        print("    industry   k mean before/after   best before/after   rank before/after (of n)   "
              "rounds k is best: weakened / no event   k over best, first window / close")
        for k in YI_INDUSTRIES:
            q, z = mech[(e, k)], mech[(e, "none", k)]
            mech_out[f"{e}|{k}"] = dict(weakened=q, no_event=z)
            print(f"    {k:>8}   {q['k_mean_before']:.3f}/{q['k_mean_after']:.3f}"
                  f"          {q['best_mean_before']:.3f}/{q['best_mean_after']:.3f}"
                  f"        {q['k_rank_before']}/{q['k_rank_after']} ({q['live_industries_before']})"
                  f"                     {q['rounds_k_best_after']} / {z['rounds_k_best_after']}"
                  f"                              {q['k_over_best_first']:.3f} / {q['k_over_best_close']:.3f}")
    print(f"\n  {len(cache)} runs cached, {time.perf_counter() - t_start:.0f} s this call")
    return dict(criteria=[], readings={"A27-5 scan": table, "switching scale": mech_out},
                note="printed, not scored: the scan the design runs before any tenure arm "
                     "of A27-5, to find an environment where the weakened industry comes "
                     "back with tenure off")


#: The copy of ``network.py`` taken immediately before the destination switch
#: (``switch_destination``) went in; ``industry.py`` has its own with the stamp.
BACKUP_DEST = "network.py.expired_20260910_193159_pre_A27目的地"

#: Block six: the weakening scan again with every better-paid industry open as
#: a destination. Share one half, so no industry is emptied by the event; the
#: need at which the production layer collapses on its own is left out.
BING2_NEEDS = (0.06, 0.04, 0.02, 0.0)
BING2_ELASTICITIES = (1.0, 0.5)
BING2_SHARE = 0.5

#: And a cheaper switch, for where the pull would have to come from if it comes
#: at all: the base's cost is a 30 per cent gain threshold, and the anchor A19
#: records puts measured mobility costs above the cliff, so these two points sit
#: on the side the evidence does not contain. Printed as a counterfactual.
BING2_COSTS = (0.1, 0.0)
BING2_COST_E = 0.5
BING2_COST_NEEDS = (0.06, 0.0)


def moves_summary(h, m, k=None) -> dict:
    """Every switch in the production layer, and where it went against the
    best-paid industry the switching rule saw that round (last round's inflow,
    live members, grouped by industry)."""
    alive = np.array(m.rec_alive)
    ind_path = np.array(m.rec_industry)
    inflow = np.array(m.rec_inflow)
    lower = np.concatenate([m._mid, m._l2]).astype(int)
    count = int(m.config.industry.count)
    into = np.zeros(count, dtype=int)
    to_best = 0
    moves = 0
    dests_per_round = []
    for t in range(1, _a19.ROUNDS):
        nodes = lower[alive[t - 1, lower]]
        gs = ind_path[t - 1, nodes]
        keep = gs >= 0
        nodes_v, gs_v = nodes[keep], gs[keep]
        moved = nodes_v[ind_path[t, nodes_v] != gs_v]
        if moved.size == 0:
            continue
        uniq = np.unique(gs_v)
        means = np.array([inflow[t - 1, nodes_v[gs_v == g]].mean() for g in uniq])
        best = int(uniq[int(np.argmax(means))])
        dest = ind_path[t, moved]
        np.add.at(into, dest, 1)
        to_best += int((dest == best).sum())
        moves += int(moved.size)
        dests_per_round.append(int(np.unique(dest).size))
    live_close = [int(((ind_path[-1] == j) & alive[-1]).sum()) for j in range(count)]
    prod = list(range(int(m.config.industry.financial_count), count))
    return _round_tree(dict(
        moves=moves, to_best=to_best, into=into.tolist(),
        rounds_with_moves=len(dests_per_round),
        destinations_per_round_median=float(np.median(dests_per_round)) if dests_per_round else 0.0,
        destinations_per_round_max=int(max(dests_per_round)) if dests_per_round else 0,
        production_nonempty_close=int(sum(live_close[j] > 0 for j in prod)),
        alive_close=int(alive[-1].sum())))


class RouteRecorder(Recorder):
    """``Recorder`` that keeps the discretionary routing in the round before
    the event, the round after it, and the last round."""

    def __init__(self, config):
        super().__init__(config)
        self.rec_routes: dict[int, np.ndarray] = {}

    def _post_round(self, t: int) -> None:
        super()._post_round(t)
        if t in (YI_AT - 1, YI_AT + 1, _a19.ROUNDS - 1):
            self.rec_routes[t] = np.array(self._route, copy=True)


def demand_summary(h, m, k) -> dict:
    """The weakened industry's market on the payment graph: the routing weight
    all payers direct to its live members, and how many payers direct any,
    in the round before the event, the round after, and the last round."""
    alive = np.array(m.rec_alive)
    ind_path = np.array(m.rec_industry)
    out = {}
    for tag_, t_ in (("before", YI_AT - 1), ("after", YI_AT + 1), ("close", _a19.ROUNDS - 1)):
        r = m.rec_routes[t_]
        members = np.flatnonzero((ind_path[t_] == k) & alive[t_])
        into = r[:, members].sum(axis=1) if members.size else np.zeros(r.shape[0])
        out[tag_] = dict(weight=float(into.sum()), payers=int((into > 0).sum()),
                         members=int(members.size))
    return _round_tree(out)


def part_bing2() -> dict:
    t_start = time.perf_counter()
    cache = load_cache()
    crits: list[dict] = []
    out: dict = {}
    print("A27 block six: the destination switch, and the wall's environment again\n")

    # ---- A27-1e: the destination switch at its default -------------------
    old = load_backup_named(BACKUP_DEST)
    cur = sys.modules["monetary_topology.network"]
    env6 = dict(_a19.LIVE, need=0.06)
    checks = []
    for label, ind_, env in (("industries on, switching on", BASE, ENV),
                             ("industries off", dict(count=0), ENV),
                             ("weakening, entry friction 0, need 0.06", bing_industry(9, 0.5), env6)):
        h_o = old.Network(config_for(old, ind_, SEED, env)).run()
        h_n = cur.Network(config_for(cur, ind_, SEED, env)).run()
        ok, differ, n = _a19.compare(h_o, h_n)
        checks.append((label, ok, n - len(differ), n))
        print(f"  A27-1e  {label:42} {n - len(differ)}/{n} history fields identical")
    crits.append(dict(
        name="A27-1e the destination switch at its default reproduces the build before it",
        kind="instrument", passed=bool(all(c[1] for c in checks)),
        detail="; ".join(f"{lb}: {a}/{b}" for lb, _, a, b in checks)
               + f"; against {BACKUP_DEST}"))

    def get(tag, ind, seed, env, k, cls=Recorder, summ=bing_summary):
        key = cache_key(ind, seed, env, tag)
        if key not in cache:
            if time.perf_counter() - t_start > BUDGET_S:
                raise TimeoutError
            h, m = run_cls(cls, ind, seed, env)
            cache[key] = summ(h, m, k)
        return cache[key]

    runs, base, mv, cruns, cbase, dem = {}, {}, {}, {}, {}, {}
    try:
        for dest in ("best", "proportional"):
            mv[dest] = get("bing2moves", dict(bing_industry(0, 0.0, weaken=False),
                                              switch_destination=dest),
                           SEED, env6, None, InflowRecorder, moves_summary)
        for e in BING2_ELASTICITIES:
            for need in BING2_NEEDS:
                env = dict(_a19.LIVE, need=need)
                for s_ in SEEDS:
                    base[(e, need, s_)] = get(
                        "bing2scan", dict(bing_industry(0, 0.0, weaken=False),
                                          supply_elasticity=e, switch_destination="proportional"),
                        s_, env, None)
                    for k in YI_INDUSTRIES:
                        runs[(e, need, k, s_)] = get(
                            "bing2scan", dict(bing_industry(k, BING2_SHARE), supply_elasticity=e,
                                              switch_destination="proportional"),
                            s_, env, k)
        # The market the weakened industry keeps, seed 0, need 0.06: the base's
        # switch and the cheapest one, each with and without the event.
        for lab_d, over in (("cost 0.3, e 1.0", dict(switch_cost=0.3, supply_elasticity=1.0)),
                            ("cost 0.0, e 0.5", dict(switch_cost=0.0, supply_elasticity=0.5))):
            for k in YI_INDUSTRIES:
                dem[(lab_d, "weakened", k)] = get(
                    "bing2demand", dict(bing_industry(k, BING2_SHARE), switch_destination="proportional", **over),
                    SEED, env6, k, RouteRecorder, demand_summary)
                dem[(lab_d, "no event", k)] = get(
                    f"bing2demand-none-{k}", dict(bing_industry(0, 0.0, weaken=False),
                                                  switch_destination="proportional", **over),
                    SEED, env6, k, RouteRecorder, demand_summary)
        for cost in BING2_COSTS:
            for need in BING2_COST_NEEDS:
                env = dict(_a19.LIVE, need=need)
                for s_ in SEEDS:
                    cbase[(cost, need, s_)] = get(
                        "bing2scan", dict(bing_industry(0, 0.0, weaken=False),
                                          supply_elasticity=BING2_COST_E, switch_cost=cost,
                                          switch_destination="proportional"),
                        s_, env, None)
                    for k in YI_INDUSTRIES:
                        cruns[(cost, need, k, s_)] = get(
                            "bing2scan", dict(bing_industry(k, BING2_SHARE),
                                              supply_elasticity=BING2_COST_E, switch_cost=cost,
                                              switch_destination="proportional"),
                            s_, env, k)
    except TimeoutError:
        save_cache(cache)
        print(f"  budget of {BUDGET_S:.0f} s reached with {len(cache)} runs cached; "
              "run the same command again to continue")
        return {}
    save_cache(cache)

    print("\nprinted, not scored (D28): where the switches go, no event, need 0.06, seed 0, "
          "entry friction 0, production layer")
    print("  rule           switches  into the round's best-paid  destinations per round "
          "(median / max)  production industries non-empty at the close  alive at the close")
    for dest in ("best", "proportional"):
        q = mv[dest]
        share = q["to_best"] / q["moves"] if q["moves"] else 0.0
        print(f"  {dest:13}  {q['moves']:8d}  {q['to_best']:6d} ({share:.1%})"
              f"               {q['destinations_per_round_median']:.0f} / {q['destinations_per_round_max']}"
              f"                          {q['production_nonempty_close']}"
              f"                                     {q['alive_close']}")
    out["where the switches go"] = mv

    print("\nweakening at round 50, share 0.5, tenure off, entry friction 0, every better-paid "
          "industry open; each row 14 production industries x 5 seeds")
    head = ("  setting                emptied  k live close/before  k live close vs no event  "
            "refilled to no event  k delivery close minus no event  joined, median (total)  "
            "extra exits  delivery drop at the event  routing moved")
    print(head)
    table = {}
    for e in BING2_ELASTICITIES:
        for need in BING2_NEEDS:
            keys = [(e, need, k, s_) for k in YI_INDUSTRIES for s_ in SEEDS]
            b = {(e, need, s_): base[(e, need, s_)] for s_ in SEEDS}
            lab = f"proportional|e={e}|need={need}|share={BING2_SHARE}"
            table[lab] = _wall_rows(runs, b, keys)
            _print_wall_row(f"e {e} need {need}", table[lab]["summary"])
    print(f"\ncounterfactual: a cheaper switch, supply constraint {BING2_COST_E}, share {BING2_SHARE}")
    print(head)
    for cost in BING2_COSTS:
        for need in BING2_COST_NEEDS:
            keys = [(cost, need, k, s_) for k in YI_INDUSTRIES for s_ in SEEDS]
            b = {(cost, need, s_): cbase[(cost, need, s_)] for s_ in SEEDS}
            lab = f"proportional|cost={cost}|e={BING2_COST_E}|need={need}|share={BING2_SHARE}"
            table[lab] = _wall_rows(cruns, b, keys)
            _print_wall_row(f"cost {cost} need {need}", table[lab]["summary"])
    print("\n  the weakened industry's live members over the run, median over cells,")
    print("  each window over its own count before the event (window 0 is rounds 25-49):")
    for lab, row in table.items():
        print(f"  {lab:<52} " + " ".join(f"{v:.2f}" for v in row["summary"]["live_path_median"]))
    out["A27-5 scan, proportional"] = table

    print("\nprinted, not scored (D28): the weakened industry's market on the payment graph, "
          "seed 0, need 0.06, every better-paid industry open")
    print("  routing weight all payers direct to its live members (payers directing any), "
          "before the event / the round after / the close, against the run with no event")
    dem_out = {}
    for lab_d in ("cost 0.3, e 1.0", "cost 0.0, e 0.5"):
        print(f"  {lab_d}")
        print("    industry   weakened: before / after / close          no event: before / after / close"
              "          members at the close, weakened / no event")
        ratios = []
        for k in YI_INDUSTRIES:
            q, z = dem[(lab_d, "weakened", k)], dem[(lab_d, "no event", k)]
            dem_out[f"{lab_d}|{k}"] = dict(weakened=q, no_event=z)
            if z["close"]["weight"] > 0:
                ratios.append(q["close"]["weight"] / z["close"]["weight"])
            print(f"    {k:>8}   {q['before']['weight']:.2f} ({q['before']['payers']}) / "
                  f"{q['after']['weight']:.2f} ({q['after']['payers']}) / "
                  f"{q['close']['weight']:.2f} ({q['close']['payers']})"
                  f"          {z['before']['weight']:.2f} / {z['after']['weight']:.2f} / "
                  f"{z['close']['weight']:.2f}"
                  f"          {q['close']['members']} / {z['close']['members']}")
        if ratios:
            print(f"    close-round weight, weakened over no event: median {np.median(ratios):.3f}, "
                  f"range {min(ratios):.3f} to {max(ratios):.3f}")
    out["the weakened industry's market"] = dem_out
    for c in crits:
        print(f"\n  {'PASS' if c['passed'] else 'FAIL':4}  [{c['kind']}]  {c['name']}")
    print(f"\n  {len(cache)} runs cached, {time.perf_counter() - t_start:.0f} s this call")
    return dict(criteria=crits, readings=out,
                note="the destination switch's gate, where switches go under each rule, and "
                     "the scan for the wall's environment with every better-paid industry open")


#: The copy of ``network.py`` taken immediately before channel formation
#: (``channel_rate``) went in; ``industry.py`` has its own with the stamp.
BACKUP_CHANNEL = "network.py.expired_20260910_195736_pre_A27渠道"

#: Block seven: the weakening scan once more, now with lost channels formed
#: again at a finite rate. Every better-paid industry open (the rule the last
#: block added), share one half, tenure off. The rate has no theoretical value,
#: so it is scanned: a lost channel comes back after about 100, 33 and 10
#: rounds on average. Zero is the fixed graph the last two blocks ran on.
BING3_RATES = (0.01, 0.03, 0.1)
BING3_ELASTICITIES = (1.0, 0.5)
BING3_NEEDS = (0.06, 0.0)
BING3_SHARE = 0.5


class MarketRecorder(Recorder):
    """``Recorder`` that also keeps, every round, each industry's market on the
    payment graph (the routing weight all payers direct to its live members,
    and how many payers direct any) and the running count of channels formed."""

    def __init__(self, config):
        super().__init__(config)
        self.rec_market: list[np.ndarray] = []
        self.rec_payers: list[np.ndarray] = []
        self.rec_channels: list[int] = []

    def _post_round(self, t: int) -> None:
        super()._post_round(t)
        ind = self.config.industry
        g = self._industry_of
        live = self._alive & (g >= 0)
        onehot = np.zeros((self._n, ind.count))
        onehot[np.flatnonzero(live), g[live]] = 1.0
        per_payer = self._route @ onehot
        self.rec_market.append(per_payer.sum(axis=0))
        self.rec_payers.append((per_payer > 0).sum(axis=0))
        self.rec_channels.append(int(self._channel_count))


def bing3_summary(h, m, k=None) -> dict:
    """``bing_summary`` plus the market: the weakened industry's before the
    event, the round after, per window and at the close, and the channels
    formed; with ``k`` None, every industry's market at the close."""
    q = bing_summary(h, m, k)
    mk = np.array(m.rec_market)
    py = np.array(m.rec_payers)
    ch = np.array(m.rec_channels)
    q["channels_formed"] = int(ch[-1])
    q["channels_formed_after_event"] = int(ch[-1] - ch[YI_AT - 1])
    if k is None:
        q["market_close"] = [round(float(v), DIGITS) for v in mk[-1]]
        q["market_before"] = [round(float(v), DIGITS) for v in mk[YI_AT - 1]]
    else:
        q.update(_round_tree(dict(
            k_market_before=float(mk[YI_AT - 1, k]), k_market_after=float(mk[YI_AT + 1, k]),
            k_market_close=float(mk[-1, k]), k_market_windows=windows(mk[:, k]),
            k_payers_before=int(py[YI_AT - 1, k]), k_payers_after=int(py[YI_AT + 1, k]),
            k_payers_close=int(py[-1, k]))))
    return q


def part_bing3() -> dict:
    t_start = time.perf_counter()
    cache = load_cache()
    crits: list[dict] = []
    out: dict = {}
    print("A27 block seven: lost channels formed again at a finite rate\n")

    # ---- A27-1f: the channel switch at its default ------------------------
    old = load_backup_named(BACKUP_CHANNEL)
    cur = sys.modules["monetary_topology.network"]
    env6 = dict(_a19.LIVE, need=0.06)
    checks = []
    for label, ind_, env in (("industries on, switching on", BASE, ENV),
                             ("industries off", dict(count=0), ENV),
                             ("weakening, every better-paid industry open, need 0.06",
                              dict(bing_industry(9, 0.5), switch_destination="proportional"), env6)):
        h_o = old.Network(config_for(old, ind_, SEED, env)).run()
        h_n = cur.Network(config_for(cur, ind_, SEED, env)).run()
        ok, differ, n = _a19.compare(h_o, h_n)
        checks.append((label, ok, n - len(differ), n))
        print(f"  A27-1f  {label:54} {n - len(differ)}/{n} history fields identical")
    crits.append(dict(
        name="A27-1f channel formation at its default reproduces the build before it",
        kind="instrument", passed=bool(all(c[1] for c in checks)),
        detail="; ".join(f"{lb}: {a}/{b}" for lb, _, a, b in checks)
               + f"; against {BACKUP_CHANNEL}"))

    def get(tag, ind, seed, env, k):
        key = cache_key(ind, seed, env, tag)
        if key not in cache:
            if time.perf_counter() - t_start > BUDGET_S:
                raise TimeoutError
            h, m = run_cls(MarketRecorder, ind, seed, env)
            cache[key] = bing3_summary(h, m, k)
        return cache[key]

    def ind_for(k, rho, e, weaken=True, conserve=False):
        d = dict(bing_industry(k, BING3_SHARE, weaken=weaken), supply_elasticity=e,
                 switch_destination="proportional", channel_rate=rho)
        if conserve:
            d["channel_conserve_degree"] = True
        return d

    # The rate-zero rows are the last block's proportional scan (same runs, other
    # tag), so they are not run again. At full strength of the constraint a
    # member's pay does not depend on the headcount while the industry is below
    # its reference, so a restored market cannot pull people back there; that
    # row is run at one need only, to show the market coming back without them.
    settings = ([(rho, 1.0, 0.06, False) for rho in BING3_RATES]
                + [(rho, 0.5, need, False) for need in BING3_NEEDS for rho in BING3_RATES]
                + [(0.03, 0.5, 0.06, True)])
    runs, base = {}, {}
    try:
        for rho, e, need, cons in settings:
            env = dict(_a19.LIVE, need=need)
            for s_ in SEEDS:
                base[(rho, e, need, cons, s_)] = get("bing3", ind_for(0, rho, e, False, cons), s_, env, None)
                for k in YI_INDUSTRIES:
                    runs[(rho, e, need, cons, k, s_)] = get("bing3", ind_for(k, rho, e, True, cons), s_, env, k)
    except TimeoutError:
        save_cache(cache)
        print(f"  budget of {BUDGET_S:.0f} s reached with {len(cache)} runs cached; "
              "run the same command again to continue")
        return {}
    save_cache(cache)

    print("\nweakening at round 50, share 0.5, tenure off, entry friction 0, every better-paid "
          "industry open; each row 14 production industries x 5 seeds")
    print("  setting                          k live close/before  refilled to no event  "
          "k market after/before  k market close/before  k market close vs no event  "
          "joined, median (total)  channels formed into the run (median)  extra exits")
    table = {}
    for rho, e, need, cons in settings:
        keys = [(rho, e, need, cons, k, s_) for k in YI_INDUSTRIES for s_ in SEEDS]
        b = {(rho, e, need, cons, s_): base[(rho, e, need, cons, s_)] for s_ in SEEDS}
        row = _wall_rows(runs, b, keys)
        mk_after = [runs[kk]["k_market_after"] / runs[kk]["k_market_before"]
                    for kk in keys if runs[kk]["k_market_before"] > 0]
        mk_close = [runs[kk]["k_market_close"] / runs[kk]["k_market_before"]
                    for kk in keys if runs[kk]["k_market_before"] > 0]
        mk_vs = [runs[kk]["k_market_close"] / b[kk[:4] + (kk[5],)]["market_close"][kk[4]]
                 for kk in keys if b[kk[:4] + (kk[5],)]["market_close"][kk[4]] > 0]
        chans = [runs[kk]["channels_formed"] for kk in keys]
        row["summary"].update(
            market_after_over_before_median=float(np.median(mk_after)),
            market_close_over_before_median=float(np.median(mk_close)),
            market_close_vs_no_event_median=float(np.median(mk_vs)),
            channels_formed_median=float(np.median(chans)))
        lab = f"rho={rho}|e={e}|need={need}" + ("|conserve" if cons else "")
        table[lab] = row
        s = row["summary"]
        cb = s["close_minus_base"]
        print(f"  {lab:32} {s['close_over_before_median']:.3f}"
              f"                {cb['positive'] + cb['zero']}/{s['cells']}"
              f"                 {s['market_after_over_before_median']:.3f}"
              f"                  {s['market_close_over_before_median']:.3f}"
              f"                  {s['market_close_vs_no_event_median']:.3f}"
              f"                     {s['joined_median']:.0f} ({s['joined_total']})"
              f"                   {s['channels_formed_median']:.0f}"
              f"                       {s['extra_exits']:+d}")
    print("\n  the weakened industry's live members over the run, median over cells,")
    print("  each window over its own count before the event (window 0 is rounds 25-49):")
    for lab, row in table.items():
        print(f"  {lab:<32} " + " ".join(f"{v:.2f}" for v in row["summary"]["live_path_median"]))
    out["A27-5 scan, channels"] = table
    for c in crits:
        print(f"\n  {'PASS' if c['passed'] else 'FAIL':4}  [{c['kind']}]  {c['name']}")
    print(f"\n  {len(cache)} runs cached, {time.perf_counter() - t_start:.0f} s this call")
    return dict(criteria=crits, readings=out,
                note="the channel switch's gate and the wall's environment with lost "
                     "channels formed again at a finite rate")


#: Block eight, A27-5 itself: the wall read against the build rate, in the
#: environment block seven found (supply constraint at half strength, the line
#: at 0.06, every better-paid industry open, lost channels formed again). Tenure
#: on at the shortfall the transfer arms used, the build rate over the design's
#: sweep points: zero is a newcomer who never learns, one is full in a round.
#: The ruler is the tenure-off arm at the same channel rate, which block seven
#: ran under the same tag, so those runs are read from the cache.
BING4_RATES = BING3_RATES
BING4_ETAS = (0.0, 0.003, 0.01, 0.03, 0.1, 1.0)
BING4_D = 0.5
BING4_E = 0.5
BING4_NEED = 0.06

#: A stronger shortfall at the middle channel rate, the top of the design's
#: sweep for it, so a flat curve at 0.5 can be read against one where a
#: newcomer counts for a quarter of an established member.
BING4_D_STRONG = 0.75
BING4_RATE_STRONG = 0.03


def part_bing4() -> dict:
    t_start = time.perf_counter()
    cache = load_cache()
    print("A27 block eight: the wall, read against the build rate\n")
    env = dict(_a19.LIVE, need=BING4_NEED)

    def get(ind, seed, k):
        key = cache_key(ind, seed, env, "bing3")
        if key not in cache:
            if time.perf_counter() - t_start > BUDGET_S:
                raise TimeoutError
            h, m = run_cls(MarketRecorder, ind, seed, env)
            cache[key] = bing3_summary(h, m, k)
        return cache[key]

    def ind_for(k, rho, eta, weaken=True, dd=BING4_D):
        if eta == "off":
            d = dict(bing_industry(k, BING3_SHARE, weaken=weaken))
        else:
            d = dict(bing_industry(k, BING3_SHARE, d=dd, eta=eta, weaken=weaken))
        d.update(supply_elasticity=BING4_E, switch_destination="proportional", channel_rate=rho)
        return d

    arms = ("off",) + BING4_ETAS
    runs, base = {}, {}
    blocks = [(rho, BING4_D) for rho in BING4_RATES] + [(BING4_RATE_STRONG, BING4_D_STRONG)]
    try:
        for rho, dd in blocks:
            for eta in arms:
                for s_ in SEEDS:
                    base[(rho, dd, eta, s_)] = get(ind_for(0, rho, eta, weaken=False, dd=dd), s_, None)
                    for k in YI_INDUSTRIES:
                        runs[(rho, dd, eta, k, s_)] = get(ind_for(k, rho, eta, dd=dd), s_, k)
    except TimeoutError:
        save_cache(cache)
        print(f"  budget of {BUDGET_S:.0f} s reached with {len(cache)} runs cached; "
              "run the same command again to continue")
        return {}
    save_cache(cache)

    def ratio(q, a, b):
        return q[a] / q[b] if q[b] else float("nan")

    table, curve = {}, {}
    print(f"weakening at round 50, share {BING3_SHARE}, supply constraint {BING4_E}, need {BING4_NEED}, "
          f"every better-paid industry open, lost channels formed again; tenure shortfall {BING4_D}")
    print("each row 14 production industries x 5 seeds; 'vs off' pairs each cell with the same "
          "industry and seed at tenure off\n")
    for rho, dd in blocks:
        lab_b = f"{rho}" if dd == BING4_D else f"{rho}|d={dd}"
        print(f"  channel rate {rho}, tenure shortfall {dd}")
        print("    build rate   k live close/before  over tenure off  paired vs off +/0/-   "
              "k delivery close/before  k market close/before  refilled to no event  "
              "joined, median (total)  extra exits")
        off_cells = {(k, s_): runs[(rho, dd, "off", k, s_)] for k in YI_INDUSTRIES for s_ in SEEDS}
        r_off = float(np.median([q["k_live_close"] / q["k_live_before"]
                                 for q in off_cells.values() if q["k_live_before"]]))
        curve[lab_b] = {}
        for eta in arms:
            keys = [(rho, dd, eta, k, s_) for k in YI_INDUSTRIES for s_ in SEEDS]
            b = {(rho, dd, eta, s_): base[(rho, dd, eta, s_)] for s_ in SEEDS}
            row = _wall_rows(runs, b, keys)
            rec = [runs[kk]["k_live_close"] / runs[kk]["k_live_before"]
                   for kk in keys if runs[kk]["k_live_before"]]
            paired = []
            for kk in keys:
                q, z = runs[kk], off_cells[(kk[3], kk[4])]
                if q["k_live_before"] and z["k_live_before"]:
                    paired.append(q["k_live_close"] / q["k_live_before"]
                                  - z["k_live_close"] / z["k_live_before"])
            dl = [runs[kk]["k_delivery_windows"][-1] / runs[kk]["k_delivery_windows"][0]
                  for kk in keys if runs[kk]["k_delivery_windows"][0]]
            mk = [ratio(runs[kk], "k_market_close", "k_market_before") for kk in keys
                  if runs[kk]["k_market_before"]]
            s = row["summary"]
            s.update(recovery_median=float(np.median(rec)),
                     recovery_over_off=float(np.median(rec)) / r_off if r_off else float("nan"),
                     paired_vs_off=_signs(paired),
                     paired_vs_off_median=float(np.median(paired)),
                     delivery_close_over_before_median=float(np.median(dl)),
                     market_close_over_before_median=float(np.median(mk)))
            table[f"rho={lab_b}|eta={eta}"] = row
            curve[lab_b][str(eta)] = dict(recovery=s["recovery_median"],
                                             over_off=s["recovery_over_off"],
                                             paired=s["paired_vs_off"])
            cb = s["close_minus_base"]
            pv = s["paired_vs_off"]
            tag = "tenure off" if eta == "off" else f"{eta}"
            print(f"    {tag:<11}  {s['recovery_median']:.3f}"
                  f"                {s['recovery_over_off']:.3f}"
                  f"            {pv['positive']:2d}/{pv['zero']:2d}/{pv['negative']:2d}"
                  f"             {s['delivery_close_over_before_median']:.3f}"
                  f"                    {s['market_close_over_before_median']:.3f}"
                  f"                  {cb['positive'] + cb['zero']}/{s['cells']}"
                  f"                 {s['joined_median']:.0f} ({s['joined_total']})"
                  f"             {s['extra_exits']:+d}")
        print()
    print("  the weakened industry's live members over the run, median over cells,")
    print("  each window over its own count before the event (window 0 is rounds 25-49):")
    for lab, row in table.items():
        print(f"  {lab:<22} " + " ".join(f"{v:.2f}" for v in row["summary"]["live_path_median"]))
    crit = dict(
        name="A27-5 the wall: a weakened industry's recovery against the build rate",
        kind="own_reading",
        detail={rho: {eta: dict(recovery=v["recovery"], over_tenure_off=v["over_off"],
                                paired_vs_off=v["paired"]) for eta, v in c.items()}
                for rho, c in curve.items()},
        note="printed object, no line drawn (rule 11): per channel rate and build rate, the "
             "median over cells of the weakened industry's headcount at the close over its "
             "count before the event, that median over the tenure-off arm's, and the paired "
             "signs of the difference cell by cell; whether the curve is a step or a slope "
             "is read off the printed curve")
    print(f"\n  ----  [own_reading]  {crit['name']}")
    print(f"\n  {len(cache)} runs cached, {time.perf_counter() - t_start:.0f} s this call")
    return dict(criteria=[crit], readings={"A27-5": table},
                note="A27-5 in the environment block seven found")


#: The copy of ``network.py`` taken immediately before the demand side
#: (``demand_skill``) went in; ``industry.py`` has its own with the stamp.
BACKUP_DEMAND = "network.py.expired_20260910_210252_pre_A27熟客"

#: Block nine, the demand side. The gates run at the tenure setting the supply
#: gates ran at; the reading runs in the wall's environment at the middle
#: channel rate, demand side alone (supply shortfall zero), over the same build
#: rates as A27-5, against the same tenure-off arm.
DING_D = 0.5
DING_RATE = 0.03
DING_ETAS = BING4_ETAS


class DemandPremium(Recorder):
    """The premium form of the demand weight: ``1 + b s`` with
    ``b = d / (1 - d)``, which is the shortfall form times ``1 / (1 - d)``. The
    split normalises within each industry, so the constant has to cancel."""

    def _demand_weights(self) -> np.ndarray:
        d = self.config.industry.demand_skill
        return 1.0 + (d / (1.0 - d)) * self._tenure


def ding_summary(h, m, k=None) -> dict:
    """``bing3_summary`` plus, for the weakened industry at the close, the
    routing weight a member gets from all payers, averaged over the members
    still short of full tenure and over the established ones."""
    q = bing3_summary(h, m, k)
    if k is not None:
        alive = np.array(m.rec_alive)
        ind_path = np.array(m.rec_industry)
        members = np.flatnonzero((ind_path[-1] == k) & alive[-1])
        col = np.asarray(m._route).sum(axis=0)
        ten = np.asarray(m._tenure)
        new = members[ten[members] < 1.0]
        old = members[ten[members] >= 1.0]
        q.update(_round_tree(dict(
            k_newcomers_close=int(new.size), k_established_close=int(old.size),
            k_weight_newcomer=float(col[new].mean()) if new.size else float("nan"),
            k_weight_established=float(col[old].mean()) if old.size else float("nan"))))
    return q


def part_ding() -> dict:
    t_start = time.perf_counter()
    cache = load_cache()
    crits: list[dict] = []
    out: dict = {}
    print("A27 block nine: the demand side, regular customers\n")

    # ---- A27-1g: the demand switch at its default --------------------------
    old = load_backup_named(BACKUP_DEMAND)
    cur = sys.modules["monetary_topology.network"]
    env6 = dict(_a19.LIVE, need=0.06)
    wall = dict(bing_industry(9, 0.5), supply_elasticity=0.5,
                switch_destination="proportional", channel_rate=DING_RATE)
    checks = []
    for label, ind_, env in (("industries on, switching on", BASE, ENV),
                             ("industries off", dict(count=0), ENV),
                             ("the wall's environment, weakening, channels", wall, env6)):
        h_o = old.Network(config_for(old, ind_, SEED, env)).run()
        h_n = cur.Network(config_for(cur, ind_, SEED, env)).run()
        ok, differ, n = _a19.compare(h_o, h_n)
        checks.append((label, ok, n - len(differ), n))
        print(f"  A27-1g  {label:46} {n - len(differ)}/{n} history fields identical")
    crits.append(dict(
        name="A27-1g the demand switch at its default reproduces the build before it",
        kind="instrument", passed=bool(all(c[1] for c in checks)),
        detail="; ".join(f"{lb}: {a}/{b}" for lb, _, a, b in checks)
               + f"; against {BACKUP_DEMAND}"))

    # ---- A27-1b, demand half: the switch on while nobody moves --------------
    still = dict(BASE, switch_rate=0.0, demand_skill=DING_D, skill_rate=RATE)
    h_o = old.Network(config_for(old, still, SEED, ENV)).run()
    m_n = cur.Network(config_for(cur, still, SEED, ENV))
    h_n = m_n.run()
    ok, differ, n = _a19.compare(h_o, h_n)
    low = float(np.asarray(m_n._tenure)[(np.asarray(m_n._industry_of) >= 0)
                                        & np.asarray(m_n._alive)].min())
    crits.append(dict(
        name="A27-1b (demand half) the demand switch on while nobody moves reproduces the build before it",
        kind="instrument", passed=bool(ok),
        detail=f"{n - len(differ)}/{n} history fields identical at demand_skill={DING_D}, "
               f"skill_rate={RATE}, switch_rate=0; lowest tenure at close {low}"))
    print(f"  A27-1b (demand)  {n - len(differ)}/{n} history fields identical, lowest tenure {low}")

    # ---- A27-2a, demand half: the premium form lands on the shortfall form ---
    rows = []
    for d in CANCEL_D:
        ind = dict(BASE, demand_skill=d, skill_rate=RATE)
        for label, env in ENVS.items():
            for s_ in SEEDS:
                h1, m1 = run_cls(Recorder, ind, s_, env)
                h2, m2 = run_cls(DemandPremium, ind, s_, env)
                r, where = max_relative_difference(h1, h2)
                split = first_split(m1, m2)
                ok2, differ2, n2 = _a19.compare(h1, h2)
                state = ("bit-identical" if ok2 else
                         "within rounding" if split is None and r < REL_TOL else
                         "discrete split" if split is not None else
                         "beyond rounding")
                rows.append(dict(d=d, env=label, seed=s_, max_relative=r, worst_field=where,
                                 first_split=split, identical_fields=[n2 - len(differ2), n2],
                                 state=state))
                print(f"  A27-2a (demand) d={d:<4} {label:24} seed {s_}  {state:15} split {split}")
    states = {r["state"] for r in rows}
    if "beyond rounding" in states:
        passed, verdict = False, "FAIL: a difference beyond rounding with no discrete split"
    elif "discrete split" in states:
        passed, verdict = None, "not judged on the split cells, which are listed"
    else:
        passed, verdict = True, "PASS"
    by_d = {str(d): sorted({r["state"] for r in rows if r["d"] == d}) for d in CANCEL_D}
    crits.append(dict(
        name="A27-2a (demand half) the premium form lands on the shortfall form",
        kind="instrument", passed=passed,
        detail=f"{verdict}; states by shortfall {by_d}; largest relative difference below "
               f"{_below(max(r['max_relative'] for r in rows))} over {len(rows)} run pairs, "
               f"tolerance {REL_TOL:.0e}"))
    out["A27-2a demand"] = dict(rows=rows)

    # ---- printed, not scored (D28): the switch with people moving ----------
    moving = dict(BASE, demand_skill=DING_D, skill_rate=RATE)
    h_off, m_off = run_cls(Recorder, BASE, SEED, ENV)
    h_on, m_on = run_cls(Recorder, moving, SEED, ENV)
    ok3, differ3, n3 = _a19.compare(h_off, h_on)
    g = np.asarray(m_on._industry_of)
    live = (g >= 0) & np.asarray(m_on._alive)
    col = np.asarray(m_on._route).sum(axis=0)
    ten = np.asarray(m_on._tenure)
    newc, estb = live & (ten < 1.0), live & (ten >= 1.0)
    moved_print = dict(
        fields_differing=len(differ3), fields=n3,
        switches_off=int(m_off._switch_count), switches_on=int(m_on._switch_count),
        newcomers_close=int(newc.sum()), established_close=int(estb.sum()),
        weight_newcomer=float(col[newc].mean()) if newc.any() else float("nan"),
        weight_established=float(col[estb].mean()) if estb.any() else float("nan"))
    out["the switch with people moving"] = moved_print
    print(f"\n  printed, not scored (D28), switching on, need {ENV['need']}, seed {SEED}: "
          f"{len(differ3)}/{n3} history fields differ from the switch off; switches "
          f"{moved_print['switches_off']} off, {moved_print['switches_on']} on; at the close "
          f"{moved_print['newcomers_close']} members below full tenure take a routing weight of "
          f"{moved_print['weight_newcomer']:.4f} each against {moved_print['weight_established']:.4f} "
          f"for the {moved_print['established_close']} established")

    # ---- A27-6b: the wall with regular customers ----------------------------
    def get(ind, seed, env, k):
        key = cache_key(ind, seed, env, "bing3")
        if key not in cache:
            if time.perf_counter() - t_start > BUDGET_S:
                raise TimeoutError
            h, m = run_cls(MarketRecorder, ind, seed, env)
            cache[key] = ding_summary(h, m, k)
        return cache[key]

    def ind_for(k, eta, weaken=True):
        if eta == "off":
            d = dict(bing_industry(k, BING3_SHARE, weaken=weaken))
        else:
            d = dict(bing_industry(k, BING3_SHARE, weaken=weaken),
                     demand_skill=DING_D, skill_rate=eta)
        d.update(supply_elasticity=BING4_E, switch_destination="proportional",
                 channel_rate=DING_RATE)
        return d

    arms = ("off",) + DING_ETAS
    runs, base = {}, {}
    try:
        for eta in arms:
            for s_ in SEEDS:
                base[(eta, s_)] = get(ind_for(0, eta, weaken=False), s_, env6, None)
                for k in YI_INDUSTRIES:
                    runs[(eta, k, s_)] = get(ind_for(k, eta), s_, env6, k)
    except TimeoutError:
        save_cache(cache)
        print(f"  budget of {BUDGET_S:.0f} s reached with {len(cache)} runs cached; "
              "run the same command again to continue")
        return {}
    save_cache(cache)

    print(f"\nA27-6b  the wall with regular customers: weakening share {BING3_SHARE}, supply "
          f"constraint {BING4_E}, need 0.06, channel rate {DING_RATE}, demand shortfall {DING_D}, "
          "supply shortfall 0; 14 industries x 5 seeds")
    print("    build rate   k live close/before  over tenure off  paired vs off +/0/-   "
          "k delivery close/before  k market close/before  refilled to no event  joined, median (total)  "
          "extra exits  close: weight per newcomer / per established (median)")
    off_cells = {(k, s_): runs[("off", k, s_)] for k in YI_INDUSTRIES for s_ in SEEDS}
    r_off = float(np.median([q["k_live_close"] / q["k_live_before"]
                             for q in off_cells.values() if q["k_live_before"]]))
    table, curve = {}, {}
    for eta in arms:
        keys = [(eta, k, s_) for k in YI_INDUSTRIES for s_ in SEEDS]
        b = {(eta, s_): base[(eta, s_)] for s_ in SEEDS}
        row = _wall_rows(runs, b, keys)
        rec = [runs[kk]["k_live_close"] / runs[kk]["k_live_before"]
               for kk in keys if runs[kk]["k_live_before"]]
        paired = []
        for kk in keys:
            q, z = runs[kk], off_cells[(kk[1], kk[2])]
            if q["k_live_before"] and z["k_live_before"]:
                paired.append(q["k_live_close"] / q["k_live_before"]
                              - z["k_live_close"] / z["k_live_before"])
        dl = [runs[kk]["k_delivery_windows"][-1] / runs[kk]["k_delivery_windows"][0]
              for kk in keys if runs[kk]["k_delivery_windows"][0]]
        mk = [runs[kk]["k_market_close"] / runs[kk]["k_market_before"]
              for kk in keys if runs[kk]["k_market_before"]]
        wn = [runs[kk]["k_weight_newcomer"] for kk in keys
              if "k_weight_newcomer" in runs[kk] and runs[kk]["k_weight_newcomer"] == runs[kk]["k_weight_newcomer"]]
        we = [runs[kk]["k_weight_established"] for kk in keys
              if "k_weight_established" in runs[kk] and runs[kk]["k_weight_established"] == runs[kk]["k_weight_established"]]
        s = row["summary"]
        s.update(recovery_median=float(np.median(rec)),
                 recovery_over_off=float(np.median(rec)) / r_off if r_off else float("nan"),
                 paired_vs_off=_signs(paired),
                 delivery_close_over_before_median=float(np.median(dl)),
                 market_close_over_before_median=float(np.median(mk)),
                 weight_newcomer_median=float(np.median(wn)) if wn else float("nan"),
                 weight_established_median=float(np.median(we)) if we else float("nan"))
        table[f"eta={eta}"] = row
        curve[str(eta)] = dict(recovery=s["recovery_median"], over_off=s["recovery_over_off"],
                               paired=s["paired_vs_off"])
        cb, pv = s["close_minus_base"], s["paired_vs_off"]
        tag = "tenure off" if eta == "off" else f"{eta}"
        wtxt = ("" if eta == "off" else
                f"{s['weight_newcomer_median']:.4f} / {s['weight_established_median']:.4f}")
        print(f"    {tag:<11}  {s['recovery_median']:.3f}                {s['recovery_over_off']:.3f}"
              f"            {pv['positive']:2d}/{pv['zero']:2d}/{pv['negative']:2d}"
              f"             {s['delivery_close_over_before_median']:.3f}"
              f"                    {s['market_close_over_before_median']:.3f}"
              f"                  {cb['positive'] + cb['zero']}/{s['cells']}"
              f"                 {s['joined_median']:.0f} ({s['joined_total']})"
              f"             {s['extra_exits']:+d}        {wtxt}")
    print("\n  the weakened industry's live members over the run, median over cells,")
    print("  each window over its own count before the event (window 0 is rounds 25-49):")
    for lab, row in table.items():
        print(f"  {lab:<12} " + " ".join(f"{v:.2f}" for v in row["summary"]["live_path_median"]))
    crits.append(dict(
        name="A27-6b the wall with regular customers: recovery against the build rate, demand side alone",
        kind="own_reading",
        detail={eta: dict(recovery=v["recovery"], over_tenure_off=v["over_off"],
                          paired_vs_off=v["paired"]) for eta, v in curve.items()},
        note="printed object, no line drawn (rule 11): the median recovery, that median over "
             "the tenure-off arm's, and the paired signs cell by cell, per build rate"))
    out["A27-6b"] = table
    print()
    for c in crits:
        v = c.get("passed")
        mark = "PASS" if v is True else "FAIL" if v is False else "----"
        print(f"  {mark}  [{c['kind']}]  {c['name']}")
    print(f"\n  {len(cache)} runs cached, {time.perf_counter() - t_start:.0f} s this call")
    return dict(criteria=crits, readings=out,
                note="the demand side's gates and its reading in the wall's environment")


#: Block ten, the rest of the demand side, no change to ``src``.
#:
#: A27-6c, the transfer of block three (half the members exchanged at round 50,
#: the industry restaffed at once, switching off) with regular customers on the
#: demand side alone, against the same transfer with them off. Before the event
#: every member sits at tenure one, the weights are exact ones and the two arms
#: are the same run (A27-1b, demand half), so every difference is the event's.
#: The registered hypothesis: the people moved lose more income than when the
#: routing re-forms at once, and the extra exits fall on them.
#:
#: A27-6a, in the wall's environment at the middle channel rate: of the people
#: who move into the weakened industry after the event, how many are switched
#: out again and after how many rounds, with regular customers on and off.
DING2_D = 0.5
DING2_RATES = YI_RATES
DING2_NEEDS = ("need=0.06", "no line, need=0")
DING2_JOIN_ETAS = (0.003, 0.03)


def moved_summary(h, m, k=None) -> dict:
    """Exits after the event and income either side of it, for four groups: the
    people moved out, the people moved in, the members who stayed, everyone
    else. Income is each group's mean inflow over the window before the event
    and the window after it."""
    alive = np.array(m.rec_alive)
    q = dict(alive_before=int(alive[YI_AT - 1].sum()), alive_close=int(alive[-1].sum()))
    if k is None:
        return q
    ind_path = np.array(m.rec_industry)
    inflow = np.array(m.rec_inflow)
    n = m._n
    out_nodes, in_nodes, _ = (m._transfer_moved if m._transfer_moved is not None
                              else (np.zeros(0, dtype=int),) * 3)
    was = alive[YI_AT - 1]
    moved_out = np.zeros(n, dtype=bool)
    moved_out[out_nodes] = True
    moved_in = np.zeros(n, dtype=bool)
    moved_in[in_nodes] = True
    stayers = was & (ind_path[YI_AT - 1] == k) & ~moved_out
    groups = dict(moved_out=was & moved_out, moved_in=was & moved_in, stayers=stayers,
                  others=was & ~moved_out & ~moved_in & ~stayers)
    left = was & ~alive[-1]
    for name, mask in groups.items():
        q[f"n_{name}"] = int(mask.sum())
        q[f"exits_{name}"] = int((left & mask).sum())
        if mask.any():
            q[f"inflow_{name}_before"] = float(inflow[YI_AT - WINDOW:YI_AT][:, mask].mean())
            q[f"inflow_{name}_after"] = float(inflow[YI_AT:YI_AT + WINDOW][:, mask].mean())
    return _round_tree(q)


def joiner_summary(h, m, k) -> dict:
    """The people who move into the weakened industry after the event: how
    many, how many are switched out again, and after how many rounds."""
    ind_path = np.array(m.rec_industry)
    alive = np.array(m.rec_alive)
    stays, leaves, still = [], [], 0
    for v in range(m._n):
        path = ind_path[YI_AT:, v]
        inside = np.flatnonzero(path == k)
        if inside.size == 0 or path[0] == k:
            continue
        t_join = int(inside[0])
        after = np.flatnonzero(path[t_join:] != k)
        if after.size:
            leaves.append(int(after[0]))
        else:
            still += 1
            stays.append(int(path.size - t_join))
    return _round_tree(dict(joiners=len(leaves) + still, left_again=len(leaves),
                            rounds_before_leaving=leaves, still_in_at_close=still,
                            alive_close=int(alive[-1].sum())))


def contact_summary(h, m, k) -> dict:
    """Where a tenure weight can bind at all. A buyer splits what it spends on
    an industry among its own contacts there, so the weight of a member changes
    its share only in the buyers that reach the industry through someone else
    too. For the people moved into the industry, the links from their payers,
    split by whether the payer has another live contact in the industry."""
    g = np.asarray(m._industry_of)
    alive = np.asarray(m._alive)
    disc = (np.asarray(m.adjacency) - np.asarray(m.wage_mask)) > 0
    members = np.flatnonzero((g == k) & alive)
    _, in_nodes, _ = (m._transfer_moved if m._transfer_moved is not None
                      else (np.zeros(0, dtype=int),) * 3)
    in_nodes = np.asarray([v for v in in_nodes if alive[v] and g[v] == k], dtype=int)
    alone = shared = 0
    for v in in_nodes:
        payers = np.flatnonzero(disc[:, v] & alive)
        for i in payers:
            others = int(disc[i, members].sum()) - 1
            if others > 0:
                shared += 1
            else:
                alone += 1
    per_pair = []
    for i in np.flatnonzero(alive):
        c = int(disc[i, members].sum())
        if c > 0:
            per_pair.append(c)
    return _round_tree(dict(links_alone=alone, links_shared=shared,
                            payers_with_contact=len(per_pair),
                            payers_with_two_or_more=int(sum(c >= 2 for c in per_pair))))


def part_ding2() -> dict:
    t_start = time.perf_counter()
    cache = load_cache()
    out: dict = {}
    crits: list[dict] = []
    print("A27 block ten: the rest of the demand side\n")

    def get(tag, ind, seed, env, k, summ):
        key = cache_key(ind, seed, env, tag)
        if key not in cache:
            if time.perf_counter() - t_start > BUDGET_S:
                raise TimeoutError
            h, m = run_cls(InflowRecorder, ind, seed, env)
            cache[key] = summ(h, m, k)
        return cache[key]

    def transfer_ind(k, eta, transfer=True):
        d = yi_industry(k, 0.0, 0.0, transfer=transfer)
        if eta is not None:
            d.update(demand_skill=DING2_D, skill_rate=eta)
        return d

    def join_ind(k, eta):
        d = dict(bing_industry(k, BING3_SHARE), supply_elasticity=BING4_E,
                 switch_destination="proportional", channel_rate=DING_RATE)
        if eta is not None:
            d.update(demand_skill=DING2_D, skill_rate=eta)
        return d

    tr, jn = {}, {}
    env6 = dict(_a19.LIVE, need=0.06)
    try:
        for label in DING2_NEEDS:
            env = YI_ENVS[label]
            for s_ in SEEDS:
                tr[(label, "base", s_)] = get("ding2", transfer_ind(0, None, transfer=False),
                                              s_, env, None, moved_summary)
                for k in YI_INDUSTRIES:
                    for eta in (None,) + DING2_RATES:
                        tr[(label, eta, k, s_)] = get("ding2", transfer_ind(k, eta), s_, env, k,
                                                      moved_summary)
        for eta in (None,) + DING2_JOIN_ETAS:
            for k in YI_INDUSTRIES:
                for s_ in SEEDS:
                    jn[(eta, k, s_)] = get("ding2join", join_ind(k, eta), s_, env6, k, joiner_summary)
        ct = {k: get("ding2contacts", transfer_ind(k, 0.03), SEED, YI_ENVS["need=0.06"], k,
                     contact_summary) for k in YI_INDUSTRIES}
    except TimeoutError:
        save_cache(cache)
        print(f"  budget of {BUDGET_S:.0f} s reached with {len(cache)} runs cached; "
              "run the same command again to continue")
        return {}
    save_cache(cache)

    # ---- A27-6c -----------------------------------------------------------
    groups = ("moved_out", "moved_in", "stayers", "others")
    print("A27-6c  the transfer with regular customers, switching off; each row 14 industries x 5 seeds")
    print("  exits against no transfer (total) and by group; each group's income, window after the "
          "event over the window before (median over cells)")
    c6 = {}
    for label in DING2_NEEDS:
        print(f"  {label}")
        print("    customers         extra exits   moved out / moved in / stayers / others        "
              "income after/before: moved out / moved in / stayers / others")
        c6[label] = {}
        for eta in (None,) + DING2_RATES:
            cells = [tr[(label, eta, k, s_)] for k in YI_INDUSTRIES for s_ in SEEDS]
            bases = [tr[(label, "base", s_)] for k in YI_INDUSTRIES for s_ in SEEDS]
            extra = sum((q["alive_before"] - q["alive_close"]) - (b["alive_before"] - b["alive_close"])
                        for q, b in zip(cells, bases))
            ex = {g: int(sum(q[f"exits_{g}"] for q in cells)) for g in groups}
            inc = {}
            for g in groups:
                vals = [q[f"inflow_{g}_after"] / q[f"inflow_{g}_before"] for q in cells
                        if q.get(f"inflow_{g}_before")]
                inc[g] = float(np.median(vals)) if vals else float("nan")
            tag = "off" if eta is None else f"on, eta {eta}"
            c6[label][tag] = dict(extra_exits=int(extra), exits=ex, income_after_over_before=inc)
            print(f"    {tag:<16}  {extra:+5d}         {ex['moved_out']:3d} / {ex['moved_in']:3d} / "
                  f"{ex['stayers']:3d} / {ex['others']:3d}"
                  f"                      {inc['moved_out']:.3f} / {inc['moved_in']:.3f} / "
                  f"{inc['stayers']:.3f} / {inc['others']:.3f}")
        # the difference the hypothesis is about: customers on minus off, per group
        off = c6[label]["off"]
        for eta in DING2_RATES:
            on = c6[label][f"on, eta {eta}"]
            d_ex = {g: on["exits"][g] - off["exits"][g] for g in groups}
            print(f"    on minus off, eta {eta}: exits {d_ex['moved_out']:+d} / {d_ex['moved_in']:+d} / "
                  f"{d_ex['stayers']:+d} / {d_ex['others']:+d}; total {on['extra_exits'] - off['extra_exits']:+d}")
            c6[label][f"on, eta {eta}"]["exits_on_minus_off"] = d_ex
    la = sum(q["links_alone"] for q in ct.values())
    ls = sum(q["links_shared"] for q in ct.values())
    pw = sum(q["payers_with_contact"] for q in ct.values())
    p2 = sum(q["payers_with_two_or_more"] for q in ct.values())
    print(f"\n  printed, not scored (D28), need 0.06, seed {SEED}, at the close, 14 industries: of the "
          f"links from payers to the people moved in, {ls} come from a payer with another contact in "
          f"the industry and {la} from a payer with none; of the {pw} payers reaching the industry "
          f"at all, {p2} reach it through two or more members")
    out["where the tenure weight can bind"] = dict(links_shared=ls, links_alone=la,
                                                   payers_with_contact=pw,
                                                   payers_with_two_or_more=p2, rows=ct)
    out["A27-6c"] = c6
    crits.append(dict(
        name="A27-6c the transfer with regular customers: who leaves and whose income falls",
        kind="own_reading",
        detail={lb: {t: dict(extra_exits=v["extra_exits"], exits=v["exits"],
                             exits_on_minus_off=v.get("exits_on_minus_off"))
                     for t, v in c6[lb].items()} for lb in c6},
        note="printed object, no line drawn (rule 11): exits after the event by group, and "
             "regular customers on minus off per group, per environment and build rate"))

    # ---- A27-6a -----------------------------------------------------------
    print("\nA27-6a  who comes into the weakened industry and is switched out again: the wall's "
          f"environment, channel rate {DING_RATE}; 14 industries x 5 seeds")
    print("    customers         joiners  switched out again (share)  rounds before leaving, quintiles"
          "          tenure at leaving implied by the build rate")
    c6a = {}
    for eta in (None,) + DING2_JOIN_ETAS:
        cells = [jn[(eta, k, s_)] for k in YI_INDUSTRIES for s_ in SEEDS]
        j = int(sum(q["joiners"] for q in cells))
        lft = int(sum(q["left_again"] for q in cells))
        rounds = [r for q in cells for r in q["rounds_before_leaving"]]
        quint = _quint(rounds)
        tag = "off" if eta is None else f"on, eta {eta}"
        implied = ([round(1.0 - (1.0 - eta) ** r, 4) for r in quint] if eta is not None and quint else [])
        c6a[tag] = dict(joiners=j, left_again=lft, rounds_quintiles=quint, tenure_at_leaving=implied)
        share = lft / j if j else float("nan")
        print(f"    {tag:<16}  {j:6d}   {lft:6d} ({share:.2f})              {quint}"
              f"          {implied}")
    out["A27-6a"] = c6a
    crits.append(dict(
        name="A27-6a who comes into the weakened industry and is switched out again",
        kind="own_reading",
        detail=c6a,
        note="printed object, no line drawn (rule 11): joiners after the event, how many are "
             "switched out again, the rounds they stayed (quintiles), and the tenure those "
             "rounds imply at the build rate"))
    print()
    for c in crits:
        print(f"  ----  [{c['kind']}]  {c['name']}")
    print(f"\n  {len(cache)} runs cached, {time.perf_counter() - t_start:.0f} s this call")
    return dict(criteria=crits, readings=out,
                note="the transfer with regular customers, and the revolving door into a "
                     "weakened industry")


def station_config() -> dict:
    cfg = _config_diff(config_for(sys.modules["monetary_topology.network"],
                                  dict(BASE, **SKILL)))
    cfg.pop("seed", None)
    if "spec" in cfg:
        cfg["spec"].pop("seed", None)
    return {
        "carrier": "A19 industry layer on the A2 two-layer graph",
        "rounds": _a19.ROUNDS,
        "gate_seed": SEED,
        "seeds": list(SEEDS),
        "env": ENV,
        "envs": ENVS,
        "industry_base": BASE,
        "skill": SKILL,
        "cancel_shortfalls": list(CANCEL_D),
        "reference_shortfall": REF_D,
        "reread_shortfalls": list(READ_D),
        "a20_industry": dict(_a20.BASE, recovery_friction=_a20.FRICTION,
                             friction_spread=_a20.SPREAD),
        "need_scan": list(NEED_SCAN),
        "transfer_envs": YI_ENVS,
        "transfer_round": YI_AT,
        "transfer_share": YI_SHARE,
        "transfer_industries": list(YI_INDUSTRIES),
        "transfer_rates": list(YI_RATES),
        "transfer_shortfall": YI_D,
        "window": WINDOW,
        "churn_switch_rate": YI2_SWITCH,
        "return_rounds": list(YI2_BACK),
        "return_rounds_read": [-1] + list(YI2_BACK),
        "wall_needs": list(BING_NEEDS),
        "wall_shares": list(BING_SHARES),
        "wall_industry_base": BING_BASE,
        "wall_elasticities": list(BING_ELASTICITIES),
        "wall_elasticity_needs": list(BING_E_NEEDS),
        "wall_elasticity_share": BING_E_SHARE,
        "wall_proportional_needs": list(BING2_NEEDS),
        "wall_proportional_elasticities": list(BING2_ELASTICITIES),
        "wall_proportional_share": BING2_SHARE,
        "wall_counterfactual_costs": list(BING2_COSTS),
        "wall_counterfactual_elasticity": BING2_COST_E,
        "wall_counterfactual_needs": list(BING2_COST_NEEDS),
        "channel_rates": list(BING3_RATES),
        "channel_elasticities": list(BING3_ELASTICITIES),
        "channel_needs": list(BING3_NEEDS),
        "channel_share": BING3_SHARE,
        "wall_rates": list(BING4_RATES),
        "wall_build_rates": list(BING4_ETAS),
        "wall_shortfall": BING4_D,
        "wall_elasticity": BING4_E,
        "wall_need": BING4_NEED,
        "wall_strong_shortfall": BING4_D_STRONG,
        "wall_strong_rate": BING4_RATE_STRONG,
        "demand_shortfall": DING_D,
        "demand_channel_rate": DING_RATE,
        "demand_build_rates": list(DING_ETAS),
        "demand_transfer_rates": list(DING2_RATES),
        "demand_transfer_envs": list(DING2_NEEDS),
        "demand_join_rates": list(DING2_JOIN_ETAS),
        "non_default_fields": cfg,
    }


def write_record(section: str, payload: dict) -> None:
    """Merge one part into the station record. No wall-clock content."""
    doc = {}
    if RECORD.exists():
        doc = json.loads(RECORD.read_text(encoding="utf-8"))
    doc["stage"] = "A27"
    doc["diagnostic_only"] = True
    doc["diagnostic_reason"] = (
        "The station is open. The supply side and the transfer event are in, "
        "with switching off and on and with a return. The scan for the wall's "
        "environment is in and found none in which a weakened industry comes back "
        "with tenure off, so the tenure arms of the wall are not opened on this "
        "carrier; the demand side follows in the order the design sets.")
    doc["config"] = _fmt(station_config())
    doc.setdefault("sections", {})[section] = _fmt(payload)
    RESULTS.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  record: {RECORD.relative_to(ROOT)}, sections {sorted(doc['sections'])}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--part", choices=["gates", "jia2", "yi", "yi2", "bing", "bing2", "bing3", "bing4", "ding", "ding2"], default="gates")
    args = ap.parse_args()
    if args.part == "gates":
        payload = part_gates()
        write_record("gates", payload)
        return 0 if all(c["passed"] for c in payload["criteria"]) else 1
    if args.part == "jia2":
        payload = part_jia2()
        write_record("jia2", payload)
        return 1 if any(c.get("passed") is False for c in payload["criteria"]) else 0
    if args.part == "yi2":
        payload = part_yi2()
        if not payload:
            return 3
        write_record("yi2", payload)
        return 1 if any(c.get("passed") is False for c in payload["criteria"]) else 0
    if args.part == "ding2":
        payload = part_ding2()
        if not payload:
            return 3
        write_record("ding2", payload)
        return 0
    if args.part == "ding":
        payload = part_ding()
        if not payload:
            return 3
        write_record("ding", payload)
        return 1 if any(c.get("passed") is False for c in payload["criteria"]) else 0
    if args.part == "bing4":
        payload = part_bing4()
        if not payload:
            return 3
        write_record("bing4", payload)
        return 0
    if args.part == "bing3":
        payload = part_bing3()
        if not payload:
            return 3
        write_record("bing3", payload)
        return 1 if any(c.get("passed") is False for c in payload["criteria"]) else 0
    if args.part == "bing2":
        payload = part_bing2()
        if not payload:
            return 3
        write_record("bing2", payload)
        return 1 if any(c.get("passed") is False for c in payload["criteria"]) else 0
    if args.part == "bing":
        payload = part_bing()
        if not payload:
            return 3
        write_record("bing", payload)
        return 0
    if args.part == "yi":
        payload = part_yi()
        if not payload:
            return 3
        write_record("yi", payload)
        return 1 if any(c.get("passed") is False for c in payload["criteria"]) else 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
