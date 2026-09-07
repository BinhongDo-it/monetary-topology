# B51 results: the rule passes the known carriers, and turns a search into a reading list

RUN: 2026-09-06　DESIGN: `b51_prereg.md`

Script `experiments/b51_class_carrier_screen.py`, record
`results/b51_class_carrier_screen.json`. No data is fetched; the station is a
screen.

## 1. The reading

| criterion | reading | |
|---|---|---|
| **B51-1** the screen passes every carrier whose class difference has been measured | electricity, piped natural gas and resident tuition, all three pass all four | PASS · `known_answer` |
| **B51-2** the screen's Q2 agrees with the paired-cell count in the price grid | 8 of 8 agree; the two the screen says no to have `0` paired cells rather than few | PASS · `known_answer` |
| **B51-3** every candidate answers all four questions, each answer carrying its ground | 17 candidates, 4 questions each | PASS · `bookkeeping` |
| **B51-4** every candidate that does not pass names which questions it failed | 8 rejections, each naming its question | PASS · `bookkeeping` |

Of 17 candidates: **carries a class difference** electricity, piped natural gas,
and resident tuition; **fails a named question** automotive diesel, gasoline,
fuel oil, light fuel oil, LPG, steam coal, cable television, fixed broadband;
**not settled** district heating, piped water, sewerage, named concession fare,
resident admission price, prescription copayment.

## 2. What writing Q0 down cost, immediately

Cable television and fixed broadband were on the candidate list because they are
metered and sold at different prices to households and to businesses. **They
fail Q0**: a business connection is not the same commodity as a residential one,
it carries a different contention ratio and a different service commitment.
Without Q0 they would have entered the panel and their difference would have
been read as a class difference when it is a product difference.

## 3. The two families, and which one is empty

Q1 is satisfied either because the commodity cannot be handed on or because the
entitlement cannot. **Every carrier this repository had read was in the first
family**, and that family is close to enumerated: electricity, piped gas, piped
water, sewerage, district heating, and the open question of whether a sixth
exists at all.

**The second family had never been used.** It is larger by construction, since
it does not require a network: the good moves freely and eligibility is checked
at the point of consumption. Resident tuition is the first carrier from it to
reach a measured reading, and `b53_results.md` is that reading. `B54` then
enumerates the family, and its record is
`results/b54_eligibility_carrier_enum.json`.

## 4. The verdict function was wrong on its first pass, and the design was right

The design says an unchecked answer is neither a pass nor a failure. The first
implementation of `verdict()` read the answer and ignored whether it had been
checked, so **four candidates whose answers were plausible but unverified were
reported as confirmed carriers**, and the passing count read 6 instead of 2.

**The cells were partitioned correctly and the map from cells to verdicts was
wrong.** That is a different fault from the ones the criterion-shape rules
already cover, it does not raise an error, and on this occasion it reported a
pass. It is now a rule of its own: when a criterion has more than two states,
print the map from each state to its verdict and check that the undetermined
state maps to no verdict at all.

## 5. An unchecked answer and a missing answer are not the same thing

The screen marks an answer read against a source differently from one carried
without a source, and the six unsettled candidates split along that line:

| what is open | cells | what closes it |
|---|---:|---|
| an answer carried, no source read yet | 9 | find the rule and read it |
| no answer at all | 3 | settle what the answer is, then find the rule |

The three with no answer are district heating and prescription copayment on Q2,
and resident admission price on Q3. **Nine of the twelve open cells are waiting
on a document rather than on a judgement**, which is what makes the remainder a
reading list rather than an open search.

## 6. What the station leaves

Six candidates not settled, and the question that blocks most of them is Q3:
whether the split is written by a statute or by the operator. **That is reading,
not fetching**, which is the useful shape of what is left: the screen converts
an open-ended search for carriers into a finite list of rules to read.
