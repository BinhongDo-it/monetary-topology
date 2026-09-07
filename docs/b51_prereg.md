# B51 pre-registration: which carriers can show a class difference at all

Two stations read a class square on electricity and piped gas. Neither of them
had a rule saying **why those two and not something else**, and without one the
choice looks like a search over carriers until a square appeared.

This station writes the rule down, applies it to every candidate that was
already on the table, and checks it against the two carriers whose answer is
known.

## 1. The four questions

A carrier can show a class difference in prices only if all four hold.

| | question | why it is here |
|---|---|---|
| **Q0** | is it **one commodity**, the same good in the same place at the same time | two different goods with different prices are not a class difference; this question was implicit and is now written down |
| **Q1** | can a member of the cheap class **not** hand the good or the entitlement on | if the two classes can trade, one price survives, whatever the tariff says |
| **Q2** | do **both classes have a posted price** | a class difference nobody publishes cannot be read off published prices |
| **Q3** | is the split **imposed** rather than chosen by either party | a split the seller chooses, the seller can also withdraw, and the disadvantaged class stops existing rather than being priced |

**Q1 has two sources and they are not the same size.** Either the commodity
cannot be handed on (a metered network: past the meter it cannot move), or the
entitlement cannot be handed on (the good moves freely, but eligibility is
checked at the point of consumption). The first family is small and close to
enumerated. The second is, by construction, much larger.

## 2. Criteria

| | asks | kind | FAIL |
|---|---|---|---|
| **B51-1** | the screen passes every carrier whose class difference has been measured | `known_answer` | a carrier with a measured class difference does not pass |
| **B51-2** | the screen's Q2 answer agrees with the paired-cell count in the price grid | `known_answer` | the screen says a class difference is posted where the grid has no pair |
| **B51-3** | every candidate answers all four questions, and every answer carries its ground | `bookkeeping` | an answer without a ground |
| **B51-4** | every candidate that does not pass names which questions it failed | `bookkeeping` | a rejection without a reason |

**Three verdicts, and the middle one is required**: passes all four, fails a
named question, or **not settled, because at least one answer has not been
checked**. An unchecked answer is not a pass. The screen records `checked`
alongside each answer for exactly this reason, and a candidate with an unchecked
answer cannot reach the passing verdict however confident the answer looks.

## 3. The four numbers before the run

**Nothing is estimated and nothing is fetched.** The station is a screen: its
inputs are the questions, the candidates and the grounds, and its cost is
reading. There is no floor, no band and no power, because there is no
measurement.

What it can produce is a rule that turns a search into a reading list, and the
check on whether the rule is any good is `B51-1`: it must pass every carrier
whose class difference has already been measured, and it must not pass carriers
the price grid shows no pair for. **That set grows as stations are run**, and
widening it cannot make the check easier, since every carrier added to it is one
the screen has to pass.

## 4. Scope

The screen answers per commodity. **Q2 is in fact a property of a commodity and
a place**, since a network exists in some countries and not others, and the
screen as written does not carry that. `b52_results.md` section 5 records the
case that showed it.

The record `results/b51_class_carrier_screen.json` carries the criteria wording,
every candidate with its four answers and grounds, and the configuration this
run used.
