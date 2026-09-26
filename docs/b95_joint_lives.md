# B95: several machines are joined by direction, not by sharing, and the life never falls

**RUN: 2026-09-13. Statement and proof below. Checks in `experiments/b95_joint_lives.py`, record
`results/b95_joint_lives.json`, which carries the configuration it ran under. Paper station: zero
data. B78's machine system, price solver and economic life are imported rather than rewritten.**

**Clause (3) of this station was published on 2026-09-13 in a form that is now superseded, and
§5 gives the whole of it.** The reading it reported, that two chains are joined when they share an
input, came from a solver that read the rows of its own system the wrong way round. The corrected
solve returns the opposite answer on the same 202 systems, and the criterion that separates the
cells is a different one.

## 0. The two registrations

[`b78_scrapping.md`](b78_scrapping.md) left both: the joint determination of lives when several
different machines are in use at once, and a configuration in which the economic life falls as the
rate rises, none having been found in the 120 profiles drawn there.

## 1. Theorem 39

**(1) The falling life is not there, on a much larger search.** Over 5,991 drawn efficiency
profiles read across 91 rates, the life falls on none.

**(2) And the direction is the other way.** It rises on a fifth of them and is flat on the rest.
**The mechanism is in the construction**: building a machine costs `c` up front while running an
old one costs `a` each period, so a higher rate makes building dearer relative to running, and the
economy keeps the machine longer.

**(3) The second chain's life enters the wage exactly when the second chain's good enters the
first chain's processes.** Four linkages are drawn, crossing what the second chain is built out of
against whether the first chain takes the second chain's good. **Only the second of those matters**,
and it decides the cell every time:

| what chain two is built out of | does chain one take chain two's good | wage moves with the second life |
|---|---|---|
| its own good | no | `0 / 209` |
| **chain one's good** | no | **`0 / 202`** |
| its own good | **yes** | **`183 / 183`**, median spread `0.450` |
| **chain one's good** | **yes** | **`163 / 163`**, median spread `0.555` |

The wage moves with the *first* life on every system in all four, so the sweep is live in both
arguments and the zeros are readings rather than a dead measurement.

**(4) So sharing an input is the wrong criterion, and the right one is reachability.** The
numeraire is the first chain's good. With no way back from the second chain, the first chain's
processes use only its own good and its own machines, the system is block triangular, and the wage
solves out of the first block alone whatever the second chain does. **The second chain is then a
non-basic in Sraffa's sense and its life is not in the wage.**
[`b96_basics_and_subsystems.md`](b96_basics_and_subsystems.md) reads the same fact off a
single-product system: what a non-basic does stays out of the basic system's prices.

**(5) The obvious measurement reports a coupling that is not there.** Where the wage is flat in a
life, the maximiser over it is whichever the enumeration reaches first, so changing the other
chain can move it without anything responding. **The measurement has to be the wage's spread over
the other life, not the identity of the maximiser.**

**(6) And a solve has to be put back into the rows it came from.** The system is built one row per
process, so the price equation is `M p = w l`. Solving `l M^-1` instead reads the rows as
commodities, returns a positive wage, inverts without complaint, and satisfies nothing.

## 2. What the checks read

All criteria pass at `seed 95`, over 5,991 single-chain profiles and 250 two-chain systems per
linkage.

