# A1c: the order inside a household

Pre-registration for **stage A1c**. A new station rather than a restatement of
[`a1_prereg.md`](a1_prereg.md) A1-2, because it tests a **different
proposition**. A1-2 stands refuted as recorded in
[`a1b_prereg.md`](a1b_prereg.md) §8, and nothing here rescues it.

Population, mechanism, inputs, baseline and zero calibration are A1b's, inherited
by reference. What is new is one measured quantity and one criterion.

---

## 1. Why a different proposition, and what the difference is

卷一·十八 gives a sequence: card, then auto loan, then shelter, then
displacement. A1-2 turned that into a **cross-section**, the share of defaulting
households whose *first* default is each class. The first scored run of A1b
showed what a cross-section of that kind measures, and it is not the sequence:

| holding | share of households |
|---|---|
| a revolving balance | `0.456` |
| a mortgage | `0.413` |
| a car loan | `0.349` |
| renting | `0.315` |
| **card and car together** | `0.212` |
| **neither card nor car** | `0.406` |

The distribution of *the cheapest rung a household holds* at zero arrears is
card `0.456`, mortgage `0.189`, basket `0.159`, rent `0.131`, auto `0.065`,
which reproduces the observed first-default shares almost exactly. A
cross-section of first defaults is the cost rule composed with the holdings, and
in a population where two households in five hold neither of the first two rungs
the registered inequality cannot hold whatever the cost ordering is.

**The manuscript's claim is about one household over time.** A household that
holds a card, a car loan and a tenancy, and that is squeezed, gives them up in
that order. That claim is silent about households holding only some of them, and
A1-2 quantified over all of them. This stage measures the claim as stated.

**This station was opened after A1-2 failed**, on 2026-08-16, and that is why §8
carries the date and what had been seen. Reporting a proposition the data
suggested is legitimate only when the fact that it was suggested travels with
it.

---

## 2. The quantity

For each household, the **period at which each obligation class was first
missed**, or absence where it never was. The model records it; nothing derives
it from a rule.

A household is **in scope** for a pair when it missed **both** classes of that
pair at some point. Households missing one or neither are outside that pair's
population and are counted separately rather than folded in as agreement.

For an ordered pair `(earlier, later)` taken from the manuscript's sequence, a
household is:

- an **inversion** when it first missed `later` **strictly before** `earlier`;
- a **tie** when it first missed both in the same period;
- **in order** otherwise.

A tie is not a violation. A household short enough to drop two rungs in one
period drops them in one period, and the manuscript's sequence says nothing
about what happens inside a month.

**The three pairs**, all of them the manuscript's own adjacency plus its one
transitive consequence:

    (card, auto)      (auto, shelter)      (card, shelter)

`shelter` is rent or mortgage, whichever the household holds. Both are the third
step of the sequence and a household holds at most one.

---

## 3. The criterion

### A1c-1. The sequence holds inside a household

For **each** of the three pairs, among the households in scope for that pair:

> households in order **strictly exceed** households inverted.

Ordinal, no level, no tolerance. **Source of the direction**: 卷一·十八 and
nothing else. **Fails** if any pair inverts, and a failure is the manuscript's
sequence being wrong for that pair rather than the code being wrong.

**Reported beside it and not scored**: the tie share for each pair, the in-scope
count for each pair, and the share of households in scope for no pair at all.
The last is the population A1-2 was quantifying over and is the size of the
mismatch between the claim and its cross-sectional form.

### A1c-2. Every inversion is attributed

An inversion is not necessarily against the cost rule: the rule has one clause
that can produce one. **What cannot be saved is released first**
(`a1_prereg.md` §2.2), so an obligation whose arrears could not be cleared even
by spending everything on hand sorts ahead of everything still savable, and a
household can therefore let a dwelling go while a cheaper car loan is still
being paid.

Every inversion is classified as **released**, the later class was unsavable in
the period it was first missed while the earlier class was savable, or
**unattributed**. The criterion is that **the unattributed share is reported and
named**, not that it is zero: a mechanism whose exceptions are all explained by
its own registered clause is a different object from one with residual
exceptions, and the stage should be able to say which it has.

**This is a reporting criterion and gates nothing.** It cannot fail. It exists
so that A1c-1's verdict, whichever way it goes, arrives with its exceptions
accounted for rather than as a bare inequality.

---

## 4. What A1c is not evidence for

**Not a level and not a rate.** Every quantity here is a share of households in
scope for a pair, and the scope is defined by the model's own defaults. There is
no published counterpart, because no source publishes the order in which one
household gave things up.

**Not a repair of A1-2.** A1-2 quantified over all defaulting households and it
failed. This quantifies over households holding both rungs of a pair. Where the
two disagree, both stand, and the disagreement is the finding that a
cross-section of first defaults is not a sequence.

**Not independent of A1b.** Same population, same records, same mechanism, same
income path. If A1b's inputs move, this moves with them.

**Not a claim about displacement.** The sequence's fourth step is eviction, and
`a1_prereg.md` A1-8's three reasons for never scoring it are unchanged.

---

## 5. Outputs

`results/a1c_household_order.json`, and rows in `RESULTS.md` written by the
renderer. The stage gets a job in `scripts/run_all.py` at the same time as its
first record, not afterwards.

---

## 6. Changelog

### 2026-08-16, written

Sections 1 to 5 are fixed at this date. **No result exists for this stage** and
no within-household ordering has been computed.

