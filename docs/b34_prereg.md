# B34 preregistration: does a published rate table leave a break at its own boundaries

**The hypothesis is out of sample.** The framework's claim is that a written rule
which names a set of positions leaves those positions readable in the quantity it
governs. The UK National Minimum Wage names age boundaries in a statutory
instrument, changes them on dated occasions, and governs an hourly wage that is
measured independently of the statute. **The question is whether the break in the
wage distribution sits where the statute puts it.**

Criteria are written in the scripts that produce each record, each record carries
the criterion text, and every quantity a run produces is reported.

---

## 1. Criteria

Four arms. **The middle state of the three exists on every one of them.**

| arm | what is read | PASS | FAIL | undecided |
|---|---|---|---|---|
| **B34-1 position** | per rate year, which ages the break in the wage floor falls on | all on that year's statutory boundaries | **on a non-statutory age, meaning a finer partition than the statute writes**; **nothing at a statutory boundary, meaning a coarser one** | the single-year-of-age cells cannot separate a break from noise |
| **B34-2 movement** | around a boundary change, does the break move with it | it moves **and the old position goes** | the old position stays | fewer than two readable years on either side of the change |
| **B34-3 placebo** | the ages the statute does not name that year | no break there | a break there | as B34-1 |
| **B34-4 structure** | the boundary set taken from the statute equals, word for word, the set the code uses | equal | not equal | none |

**The load-bearing half is B34-2's second clause, that the old position goes.**
Every rival account in which age alone raises wages predicts the old break stays,
because nobody becomes less skilled at 25 when a regulation is amended.

**Boundary changes, all with statutory dates:**

```
2010-10   adult rate boundary 22 -> 21
2016-04   living wage set at 25
2021-04   living wage boundary 25 -> 23
2024-04   living wage boundary 23 -> 21, the 21-22 band merged away
```

Low pay as a dimension is fixed before the data as enforcement intensity and does
not count as a finer partition, unless that low pay is itself split by a nameable
rule.

## 2. Gate numbers

Computed before opening. The gate that binds here is the resolution floor: is the
non-zero readable, that is, how many of the instrument's own floors does it stand
on. **This station's criteria are point predictions about position, not an
estimate against a band, so the band-readability gate and the power gate do not
apply.** The visibility multiple is fixed at `1.645`, the single-sided five per
cent critical value, which is the multiple at which the power gate and the
readability gate are the same inequality.

## 3. Reachability

Each FAIL branch was checked against what was already known before the run, to be
sure it had probability mass left. The branch that was at risk is B34-2's
undecided state, which requires two readable years on each side of a change; that
is a data question and is tracked as such.

## 4. Carrier and definitions

**Quarterly Labour Force Survey microdata, End User Licence**, four quarters per
rate year, one rate year running 1 April to 31 March so that it matches the
statutory rate changes. Income questions are asked at waves one and five only,
and those are exactly four quarters apart, so the four quarters of a rate year
hold disjoint people. That is measured, not assumed.

**A second arm, B34-5, runs on published ASHE percentiles** and needs no
microdata: a difference in differences across the 2016-04 change, on age groups
whose boundaries the statutory boundary crosses.

## 5. Additions made while the station ran, added and never removed

### 5.1 The scale is fixed by reporting both

Every boundary is reported with **both** the level difference `delta = p(a+1) -
p(a)` and the survival ratio `r = p(a+1) / p(a)`. The verdict reads the survival
ratio; the level difference is printed beside it on the same line. Reason: `p` is
a share decaying toward zero, and a boundary pushes people up over a line, which
is a hazard rather than a level difference, while a level difference necessarily
shrinks as `p` shrinks whether or not a boundary is there. **Where the two
disagree, both are reported and the disagreement is stated.**

### 5.2 One common threshold across all ages

For rate year `t`, take that year's adult rate `R(t)` as the single threshold and
compute, for every single year of age `a`, the share of employees whose hourly
pay falls below `R(t)`. **All ages use the same `R(t)`.** Using each age's own
statutory rate would carve the read partition out of the written one, which is
circular. Under a common threshold the profile does not know where the boundaries
are, so where it bends is a reading.

### 5.2a Which `R(t)` when a year has two adult bands

From the introduction of the living wage every year carries both a living wage
and a next-highest adult band, so "the adult rate in force" is ambiguous. Both
are drawn and neither is chosen:

```
R_main(t) = that year's National Living Wage
R_alt (t) = that year's next-highest adult band
```

Both are constants across all ages and neither knows where the boundaries are, so
neither is circular. They differ only in which end of the profile saturates,
which is a resolution question one scan answers.

### 5.3 Step order, one step audited at a time

| step | what it does | condition to continue |
|---|---|---|
| 1 | count cells only; list the variables recognised in each file, build a cache, print the three thinnest single-year-of-age cells | the thinnest three carry enough to put the binomial standard error of `p` under the boundary effect |
| 2 | draw the `p(.,t)` profile, per year, draw only | the profile is readable |
| 3 | run the kink detector, report every position | none |
| 4 | report the two numbers of 5.1 at every boundary, score arm one | |
| 5 | score arm two on the years around a boundary change | |
| 6 | placebo and structural check, score arms three and four | |

**If step 1 does not pass, no other step runs.**

### 5.4 The placebo ages must avoid the two benefit-system boundaries

The cited literature names them: `"The main changes in the benefit system happen
to individuals at age 18 and then at 25."` So a break read at 18 or at 25 cannot
be attributed to the rate table alone. At 25 the available identification is arm
two, since the break there disappears in 2021 while the benefit boundary does not
move. At 18 there is no matching movement, so it is undecided.

