# B155: one corporate bond, two capital prices on one rating axis

A bank and an insurer in the European Union hold the same corporate bond. The bank's capital charge is set by
Article 122 of the Capital Requirements Regulation (standardised approach, banking book): 8% times a risk weight
that depends on the bond's credit quality step and nothing else. The insurer's charge is set by Article 176 of
Delegated Regulation (EU) 2015/35 (Solvency II standard formula, spread risk on bonds and loans): a stress factor
that depends on the credit quality step and on the bond's modified duration, piecewise linear in five duration
segments. Two implementing regulations map the same agency ratings onto the two step scales (2016/1799 for
banks, 2016/1800 for insurers). The two tables come from two legislative procedures and are written on one
rating axis. This station reads their exact squares. Script `experiments/b155_capital_square.py`; record
`results/b155_capital_square.json`, which carries the quoted page texts with version and access date
(`page_text`). Nothing is collected beyond the legal texts.

## 1. What is read

Positions are (letter grade, modified duration): AAA, AA, A, BBB, BB, B, CCC and an unrated position, on the
duration grid {1, 7.5, 10, 12.5, 15, 17.5, 20, 25, 30} years. Classes are the two licences. With `RW` the bank's
risk weight and `s` the insurer's stress factor, the square on two positions `p`, `q` is

    ln [ (s(p) / RW(p)) / (s(q) / RW(q)) ]

The bank's 8% and the insurer's market value are constants within each class and cancel. Squares are decided in
rationals; a square is zero exactly when the two ratios are equal. Three families are printed: grade pair at one
duration (GP), grade pair across two durations (GPD, the GP square at one duration minus the GP square at the
other), and one grade across two durations (CD).

The point prediction scored here: the capital price per euro of a bond is a scalar on its position, and the
holder's licence carries only a constant multiple. Then `ln P(class, position) = c(class) + phi(position)` and
every log square is zero. This framework states no direction for these squares, so no criterion is attached to
the prediction; it is carried in the detail of criterion MATH1-4.

The floor is the printed format. Risk weights are whole percentages (tick 1 point); the stress coefficients `a`
and `b` are printed to 0.1 point (tick 0.1). One cell of the current insurer table is printed "11 %" without a
decimal; it is also read with a 1 point tick. A number printed once is one input: the bank prints 20% once for
step 1, which holds both AAA and AA, so moving it moves both. A square stands above the floor when its log is
larger than the largest change one tick of one input produces, compared exactly; equal is on the floor and is not
counted.

## 2. The tables

Bank, Article 122, rated corporates:

| credit quality step | 1 (AAA, AA) | 2 (A) | 3 (BBB) | 4 (BB) | 5 (B) | 6 (CCC and below) | unrated |
|---|---|---|---|---|---|---|---|
| until 31 December 2024 | 20 | 50 | 100 | 100 | 150 | 150 | 100, or the sovereign's weight if higher |
| from 1 January 2025 (Regulation 2024/1623) | 20 | 50 | 75 | 100 | 150 | 150 | 100 |

Insurer, Article 176(3) as corrected by Delegated Regulation 2016/467 (in force from 2 April 2016); `a` and `b`
in percent, stress = `b x dur` up to 5 years, `a + b x (dur - start)` above:

| duration | step 0 (AAA) | 1 (AA) | 2 (A) | 3 (BBB) | 4 (BB) | 5 and 6 (B, CCC) |
|---|---|---|---|---|---|---|
| up to 5 | b 0.9 | b 1.1 | b 1.4 | b 2.5 | b 4.5 | b 7.5 |
| 5 to 10 | 4.5, 0.5 | 5.5, 0.6 | 7.0, 0.7 | 12.5, 1.5 | 22.5, 2.5 | 37.5, 4.2 |
| 10 to 15 | 7.0, 0.5 | 8.5, 0.5 | 10.5, 0.5 | 20.0, 1.0 | 35.0, 1.8 | 58.5, 0.5 |
| 15 to 20 | 9.5, 0.5 | 11, 0.5 | 13.0, 0.5 | 25.0, 1.0 | 44.0, 0.5 | 61.0, 0.5 |
| above 20 | 12.0, 0.5 | 13.5, 0.5 | 15.5, 0.5 | 30.0, 0.5 | 46.6, 0.5 | 63.5, 0.5 |

