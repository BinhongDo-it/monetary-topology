# A3 restated: what this stage is for, and the intervention that decides it

**Standby document. Nothing is deleted by it.** `a3_asset_channel.md` remains in
place as the registered pre-registration and its numbers remain the ones on
record. This file states the scope the stage is now believed to have, and
registers the one arm that can settle it. If the intervention in §4 runs and
returns a verdict, this document's §5 becomes the basis for rewriting
`a3_asset_channel.md`; if it does not run, nothing here is a result.

Written 2026-08-10.

---

## 1. Why a restatement was needed

`a3_asset_channel.md` §9.9 records that no A3 criterion carries new content:
A3-1 is a regression check, A3-2 says of itself that it is "a floor, not a
finding", A3-3 and A3-4 are two readings of the same construction identity
`adjusted return ≡ −log γ`, and A3-7 is that identity's sign consistency.

§9.9 diagnosed this correctly and stopped there. What it did not supply is the
**reason** the identity readings are uninformative and the **test** that would
not be. Both are below.

An external review of the A3 files, run independently, reproduced §9.9's
diagnosis and added one point worth keeping: **A3b is orthogonal to A3-4.** A3b
moves who holds at `t = 0`, which is `H⁰`; A3-4 measures the terms differential,
which is `H¹`, and the price cancels out of it, so holding or not holding does
not enter. Fixing the opening construction cannot fix A3-4. That is correct and
is recorded here rather than in A3b, because it is a statement about A3.

The same review proposed two dispositions, and **both are rejected**, with
reasons, because rejecting them is part of the argument for what follows.

*Rejected: "re-register A3 as identity verification, which is B-track work."*
B1 proves that heterogeneous terms imply a non-zero holonomy and therefore no
global potential. B1 neither states nor can state that agents in a running
economy **traverse** the cycle. That is the one thing a simulation can supply
and a theorem cannot, and it can come out zero: with `turnover = 0` the cycle is
walked zero times, which the registered document already records as a
`DesignDeviation`. Traversal is not an identity check.

*Rejected: "the loop sum is a constant, not an exponent."* §2 of the registered
document devotes a section to exactly this. One traversal buys the fixed ratio
`γ_b/γ_a`; compounding comes from `N` round trips giving `(γ_b/γ_a)^N`. The
worry underneath — whether the compounding is real or definitional — is live,
and §4 is what settles it.

**Neither disposition adds a test.** Both are relabelling. The missing thing is
not a name for the current result; it is an arm whose outcome is not fixed by
construction.

---

## 2. What A3 is for

The source manuscript's Volume I §5 settlement ratchet and Volume II §2
non-integrability are asserted to be **one object read at two time scales**
(`b1_setup.md` §3). That assertion is what A3 exists to test. It decomposes into
three propositions, and only the third can fail in an informative way.

**P-A. The cycle is actually traversed.** A theorem says a cycle exists. It does
not say anyone walks it. In an economy with turnover, forced sales, a price
path, a wage bill and issuance, whether two agents repeatedly enter and leave
the same tier is a contingent fact about the dynamics.

*Status: established.* 38 to 50 traders per seed, up to 25 completed round
trips. *Can fail*: at `turnover = 0` it is zero, and the model warns.

**P-B. The algebra survives the embedding.** The three-line derivation in §2 of
the registered document assumes both agents enter and exit the same tier on the
same dates against a common sale price. A running economy does not guarantee
those conditions: holding periods may correlate with `γ`, forced sales may
select on it, the price may move between entry and exit.

*Status: established, 3.05% relative error.* That residual is the aggregation —
geometric collapse of `γ` to two classes, centrality binning, finite samples —
and it is the quantity of interest, because it measures how far the embedding
perturbs a relation that is exact in isolation.

*Why passing is weak*: the relation is an identity, so surviving is close to
guaranteed. The informative number is the size of the perturbation, not the fact
of agreement.

**P-C. The holonomy is load-bearing.** Remove it and the divergence must go.

*Status: not tested. This is the whole of §4.*

**P-C is the only one of the three whose outcome is not determined by
construction**, and it is the only one that can falsify the identification of
the ratchet with non-integrability. If divergence persists with the loop sum at
zero, the ratchet and the obstruction are **not** the same object, and
`b1_setup.md` §3 is wrong. That is a thing this project can learn.

