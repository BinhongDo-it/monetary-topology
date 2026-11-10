"""A50 blocks 5 and 6: one run with extra switches, read the same way as blocks 2 to 4."""
from __future__ import annotations

import json
from dataclasses import replace

import numpy as np

import a50_grid
from a50_grid import rules_for

C = 0.12
LEVIES = (0.20, 0.15, 0.25)
#: Wages due over the last 50 rounds on this carrier (8 a round). A run that paid less than half
#: of it has stalled; a difference in shares that involves such a run is not a reading of the
#: distribution (A50 design, block 5).
WAGE_DUE = 400.0
ACTIVE_FLOOR = 0.5 * WAGE_DUE


def active(x) -> bool:
    return x["wage_paid_last50"] >= ACTIVE_FLOOR


def read_by_activity(values, act) -> dict:
    """values and act are aligned lists over pairs. Signs over the pairs whose every run is
    active, signs over the stalled ones, and whether the active pairs give one direction."""
    def sg(v):
        return sorted({"+" if x > 0 else ("-" if x < 0 else "0") for x in v if x is not None})
    on = [v for v, a in zip(values, act) if a and v is not None]
    off = [v for v, a in zip(values, act) if not a and v is not None]
    s_on = sg(on)
    return {"pairs": len(on) + len(off), "active_pairs": len(on), "signs_active": s_on,
            "signs_stalled": sg(off), "read": bool(on) and len(s_on) == 1 and "0" not in s_on}


def rules(regime, arm, levy, **extra):
    knob = {} if levy == 0.20 else {"levy_rate": levy}
    return replace(rules_for(regime, arm, C if arm != "none" else 0.0, **knob), **extra)


def row(m, secs, **tags) -> dict:
    import a50_block1
    f_ok, f = a50_block1.fund_check(m)
    l_ok, lk = a50_grid.lock_check(m)
    f = {k: v for k, v in f.items() if k not in ("account_residual", "cash_residual")}
    h = m.history
    wage = np.asarray(h.wage_paid, dtype=float)
    return {**tags, "seconds": round(secs, 3), "fund_ok": f_ok, "lock_ok": l_ok, **f, **lk,
            "issuance_total": round(float(np.sum(h.issuance)), 4),
            "circulating_end": round(float(np.asarray(h.total_claims)[-1]), 4),
            "wage_paid_last50": round(float(wage[-50:].sum()), 4),
            "pf_target_cut": round(getattr(m, "pf_target_cut", 0.0), 4),
            "pf_released": round(getattr(m, "pf_released", 0.0), 4),
            **a50_block1.preview_row(m)}


def unseen_rows():
    """Block 2's rows at c 0.12 and 0, levy 0.20 and the two knob levies."""
    rec = json.loads(a50_grid.OUT.read_text(encoding="utf-8"))
    out = [dict(x, levy=0.20) for x in rec["grid_rows"] if x["c"] in (0.0, C)]
    out += [dict(x, levy=x["knob"]["levy_rate"]) for x in rec["knob_rows"]]
    return out


def mean_cells(rows, keys, group):
    out = {}
    for x in rows:
        out.setdefault(tuple(x[g] for g in group), []).append(x)
    return {k: {q: round(float(np.mean([r[q] for r in v if r.get(q) is not None])), 4) for q in keys}
            for k, v in out.items()}