**What had been seen when this was written**, in full: A1b's first scored run,
which is A1-3 holding, A1-2 failing at `card 0.4278, auto 0.0627, shelter 0.3500`
among 7,277 defaulting households, the holdings table in §1, and the
cheapest-rung-held distribution in §1. Those are what made the mis-specification
visible and they are the reason this station exists. **Nothing about the order
inside a household was measured before this document was fixed**, and the
model did not record it: `first_missed` is added to the model as part of
implementing this stage.

### 2026-08-16, the first run. A1c-1 fails, entirely on the mortgage

20,000 households, A0's path at seed 7 over 60 months, 7,277 defaulting.

| pair | in scope | in order | tied | inverted |
|---|---|---|---|---|
| card before auto | `1,142` | `607` | `533` | `2` |
| auto before shelter | `1,765` | `449` | `546` | `770` |
| card before shelter | `2,703` | `777` | `1,899` | `27` |

**The card leads everything.** Two inversions in 1,142 against the car, and 27
in 2,703 against shelter. The card costs nothing to skip at any arrears, its
resource support being zero, so this is the rule showing through cleanly.

**The middle pair fails, and splitting the aggregate says why.** Among
households missing both the car and a shelter class:

| shelter class | in order | tied | inverted |
|---|---|---|---|
| rent | `449` | `526` | `2` |
| mortgage | `0` | `20` | `768` |

**The renter's sequence is exact.** Car before rent, 449 to 2. **The mortgage
inverts without exception**, 768 to nil, by a median of one month.

**Both halves were registered in advance, in a different document, before any
run of anything.** [`a1_prereg.md`](a1_prereg.md) §2.2, written 2026-08-13:
"at no arrears the mortgage is the cheapest real obligation to skip, because one
missed payment consumes a twelfth of the foreclosure clock against a third of
the repossession clock. So a squeezed owner skips the mortgage before the car.
This is the reversal of the payment hierarchy reported after 2008, and it is a
prediction here rather than an input." At zero arrears the pairs are mortgage
`0.083`, auto `0.117`, rent `0.250`, and the run is that prediction at
population scale.

And §9 of the same document: "**No mortgage cascade.** Mortgage enters as an
obligation class for the K shape and does not get a rung; the manuscript's
cascade is a renter's cascade."

**So the failure is a drafting error in §2 of this document, not a discovery.**
§2 defined `shelter` as rent or mortgage and put both in the pair, against a
scope that had already excluded the mortgage from the cascade three days
earlier. A1c-1 as written therefore asks the sequence to hold for a class the
project had registered as not being in it. The criterion fails as written and
that stands; what it refutes is this document's §2 rather than 卷一·十八.

**The size of the claim's domain, reported and not scored.** `16,518` of
`20,000` households, `82.6%`, are in scope for no pair at all: they never miss
two of the named classes, most often because they hold at most one of them. The
manuscript's sequence is a statement about the other `17.4%`.

**A1c-2 reports 799 inversions, of which 29 are the release clause and 770 are
not.** The 770 are the mortgage, above. The classification registered in §3 has
two buckets and the second is doing the work of naming a phenomenon registered
elsewhere; that is the classification being coarse rather than wrong, and it is
left as registered rather than refined after the fact.

### 2026-08-16, A1c-1 restated on the renter's cascade, and the run that followed

**What changed.** §2's third step is **rent**, not rent or mortgage. The three
pairs are `card -> auto`, `auto -> rent`, `card -> rent`.

**What had been seen when it changed**: the whole of the entry above, which is
A1c-1 failing at `auto before shelter` with 770 inversions against 449 in order,
and the split showing rent inverting 2 times against 449 while the mortgage
inverted 768 times against nil.

**Why this is a restatement and not a rescue.** The scope was registered on
2026-08-13 in [`a1_prereg.md`](a1_prereg.md) §9, three days before this document
existed: "**No mortgage cascade.** Mortgage enters as an obligation class for
the K shape and does not get a rung; the manuscript's cascade is a renter's
cascade." §2 of this document asked the sequence to hold for a class the project
had already excluded from it. The restatement brings this document into line
with a scope that pre-dates every run, and the entry above stands as the record
of what the mis-drafted version produced.

**The mortgage reversal is reported and is not scored.** `a1_prereg.md` §2.2,
also 2026-08-13, predicted it in words before anything ran. The direction was
registered in advance; **the decision to gate it would not be**, arriving after
768 to nil was on the screen, so it is printed with its registration quoted and
kept out of A1c-1.

**The result, on the restated criterion.**

| pair | in scope | in order | tied | inverted |
|---|---|---|---|---|
| card before auto | `1,142` | `607` | `533` | `2` |
| auto before rent | `977` | `449` | `526` | `2` |
| card before rent | `1,612` | `523` | `1,080` | `9` |

A1c-1 **holds on all three**. Reported beside it: the mortgage goes before the
car `768` times against nil, `20` in the same month.

`17,499` of `20,000` households are in scope for no pair, so the sequence is a
statement about `12.5%` of this population. That figure is the domain of the
claim and is reported at every run.

**One defect fixed between the two runs of this stage**, and it moved a reported
number. A1c-2 attributed an inversion to the release clause by comparing each
class's savability **at its own** first-miss period, and the criterion registers
one period: whether the later class was unsavable *in the period it was first
missed* while the earlier one was savable *then*. Two households that released a
car in period 1 while still paying a card, and lost the card in period 6,
therefore read as unattributed anomalies. The model now records which classes
were savable in that one period and the attribution reads them there: `13`
inversions, `13` released, `0` unattributed.

### Anything altered after this date

Goes here with the date, the reason, and what had been seen at the time.