---

## 3. What A3 is not for, stated as a prohibition

This project's largest open seam was recorded as: "nothing has shown that the A-side connectivity parameter generates the number
the B side measured". **That target is withdrawn here and its pursuit is
prohibited.**

The reason is not that it is hard. It is that the only way to hit it is to tune
`κ`, and `κ` is the terms dispersion — the quantity being claimed. **Calibrate
on what you are not claiming; never on what you are.** The registered
parameters already obey this rule and it is worth naming: `units_per_node = 1.1`
comes from dwellings per household, `turnover = 0.04` from housing turnover,
`rent_rate = 0.05` from gross rental yield, `ownership_rate` from occupancy
statistics. **None of those is a thing this framework claims.** `κ` is.

Further, B2's 78–85% within-share is produced by credit scoring, LTV, lender
competition, the legacy of redlining, GSE pricing grids and more. A two-hundred
node mechanism model that reproduced it would have reproduced the sum of dozens
of mechanisms it does not contain. **Matching would be bad news, not good.**

**A and B are not two halves of one empirical claim.** B1 is a theorem, B2 is a
check that the theorem's antecedent holds in the world, and the two together are
complete without A. A carries a different proposition, stated in §2.

**Permitted**: reporting the A-side within-share as a *curve* over `κ`, and
asking whether any single `κ` simultaneously satisfies several mutually
independent surfaces. That is the coverage test the source manuscript sets for
itself. **Forbidden**: selecting `κ` to land in 78–85%, and reporting any run so
selected as a result.

---

## 4. The intervention: `γ` does double duty and must be split

### 4.1 Why `κ = 0` cannot serve

`γ_{i,q}` is used twice: as the **premium paid**, `cost = γ_{i,q} · P_q`, and as
the **admission gate**, `claims_i ≥ γ_{i,q} · P_q`. §2 of the registered
document presents this as a feature — one parameter carrying the framework's
own distinction between a hole and a high price.

For an intervention it is a defect. Setting `κ = 0` zeroes the loop sum *and*
levels the gate, so it moves `H¹` and `H⁰` together. `MEASUREMENT.md` rule 4:
one switch, one thing. If divergence vanishes at `κ = 0`, the run cannot say
which channel did it.

This is the completion of a correction §9.9 already began. §9.9 observed that
defining `γ` as a terms premium made the price cancel, and that this "exposed
that the original A3 had `H⁰` and `H¹` mixed together". It identified the
mixing. It did not unmix it.

### 4.2 The split

Two parameters where there was one:

- `γ_pay` — what is paid. This is what enters the cochain and therefore the
  holonomy. The product graph sees prices paid and nothing else.
- `γ_gate` — the admission threshold. This is a restriction on the domain: a
  hole. It is outside the cochain by construction.

`γ_gate = γ_pay` recovers the current behaviour **bitwise**, the same discipline
as `elasticity = 0`. The split adds no freedom in the default configuration.

The correspondence to the topology is exact and is the reason the split is
principled rather than convenient: **`H¹` lives in what is paid, `H⁰` lives in
who may enter.** They were sharing a symbol.

### 4.3 The 2 × 2

Terms dispersion is now two knobs, `κ_pay` and `κ_gate`.

| | `κ_gate > 0` (gate differential) | `κ_gate = 0` (gate level) |
|---|---|---|
| **`κ_pay > 0`** (loop sum ≠ 0) | the registered configuration | `H¹` alone |
| **`κ_pay = 0`** (loop sum = 0) | **`H⁰` alone — the load-bearing arm** | double null |

**Registered readings, written before the run:**

- **Divergence collapses in the `H⁰`-alone cell** → the holonomy is
  load-bearing. The ratchet and the obstruction are one object, and A3's
  identification claim stands.
- **Divergence survives the `H⁰`-alone cell and collapses in the `H¹`-alone
  cell** → **the load-bearing channel is reachability, not the loop sum.** A3
  has been telling an `H¹` story about an `H⁰` mechanism. This outcome is
  registered as a live possibility and, if it occurs, is the stage's headline.
- **Divergence survives both single-channel cells** → the divergence is neither,
  and is produced by the price path or the rent transfer. Both are present in
  every cell and neither is `γ`.
- **The double-null cell must be near zero.** It is the zero calibration,
  `MEASUREMENT.md` checklist item 7. If it is not, nothing else in the table
  means anything.