### 5.5 A boundary lives in a gap, so the criterion is indexed by gap

The floor rises on reaching age `b`, so the jump lies between `b-1` and `b`. A
second difference indexed by age splits one step across two indices: for a profile
flat everywhere except one gap of size `d`, `ch(a) = -d` and `ch(a+1) = +d`
exactly, and nothing elsewhere. An age index therefore cannot say which side of
it the boundary is on. The criterion is indexed by gap and the statistic follows:

```
D(a)      = p(a) - p(a+1)
excess(a) = D(a) - ( D(a-1) + D(a+1) ) / 2  =  ( ch(a+1) - ch(a) ) / 2
a boundary at age b lives in the gap (b-1, b)
```

No number in the profile record changes; only which combination the criterion
reads.

**Arm one is scored on order, not on a count of profiles.** The eight profiles per
rate year are eight readings of one quantity off overlapping data, and requiring
each of N to clear a line is a barred shape. The null is enumerated: with `G`
scorable gaps of which `K` are statutory, all `C(G, K)` placements are written out
and the rank sum of the statutory gaps is read against them. No constant is
chosen. The line for the coarser-partition branch is the null's own centre,
`(G+1)/2`.

**Arm four writes the statute side out in its own script rather than importing it
from the steps it checks**, because a check that imports what it checks checks
nothing. Two exclusions belong to the statute side and are checked as such:
entitlement begins on ceasing to be of compulsory school age, `National Minimum
Wage Act 1998 s.1(2)(c)`, which is fixed by school year and not by a birthday, so
16 and 17 are not boundaries; and the apprentice rate reaches an apprentice who is
either within twelve months of starting **or** under nineteen, `National Minimum
Wage Regulations 2015 reg 5(1)`, disjunctively, so it crosses the age bands and 19
is not a boundary.

### 5.6 Country scope

Participation in education or training to 18 is compulsory in England and not in
Scotland, Wales or Northern Ireland, so any account of the profile that runs
through the education exit is an account about England. The profile builder takes
a scope:

```
uk           every country, the default, and the main specification
england      COUNTRY = 1
non-england  COUNTRY in {2, 3, 4, 5}
```

`COUNTRY`, labelled `Country within UK`, carries five categories and not four:
England, Wales, Scotland, Scotland North of Caledonian Canal, Northern Ireland.
The two Scottish categories are added, and the collapse is checked inside the
extractor against `CTRY9D`, a separate nine-digit country code in the same files.

**The scope is a printed object and not a verdict.** The contrast between England
and the rest is gated before it is run, and the gate is in the results.

## 6. Registered explorations

Two predictions were registered before the data that would judge them were on
disk, and both were judged. They are recorded here so that they are not tested a
second time.

**Adoption speed.** The living wage boundary moved from 25 to 23 on 2021-04. If
the new position is unreadable because employers have not yet moved to it, then
the second year after the move should show it more strongly than the first. **This
prediction can fail.**

**Cohort scarring.** Hiring freezes cut entry-level roles first, so a cohort
leaving education into the 2020 freeze would carry a wage penalty. That account
predicts the anomaly travels with the birth cohort rather than staying at an age.
**This prediction can fail, and the two accounts separate because they put the
anomaly at different ages in a later rate year.**

## 7. The ASHE arm, B34-5

Published ASHE percentiles by age band, with the age-band edges fixed by the
publication and the statutory boundary crossing them, so the dose differs by band
without the bands moving. The main contrast is the 2016-04 change; the scale is
fixed to logs before any difference is taken; the pre-trend is the load-bearing
half and is judged, while the post-trend is reported and not judged.


---

## 8. The fourth rate year, 2018-19

Written before the fetch. Only-add: nothing above changes.

### 8.1 What goes in, and where it comes from

SI 2018/455 reg 2(2) and reg 2(3)(a) to (d), in force 1 April 2018. That
instrument substitutes figures only and carries no age wording of its own; the
age wording is in SI 2015/621 reg 4A as in force that day. Rates £7.83, £7.38,
£5.90, £4.20 and £3.70; boundary set {18, 21, 25}, the same set as 2019-20.
Four independent sources agree cell for cell.

### 8.2 No criterion is added and none is changed

The year goes through the same six steps and is scored against the same
criteria. It enters in exactly two places: every criterion scored per year
gains a year, and arm two's third state is a count of readable years.

Fixed before the run: **this year changes no verdict already reached on arms
one, three and four.** If it does, the pipeline was broken by the act of adding
a year, which is a code question and not a data one.

### 8.3 What arm two gains, and what it cannot gain

`PRE_YEARS` mirrors `POST_YEARS`, and a new section reads ages 25 and 23 in
each pre-move year.

1. The year count. The criterion's third state is "fewer than two readable
   years on each side", and with 2018-19 there are two on each side, so that
   clause stops applying.
2. A second, independent pre-move reading of the old boundary at 25. That half
   had been resting on one year.

Also fixed before the run: **the verdict does not turn on either.** It comes
from the second half of the PASS conjunction, age 23 clearing the floor on 1 of
8 profiles in 2021-22, and that is a count of profiles rather than of years.

Reachability, all three branches: both pre-move years read the old boundary,
neither does, or one does and the other does not. Existing readings cover only
2019-20, so no branch is closed by construction.

### 8.4 How rule 19 is checked

Each of the six records is copied to a dated baseline before the run. After the
run, the records are compared key by key with the 2018 entries removed, and
they must be identical. The only differences allowed are pooled quantities:
the file list, the total row count, the pooled rank sum, and the year strings
inside criterion text. Any other difference means the pipeline changed.