Unrated (Article 176(4)): `3 x dur` up to 5; `15 + 1.7 (dur - 5)` to 10; `23.5 + 1.2 (dur - 10)` to 20;
`35.5 + 0.5 (dur - 20)` above. The 2015 Official Journal text differs in four cells: step 1 starts its 10 to 15,
15 to 20 and above-20 segments at 8.4, 10.9 and 13.4, and step 4 starts its above-20 segment at 46.5. Delegated
Regulation 2026/269 (applying from 30 January 2027) replaces only paragraph 1 of the article and leaves the table
as it is.

## 3. Readings, current tables

Adjacent letter squares, log square (multiple of the floor):

| square | 1 | 7.5 | 10 | 12.5 | 15 | 17.5 | 20 | 25 | 30 |
|---|---|---|---|---|---|---|---|---|---|
| AAA/AA | -0.201 (1.70) | -0.197 (4.43) | -0.194 (2.62) | -0.167 (5.43) | -0.147 (2.71) | -0.131 (5.55) | -0.118 (2.77) | -0.098 (2.81) | -0.085 (1.39) |
| AA/A | +0.675 (7.08) | +0.693 (13.51) | +0.705 (11.63) | +0.730 (14.23) | +0.749 (14.61) | +0.765 (14.92) | +0.778 (15.17) | +0.799 (15.57) | +0.814 (14.64) |
| A/BBB | -0.174 (2.35) | -0.214 (7.37) | -0.239 (4.90) | -0.244 (11.35) | -0.248 (6.33) | -0.252 (12.47) | -0.255 (7.77) | -0.185 (6.58) | -0.129 (2.59) |
| BBB/BB | -0.300 (7.35) | -0.283 (18.24) | -0.272 (10.74) | -0.275 (20.49) | -0.278 (13.74) | -0.210 (15.67) | -0.151 (8.96) | -0.125 (8.06) | -0.100 (3.47) |
| BB/B | -0.105 (4.69) | -0.107 (10.66) | -0.108 (7.52) | -0.008 (0.84, on floor) | +0.079 (6.89) | +0.087 (8.61) | +0.094 (8.68) | +0.110 (10.71) | +0.122 (6.24) |
| B/CCC | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Counts on the current tables:

| family | above the floor | on the floor | exactly zero | total |
|---|---|---|---|---|
| GP (28 grade pairs including unrated, 9 durations) | 225 | 15 | 12 | 252 |
| GPD (28 grade pairs, 36 duration pairs) | 699 | 269 | 40 | 1008 |
| CD (8 positions, 36 duration pairs) | 288 | 0 | 0 | 288 |

With the "11 %" cell read at a 1 point tick, GP and CD do not move and GPD reads 686 above the floor.

The exact zeros are set by the texts. Both tables write B and CCC as one number (the insurer prints one column
for steps 5 and 6; the bank prints 150% for both), so B/CCC is zero on every duration. AAA/BB is zero on 1, 7.5
and 10 years: up to 10 years the insurer's step 4 column is exactly five times its step 0 column, and the bank's
100/20 is also five. On these twelve GP cells the point prediction holds, and this framework says the same.

The CD family is set by the insurer side alone: the bank's risk weight does not depend on duration, so every
square across two durations is the insurer's own log stress ratio. All 288 are above the floor (from 2.2 to 162
times).

Level squares, read in capital per euro with the bank multiplier at 8%, 10.5% and 13%, change sign across the
multipliers on 12 of 252 GP cells. They are printed in the record and not read.

## 4. Three dated steps, each on one class

**1 January 2025, banks only (Regulation 2024/1623).** Step 3 goes from 100% to 75%; the unrated weight loses its
sovereign floor (read on the branch where the sovereign weight is at most 100%, where nothing changes). The step
moves the 63 GP squares that involve BBB. A/BBB changes sign at each of the six durations where both sides
stand above the floor; at 10, 15 and 20 years the earlier side sits on the floor and is not counted:

| duration | 1 | 7.5 | 10 | 12.5 | 15 | 17.5 | 20 | 25 | 30 |
|---|---|---|---|---|---|---|---|---|---|
| before | +0.113 (1.53) | +0.074 (2.56) | +0.049 (1.00, on floor) | +0.043 (2.02) | +0.039 (1.00, on floor) | +0.036 (1.77) | +0.033 (1.00, on floor) | +0.102 (3.63) | +0.158 (3.16) |
| after | -0.174 (2.35) | -0.214 (7.37) | -0.239 (4.90) | -0.244 (11.35) | -0.248 (6.33) | -0.252 (12.47) | -0.255 (7.77) | -0.185 (6.58) | -0.129 (2.59) |

