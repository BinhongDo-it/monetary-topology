# B34 results: the break is on the statute, it moves when the statute moves, and one gap inside a band is flat when both should be

Criteria in [`b34_prereg.md`](b34_prereg.md). **All four microdata arms are
scored. B34-5, the ASHE arm, is scored and undecided at one cell.**

Records: `b34_lfs_profile.json`, `b34_lfs_kink.json`, `b34_lfs_arm1.json`,
`b34_lfs_arm3_arm4.json`, and the `_england` and `_noneng` scope variants;
`b34_arm5_did_main_2015_2017.json` and `b34_arm5_did_pretrend_2014_2015.json`.

---

## 1. What the station reads on, and what it measured about itself first

Twelve quarters, three rate years: 2019-20, 2021-22, 2022-23. The rate table in
each, from the instrument:

| in force | living wage | next adult band | 18 to 20 | under 18 | apprentice |
|---|---|---|---|---|---|
| 2019-04 | 8.21 (25+) | 7.70 (21-24) | 6.15 | 4.35 | 3.90 |
| 2021-04 | 8.91 (23+) | 8.36 (21-22) | 6.56 | 4.62 | 4.30 |
| 2022-04 | 9.50 (23+) | 9.18 (21-22) | 6.83 | 4.81 | 4.81 |

`SI 2019/603`, `SI 2021/329`, `SI 2022/382`. Four independent sources agree cell
by cell except one, where a secondary table's 21-22 figure for 2021 reads `4.30`,
which is the apprentice figure from the row above; the instrument settles it at
`8.36`, and the disagreement is named rather than averaged.

**The four quarters of a rate year hold disjoint people, and that is measured.**
The income questions are asked at waves one and five only and those are exactly
four quarters apart, so the collision table returns zero of eight entry cohorts
appearing twice. That measurement is what makes the analytic floor below valid.

**Two instruments, and they behave differently.** `HRRATE` is the directly asked
hourly rate; `HOURPAY` is derived from weekly pay over hours. **`HRRATE` codes
998 and 999 as special values, and they are positive and larger than any
threshold**, so they were counting as "not below" and their share rises
monotonically with age, 18.0 per cent at 16 to 34.8 per cent at 28, deforming the
profile's shape. They are dropped, sourced to the LFS User Guide, and the
pre-cleaning numbers are kept.

**`HOURPAY` codes missing as `-9`.** In one file 76,481 of 86,548 rows carry it,
so a count of non-null values overstates the sample tenfold. Counting values above
zero gives 7,736 usable readings for 2019-20 across ages 16 to 30.

## 2. Arm one: the break sits on the statutory gaps

The statistic is `excess(a) = D(a) - (D(a-1)+D(a+1))/2` with `D(a) = p(a) -
p(a+1)`, the fall across a gap net of its neighbours, which equals
`(ch(a+1) - ch(a))/2`. The null for the order is enumerated, `C(12,3) = 220`
placements per rate year, convolved across the three years.

| rate year | order of gaps by mean excess, `*` statutory | statutory ranks | rank sum | exact p |
|---|---|---|---|---|
| 2019-20 | `20-21*  24-25*  26-27  18-19  27-28  23-24  17-18*  28-29  22-23  21-22  19-20  25-26` | 1, 2, 7 | 10 | 0.0500 |
| 2021-22 | `18-19  20-21*  28-29  26-27  21-22  17-18*  25-26  23-24  22-23*  24-25  27-28  19-20` | 2, 6, 9 | 17 | 0.3636 |
| 2022-23 | `20-21*  22-23*  25-26  17-18*  18-19  23-24  26-27  27-28  28-29  24-25  19-20  21-22` | 1, 2, 4 | 7 | 0.0091 |

**Pooled rank sum 34 against a chance 58.5, exact p = 0.00427.**

| criterion | | |
|---|---|---|
| B34-1a the break sits on the statutory gaps, by order | pooled exact p 0.00427 against a single-sided 0.05 | **PASS** |
| B34-1b no gap outside the statute outranks every gap inside it | 2021-22: the 18-19 gap does; 2019-20 and 2022-23 clean | **FAIL** |
| B34-1c no statutory gap ranks worse than chance would give it | 2019-20: 17-18 at rank 7; 2021-22: 22-23 at rank 9; chance rank 6.5; 2022-23 clean | **FAIL** |

