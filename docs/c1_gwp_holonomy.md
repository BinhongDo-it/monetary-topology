# C1. An administratively declared exchange rate, and where it fails to compose

    RUN:     2026-08-27T17:22Z
    SOURCE:  data/raw/gwp/globalwarmingpotentials.csv (pinned commit d3cb489, CC0)
    SCRIPT:  experiments/c1_gwp_holonomy.py
    RECORD:  results/c1_gwp_holonomy.json
    STATUS:  closed. Both halves have run; section 8 is the second.

## 1. Why this carrier

Everything measured in this project until now has been money, and a price
field's failure to be integrable can always be argued back to friction:
transaction costs, thin books, stale quotes, someone not paying attention. The
argument is weak but it is available, and it costs work to close.

A global warming potential closes it by construction. It is not a measurement of
a gas and not a price of anything. It is a declaration, printed in an assessment
report and adopted by statute and by protocol, that one tonne of species `a` is
to be counted as `GWP_s(a)` tonnes of CO2-equivalent. Compliance schemes offset
against that number, so the declaration is executable. There is no market in it
at all.

So if the declarations do not compose, friction cannot be the reason. The
remaining explanation is that the scalar they are declarations about does not
exist.

## 2. The object, and why the count comes before the values

Put every species on one side and CO2-equivalent on the other. Draw one edge per
standard that quotes that species. The graph is a star with parallel edges.

A species quoted under `S_a` standards contributes `S_a - 1` independent loops,
so

    b1 = sum_a (S_a - 1)

and each basis loop is `a --(s)--> CO2e --(s')--> a`, whose holonomy is
`GWP_s(a) / GWP_s'(a)` under the two standards: the same gas, read twice.

**One standard gives `b1 = 0`.** There is nothing to be inconsistent with. Every
additional standard adds one loop per species it covers, so the cycle rank is a
direct measure of how much room the institutional arrangement leaves for
disagreement, computable before any value is read. That is gate zero for this
carrier and it costs nothing.

## 3. C1-1. The count, two ways

`cycle_rank` takes an adjacency matrix, so parallel edges cannot be spelled
directly. Subdividing each parallel edge with its own midpoint gives a simple
graph and changes nothing about the cycle space, so the repository's own
function can check the closed form rather than the closed form standing alone.

    E=444 edges over V=106 nodes; closed form sum(S_a-1)=339; cycle_rank on the subdivided graph=339; species quoted by exactly one standard=17 contribute no loop

The two agree. This criterion is structural: it is about this code, not about
the world, and it has no threshold in it.

**The seventeen species quoted by exactly one standard contribute no loop and
are undecidable here, not integrable.** They are named in the record. Counting
them as agreement would be the error this separation exists to prevent.

## 4. C1-2. The holonomy spectrum

Reading fixed before the run: a species whose six GWP-100 values agree reads
holonomy exactly 1, and that is evidence the declared field is integrable on
that species. Fewer than two quotes is the third state.

    88 species decidable, 17 undecidable (one quote only); holonomy exactly 1: 0; median 1.4150, quartiles 1.2568/1.8483, max 60.640 (HFE374pc2)

Not one of the eighty-eight decidable species reads 1.

The ten widest loops, printed as objects rather than summarised:

| holonomy | species | low | high |
|---:|---|---|---|
| 60.640 | HFE374pc2 | AR6GWP100 = 12.5 | AR5CCFGWP100 = 758 |
| 11.000 | HFE263fb2 | AR5GWP100 = 1 | TARGWP100 = 11 |
| 11.000 | HFE365mcf3 | AR5CCFGWP100 = 1 | TARGWP100 = 11 |
| 7.500 | CHCl3 | SARGWP100 = 4 | TARGWP100 = 30 |
| 5.013 | HFE227ea | TARGWP100 = 1500 | AR6GWP100 = 7520 |
| 4.776 | HFE356mec3 | TARGWP100 = 98 | AR5CCFGWP100 = 468 |
| 4.545 | HFE356pcc3 | TARGWP100 = 110 | AR5CCFGWP100 = 500 |
| 4.236 | HFE329mcc2 | TARGWP100 = 890 | AR6GWP100 = 3770 |
| 3.561 | HFE245fa1 | TARGWP100 = 280 | AR5CCFGWP100 = 997 |
| 3.335 | HFE356pcf2 | TARGWP100 = 260 | AR5CCFGWP100 = 867 |