### 4.4 The outcome measure, and its trap

The measure must be a **divergence**, not a level, and it must not have a
treated quantity in a denominator — A3-5 was rescaled once for exactly that
(§9.13). Registered:

> The paired growth-multiple spread: each node's terminal net worth divided by
> **its own opening claims**, and the spread taken as the ratio of the 90th to
> the 10th percentile of that quantity across the production layer.

Opening claims are pre-treatment and no cell can move them. The spread is
scale-free. The production layer is named because the claim is about who is
squeezed out, and because the financial layer's spread is dominated by the
residual stock it holds under A3b.

**Trap, recorded before running.** `κ_pay = 0` removes the terms premium and so
**lowers the average acquisition cost**. Nodes then have more claims left over,
which is a level effect, not a divergence effect. The base terms `γ̄_q` must be
rescaled so that the **mean** cost is held constant across cells and only the
**dispersion** moves. Without that the `H⁰`-alone cell is cheaper as well as
flatter, and the two are not separable.

---

## 5. Disposition of the existing seven criteria under this restatement

Nothing here is executed until §4 returns a verdict. Recorded now so the
rewrite is not designed after seeing the result.

| criterion | disposition |
|---|---|
| A3-1 closed channel reproduces A2 bitwise | **Keep unchanged.** It is a regression check, it says so, and regression checks are worth having. |
| A3-2 a gap opens between agents who started level | **Demote to a diagnostic.** It already says it is a floor. A floor is not a criterion. |
| A3-3 the gap compounds rather than levelling off | **Retire as a criterion, keep as an assertion.** `2.64e-15` is a machine-precision reading of an identity; it belongs in the test suite, not in the results table. |
| A3-4 the realised terms differential is the loop sum | **Keep, restated as P-B.** Its content is the 3.05%, which measures how far the embedding perturbs an exact relation. Report the perturbation, not the agreement. |
| A3-5 the gate binds at the high tier | **Void, not failed.** §9.14 established it cannot be evaluated: `open_tiers` never reaches resale, the high tier allocates fully at the opening, and no production-layer node can reach it at any supply. Under the `γ` split this criterion is subsumed by the `κ_gate` axis and should be rewritten there. |
| A3-6 the stock survives a generation | **Rewrite the domain.** The threshold sits on the median node while the framework's own claim is that the median node cannot hold a stock, so the criterion currently requires the model to contradict the thesis before A4 is unblocked. The correct form restricts A4 to the population that does hold a stock and says so in the criterion body rather than in a detail string. |
| A3-7 non-overlapping windows agree in sign | **Keep.** It is the guard against a one-off repricing and that guard is real. |
| **new** | **P-C, the 2 × 2 of §4.3.** The only arm whose outcome is not fixed by construction. |

---

## 6. Falsification

| observation | consequence |
|---|---|
| Double-null cell shows non-zero divergence | The measurement is broken. Nothing in §4 may be reported. |
| Divergence unchanged with `κ_pay = 0` | The loop sum is not load-bearing. `b1_setup.md` §3's identification of the ratchet with non-integrability is withdrawn for this carrier, and A3-4's agreement is recorded as decorative. **This is the outcome that would cost the most and it is registered as an ordinary possible result.** |
| Divergence collapses in both single-channel cells but is present in the full cell | The two channels are interacting rather than additive. The stage reports an interaction and does not attribute to either. |
| The mean-cost rescale of §4.4 cannot be made to hold | The cells are not comparable and the 2 × 2 is void. Reported as void rather than as a favourable reading. |

---

## 7. What A3 will still not be able to say, after all of this

Even with P-A, P-B and P-C all established, the stage supports exactly this:

> In a running stratified economy, agents repeatedly traverse the position-agent
> cycle; the holonomy of that cycle accumulates; and removing the holonomy while
> holding everything else removes the divergence.

It does **not** support "the real economy's holonomy causes the real economy's
distributional divergence". That would need the real-data counterpart of the
`κ_pay = 0` arm — setting mortgage terms uniform and re-running history — which
does not exist. Statutorily uniform carriers such as federal student loans have
been considered and are recorded as near-tautological in the placebo role; whether they are usable in the **intervention** role is a
different question and is **not resolved here**.

