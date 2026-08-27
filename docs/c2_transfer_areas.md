# C2. A control arm for C1: the same question asked of a system without prices

    RUN:     2026-08-27T18:46Z
    SOURCE:  data/raw/assist/transferability_2024/  (115 colleges x 6 list types, 690 files)
    SCRIPT:  experiments/c2_transfer_areas.py
    RECORD:  results/c2_transfer_areas.json
    STATUS:  diagnostic_only, one college absent. See section 7.

## 1. What this stage is for

C1 measured the declared conversion between a greenhouse gas and
CO2-equivalent and found it multivalued: of 88 species quoted under two or more
of the six published GWP-100 vintages, none reads the same ratio under all of
them. The cheapest objection to that reading is that any administrative system
of state or global scale accumulates inconsistency, and that the finding is
therefore about bureaucratic entropy rather than about whether the scalar those
declarations are about exists.

**That objection is answerable, and answering it needs a second system rather
than an argument.** The second system has to be comparable in scale and age,
carry several parallel classification schemes at once, publish its declarations
in the same way, and have no prices, no trading and no friction in it. If such a
system is internally consistent, then inconsistency is not what systems of that
kind do by default, and C1's reading survives.

California's course articulation system meets every one of those conditions.

## 2. Three arms that were scoped and did not open

All three were closed before any sweep was paid for, and their common cause is
a single measured fact.

| arm | what it would have shown | why it does not run |
|---|---|---|
| unit conservation around a loop | units do not close | units are a scalar attached to a course, so any ratio built from them telescopes and closes at 1 by construction |
| "two courses satisfying the same receiving course are equivalent" | the induced relation is not transitive | articulation declares an inequality, `v(sending) >= v(receiving)`, and two courses above one threshold need not be equal |
| the Ferrers 2x2 | the relation admits no scalar representation at all | at college level it is confounded by curriculum coverage: one college teaches mathematics and another teaches Spanish |

**The common cause.** `courseIdentifierParentId` is institution-local. Of 972
sending identifiers seen, none appears at two colleges; of 633 receiving
identifiers, none appears at two universities. So "the same course" is not
sayable in this system, and every proxy for it also encodes "these two
institutions are different", which makes an inconsistency reading and a
coverage reading the same number rather than two numbers that could be
separated.

## 3. What is sayable

Transfer areas. `1A`, `3B`, `A2`, `C1` mean the same thing state-wide, and five
list types carry them: CSU Transferable, IGETC, UC Transferable, UC Transfer
Eligibility, CSU GE-Breadth and CSU American Ideals. Four of those annotate a
course with areas belonging to more than one scheme at once. **That is a shared
coordinate system, and it is the only one this carrier has.**

## 4. Why the comparison is made one scheme at a time

Comparing the whole `transferAreas` set of a course across lists returns
disagreement for 370 of 370 comparable courses at the first college examined.
That number is manufactured: the CSU-transferable list annotates with IGETC,
CSU GE-Breadth and CSU American-Ideals areas together, the IGETC list carries
IGETC areas only, and the UC lists carry their own markers as well. **Which
schemes a document annotates with is a property of the document.** Read as
disagreement about a course it reports a rate of 100%, and a statistic forced to
100% by a data model is indistinguishable at a glance from a very strong
finding.

Restricted to one `areaType` at a time, between the lists that actually carry
it, the comparison is about placement.

## 5. The reading

    84018 comparable placements over 115 colleges; areaType 1 0 comparable 0 conflict, areaType 2 22761 comparable 0 conflict, areaType 3 24706 comparable 0 conflict, areaType 4 35398 comparable 28 conflict, areaType 5 1153 comparable 0 conflict; 3174 nested, where one list records a finer sub-area than another; 28 mutually non-containing

| areaType | comparable | agree | nested | conflict |
|---|---:|---:|---:|---:|
| 1 | 0 | 0 | 0 | 0 |
| 2 | 22761 | 22761 | 0 | 0 |
| 3 | 24706 | 23461 | 1245 | 0 |
| 4 | 35398 | 33448 | 1922 | 28 |
| 5 | 1153 | 1146 | 7 | 0 |

`areaType` 1 has no comparable placements because only one list carries it.
That is the third state and it is counted separately rather than folded into
either side.

**Nested is not disagreement.** One list records a finer sub-area than another
and neither contradicts the other, which is a difference of resolution between
documents written for different purposes:

| college | areaType | course | placements |
|---|---|---|---|
| Columbia College | 4 | ETHS 15 | CSUGE={D,D1,D3,F} CSUTC={D,F} |
| Columbia College | 3 | ETHS 15 | CSUTC={4,7} IGETC={4,4A,4C,7} UCTCA={4,7} UCTEL={4,7} |
| Columbia College | 4 | HIST 13 | CSUGE={D6} CSUTC={D,D6} |
| Columbia College | 4 | GEOGR 12 | CSUGE={D5} CSUTC={D,D5} |
| Columbia College | 4 | SOCIO 12 | CSUGE={D,E} CSUTC={D} |
| Columbia College | 4 | CHILD 1 | CSUGE={D,D9,E} CSUTC={D,E} |
| Columbia College | 4 | POLSC 10 | CSUGE={D8} CSUTC={D,D8} |
| Columbia College | 4 | POLSC 14 | CSUGE={D8} CSUTC={D,D8} |

## 6. Where the conflicts sit, and what that shape says

    28 conflicts over 12 colleges of 115; the three heaviest hold 17 of them; every one is between CSUGE vs CSUTC; the heaviest college contributes 10 courses carrying one identical discrepancy

