# B8 instrument notes: what the published criteria depend on

**Purpose.** B8's eight published criteria are registered in
`b8_fannie_slice.md` and their verdicts are in `RESULTS.md`. Between those two
sits a run of instrument work (C8-1 through C13) that settled how the quantities
are constructed. **This file states the conclusions of that work that a
published criterion depends on, and nothing else.**

**Where the rest is.** The deliberation itself, 259 sections of it written day
by day, is the B8 inputs register. It is kept outside this repository, and the
section numbers cited in `experiments/b8_c*.py` docstrings refer to it. **The
evidence it produced is here and is not in that file**: fourteen result
documents (`results/b8_c8_arithmetic.md`, `b8_c8_1c_contract_payment.md`,
`b8_c8_1c_contract_payment_b.md`, `b8_c8_1e_undermode.md`,
`b8_c8_1f_freeze_recovery.md`, `b8_c9_cells.md`, `b8_c10_contract_move.md`,
`b8_c10_4_tier_carrier.md`, `b8_c11_deferred_balance.md`, `b8_c12_impact.md`,
`b8_c13_double_balance.md`, `b8_cmt_availability.md`, `b8_cmt_sensitivity.md`,
`b8_cmt_sensitivity2.md`) are tracked, are in English, and carry the numbers.

---

## 1. `V` is a contractual present value and never a market price

`b8_fannie_slice.md` section 3.1 defines `V` as the present value of the
remaining contractual obligation: the scheduled payment stream implied by the
current rate, the current actual balance and the remaining months to maturity,
discounted on a common curve. **No market price is read anywhere in B8.**

**The interest-bearing balance nets two fields out of field 12.** C8-1 ruled
that field 12 contains field 63 (a modification's principal forbearance) and
C11-1 ruled that it also contains field 108 (a payment deferral), so the
interest-bearing balance is **`12 − 63 − 108`**. That arithmetic is collected in
`b8_core.zero_interest_split` and both `quiet_pairs` and `b8_0a_gate` route
through it, verified bit-identical to the previous inline versions.

## 2. C8-1a: the control group does not land on 1.00, and the verdict is per downstream

The deviation is real: a median of +1 percent, with **more than half of quiet
months showing a balance decline strictly larger than the recomputed scheduled
principal**. Its consequence differs by eleven orders of magnitude between the
two things that consume it, so a single binary verdict was the wrong shape:

- **against C8-1** it is 1 point against a 15 to 20 point discriminant, acting
  in the same direction on both branches, and is negligible;
- **against B8-0a(i)** it is 1e-4 to 3e-2 against a floating-point tolerance of
  1e-15, and is fatal.

Evidence: `results/b8_c8_arithmetic.md`.

**A wrong column cannot produce this.** For more than 25 percent of 170 million
rows to land exactly inside [0.995, 1.005], fields 9, 12 and 17 must all be
correct, which is a stronger field identification than the eighteen behavioural
anchors that preceded it.

## 3. C8-1c: the lower-bound payment estimator is not robust, and was replaced

A segment minimum is an extreme-order statistic, not an estimate of the baseline
payment: **one flat-UPB month or one interest-only month punches through an
entire segment**, and the longer the segment the likelier that is. Replaced with
a **modal cluster**, after which the pairing rate rose from 53.5 and 65.7 percent
to 99.73 and 99.77 percent.

Evidence: `results/b8_c8_1c_contract_payment.md` and `_b.md`.

## 4. C9: the class-grid floor, and why B8-4b is VOID

C9 sets a floor of **20 observations per cell** for a class grid to be usable.
Of eleven candidate grids, **five clear the floor and hang on the borrower
rather than on the house or the location**; among those, the comfortable ones
are the coarse ones (`fthb` at two levels, `purpose` at three).

**What clears the floor is not decided by how many levels a grid has but by
which levels are merged.** `dti_complement15` clears at fifteen levels while
`dti_coarse6` fails at six, because complement absorbs `>60` into "outside
36-49" and coarse6 leaves it standing.

**B8-4b is VOID on this.** On (class by origination cohort) inside the Flex
window, **every one of eleven grids has a minimum of 0 or 1**. This is a
comparability problem in quantified form rather than a thinness problem: the
Flex window is 2017 to 2019, so the 2019Q1 vintage has at most one year of age
inside it and cannot complete a triangle, while 2002Q1 has fifteen.
`b8_fannie_slice.md` section 15.3 registers this as **not** a failure of the
stage, and the branch table sends the second domain to corporate credit.

**What C9 excludes are levels that are not classes**, not observations: a blank
means the field was not reported, which is a measurement gap. The all-levels
readings stay in the same table cell by cell so the effect of the exclusion is
visible. `purpose`'s `U` has only a layout document behind it, does not meet the
behavioural identification standard, is excluded with its count printed
(14 loans), and **may not be treated downstream as identified**.

Evidence: `results/b8_c9_cells.md`.

## 5. C10-4: the deferral carrier is field 108, not field 63

Taking section 14.4's own definition as a conjunction (`still` = rate unchanged
**and** term down by exactly one): **field 63 reads 0.0513 while field 108 and
the ADR code read 0.9966**, a factor of 19.4, in the same direction in all six
vintages. The first rising edge of field 108 and of the ADR code **coincide row
for row on 35,617 loans with zero exceptions**, which is behavioural
identification from two non-adjacent columns, one an amount and one a code.