`HFE374pc2` is not a parse error. It runs TAR 540, AR5 627, AR5CCF 758, then
AR6 12.5: a genuine reassessment of two orders of magnitude, published.

## 5. C1-3. Two numbers from one report

This is the sharpest form, because it holds the report fixed as well as the gas
and the horizon. AR5 published a 100-year value with climate-carbon feedback and
one without. Both are authoritative, both are in current use, and institutions
choose between them: methane is 28 on one and 34 on the other.

    one report, one gas, one horizon, two published numbers: 86 species comparable, ratio exactly 1 for 1 of them, median 1.1913, range 1.0000 to 2.0000; CH4 is 28 against 34

The five widest:

| ratio | species | AR5 | AR5 with feedback |
|---:|---|---:|---:|
| 2.0000 | HFE263fb2 | 1 | 2 |
| 1.5000 | CH3Br | 2 | 3 |
| 1.2500 | HFC152 | 16 | 20 |
| 1.2500 | CHCl3 | 16 | 20 |
| 1.2500 | CH3Cl | 12 | 15 |

**No appeal to vintage, horizon or jurisdiction is available against this one.**
The multivaluedness is inside a single document.

## 6. C1-4. Whether the vintages are converging

The obvious reading of sections 4 and 5 is that science improved and the older
numbers are superseded. That reading makes two predictions which were fixed
before the run: the vintage sequence should be close to monotone, and the size
of successive revisions should shrink. Both branches were reachable.

    54 of 79 species non-monotone in vintage order, including CH4 N2O CFC11 CFC12; median relative revision SAR->TAR 19.68% TAR->AR4 3.68% AR4->AR5 9.05% AR5->AR6 12.63%; steps shrinking: False

Successive revisions, median relative change:

| step | n | median |
|---|---:|---:|
| SAR -> TAR | 36 | 19.68% |
| TAR -> AR4 | 50 | 3.68% |
| AR4 -> AR5 | 58 | 9.05% |
| AR5 -> AR6 | 84 | 12.63% |

The largest step is the first and the second largest is the most recent. The
four most-used gases are all non-monotone:

| species | SAR -> TAR -> AR4 -> AR5 -> AR6 |
|---|---|
| CFC11 | 3800 -> 4600 -> 4750 -> 4660 -> 6230 |
| CFC12 | 8100 -> 10600 -> 10900 -> 10200 -> 12500 |
| CH4 | 21 -> 23 -> 25 -> 28 -> 27.9 |
| N2O | 310 -> 296 -> 298 -> 265 -> 273 |

Nitrous oxide falls and then rises. Methane's AR6 value is below its AR5 value.

**Concurrency is the separate and stronger point.** These are not a sequence of
replacements. Reporting standards in force at the same time specify different
members of this family: the latest GWP-100 under some, GWP-100 not necessarily
the latest under others, and a 20-year horizon under others again. The older
values are not historical.

## 7. What this does not show

**Anything about carbon markets.** The readings above are about declarations.
The record carries `diagnostic_only` and its reason for exactly this distance.

**That a scalar is impossible in principle.** What is shown is that the
institutions issuing these declarations do not agree on one, that they have not
converged on one across thirty years, and that a single report can decline to
pick between two. Whether some other procedure could construct one is a
different question and this stage does not touch it.

## 8. Whether the disagreement is operative

