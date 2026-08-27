# The C track: an exchange rate with no market in it

A price field that does not compose can always be argued back to friction.
Transaction costs, thin books, stale quotes, someone not paying attention: the
argument is weak, but it is available, and it costs work to close.

**The C track closes it by moving the question somewhere friction does not
reach.** Wherever an institution declares that one unit of `a` counts as
`R(a,b)` units of `b`, it is asserting that a scalar `v` exists with
`R(a,b) = v(a)/v(b)`. That assertion has an exact consequence: around any closed
loop of declarations the product is 1. The consequence is checkable, it requires
no market, and where the declarations are administrative rulings rather than
prices, friction is not among the things that could explain a product away
from 1.

Two carriers, one claim and one control.

## C1. A greenhouse gas against CO2-equivalent

A global warming potential is not a measurement of a gas. It is a declaration,
printed in an assessment report and adopted by statute and by protocol, that one
tonne of a species counts as so many tonnes of CO2-equivalent, and compliance
schemes offset against that number. Nothing is traded to produce it.

Put every species opposite CO2-equivalent, one edge per standard that quotes it.
A species quoted under `S` standards contributes `S - 1` independent loops, so
the cycle rank is `sum (S_a - 1)`, each loop being the same gas read twice.
**One standard gives a cycle rank of zero**: the field is integrable by
construction and there is nothing to disagree with. The count is therefore a
measure of how much room the arrangement leaves, computable before any value is
read.

| | |
|---|---|
| species, published 100-year values | 105 |
| cycle rank over the 100-year family | 339, checked two ways |
| species whose six values agree | **0 of 88** |
| median loop | 1.4150, quartiles 1.2568 and 1.8483, largest 60.640 |

**The sharpest reading holds the report fixed as well as the gas and the
horizon.** AR5 published a 100-year value with climate-carbon feedback and one
without. Both are authoritative and institutions choose between them. Across 86
comparable species **the two agree exactly once**; methane is 28 on one and 34
on the other.

**The obvious reading of that, which is that science improved and the older
numbers are superseded, makes two predictions.** The vintage sequence should be
close to monotone and successive revisions should shrink. Of 79 species with
three or more vintages, **54 are non-monotone**, including the four most-used
gases: methane runs 21, 23, 25, 28, 27.9 and nitrous oxide falls and then rises.
Median revisions run 19.68, 3.68, 9.05 and **12.63 percent**, so the largest step
is the first and the second largest is the most recent.

## C1, second half. The disagreement is operative

Sections above establish that the declarations disagree. Whether that is a live
arrangement or a historical record is a separate question, and the reading was
fixed before the survey: one basis in force anywhere and this measures a
transition; more than one at the same time and an obligation can be discharged
two different ways in the same year.

**Four methane values are in force at once**, spanning 1.104; across the whole
record seven values span 4.000. Seven of the surveyed values cross-check against
an independent dataset and none disagrees.

**The treaty layer did converge, and the disagreement moved rather than
closing.** Reporting under the Paris Agreement framework has required AR5
100-year values since the end of 2024. What is left is current and of two kinds.
AR6 publishes three methane values and all three circulate: one for biogenic and
combustion methane, a higher one for fossil fugitive methane, and a third that
programmes list and that specialists describe as resting on assumptions
unsuited to the purpose. And the treaty adopts AR5 while excluding the fossil
methane distinction its own source draws, so **one tonne of fugitive fossil
methane is 28 under the treaty and 29.8 under the corporate standard, in the
same year, for the same physical release**.

**One jurisdiction priced the choice this year, in public.** New York legislated
a twenty-year horizon in 2019, putting methane at 84, and replaced it with a
hundred-year basis on 26 May 2026, putting methane at 27.9. Applied to the same
physical record for 1990 to 2023, the reported reduction moves from 14.8 percent
to 24 percent. **Nothing was emitted or abated to produce those 9.2 percentage
points.** That is the cost of choosing which declaration is in force, measured
by the body that changed it.

## C2. The control

C1 has one cheap objection: any administrative system of that scale accumulates
inconsistency, so the reading might be about bureaucracies rather than about
whether the scalar exists. **Answering it takes a second system rather than an
argument** — comparable in scale and age, carrying several parallel
classification schemes at once, publishing its declarations the same way, and
with no prices, no trading and no friction in it.

California's course articulation system meets each condition. It publishes, per
college, which transfer areas each course is certified for, under six list
types, in a vocabulary that means the same thing state-wide.

| | |
|---|---|
| colleges swept, of 116 | 115, each with all six list types |
| comparable placements | 84,018 |
| agree | 80,816 |
| one list recording a finer sub-area than another | 3,174 |
| mutually non-containing | **28** |

The 28 sit in 12 colleges, **every one of them falls between the same two
documents of the same system**, and the heaviest college contributes ten courses
carrying a single identical discrepancy. A disagreement between two authorities
is spread across the system that declares it; this clusters.

**One arm could have read either way and read the other one.** If a scalar with
two thresholds governs transferability, the stricter system's list is contained
in the looser one's. It is, at 113 colleges of 115, with three courses in total
on the other side.

**So the multivaluedness C1 measures does not follow from the size of an
institution.** Here is an institution of the same kind, asked the same question,
and it agrees with itself.

## What the two together license

**That a declared conversion can be multivalued with no market present, and that
this is a property of the declarations rather than of institutional scale.**
C1 measures it; C2 shows a comparable system where it does not appear.

**That the choice between declarations is a policy variable with a measurable
price.** New York's own reporting moves 9.2 percentage points on the change of
basis, with the physical record fixed.

**Readings about declarations, and about which of them an obligation can be
discharged against.** Neither stage reads carbon market prices or volumes,
neither reads what any gas does in the atmosphere, and C2's scope is the
placements where a shared vocabulary exists: course identifiers in that system
are institution-local, so questions phrased in terms of the same course are put
to a different carrier or not at all.

C2 carries one named absence. Compton College returned a server error for all
six list types and holds no record; it is the one California community college
whose institutional identity changed inside the record window. **A null needs
coverage in a way a positive does not**, so that gap is named rather than left
as the difference between two counts.

## Reproducing it

    python data/fetch_gwp.py --pull
    python experiments/c1_gwp_holonomy.py          -> results/c1_gwp_holonomy.json

    python data/fetch_assist.py --transferability CSUTC IGETC UCTCA UCTEL CSUGE CSUAI
    python experiments/c2_transfer_areas.py        -> results/c2_transfer_areas.json

Both records are byte-identical across runs. C1 reads one 6,744-byte table
pinned to a commit and verified by hash. C2 reads 690 payloads pulled from a
public API, each checked against the list type it reports rather than the one
requested. Per-stage detail is in `docs/c1_gwp_holonomy.md` and
`docs/c2_transfer_areas.md`; every criterion, including the ones that read the
other way, is in `RESULTS.md`.

A third carrier, provincial university admission cutoffs, has its design and
criteria written and is held on availability. What would open it is recorded in
`data/SOURCES.md`.