**The two failures each have a name and they are not the same failure.** The
22-23 gap ranks 9th in 2021-22 and 2nd in 2022-23, which is the adoption speed
measured on arm two appearing again in a different statistic. The 17-18 gap is
unreadable on excess in all three years while being the strongest gap in the table
on the survival ratio the scale rule fixes: at the 2022-23 main threshold with
apprentices held out it reads `|log r| / se = 3.71`, the largest of thirteen gaps.
The two statistics disagree there because excess nets 17-18 against 16-17 and
18-19, and both of those carry institutional content of their own. **That is a
statement about the instrument at that gap.**

## 3. Arm two: the boundary that moved

The living wage boundary moved from 25 to 23 on 2021-04. The other two boundaries
did not move. Eight profiles per rate year, readings in floors:

| | 2019-20 | 2021-22 | 2022-23 |
|---|---|---|---|
| age 25, the old boundary | **+2.22, visible on 7 of 8** | -0.30, 0 of 8 | -0.73, 0 of 8 |
| age 23, the new boundary | -0.30, 0 of 8 | +0.75, 1 of 8 | **+1.05, 4 of 8** |

| criterion | | |
|---|---|---|
| B34-2a the old position disappears | 7 of 8 in the year it was a boundary, 0 of 8 in both years after; the numerator changes sign in 6 of 8 | **PASS** |
| B34-2b the break follows to the new position | 1 of 8 then 4 of 8 | **not established** |
| **B34-2 overall** | PASS is the conjunction, and there is still only one readable year before the move | **undecided** |

**The disappearance is not a resolution artefact.** The floor widens by at most
1.9 times between the years while the numerator changes sign, and counterfactually
2019-20's reading placed in 2021-22's floor would still read 1.67 to 2.53.

**A year effect is excluded by magnitude rather than by counting.** Age 25 falls
by a mean 1.622 across the profiles; the two boundaries that did not move average
0.041 between them, 21 falling 0.481 and 18 rising 0.399, and 7 of 8 profiles have
the age-25 fall exceeding the larger of the two unmoved boundaries.

**Adoption has a measurable speed**, which is the registered prediction coming in:
the new position goes from 1 of 8 to 4 of 8 over the two years after the move, and
on `HOURPAY` it strengthens on all four profiles, two of them reaching 2.7 floors.

**The two boundary movements are not two independent observations.** The
Commission's own report calls the 2021 step `"the first step towards the National
Living Wage applying to workers aged 21 and over by 2024"`, so 2021-04 and 2024-04
are two steps of one published plan. That does not weaken the arm, which reads the
mechanical consequence of each move; it fixes the count.

## 4. Arms three and four

| criterion | | |
|---|---|---|
| B34-3a no gap outside the statute carries a break | 27 non-statutory gaps across three rate years, none reaches 1.645 floors in a majority of its eight profiles | **PASS** |
| B34-3b the largest excess of each rate year sits on the statute | 2019-20 and 2022-23 top at 20-21; 2021-22 tops at 18-19 | **FAIL** |
| B34-4a boundary set, statute against code | three rate years, both steps carrying the set, six comparisons equal; fifteen rates equal; the two thresholds used equal the two adult bands | **PASS** |
| B34-4b excluded ages never used as boundaries | 16, 17 and 19 absent from every boundary set | **PASS** |

## 5. The object the statute half predicts and half does not

An age-indexed reading of the kink detector gave a positive at 19 and a negative
at 20 in all three rate years, eight profiles each, twenty-four readings with no
exception. **Under the gap index those are one object and half of it is
statutory.**

```
ch(19) > 0  is  D(18) > D(19)
ch(20) < 0  is  D(20) > D(19)
together: D(19) is a local minimum
```

`ch(20) < 0` is the lower lobe of the dipole the 20-21 statutory boundary leaves;
in the data `ch(20) < 0` holds in 24 of 24 profiles and `ch(21) > 0` in 22 of 24,
as the pure-step algebra says it must.

First differences, mean over the 24 profiles, percentage points:

| gap | mean fall | min | max |
|---|---|---|---|
| 16 to 17 | 12.9 | 3.9 | 21.3 |
| 17 to 18 | 14.6 | 7.1 | 25.4 |
| 18 to 19 | 12.4 | 7.2 | 20.6 |
| **19 to 20** | **3.6** | -3.0 | 11.1 |
| 20 to 21 | 13.4 | 1.2 | 20.8 |
| 21 to 22 | 6.0 | -2.4 | 19.3 |