The limit is structural and is not a defect of this experiment. It is the
boundary between what a mechanism model can establish and what it cannot, and
naming it is cheaper than discovering it in review.

---

## 8. P-C, run. The loop sum is load-bearing; the gate is not distinguishable from zero

`experiments/a3c_load_bearing.py`, registered parameters, five seeds, three
hundred rounds. Sandbox and local runs agree to every printed digit.

| cell | `κ_pay` | `κ_gate` | gap | net of stretch | central | peripheral | across seeds |
|---|---|---|---|---|---|---|---|
| both | 1 | 1 | **+23.267** | +23.279 | +22.364 | −0.903 | same sign, `[+10.96, +38.31]` |
| `H1_only` gate removed | 1 | 0 | **+21.671** | +21.742 | +21.370 | −0.302 | same sign, `[+8.43, +27.17]` |
| `H0_only` loop sum removed | 0 | 1 | **+1.409** | +1.346 | −1.274 | −2.683 | **sign flips**, `[−16.26, +10.62]` |
| null | 0 | 0 | **0.000** | 0.000 | 0.000 | 0.000 | — |

**Guards, all of them, before the reading.** The zero calibration is two
independent executions of the null configuration and returns exactly `0.000`.
The mean acquisition cost is identical across cells to `1.86e-16`, so §4.4's
trap did not fire and the cells differ in dispersion alone. The paired
population is 41.6 nodes completing a round trip in *every* cell, with 11
dropped to form the intersection. No cell reported a `DesignDeviation`.
Deducting the stretch write-off changes nothing at the third digit.

### 8.1 The verdict

§4.3's first registered reading: **divergence collapses when the loop sum is
removed.** From `+23.267` to `+1.409`, while removing the gate instead leaves
`+21.671`. The holonomy is load-bearing on this carrier, and the identification
of the settlement ratchet with non-integrability stands.

The paired per-seed differences between `both` and `H1_only` are `+2.53, −0.85,
+12.51, +3.32, −9.53` — sign flips twice. **Removing the gate does nothing that
five seeds can see.**

### 8.2 What is refused, and why the refusal is part of the result

A first pass through this table quoted "H¹ 93.9%, H⁰ 6.9%". **That attribution
is withdrawn and the script now refuses to print it.**

`H0_only`'s five seeds are `4.02, 1.53, 10.62, 7.13, −16.26`. A mean of `+1.409`
sitting on a range that crosses zero is not a small positive contribution; it is
**not distinguishable from zero**. Quoting `6.9%` would assert a stable minority
share where the data say the channel might be doing nothing at all, or the
opposite of nothing.

This is the same defect this project has already noted in A4-4: a point
comparison with no sampling distribution behind it. The harness now checks sign
consistency across seeds — the weakest statistic that can refuse an attribution,
and one that needs no distributional assumption — and declines to decompose when
a cell's sign is unstable.

**The refusal makes the result cleaner rather than weaker.** The finding is not
a 94/7 split. It is: *the loop-sum channel is stable across every seed and
carries the divergence; the gate channel is indistinguishable from zero.*

### 8.3 Two readings the table does not support

**`H0_only` is not "the central third gains a little".** Both group means there
are **negative**: `−1.274` and `−2.683`. Relative to the null, a differential
gate with uniform payment leaves the traded population *worse off*, the
peripheral third more so. The small positive gap is a difference of two
negatives and must not be described as a gain.

**The magnitude does not transfer.** `κ_pay = 1` and `κ_gate = 1` are the same
number and are not the same strength of treatment. The payment premium is a
**per-round-trip multiplier** and compounds over the twenty-odd traversals the
population completes; the gate acts **once**, at admission. That a compounding
channel beats a one-off filter over three hundred rounds is partly arithmetic.
**Direction transfers, ratio does not** — the same limit recorded for A6's `R*`
and A3b's terminal ownership rate.

### 8.4 What this is not

It is **not empirical support** for the framework's claim about the world, and
it adds none. It is a within-model intervention: `do(κ_pay = 0)`. It establishes
that in this economy the obstruction is what produces the divergence, which is
what P-C was registered to ask.

The empirical leg is B2, on 28.1 million mortgages, and it is a separate leg.
§3's prohibition is unaffected: nothing here licenses tuning `κ` toward B2's
within-share, and §7's limit stands unchanged — the real-data counterpart of
this intervention does not exist.