| college | conflicts |
|---|---:|
| Bakersfield College | 10 |
| College of the Redwoods | 2 |
| Cypress College | 2 |
| Fresno City College | 1 |
| Imperial Valley College | 1 |
| Los Angeles Harbor College | 2 |
| Mendocino College | 1 |
| Monterey Peninsula College | 5 |
| Napa Valley College | 1 |
| Palomar College | 1 |
| Reedley College | 1 |
| Victor Valley College | 1 |

| college | course | placements |
|---|---|---|
| Bakersfield College | ETHN B20A | CSUGE={D,D3,D6,F} CSUTC={C2,D,F} |
| Bakersfield College | ETHN B20B | CSUGE={D,D3,D6,F} CSUTC={C2,D,F} |
| Bakersfield College | ETHN B30A | CSUGE={D,D3,D6,F} CSUTC={C2,D,F} |
| Bakersfield College | ETHN B30B | CSUGE={D,D3,D6,F} CSUTC={C2,D,F} |
| Bakersfield College | ETHN B36H | CSUGE={D,D3,D6,F} CSUTC={C2,D,F} |
| Bakersfield College | HIST B20A | CSUGE={D,D3,D6,F} CSUTC={C2,D,F} |
| Bakersfield College | HIST B20B | CSUGE={D,D3,D6,F} CSUTC={C2,D,F} |
| Bakersfield College | HIST B30A | CSUGE={D,D3,D6,F} CSUTC={C2,D,F} |
| Bakersfield College | HIST B30B | CSUGE={D,D3,D6,F} CSUTC={C2,D,F} |
| Bakersfield College | HIST B36 | CSUGE={D,D3,D6,F} CSUTC={C2,D,F} |
| College of the Redwoods | ANTH 2 | CSUGE={B1,D1} CSUTC={B1,B3,D} |
| College of the Redwoods | NAS 21 | CSUGE={D,D6} CSUTC={D,F} |
| Cypress College | ETHS 151 C | CSUGE={C2,D,D3,D6} CSUTC={C2,D,F} |
| Cypress College | ETHS 152 C | CSUGE={C2,D,D3,D6} CSUTC={C2,D,F} |
| Fresno City College | SOC 1B | CSUGE={D,D0} CSUTC={A3,D} |
| Imperial Valley College | HIST 140 | CSUGE={C2,D6} CSUTC={D} |
| Los Angeles Harbor College | HISTORY 001 | CSUGE={D,D6} CSUTC={C2,D} |
| Los Angeles Harbor College | HISTORY 002 | CSUGE={D,D6} CSUTC={C2,D} |
| Mendocino College | PSY 220 | CSUGE={D,D9} CSUTC={D,E} |
| Monterey Peninsula College | ECON 2 | CSUGE={D2,D3,D4,D5,D6} CSUTC={D,D2} |
| Monterey Peninsula College | ECON 4 | CSUGE={D2,D3,D4,D5,D6} CSUTC={D,D2} |
| Monterey Peninsula College | POLS 5 | CSUGE={D2,D7,D8} CSUTC={D,D8} |
| Monterey Peninsula College | PSYC 6 | CSUGE={D1,D4,D9,E} CSUTC={D,D4,D9,E} |
| Monterey Peninsula College | SOCI 1 | CSUGE={D0,D1,D4,E} CSUTC={D,D0,E} |
| Napa Valley College | ADMJ 120 | CSUGE={D0,D4} CSUTC={D,D0} |
| Palomar College | AIS 121 | CSUGE={C2,D5} CSUTC={D} |
| Reedley College | COMM 2 | CSUGE={A1,E} CSUTC={D,E} |
| Victor Valley College | HIST 157 | CSUGE={C2,D3,D6} CSUTC={C2,D} |

**A disagreement between two authorities is spread across the system that
declares it. A record-keeping discrepancy clusters.** These cluster: twelve
colleges of 115, the three heaviest holding 17 of 28, one college contributing
ten courses that carry a single identical discrepancy, and every one of the 28
falling between two documents of the same system rather than between two
systems.

**Contrast with C1, which is the point of running both.** There the two values
are published deliberately, in one report, by one body: AR5 gives methane 28 and
AR5 with climate-carbon feedback gives 34, and different reporting standards
knowingly adopt each, both executable against a compliance obligation. Here two
documents of one system disagree about where one course sits. **The first is a
declared multivaluedness. The second is not, and this stage does not report it
as one.**

## 7. Coverage, and why this stage stays open

    115 of 116 colleges returned data, 115 of those carry all 6 list types; 1 college(s) returned HTTP 500 for every list type and hold no record here

Compton College returned HTTP 500 for all six list types and holds no record
here. It is named in the record rather than left as the difference between two
counts. It is also the one California community college whose institutional
identity changed inside the record window, having operated for roughly a decade
under another college's accreditation before regaining its own; **whether that
is why the lists fail is a lead and not a finding, and one call would separate
it from a plain server error.**

**A null needs coverage in a way a positive does not.** One witness settles an
existence claim, and no number of witnesses settles an absence, so this stage
carries `diagnostic_only` until the hole is closed or shown not to matter.

## 8. What this stage does not show

**That articulation is consistent in every respect.** It is consistent where a
shared coordinate system exists. Section 2 lists three respects in which the
question cannot be put to this carrier at all, and their absence is a property
of the identifiers rather than evidence either way.

**That C1's carbon reading is right.** This stage removes one objection to it.
The reading itself stands on C1's own numbers.

**That the 28 are errors.** They are named, their shape is reported, and the
shape is the one record-keeping makes. Deciding which they are would take the
two offices' own correspondence, which is not a dataset.
