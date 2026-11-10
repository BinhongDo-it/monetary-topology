# B151: one self-regulatory initiative, two positions at one bank, and the values it writes by class of depositor

China's market interest-rate pricing self-regulatory mechanism, a body of banks set up under the
guidance of the People's Bank of China, adopted on 28 November 2024 an initiative on the rates
banks pay on deposits placed with them by non-bank financial institutions. It took effect on
1 December 2024, with one month's grace, and from the first quarter of 2025 compliance enters
the central bank's macroprudential assessment of each bank.

The initiative writes a rate for two positions at the same bank and names its classes of
depositor at each. At the demand-deposit position it names two classes and gives them two
values; at the position of a time deposit withdrawn early it names one class and gives it one
value. Every cell is written by reference to a published policy rate, a reference rate at the
demand position and a ceiling at the early-withdrawal position, so every cell's value is read off
a central bank notice.

Script: `experiments/b151_nonbank_interbank_caps.py` (the reading and its self-test).
Record: `results/b151_nonbank_interbank_caps.json`, carrying the configuration it ran under.
Snapshots of every page read, with their hashes, sit under `data/raw/b151/` (not redistributed).

## 1. The object

Writer: the self-regulatory mechanism. Programme: the initiative on optimising the
self-regulatory management of non-bank interbank deposit rates. Classes: financial market
infrastructure institutions, and every other non-bank financial institution (unincorporated
products included). Positions, both at the same bank: a demand deposit (A), and the early
withdrawal of a time deposit (B). Value: the rate the initiative writes for the cell, in
percentage points.

The three operative sentences, as three outlets carry them, word for word the same:

| position | class | operative wording | refers to |
|---|---|---|---|
| A, demand | infrastructure institutions | "should refer to" the rate on excess reserves "to set the rate reasonably"; the stated reason is that these deposits mainly serve payment and settlement | rate on excess reserves |
| A, demand | all other non-bank institutions | "should refer to" the 7-day reverse repo rate "to set the rate reasonably" | 7-day reverse repo rate |
| B, early withdrawal | every non-bank institution | "in principle should not be above" the rate on excess reserves | rate on excess reserves |

Two regimes, cut where the 7-day rate changed:

| segment | dates | rate on excess reserves | 7-day reverse repo rate |
|---|---|---|---|
| one | 2024-12-01 to 2025-05-07 | 0.35 (since 2020-04-07) | 1.50 (since 2024-09-27) |
| two | 2025-05-08 to 2026-10-14 | 0.35 | 1.40 (since 2025-05-08) |

## 2. Two accounts, each against the text

The standard account places one number on each position: the cost of a bank's funding at a
position is one rate, and the object carries no index for the class of the depositor, so it has
nowhere to write two values at one position. Two forms that add a class term are scored here
against the written schedule: an additive one (rate = class term + position term), whose 2 x 2
square in percentage points is zero, and a multiplicative one (rate = class term x position
term), whose square in logs is zero.

The framework reads the price as a field with two indices, position and class. A writer may name
several classes at one position and give them different values, and the square over two classes
and two positions is open by the amount the writer chose.

## 3. Sources

- The initiative itself has not been published by its writer. Its existence and full name are on
  the central bank's own release of 29 November 2024 on the mechanism's meeting. The central bank's
  monetary policy report for 2025Q1 names it among the self-regulatory initiatives in force, and the
  report for 2024Q4 records the November 2024 optimisation of the self-regulation of interbank
  demand deposit rates. Its operative sentences are read from three outlets that carry them word
  for word the same (The Paper,
  2024-12-04; 21st Century Business Herald as carried by Sina Finance, 2024-11-29; Xinhua's China
  Economic Information Service bank bulletin, 2024-12-09). The script checks that each sentence
  appears word for word on all three pages, and that each sentence names the policy rate its
  cell's value is taken from and no other.
- The two policy rates are read off the central bank's notices: excess reserves cut from 0.72 to
  0.35 from 2020-04-07; the 7-day rate cut from 1.70 to 1.50 from 2024-09-27 (open market notice
  2024 No. 5) and from 1.50 to 1.40 from 2025-05-08 (open market notice 2025 No. 1). On the reading
  date the day's operation (open market trading notice 2026 No. 198) was at 1.40, the level at which the
  central bank's 2026Q1 report states the 7-day rate was held. The latest statement of the
  excess-reserve rate found is a 2026-05-07 press report giving 0.35.
- The script reads each rate and its effective date off the saved notice and refuses a table
  value the notice does not print.

## 4. How the reading is made

Nothing is estimated. For each segment the script takes the policy rate in force at the segment's
start, checks that no notice changes it inside the segment, assigns each cell the rate its
sentence refers to (checking that the sentence names that rate and no other), and counts distinct values at each position. The square is

    pp  = (other - infrastructure) at A - (other - infrastructure) at B
    log = log(other / infrastructure) at A - log(other / infrastructure) at B

