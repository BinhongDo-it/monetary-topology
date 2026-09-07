# B53 results: 8,972 exact collisions, and a control group the law predicts

RUN: 2026-09-06　DESIGN: `b53_prereg.md`

Script `experiments/b53_tuition_class_values.py`, record
`results/b53_tuition_class_values.json`.

## 1. The corpus

**5,605 schedules over 3,861 institutions**, 2020. 56 states and territories
requested, 56 returned. All 3,861 institutions matched a control code, none
unmatched. 124 rows carried a negative absence code and were dropped and
counted.

## 2. The reading

| criterion | reading | |
|---|---|---|
| **B53-1** every private institution writes one value across the three classes | 3,439 private schedules, **15 write more than one**, each named | **FAIL** · `known_answer` |
| **B53-2** how many schedules write `3 -> 1`, `3 -> 2` and `3 -> 3` | `3 -> 1` 3,617; `3 -> 2` 1,738; `3 -> 3` 250 | PASS · `own_reading` |
| **B53-3** every figure a whole dollar amount | 0 non-integer figures over 5,605 schedules | PASS · `premise` |
| **B53-4** coverage state by state | 56 requested, 56 returned, none empty; 124 rows dropped for a negative code, counted per state | PASS · `bookkeeping` |

**8,972 collisions**, and every one of them is exact: `3,617 x 2 + 1,738 x 1`.
Three classes written, one or two values produced.

## 3. The control group

| control | level | `3 -> 1` | `3 -> 2` | `3 -> 3` |
|---|---|---:|---:|---:|
| public | undergraduate | 136 | **1,227** | **243** |
| public | graduate | 57 | **500** | 3 |
| private nonprofit | undergraduate | **1,510** | 6 | 3 |
| private nonprofit | graduate | **1,246** | 2 | 1 |
| private for-profit | undergraduate | **480** | 1 | 0 |
| private for-profit | graduate | **188** | 2 | 0 |

Of 3,439 private schedules **3,424 write one value**; of 2,166 public schedules
**1,973 write two or three**.

**This is what makes the carrier more than a corpus.** The counting law says the
number of prices follows the number of distinct class values a programme writes,
and here the two sides of the split differ in exactly the way the law requires:
where residency is imposed from outside the transaction the schedule writes
distinct values, and where nobody imposes it the three classes collapse to one
number. The split is not the seller's to choose, and the reading demonstrates
that across 56 states at once rather than by reading one statute.

## 4. What the failing line returns

`B53-1` does not pass, and what it returns is its product: **15 named private
schedules that write more than one value**, four of them at both levels. Under
the four questions this carrier passes, a private institution has no residency
distinction to write, so each of these is a case to go and read.

The expectation withdrawn is "private is always `3 -> 1`", which was inferred
from the screen rather than measured. **The screen's discriminant is not
affected**: the fifteen are a named exception list, and the reason they can be
named is that the check was run.

## 5. Why the exactness matters beyond this station

The tariff corpus reports collisions bounded above by a two-decimal publication
step. **Here the premise that removes that bound is checked, not assumed**, and
it holds on all 5,605 schedules. A counting-law reading on this carrier
therefore takes no resolution caveat at all, which is the first such reading in
the corpus set.
