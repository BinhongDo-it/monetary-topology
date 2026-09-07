# B53 pre-registration: a corpus where the collisions are exact

The counting law says that a programme writing classes produces as many prices
as it writes distinct class values: not as many as it has cells, and not as many
as the rule names factors. Counting that on a real corpus needs collisions to be
**exact** rather than bounded above, and the tariff corpus cannot give that. Its
figures are published to two decimals, so two class values that differ in the
third place are recorded as one, and every collision it reports is an upper
bound at the published resolution.

A published tuition schedule closes that gap. It writes three classes for the
same course in the same room in the same term, in-district, in-state and
out-of-state, and **it writes them in whole dollars**. Two distinct amounts
cannot round into one, so a collision on this carrier is a collision.

The same schedule also carries a second, independent split. Residency is a legal
status set by the state, so a public institution has the distinction imposed on
it and a private one does not. **That gives the corpus a control group that the
counting law itself predicts the shape of**, and the control code comes from a
different endpoint, so testing it is a check and not a restatement of the
tuition figures.

## 1. Criteria

| | asks | kind | FAIL |
|---|---|---|---|
| **B53-1** | every private institution writes one value across the three classes | `known_answer` | one or more write more, in which case each is named |
| **B53-2** | how many schedules write `3 -> 1`, `3 -> 2` and `3 -> 3`, by control and level | `own_reading` | the census is empty |
| **B53-3** | the premise that makes these collisions exact: every figure is a whole dollar amount | `premise` | any non-integer figure, which would put the corpus back on the tariff corpus's footing |
| **B53-4** | coverage state by state, a state returning nothing named rather than absent | `bookkeeping` | a state is silently missing |

`B53-1` is a known-answer check, and known-answer checks earn their keep when
they do not pass: what they return is a named and checkable list. **A failure
here is a list of institutions to go and read, not a result about the world.**

## 2. The four numbers before the run

**No estimator, no band, no power.** Every quantity is a count of distinct
values, so there is nothing to place a line on. What the station needs instead
is `B53-3`: a resolution premise, checked rather than assumed.

**Reachability.** All three shapes are reachable before the run: a schedule can
write one, two or three distinct values, and both the private and the public
side can land anywhere among them. Nothing about the pull forces the answer.

**One thing has to be handled or the count is wrong.** Negative values in this
collection are absence codes, not fees. Read as fees they would put a fourth
distinct value into a schedule that has three. They are dropped and counted.

## 3. Carrier and basis

The Urban Institute Education Data API over the federal IPEDS collection,
public, no key. `academic-year-tuition` for the rates and `directory` for the
control code, 2020, requested state by state so an interrupted pull resumes.
The field is `tuition_fees_ft`: full-time tuition and required fees **as
published for the academic year, before any aid**. That is the object the
counting law is about, since the law concerns what the schedule writes rather
than what anyone pays.

A schedule is one institution at one level. Class codes `2`, `3` and `4` are
in-district, in-state and out-of-state; control codes `1`, `2` and `3` are
public, private nonprofit and private for-profit.

Full source basis in `data/SOURCES.md`. The record
`results/b53_tuition_class_values.json` carries the criteria wording, the
configuration this run used, and every quantity it produced.