Both rates are published to two decimals, a fixed format, so the floor is 0.01 percentage point
for the first composition and log((x + 0.01) / x) for the second, with x the smallest of the four
cells (0.35, giving 0.0282). A composition at or under its floor, or two compositions of opposite
sign, map to no verdict. The square is taken over the written values, a reference rate at A and a
ceiling at B.

## 5. Readings

| | segment one | segment two |
|---|---|---|
| values at A (demand) | 2: infrastructure 0.35, other 1.50 | 2: infrastructure 0.35, other 1.40 |
| values at B (early withdrawal) | 1: 0.35 for every non-bank | 1: 0.35 |
| square, percentage points | +1.15, 115 times the floor | +1.05, 105 times the floor |
| square, logs | +1.4553, 51.7 times the floor | +1.3863, 49.2 times the floor |

With one value at the early-withdrawal position, both compositions reduce to the class gap at the
demand position, so their agreeing in sign checks the code and adds nothing to the reading.

At each position the number of distinct values equals the number of classes the initiative
writes separately: two at A, one at B. Banks placing interbank deposits with banks are not written
for by this initiative. Corporate and household deposits are general deposits, not interbank
deposits, so they are not at either position; their rates are written under other rules and are
not read here.

Against the accounts in section 2:

- One rate per position: the demand-deposit position carries two written values in both
  segments, and an account with one value per position has no place for them.
- Additive class term: the square in percentage points is +1.15 and +1.05, far off zero. Not
  borne out as a shape of the written schedule.
- Multiplicative class term: the square in logs is +1.4553 and +1.3863. Not borne out as a
  shape of the written schedule.

Both shapes are read on the written values only; rates actually paid are not read at either
position.

At the early-withdrawal position the initiative writes one value for all non-bank depositors,
and a one-rate-per-position account gives one value there too. Both readings agree on that
position, and the count of one is what the framework predicts for a position where one class is
named.

The class difference at the demand position moves with the 7-day rate and not with the rate on
excess reserves: when the 7-day rate fell on 2025-05-08 the gap fell from 1.15 to 1.05, while
the early-withdrawal value stayed at 0.35. No published conversion rule ties the two classes'
values together; they follow two different policy rates.

## 6. Criteria

Criteria come in kinds. `instrument` and `bookkeeping` ask about the tool and the record;
`own_reading` is a reading this station registers, and B151-6 is the same reading made again once
the second step's text is public.

| criterion | kind | state | reading |
|---|---|---|---|
| B151-1 | instrument | PASS | each segment's two policy rates read off a central bank notice, value and effective date as the table has them; 1.40 on the reading date's operation |
| B151-2 | bookkeeping | PASS | every cell's sentence on three verified snapshots, its operative wording inside the sentence, its source level, and the one policy rate the sentence names is the rate its value is taken from; existence and name on the central bank's release |
| B151-3 | own reading | PASS | two values at the demand position in each segment, one per class named |
| B151-4 | own reading | PASS | square +1.15 / +1.05 pp and +1.4553 / +1.3863 in logs, both over their floor, same sign |
| B151-5 | own reading | PASS | values equal separately written classes at each position: 2 and 1 |
| B151-6 | own reading | no verdict, waiting for the event | the second step (interbank time deposits) has no public text as of 2026-10-14 |

The self-test seeds a fault for every criterion and checks that the flag turns: a notice removed,
a rate written at another value, a cut date the notice does not print, a sentence missing from
its pages, a cell pointed at the other policy rate, the two demand-position cells' rates swapped,
two values under one named class, squares made zero in one composition and not
the other, a position emptied, a cell left without a value or without a verified sentence (the
count and the square then carry no verdict), a second-step table that fails its own count, a
second-step table whose sentences fail their checks, and a changed byte in a snapshot. A separate pass breaks the implementation on purpose, and the self-test fails on each
break.

## 7. Scope and what comes next

The readings are statements that this initiative writes these values in these cells. Rates
actually paid on any interbank deposit are not read. Where the funds of a repriced class moved is
not read either: the central bank's credit balance sheet publishes non-bank deposits as one line,
demand and time and both classes together, so the published aggregate cannot separate the
classes.

Press reports of May 2026 describe a second step: interbank time deposits brought under the
self-regulation from the third quarter of 2026, capped at the same-tenor Shibor plus 10 basis
points. No text of that step was public on 2026-10-14; the central bank's reports for 2026Q1 and
2026Q2 do not mention it and the 2026Q3 report was not yet out. The text is checked from mid
November 2026, once a month. When it appears, B151-6 reads which classes it names and what each
cell carries (a cap, or a cap with a share threshold), and recomputes the counts with the new
positions. If no text is public by 2027-03-31, B151-6 reads "announced, not landed"; the other
five criteria do not depend on it.

The same shape, one obligor and one instrument with a rule that writes two values by holder,
appears in B59 for balances at a Federal Reserve Bank. Here one writer fills all four cells of
the square itself.