The three "before" points on the floor are exact ties: the square equals the move of the A column's `b` by one
tick (ratios 21/20, 26/25 and 31/30).

**2 April 2016, insurers only (Delegated Regulation 2016/467).** Four cells each move by one 0.1 tick. The step
moves 46 GP, 273 GPD and 48 CD squares; none moves by more than its own floor. The unrated position is left out of
this comparison because paragraph 4 of the 2015 text is not in the stored page text.

**30 January 2027, insurers only (Delegated Regulation 2026/269).** Only paragraph 1 is replaced: defaulted and
forborne loans leave the scope of the article. The table is unchanged and so is every square.

**BB/B across duration.** The bank's BB/B ratio is 2/3 before and after 2025. The square changes sign exactly
once on [1, 30], at 140/11 = 12.727 years, inside the insurer's 10 to 15 year segment where
`(35 + 1.8 t)/(58.5 + 0.5 t) = 2/3`. One tick of any of the insurer's four coefficients in that segment moves the
crossing by 0.045 to 0.200 years; one point of the bank's BB or B weight by about 0.18 to 0.27 years.

## 5. Checks

Every transcribed number (189 cells across two bank texts and three insurer texts) is compared with the quoted page
text; none differs. Segment boundaries: the 2015 text has one break (step 1 at 10 years, 8.5 against 8.4), the
corrected text one other (step 4 at 20 years, 46.5 against 46.6); the unrated column has none. The two mapping
standards place Fitch, Moody's and S&P (issuer and issue scales, 56 placements) exactly as the position axis
assumes. The structural zeros are checked as known answers: B/CCC (36 squares), squares between notches of one
letter (225; both mapping standards list letter classes, so this family checks the code's notch-to-letter
routing), grade pair across two durations within five years (420, on a separate short grid), and the CD family
against the insurer's own stress ratio (1116). The 2016 correction check holds almost by construction, since each
of its four cells moves by one tick; it catches a cell typed three ticks or more off, and smaller slips are caught
by the comparison with the quoted text. In the insurer-side mapping standard as consolidated, the A.M. Best
long-term issuer row prints no "aa+"; A.M. Best is not on the position axis.

The self-test plants one wrong input per criterion and checks that the criterion fails, and runs seven mutations
of the implementation (open segment ends, no duration floor, flipped orientation, floor from bank ticks only, CCC
read from the step 4 column, a crossing search that skips a segment, ties counted as above the floor); the
known-answer checks catch each.

## 6. Criteria

| criterion | kind | status | reading |
|---|---|---|---|
| MATH1-1 | instrument | PASS | 189 cells match the quoted text; break sets {step 1 at 10} in 2015, {step 4 at 20} after 2016 |
| MATH1-2 | premise | PASS | 56 agency placements on the position axis, none off |
| MATH1-3 | known_answer | PASS | four structural-zero families, 1797 squares, none off (225 of them check the notch-to-letter routing) |
| MATH1-4 | own_reading | PASS | current tables: 225 of 252 GP squares above the floor, 12 exactly zero, 15 on the floor |
| MATH1-5 | own_reading | PASS | the 2025 step moves the 63 squares with BBB; A/BBB changes sign at the six durations where both sides stand above the floor |
| MATH1-6 | own_reading | PASS | BB/B crosses zero once, exactly at 140/11 years in the insurer's 10 to 15 year segment; the bank ratio is 2/3 in both versions |
| MATH1-7 | bookkeeping | PASS | every table version carries URL, access date, version and quoted text |
| MATH1-8 | known_answer | PASS | the 2016 correction moves no square by more than its floor |
| MATH1-9 | known_answer | PASS | the 2027 amendment replaces paragraph 1 only; the table is unchanged |

Kinds: `instrument` and `known_answer` ask whether the transcription and the code are right, `premise` whether
the two tables share a position axis, `bookkeeping` whether the record is complete, `own_reading` about a reading
this station registers. On the floor and exactly zero carry no verdict.

## 7. Not read

The insurer's capital is the loss in basic own funds under the stress, so liability-side loss absorption can move
an individual insurer's marginal charge away from `stress x market value`; this station reads the printed factor.
Internal-ratings banks, the trading book and insurers on internal models are outside the two tables read here.
