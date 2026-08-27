"""Where the 0.50 power floor comes from: it is gate two written a second way.

**The debt.** `D17` records a failure as undecidable when the test's power is
below `0.50`, and `D5` requires every number in a criterion to have a source
outside this repository. The `0.50` had none on record.

**The source, and it is not a convention.** For a one-sided test of `theta = 0`
that rejects when `theta_hat / se > z`, the power at a true effect `theta` is

    power(theta) = Phi(theta / se - z)

so **power is exactly 0.50 when `theta = z * se`**, which is the critical value
itself. Power below 0.50 therefore means one thing only: **the effect being
tested is smaller than the value the instrument needs to see before it will call
anything non-zero.** A failure there is a statement about the instrument.

**And that is gate two.** `D14` asks whether `z * se` fits inside the band the
criterion has to resolve, `z * se < band`. Substituting `theta = band`:

    gate two passes   <=>   band > z * se   <=>   power(band) > 0.50

**The two gates are one inequality written twice**, one on the standard error
and one on the power. That is why the floor is `0.50` and not `0.40` or `0.60`:
no other value makes them the same line.

**What a failure is worth, printed beside it.** A non-rejection has likelihood
ratio `(1 - alpha) / (1 - power)` in favour of the null, and that ratio is the
whole evidential content of a failure. At the floor it is `1.90` for a one-sided
test at five per cent. **A failure at the floor is worth less than one bit.**

This file runs no model. It checks the identity on a grid and prints the ratio.

Usage::

    python experiments/d14_d17_equivalence.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "d14_d17_equivalence.json"

#: One-sided critical values. 1.645 is the one this repository's gate two uses.
Z = {"0.10": 1.2815515655446004, "0.05": 1.6448536269514722,
     "0.025": 1.9599639845400545, "0.01": 2.3263478740408408}



def fixed(o, nd: int = 8):
    """Every float written to disk goes through here.

    **The derived-file rule this repository already carries**: write floats
    through an explicit format rather than through ``repr``, so a last-digit
    difference between two builds does not surface as a text diff. It was not
    hypothetical — the same code over the same cached bytes gave last-digit
    differences between a Windows run and a Linux one, and the record stopped
    reproducing byte for byte. Eight decimals is far below anything reported.
    """
    if isinstance(o, float):
        return round(o, nd)
    if isinstance(o, dict):
        return {k: fixed(v, nd) for k, v in o.items()}
    if isinstance(o, list):
        return [fixed(v, nd) for v in o]
    return o

def phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def power(theta: float, se: float, z: float) -> float:
    return phi(theta / se - z)


def main() -> int:
    rows = []
    # The identity: at theta = z * se the power is one half, for every se and z.
    for name, z in sorted(Z.items()):
        for se in (0.001, 0.01, 0.1, 1.0, 10.0, 1000.0):
            rows.append({"alpha": name, "z": z, "se": se,
                         "theta_at_critical_value": z * se,
                         "power_there": power(z * se, se, z)})
    worst = max(abs(r["power_there"] - 0.5) for r in rows)

    print("identity: power at theta = z * se, over %d combinations of alpha and se"
          % len(rows))
    print("  largest departure from one half: %.3e" % worst)
    print()

    # The two gates agree at every point on a band grid, by construction and in fact.
    z = Z["0.05"]
    se = 0.60 / math.sqrt(2242)   # B21's measured per-event standard error
    grid = [0.0005, 0.001, 0.002, 0.005, 0.01, 0.0126, 0.02, 0.05, 0.10, 0.15, 0.25]
    agree = []
    print("gate two against the power floor, se = %.6f (B21's measured value)" % se)
    print("  %10s %12s %10s %10s %8s" % ("band", "z * se", "gate two", "power", "agree"))
    for band in grid:
        g2 = band > z * se
        pw = power(band, se, z)
        ok = (g2 == (pw > 0.5))
        agree.append(ok)
        print("  %10.5f %12.6f %10s %10.4f %8s" % (band, z * se, g2, pw, ok))

    print()
    print("what a failure is worth, likelihood ratio (1 - alpha) / (1 - power):")
    lrs = []
    for pw in (0.00, 0.25, 0.50, 0.525, 0.55, 0.80, 0.95):
        for a in (0.05, 0.10):
            lrs.append({"power": pw, "alpha": a, "likelihood_ratio": (1 - a) / (1 - pw)})
    for r in lrs:
        print("  power %.3f  alpha %.2f  ratio %6.2f" % (r["power"], r["alpha"], r["likelihood_ratio"]))
    one_bit = {a: 1 - (1 - a) / 2 for a in (0.05, 0.10)}
    print("\n  a failure carries one bit (ratio 2) at power %.3f for alpha 0.05 and "
          "%.3f for alpha 0.10" % (one_bit[0.05], one_bit[0.10]))
    print("  so the 0.50 floor sits just below the one-bit line, on the permissive side")

    criteria = [
        {"name": "D-1  power is one half exactly at the critical value, for every alpha and se",
         "passed": worst < 1e-12,
         "detail": "largest departure from one half over %d combinations: %.3e" % (len(rows), worst)},
        {"name": "D-2  gate two and the power floor agree at every band on the grid",
         "passed": all(agree),
         "detail": "%d of %d bands agree, se = %.6f, z = %.6f"
                   % (sum(agree), len(agree), se, z)},
        {"name": "D-3  print what a failure at the floor is worth",
         "passed": True,
         "detail": "likelihood ratio for the null given a non-rejection is 1.90 at alpha 0.05 "
                   "and 1.80 at alpha 0.10, both below one bit; the one-bit line is power "
                   "%.3f and %.3f respectively" % (one_bit[0.05], one_bit[0.10])},
    ]

    record = {
        "stage": "D14/D17 equivalence",
        "step": "power_floor_source",
        "diagnostic_only": True,
        "diagnostic_reason": ("This is arithmetic about two of the repository's own gates and not "
                              "a reading about the world. It supplies the source D5 asks for."),
        "identity_worst_departure_from_one_half": worst,
        "gate_grid_agreement": {"bands": grid, "agree": agree, "se": se, "z": z},
        "one_bit_power": one_bit,
        "likelihood_ratios": lrs,
        "rows": rows,
        "criteria": criteria,
    }
    OUT.write_text(json.dumps(fixed(record), indent=2, sort_keys=True, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    print("\nwrote %s: %d criteria, %d passing"
          % (OUT.name, len(criteria), sum(1 for c in criteria if c["passed"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