Four consecutive gaps between 12.4 and 14.6 points with one at 3.6 among them.
The 19-20 gap ranks 11th, 12th and 11th of twelve by excess in the three years.

**The statute puts 18, 19 and 20 on one rate in all three years, so it predicts
both interior gaps of that band to be flat. One is and one is not.** An account in
which age alone raises wages predicts the two gaps alike and does not fit; an
account in which the statutory boundaries drive everything predicts both flat and
does not fit either.

**Pooled, the quantity reads.** `D(18) - D(19) = ch(19)`, inverse-variance pooled
across the three rate years:

| scope | 2019-20 | 2021-22 | 2022-23 | pooled |
|---|---|---|---|---|
| UK | +5.81 pp (0.80 floors) | +13.75 (1.58) | +4.83 (0.52) | **+7.97 pp, floor 4.79, 1.66 floors** |
| England | +4.44 (0.54) | +19.28 (1.97) | +2.86 (0.27) | **+8.62 pp, floor 5.43, 1.59 floors** |
| non-England | +10.25 (0.66) | -8.73 (-0.47) | +8.55 (0.45) | **+4.21 pp, floor 10.13, 0.42 floors** |

The UK pooled reading clears the 1.645 this station uses; no single rate year
does.

## 6. Two accounts of the 18-19 fall, both cited as literature and neither measured here

Post-16 education funding in England is banded by the learner's age on 31 August
and the adult skills regime replaces it from 19; participation to 18 is compulsory
in England and not in the other three countries. Research commissioned for the Low
Pay Commission's review of the youth rates reports participation in education
falling from 68 per cent at 18 to 29 per cent at 19 and employment rising from
12.3 to 37.7 per cent across the same year of age. The direction and the size
match, and the 31 August rule regenerates the discontinuity for every birth
cohort, which matches the finding that the pattern is pinned to age.

Separately the apprentice rate is lost by an apprentice who is both nineteen and
past the first year, a 42 to 58 per cent jump landing at 19. **Twelve of the
twenty-four profiles hold apprentices out entirely and give the same shape**,
which counts against that channel.

On the other side, child benefit and child tax credit end the day before the
twentieth birthday and the universal credit child element on the 31 August after
the nineteenth; and higher education entry is concentrated at 18, so second and
third year students living out and working sit at 20 rather than 19. Both raise
the share at 20 and both fit the flatness of 19-20.

**The discriminating test was gated and does not clear.** England against
non-England, three rate years stacked, gives a difference of +4.40 pp against a
floor of 11.50, that is 0.38 floors, and reading it would take 18.9 pp; the gate
computed 16.1 pp before it was run. The ratio `D(19)/D(18)` is 0.30 in England,
0.34 in the UK and 0.70 outside England, which is the ordering the account
predicts, at a resolution that cannot carry it. **Recorded as undecided, not as
failed.** A furlough split of the 2021-22 rate year was gated the same way and is
worse: 23.6 pp needed against the same 7.2 pp object.

Cell counts, usable `HOURPAY` readings, four quarters pooled, age 18:

| rate year | England | N. Ireland | Scotland | Wales | non-England | UK |
|---|---|---|---|---|---|---|
| 2019-20 | 257 | 30 | 25 | 17 | 72 | 329 |
| 2021-22 | 167 | 21 | 19 | 13 | 53 | 220 |
| 2022-23 | 155 | 18 | 9 | 5 | 32 | 187 |
| stacked | 579 | 66 | 53 | 38 | 157 | 736 |

**Wales alone is five to seventeen people per single year of age per rate year. A
four-way split does not exist on this carrier.**

**Restricting to England improves no criterion.** Arm one 1a still passes with
pooled exact p moving from 0.00427 to 0.01543; 1b, 1c and 3b each fire in one more
rate year. The 22 per cent of the sample dropped costs a floor factor of 1.13 and
the confound it removes contributes less than that. The UK specification stays the
main one.

## 7. A prediction that failed, and the sharper statement it bought

