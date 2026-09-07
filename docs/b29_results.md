# B29 results: the cost band cannot destroy the defect, and the registered readout cannot recover it

**B29-3 read 2026-08-30.** Pre-registered design: the criteria are written into
the script that produced the record, the record carries their text, and every
quantity this run produced is reported.

**Where the other chunks live.** The locality theorem and its verification are in
[`b29_locality_theorem.md`](b29_locality_theorem.md). The two-threshold sweep is in
[`b30_propagation.md`](b30_propagation.md) §12.7 with the script at
`experiments/b29b_two_thresholds.py`. **This file carries B29-3 and everything
after.**

---

## 1. What was tested and why it had to come first

B29's arbitrage was an exact orthogonal projection: every visible cycle closes to
machine zero. **Real arbitrage has a cost band.** A loop whose discrepancy is under
the round-trip cost is not worth doing and stays open.

**If the band can swallow the defect, then a zero read on a real carrier cannot be
told from a defect hidden under cost**, and B29-1 has no interpretation. That is
D24's resolution floor and it is why this arm is first.

**Model.** Cycle-by-cycle Kaczmarz with a dead zone `tau`. For each visible cycle
`c`, if `|c·w| > tau`, move `w` so that `|c·w|` becomes exactly `tau`, the point
where the trade stops paying:

```
w <- w - ((c·w) - sign(c·w)·tau) / (c·c) · c
```

Ring of 20, range 2, horizon 6, so `ceil(n/r) = 10` and the defect survives by
Theorem 7. Eighty visible cycles. Three seeds. `tau` from 0 to 10 against a largest
pre-arbitrage cycle sum of about 3.7.

---

## 2. The structural fact, stated before any number

**Every update is a multiple of some `c` in `V`.** So `w` moves only inside
`span V`, and **the component of `w` orthogonal to `span V` is exactly conserved,
for every `tau`.** The defect lives there.

**So the cost band cannot destroy the defect. It can only raise the floor until the
defect is not measurable**, and quantifying that is what the arm is for.

**Confirmed numerically to the last digit.** The invariant `hol_inv = ((I - P_V) R)·w`:

| seed | `hol_inv` at `tau = 0` | at `tau = 10` |
|---|---|---|
| 0 | 0.1152 | 0.1152 |
| 1 | 0.0154 | 0.0154 |
| 2 | -0.8671 | -0.8671 |

Identical across the whole sweep, twelve values of `tau` each.

**And `resid` equals `tau` exactly** once `tau` is below the largest initial cycle
sum, since the iteration drives every visible cycle to the band edge. Above that,
no cycle is ever touched and `resid` stays at its initial value. **Both ends of the
design's reachability requirement are realised.**

---

## 3. The registered statistic fails, and that is the arm's result

The design registered `ratio = |hol| / resid`, where `hol` is the sum around the
ring. **`hol` is not conserved and it is not even well behaved.**

| seed | conserved `hol_inv` | range of `hol` over the sweep | sign flips |
|---|---|---|---|
| 0 | 0.1152 | -5.4116 to 0.1152 | 1 |
| 1 | 0.0154 | -0.0166 to 0.4339 | 2 |
| 2 | -0.8671 | -0.8671 to 4.6268 | 1 |

**The ring sum wanders up to forty-seven times its conserved value and changes
sign.** The reason is plain once seen: `R` has a large component **inside**
`span V`, the dead zone leaves `w` anywhere in a large feasible set rather than at
a point, and the ring sum reads mostly where in that set the system happens to sit.

**The registered verdict is therefore non-monotone in the noise floor**, which
disqualifies it as a resolution criterion:

```
tau ascending, M measurable, m marginal, S swallowed

|hol| / resid     seed 0   M M M m m m m m m m m m
                  seed 1   M M m S S S S S S S S S
                  seed 2   M M M M M m S m m m S S
```

**Seed 2 goes swallowed, then back to marginal, then swallowed again.** A criterion
that recovers as the cost band widens is measuring something other than
recoverability.

---

## 4. The replacement, and why it is a repair rather than a patch

**Statistic: `|hol_inv| / tau`**, the conserved invariant over the cost floor.

```
|hol_inv| / tau   seed 0   M M M M m S S S S S S S
                  seed 1   M M m S S S S S S S S S
                  seed 2   M M M M M m m S S S S S
```

**Monotone in every seed, one crossover each.** The crossover, at the design's
registered threshold of 3, is simply `tau = |defect| / 3`: 0.0384, 0.0051 and
0.2890 for the three seeds, tracking their different defect sizes.

**This passes failure mode 108's two gates.** The parameter is not fitted to
anything: `hol_inv` is the exactly conserved component, derivable before any run
from the fact that updates lie in `span V`. And it makes a new prediction that can
fail, in §5.

---

## 5. The design correction this forces on B29-1

**B29-1 was registered as "measure the cycle-sum defect as a function of cycle
length". Under a cost band that instruction is under-specified and would produce
garbage**, because §3 shows a single loop's sum is dominated by where in the
feasible set the field sits.

**Corrected instruction.** The defect must be extracted as **the component of the
observed field orthogonal to the span of the cycles the traders can actually
close**, which is a Hodge extraction over the whole observed field rather than an
arithmetic sum around one loop. **That is HodgeRank's operation** (Jiang, Lim, Yao and Ye, *Math. Prog. B* 2010,
arXiv:0811.1067), and this arm is the reason the project now needs it rather than
merely acknowledging it.

**Two consequences for any real reading.**

1. **Many loops, not one.** A reading that walks one long loop and reports its sum
   is not measuring the defect once transaction costs exist.
2. **The trading graph and the horizon must be known**, because the extraction
   projects onto the complement of `span V` and `V` is defined by what the traders
   can reach. **A reading that cannot state who can arbitrage what cannot state a
   defect.**

**The new falsifiable prediction.** On a real carrier, **the Hodge-extracted defect
should be invariant to the arbitrageurs' cost level while single-loop sums should
not.** Periods of higher trading friction should leave the extracted defect
unchanged and scatter the loop sums. **If the extracted defect moves with friction,
this reading is wrong.**

---

## 6. The resolution floor, stated operationally

```
a cycle defect is measurable iff  round-trip transaction cost < defect / 3
```

**That is D24's floor for this station, in units a data collector can check before
collecting.** It also says what to do when it fails: **look at longer loops**,
since by Theorem 7 the defect is carried by the winding class and does not shrink
with loop length, while the cost of the loops an arbitrageur would actually close
does not grow with it either.

---

## 7. Limits

1. **One graph family.** Ring with range 2 and horizon 6. The conservation argument
   is general and needs no simulation, but the size of `R`'s component inside
   `span V`, which is what makes the ring sum useless, is graph-dependent and has
   only been seen here.
2. **Three seeds**, which is enough because the conserved quantity is identical to
   the last digit in all of them and the estimator failure appears in all of them.
   **A fourth seed would confirm arithmetic that is already proved.**
3. **The dead zone is symmetric and the same for every cycle.** Real costs differ
   by route and by direction, and an asymmetric band is the obvious next variant.
   **It is not run and nothing here covers it.**
4. **The soft-threshold rule assumes the arbitrageur takes the whole profit above
   cost.** The alternative, closing the gap fully to zero whenever it is worth
   acting at all, was not run and would give a different `resid` while leaving the
   conservation fact untouched.

---

## Sources

**None external.** Everything here is computed by
`experiments/b29c_cost_band.py`, cached at `results/b29c_cost_band.json` by
`(n, r, L, seed)`. The theorem it rests on is in
[`b29_locality_theorem.md`](b29_locality_theorem.md) §2.