| | criterion | reading |
|---|---|---|
| `B95-1` `known_answer` | B78's own life | its first profile gives lives `[6, 7, 8, 8]` at its own spot rates `[0.0, 0.2, 0.5, 0.9]`, through its own solver |
| `B95-2` `own_reading` | **the falling life is not there** | falls on `0` of `5991`, rises on `1285`, flat on `4706`. B78 drew 120; this is fifty times that. **Both other directions occur**, so the search can tell them apart |
| `B95-3` `own_reading` | **and the direction is the other way** | rises on `1285 / 5991` (`21.4%`), with the mechanism named in the construction rather than asserted |
| `B95-4` `own_reading` | **the coupling follows direction, not sharing** | the four cells of §1(3). The two where chain one takes chain two's good move with the second life on `183 / 183` and `163 / 163`; the two where it does not move on `0 / 209` and `0 / 202`, the latter sitting at `2.0e-16`. **Whether chain two is built out of chain one's good makes no difference at all** |
| `B95-5` `own_reading` | **why the obvious measurement is wrong** | on all `411` uncoupled systems the wage is flat in the second life, and **more than one second life is viable on `276`**, so there is a tie for the maximiser to break. It moved on `24`. **Whether a tie breaks differently is luck; that the objective is flat is not** |
| `B95-6` `instrument` | the life is enumerated | every truncation from 1 to 8 is tried, `8 / 8` viable at `r = 0.2`, and the life returned carries the largest wage. **Nothing is read off a rule for where to stop**, which matters because the station is about how that point moves |
| `B95-8` `instrument` | **the solve is checked against its own rows** | `B p - (1 + r) A p - w l` over `747` solves is at worst `2.7e-14`. The orientation this station shipped first leaves up to `1.7e+02` and is above tolerance on `746 / 746`. **Both orientations invert and both return a positive wage**, so only putting the answer back into the equations separates them |
| `B95-7` `bookkeeping` | write-back | B78 names this station against both registrations |

**Every mutation seeded was caught.** The load-bearing ones are two. Reading the coupling off the
maximiser rather than off the spread passes on the real data and reports the opposite conclusion.
And a fixture in which the four cells couple the other way round, which is what this station
published first, is now rejected by `B95-4` itself.

## 3. Placement

**A.** The economic life of a machine as an envelope over truncations is B78's and the classical
literature's. That a commodity no one else uses stays out of the rest of the system's prices is
Sraffa's, and §1(4) is that statement carried onto a chain of machines.

**D.** That the lives of several machines are joined by reachability rather than by sharing, so
that a chain feeding the numeraire's chain couples while a chain fed by it does not; that on this
construction the life is monotone non-decreasing in the rate, against an expectation that a higher
rate shortens it; **that a coupling read off maximisers is an artefact of a flat objective**; and
that two orientations of the same rows both invert, both return a positive wage, and only one
solves anything. The last two are measurement statements the literature has no occasion to make
because it does not enumerate.

**C is empty and this station cannot produce it**: it reads no data.

## 4. Scope

B78's machine parameters, efficiency profiles drawn on `[0.2, 2.0]`, chains of 3 to 8 ages for the
single-chain search and 2 to 5 for the pairs, rates from `0` to `0.9`, and a back-link coefficient
of `0.5`. **(1) and (2) are readings about this carrier and not theorems**: what is shown is that
the registered configuration is absent here and that the opposite is common. **(3), (4), (5) and
(6) are structural**: a block triangular system gives a wage that cannot depend on the block it
does not reach, a flat objective has an arbitrary maximiser, and a linear system has one
orientation that solves it.

## 5. What was superseded, and how

**Published 2026-09-13 and withdrawn the same day.** The first version of clause (3) read: two
chains that share only labour do not interact, two chains that share an input do, so the lives are
jointly determined exactly when the chains share an input. It was carried by `B95-4` reporting
`202 / 202` on the shared-input linkage.

**The cause was the orientation of the solve.** `two_chain_system` appends one row per operated
process, so the unknowns are commodity prices and the equation is `M p = w l`. The station solved
`l M^-1`, which is right for a system built with commodities on rows and is what B78's own solver
does on B78's own matrices. On this station's rows it returns a vector satisfying no equation:
the residual of the price equation is `2.96` against `6.4e-16` for the correct solve on the same
system.

**The correction reverses the reading on the same draws.** With the same seed and the same 202
systems, the shared-input linkage now reports `0 / 202`, with a largest spread of `1.3e-15`.

**And it was not a near miss.** The cell that the first version reported as coupled cannot couple,
for a reason visible without any arithmetic: the numeraire is the first chain's good, the first
chain is closed when nothing runs back into it, and the wage is then fixed by that block alone.
**A measurement was standing where a block triangular system had already answered.** The single
chain readings, (1) and (2), use B78's solver throughout and are unchanged to the digit.

**What is now in place so it cannot recur.** `B95-8` puts every solve back into its own rows, and
`B95-4` is seeded with a fixture whose cells couple the other way round and rejects it.