Registered before the third rate year was on disk: if the anomaly at 19 and 20
marks the cohort that left education into the 2020 hiring freeze, it travels with
the birth cohort. Following the 2002 cohort across the three rate years gives
`+0.43` at 17, `+1.59` at 19 and `-1.16` at 20, so the sign inverts. Read by age
instead, 19 is positive in all three years and 20 negative in all three, eight
profiles each. **The anomaly is pinned to age. That is a sharper statement than
the station had before, and the failed prediction is what produced it.**

The competing account, that post-pandemic recovery offset any scarring, was
checked and the two sides answer differently: graduate vacancies recovered to 20
per cent above the pre-pandemic level, while employment among 16 to 24 year olds
fell by 201,000 in the year to September 2021 against a record national vacancy
count. **This station reads the second group.** A separate limitation bounds the
whole question: the living wage rose 15.7 per cent across the three rate years, so
threshold movement dominates any level reading and this carrier carries only the
kink dimension.

## 8. B34-5, the ASHE arm

| criterion | | |
|---|---|---|
| B34-5 difference in differences, 2015 to 2017 | 20th percentile log DiD `+0.0675`, `t = 9.28`; one of the three cells does not clear | **undecided** |
| B34-5p pre-trend, 2014 to 2015 | `-0.0008`, and it is a zero rather than a non-rejection | **PASS** |

The undecided cell's noise comes entirely from the control group, which is a
statement about the instrument. The pre-trend being an exact zero rather than a
failure to reject is what makes the main reading stand where it does.

## 9. What is settled and what remains

**Settled.** The break is on the statutory gaps by order, pooled exact p 0.00427.
The old boundary's break disappears when the statute moves it, on 7 of 8 profiles
in the year it existed and 0 of 8 in both years after, and that is not a
resolution artefact and not a year effect. Adoption has a measurable speed. No gap
outside the statute carries a break at the visibility multiple. The statute
against the code is equal in every comparison. One gap inside a single-rate band
is flat and the other is not, and pooled that asymmetry reads at 1.66 floors.

**Open.** Arm two's conjunction needs a second readable year before the move,
which needs the 2018-19 rate year: one fetch, four quarters. Until then arm two
stands undecided with its load-bearing half holding. The source of the 18-19 fall
has two cited accounts and no measurement that separates them on this carrier.
The arithmetic garbage at the low end of `HOURPAY` has no bound set; it moves the
level of `p` and its effect on a second difference is not quantified.


---

## 10. The fourth rate year, 2018-19

Run 2026-09-05 through the same six steps. Design: section 8 of the
pre-registration.

### 10.1 The fetch, and a key that is not the content

Four serial numbers, four quarters. Each archive was opened and the quarter
read off the file inside it rather than off the serial number, because the
catalogue number is a key to the catalogue and not to the contents: the
household datasets for the same quarters carry adjacent numbers and nearly
identical titles, and one of them sorts below one of these. The unpacking
script asserts that the quarter code appears in the internal name and stops
otherwise.

| serial | file inside | quarter |
|---|---|---|
| 8381 | `lfsp_aj18_eul.dta` | Apr-Jun 2018 |
| 8407 | `lfsp_js18_eul_pwt18.dta` | Jul-Sep 2018 |
| 8447 | `lfsp_od18_end_user_pwt18.dta` | Oct-Dec 2018 |
| 8485 | `lfsp_jm19_eul_pwt24.dta` | Jan-Mar 2019 |

One thing recorded and not used: the person weight vintage is not constant
inside this rate year, `PWT18` for three quarters and `PWT24` for the fourth.
The income weight is `PIWT18` for all four, and every weighted reading here
runs on the income weight, so the inconsistency touches nothing.

### 10.2 Rule 19, checked by running

The twelve cached quarters are untouched, byte for byte, and eight cache files
are added. Across the six records, every reading for 2019-20, 2021-22 and
2022-23 reproduces exactly. The differences are the pooled ones the design
allowed in advance: the file list, the total row count of 942,150 against
1,293,333, the pooled rank sum, and the year strings inside criterion text.

The country collapse guard reads zero differing rows on each of the four new
files. The wave guard holds out two more rows whose entry quarter is misfiled,
three of 183,122 in all, from the duplicate analysis only; they stay in the
data and in every cell count.

Cells go from 45 to 60. The thinnest cells are still at age 16, and this year
is not among the thin ones: 146 and 150 against 113 and 115 in 2019-20.