Fields 63 and 108 **never fire on the same row**, and 63's fingerprint (rate
0.4610, term 0.8423) is the modification described in section 14.3's leg 2.
**Nothing registered was wrong; only which column the implementation cut on.**

Evidence: `results/b8_c10_4_tier_carrier.md`.

## 6. C10-1: `t_M == t_B` loops are triangles

`t_M == t_B` is 76.8 percent of registered loops, and the objection was that the
`modified → current` edge spans zero months on them. **The contract on that row
does move**: leg A `any` is 0.6905 to 0.9986 against leg B (a known re-signing
during delinquency) at 0.6784 to 1.0000, an A/B ratio of 0.957 to 1.224, both
four decimal orders above the noise floor. **The floor validates the criterion
at the same time**: on 919,207 clean-cure rows `term` reads exactly 0.0000, so a
wrong "minus one" baseline would have lit up all nine hundred thousand.

**`ω₃` is measurable on only 10,449 loops, which is a selected subsample, and
that qualification travels with every citation of it.**

Evidence: `results/b8_c10_contract_move.md`.

## 7. Three different quantities in this repository are called a floor

This is the one naming hazard a reader has to know about.

| name | what it is | who uses it |
|---|---|---|
| **`N_cure`** | `MAD(ω − closed)` on the ideal subset of the clean-cure arm, 2.68e-08 to 5.22e-08 | B8-0b, B8-1, B8-3, B8-4a, all correctly |
| **`N_placebo(L)`** | `median\|ω\|` on never-delinquent loans over a window of length `L`, 2.821e-08 to 3.923e-08 at `L = 2` | `b8_0a_gate`, correctly. **It is a function of `L`**: 2002Q1 climbs 170-fold from `L=2` to `L=7`, so citing it without `L` is meaningless |
| **`IB_RESIDUAL`** | the clean-cure loop minus its closed form, 6.469e-06 to 6.707e-05. **This is a signal, not a floor**, and the same table measures it as 172 to 2,343 times the floor | it was used as a denominator in four places and that has been corrected |

The first two are different quantities with the same physics (different
population, construction, statistic and window length), and their per-vintage
ratio lands between 0.90 and 1.39 with a median of 0.95. **Two independent
populations landing in one place is corroboration of B8-0b's finding that the
floor is the quantile rounding of field 12**, not a contradiction.

**A floor and a signal must be drawn on the same measurable set.** The one
downstream consequence of getting this wrong: B8-3's exemption from re-running
under an alternative curve construction rested on a comparison with the wrong
denominator, so **B8-3 was re-run for real** (`results/b8_3_curve.md`), keeping
its sign in all six vintages with permutation p of 0.001 throughout.

## 8. The quiet-month filter

A quiet month requires a continuous period, `00` delinquency on both sides, an
empty modification flag, **an empty zero-balance code**, a positive UPB, and an
unchanged current rate. Three corrections to it are worth knowing:

- **`upb[current row] > 0`** was added because the old filter let the pair
  "positive balance to zero balance" into the sample, where `obs` equals the
  whole balance. It deletes zero pairs in all six vintages today, **so it is a
  guard rather than a fix**, and it is kept because what actually blocks
  terminating pairs (an empty remaining legal term on the termination row) is
  itself leaking on 5 / 2 / 5 / 1 / 0 / 0 rows and is changing over time.
- **`require_never_deferred` is now `False`** and **`ib_net` is `True`**, per
  section 5 above. The old parameters are kept and reproduce the old sample.
- The old definitions are bit-reproducible, and the double reports are in
  `results/b8_quiet_delta.md` and `results/b8_c12_impact.md`.

## 9. What this file does not contain

The reasoning that produced any of the above, the readings that were superseded
along the way, and the instrument defects found and fixed. Those are in the B8
inputs register outside this repository. **Anything a published criterion rests
on is either in this file, in `b8_fannie_slice.md`, in `RESULTS.md`, or in one
of the fourteen result documents named at the top.**
