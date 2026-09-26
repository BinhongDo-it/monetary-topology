"""A50 blocks 5 and 6: one run with extra switches, read the same way as blocks 2 to 4."""
from __future__ import annotations

import json
from dataclasses import replace

import numpy as np

import a50_grid
from a50_grid import rules_for

C = 0.12
LEVIES = (0.20, 0.15, 0.25)


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