### 10.3 No verdict changed

| criterion | verdict | with the fourth year |
|---|---|---|
| B34-1a | PASS | pooled rank sum 50 against a chance 78, exact p 0.00481. Per year 0.3000, 0.0500, 0.3636, 0.0091 |
| B34-1b | FAIL | 2018-19: 26-27 and 18-19; 2021-22: 18-19; 2019-20 and 2022-23 clean |
| B34-1c | FAIL | 17-18 at rank 9 in 2018-19 and rank 7 in 2019-20; 22-23 at rank 9 in 2021-22; chance rank 6.5 |
| B34-3a | PASS | holds in all four rate years |
| B34-3b | FAIL | 2018-19 tops at 26-27; 2021-22 at 18-19; the other two at 20-21 |
| B34-4a, B34-4b | PASS | four rate years, equal throughout |

### 10.4 The 18-19 gap now has a year with no furlough in it

That gap outranking every statutory gap had appeared only in 2021-22, a year
carrying a named contaminant, and this station declined to explain anything
with that contaminant. 2018-19 runs April 2018 to March 2019, entirely before
the pandemic, and shows the same thing. **The contaminant does not account for
the 18-19 gap.** The companion criterion moves the same way: 17-18 ranks worse
than chance in both years the 25 boundary was in force.

### 10.5 The 19 to 20 flat spot is in three of the four years, not four

Averaged over three rate years the fall from 19 to 20 was 3.6 pp, the smallest
step between 16 and 22. Read per rate year that step is:

| step, pp | 2018-19 | 2019-20 | 2021-22 | 2022-23 |
|---|---|---|---|---|
| 18 to 19 | +16.0 | +11.1 | +14.2 | +10.4 |
| **19 to 20** | **+10.2** | +4.9 | +1.7 | +6.1 |
| 20 to 21 | +10.6 | +15.3 | +12.8 | +11.8 |

It is the smallest step in its own year only in 2021-22. In 2019-20 it is
second smallest, in 2022-23 third, and in 2018-19 it is the same size as the
steps on either side of it.

The three-year average is arithmetically right and it carries less than it
appeared to. The shape holds in three rate years of four and it is deepest in
the year with the contaminant. Its scope is narrower than stated, and one year
without it does not remove three years with it.

An average that pools rate years hides the spread between them. This station's
own rule is to print the object rather than the summary, and a pooled mean is a
summary: the per-year numbers were always available and were not printed.

### 10.6 Arm two: the year count is met, the verdict is not moved

| rate year | age 25 mean | visible | age 23 mean | visible |
|---|---|---|---|---|
| 2018-19 | +1.23 | 2 of 8 | +0.42 | 0 of 8 |
| 2019-20 | +2.22 | 7 of 8 | -0.30 | 0 of 8 |
| 2021-22 | -0.30 | 0 of 8 | +0.75 | 1 of 8 |
| 2022-23 | -0.73 | 0 of 8 | +1.05 | 4 of 8 |

Three readings, each in its own words.

1. **The year clause is met.** Two readable years on each side of the move, so
   the criterion's third state stops applying. The record carries
   `criterion_third_state_met: false`.
2. **The verdict stays undecided, and it was never the year count holding it.**
   It comes from the second half of the conjunction, age 23 visible on 1 of 8
   profiles in 2021-22. Years and profiles are different counts, and adding a
   year cannot move a count of profiles. This was fixed before the run.
3. **The two pre-move years do not read alike at the old boundary.** Age 25 is
   visible on 7 of 8 profiles in 2019-20 and on 2 of 8 in 2018-19.

By sign the two pre-move years agree: all sixteen readings at age 25 are
positive before the move, and all eight are negative in 2022-23, with 2021-22
the year in between at two of eight positive. Both statements hold and both are
reported: the visible count separates the years, the sign does not.

The new boundary gains a clean placebo. Age 23 clears nothing in **both**
pre-move years, 0 of 8 and 0 of 8, before going to 1 of 8 and then 4 of 8. That
zero had been resting on one year.

### 10.7 One thing repaired while running

Two criterion texts in step six had the number of rate years written into them.
Adding a year made those sentences false while every number beside them stayed
right. They now count the years from the data. A number written into a string
has to be maintained by hand, and it drifts.