Sections 4 to 6 show the declared conversions disagree and are not converging.
Neither settles whether that is a live arrangement or a historical record, and
**the reading was fixed before the survey was compiled**: one basis in force
anywhere and this stage measures a transition; more than one in force at the
same time and an obligation can be discharged two different ways in the same
year. The first branch was reachable, and the treaty layer converging on a
single basis by the end of 2024 is exactly what would have produced it.

    10 regimes surveyed, 6 of them in force now; 7 of their methane values cross-check against the dataset and 0 disagree; values in force now [27.0, 27.9, 28, 29.8], spanning 1.104; values across the whole record [21, 25, 27.0, 27.9, 28, 29.8, 84], spanning 4.000

| regime | basis | CH4 | in force | |
|---|---|---:|---|---|
| UNFCCC, Annex I national inventories | SAR GWP-100 | 21 | 2002 to the second commitment period | superseded |
| Kyoto Protocol, second commitment period | AR4 GWP-100 | 25 | 2013 to 2020 | superseded |
| Paris Agreement, Enhanced Transparency Framework | AR5 GWP-100 | 28 | from 31 December 2024 | in force |
| US EPA Greenhouse Gas Reporting Program, 40 CFR part | AR4 GWP-100 | 25 | reporting years 2013 to 2023 | superseded |
| US EPA Greenhouse Gas Reporting Program, 40 CFR part | AR5 GWP-100, with AR6 values for gases AR5 does not cover | 28 | from reporting year 2024 | in force |
| New York State, statewide emissions accounting | AR5 GWP-20 | 84 | 2019 to 26 May 2026 | superseded |
| New York State, statewide emissions accounting | AR6 GWP-100 | 27.9 | from 26 May 2026 | in force |
| AR6 as applied by corporate and crediting programmes | AR6 GWP-100, non-fossil | 27.9 | current | in force |
| AR6 as applied by corporate and crediting programmes | AR6 GWP-100, fossil | 29.8 | current | in force |
| Programmes listing the third AR6 methane value | AR6 GWP-100, third variant | 27 | current | in force |

**The treaty layer did converge, and the disagreement moved rather than
closing.** Reporting under the Paris Agreement framework has required AR5
100-year values since the end of 2024, and the United States reporting
programme moved to the same basis from reporting year 2024. What remains is of
two kinds, and both are current.

**One assessment report publishes three methane values and all three are in
circulation.** AR6 gives a value for biogenic and combustion methane, a higher
one for fossil fugitive methane, and a third that reporting and crediting
programmes list and that the Greenhouse Gas Management Institute describes as
resting on assumptions unsuited to greenhouse gas accounting. **So the split is
no longer between assessment reports. It is inside one.**

**And the treaty excludes the distinction its own source draws.** Decision
7/CP.27 adopts AR5 table 8.A.1 while excluding the fossil methane values, so
one tonne of fugitive fossil methane counts as 28 under the treaty and as 29.8
under the corporate standard, in the same year, for the same physical release.

**One jurisdiction priced the choice, in public, this year.** New York
legislated a twenty-year horizon in 2019, putting methane at 84, and replaced it
with a hundred-year basis on 26 May 2026, putting methane at 27.9. Applied to
the same physical record for 1990 to 2023, the reported reduction moves from
14.8 percent to 24 percent. **Nothing was emitted or abated to produce those 9.2
percentage points.** That is what it costs to change which of these declarations
is in force, measured by the jurisdiction that changed it.

**Two regimes named and not surveyed**: the European Union, and a New Jersey
statute reported to mandate a twenty-year horizon. Sources located for both were
commentary rather than the instruments. This bounds the survey's breadth and not
its reading: more than one basis in force is an existence claim, and one pair
settles it.

**The table is checked rather than trusted.** Seven of its methane values name a
column of the independent dataset section 2 uses, and all seven agree with it.
Three name none, because the dataset carries no AR5 20-year column and no
fossil against non-fossil AR6 pair; those are recorded as uncheckable rather
than matched to the nearest available column.
