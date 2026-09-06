# B44 — the Sound Toll, a flag class created by one treaty and abolished by another

A toll that two treaties switched on and off gives the class index of
`docs/b4_directed_edges.md` §5.1 something it rarely has: a carrier where the
class difference is created by a dated public instrument, removed by another
dated public instrument, and where both halves of the registered ratio are
written down in the same ledger.

The Peace of Brömsebro (1645) exempted Swedish ships and Swedish goods from the
Sound Toll. The Peace of Frederiksborg (1720), Article 9, ended the exemption
and put Sweden on the same tariff as the English and the Dutch. Between those
two dates one class of ship paid a lighthouse due and nothing else while every
other class paid by cargo; after 1720 both paid the same way. The Danish crown
recorded every passage either way, so the exempt years are legible in the same
ledger as the taxed ones.

Pre-registered design: the criteria are written into the scripts that produce
each reading, each record carries the criterion verbatim, and every quantity a
run produced is reported here.

## The carrier

Sound Toll Registers Online, the classic packaging: `doorvaarten.csv`,
2,152,670 passages of the Sound between 1497 and 1857, and `ladingen.csv`,
5,568,590 cargo parcels keyed to them. Ship's home port comes from
`schipper_plaatsnaam`, standardised through the project's source-place table to
the register's own place codes; the coding resolves 98.49 percent of names.
Treatment is assigned by **sovereignty inside the window**, not by the modern
country field, and that distinction is the whole of arm C below.

**Currency, pinned before anything else.** Over 1630–1780 the `totaal_muntsoort1`
field is Daler 444,395 times (86.8 percent), Rosenobel 51,212 (10.0), Skilling
15,212 (3.0) and Rigs Daler 1,231. Only Daler enters a column here; the other
three are reported separately and never added in. About a third of all amounts
are written as fractions (`8 1/2`, `1/2`), and a parser that truncates them
silently biases every median downward. The first pass of this station did
exactly that, and its readings are withdrawn for that reason among two others,
recorded below.

## The estimator, and why the fixed fee does not need to be modelled

From `docs/b4_directed_edges.md` §5.1, with `ω(u,v) = −t(u→v)`:

```
S − S'  = 2[ŵ_a − ŵ_b]        the index part
−(S+S') = 2[ω̄_a + ω̄_b]        the friction part
rho     = |S − S'| / −(S + S')  ∈ [0,1]        Theorem 6(4)
```

`docs/b1_theorem.md` §9.1 records the case where this ratio cannot be formed at
all: the numerator was exactly known from a treaty and the denominator lived in
a private bilateral contract. **Here both halves are in the ledger.** The toll is
levied in each direction and both levies are recorded, so the friction term is
read rather than assumed. This is the first carrier in this family whose
denominator is observable.

Written out for two classes and two directions:

```
S − S'  = [t_b(east) − t_b(west)] − [t_a(east) − t_a(west)]
−(S+S') =  t_a(east) + t_a(west) + t_b(east) + t_b(west)
```

A fee that is common to both classes and symmetric in direction cancels from the
numerator and stays in the denominator. That matters because the fixed component
is a constant only inside the exemption window: its median is 4 Daler there and
drifts to 2 to 3 after 1720. In the double difference it does not have to be
separated at all, and a step that looked mandatory turns out to have been an
artefact of the earlier way of measuring rather than a property of the world.

**The decomposition is an identity, and it was checked.** Subtracting the sum of
a voyage's parcel charges from its recorded total leaves a small discrete
residual: 88 distinct values, 96 percent of them between 0 and 4.5, stepping in
half Daler. Inside the exemption window that residual is the constant 4 in both
directions, 95.1 percent of westbound voyages and 91.9 percent of eastbound.
The exempt class pays the same 4. So the exemption remitted the charge on cargo
and not the fixed due, which is why exempt ships appear in the ledger at all.

**What that residual is, from a transcribed ledger page.** The archive's own
published transcription of an entry of 25 September 1731 prints the charges of a
single voyage separately: a ship of 16 læster carrying French salt, cargo duty
4 Rdr 12 S, **fyrpenge 1 Rdr on its own line**, total 5 Rdr 12 S. Joining the
residual to the burden recovered from the free-text tonnage field, over 44,265
voyages that carry both, the 15 to 19 læster band has a modal residual of exactly
1.0000. **The transcribed entry and the measured band agree on the value, not
merely on the order of magnitude**, which identifies the residual as the
lighthouse due rather than leaving it as an unnamed remainder.

It is a charge on the ship rather than on the cargo, and that is measured rather
than inferred: the median residual is 4.000 at one parcel, at two, at three and
at six, and 4.000 in both the seventh and ninth deciles of cargo value. Above
about 20 læster it tracks burden at close to one skilling per læst (0.542 Daler
on a median 24, 0.750 on 35, 1.500 on 68, 2.667 on 126.5, so 1.08, 1.03, 1.06 and
1.01 skilling per læst), and below that a floor of one Daler takes over.

The published schedule gives 2 skilling per læst for a laden ship, and the factor
of two between that and the measured figure is the factor this station has
already measured for something else. The conversion base identified here is 48 to
the Daler, and the external chain behind it runs 1 daler = 96 Danish skilling =
48 Lübeck skilling, the accounts being kept in Lübeck. So every skilling printed
above is a Lübeck one, and one Lübeck is two Danish. Read in Danish skilling the
same cells give 2.02 at 100 læster and above, 2.12 at 50 to 99, 2.33 at 30 to 49
and 2.50 at 20 to 29, converging on the published figure as the ship grows, which
is what a per-læst rate with a small floor under it does. **The likely reading is
that the two figures are the same rate in two units**; what would settle it is
one sentence of the schedule, whether its skilling is named Danish or Lübeck. It
does not bear on which line of the ledger the residual is, which the transcribed
entry settles on its own.

**The residual is class-dependent, so the constant belongs to the western fleets
rather than to the carrier.** Median residuals in the exemption window are 4.000
for Dutch, English and German ships, against 1.375 Danish and 1.542 Norwegian,
whose values cluster on 0.5 and 1.0 as the per-læst rate would predict for
smaller ships. Whether a burden was recorded is itself collinear with the flag,
so a subsample selected on having one has a median of 1.000 while the rest has
4.000: two class mixtures rather than two answers.

## The conversion base was identified, not borrowed

Roughly half of the amounts carry a subsidiary unit, and dropping them leaves
13.1 percent of voyages whose median parcel count is 1, that is, the simplest
cargoes only. Recovering the rest needs the ratio of Daler to skilling in these
accounts.

Two internal routes give it. The subsidiary value itself has a hard edge: 47
occurs 6,326 times in the parcel file, 48 occurs 19 times, and everything above
is single-digit keying error. And the base can be made to answer to a constant it
must reproduce: sweeping the base and asking which one puts the exemption-window
residual back on 4 gives 56.70 percent at 48 against 44.74 at the next best and a
floor of about 38.

An external chain, found afterwards, agrees to the digit. A Danish reference work
gives 16 skilling to the mark and 6 mark to the daler from 1625, so 96 Danish
skilling to the daler; Gøbel (2010) records that the skilling figures in these
accounts are Lübeck skilling, each worth two Danish. **96 Danish = 48 Lübeck**,
which is the number the residual scan had already picked out.

## The registered quantity, exemption window

Exemption window 1650–1709, non-exempt class, both endpoints resolvable and the
voyage genuinely crossing the Sound: 27,020 voyages, 16 route cells with at least
40 passages in each direction.

```
rho median 0.2552, quartiles 0.1809 / 0.3802, range 0.0478 – 0.4661
```

Two limits travel with those numbers. There are 16 route cells, so nothing is
inferred across cells and only the per-cell readings and their distribution are
reported. And `E` and `W` are medians over each direction rather than the two
legs of one voyage, so this is a route-level reading.

No cell reaches 1. By Theorem 6(4), `rho = 1` exactly when one of `S`, `S'`
vanishes, so none of the 16 is degenerate. The same statistic measured on an
unrelated carrier (`docs/b4_directed_edges.md` §5) has median 0.2000. Two
carriers with nothing in common return the same order of magnitude.

**The withdrawn first pass, and what withdrew it.** An earlier substitution set
the exempt class to `ω ≡ 0` and read the total charge as a price in both
directions. It returned a median of 0.6686 and a maximum of 0.9765. Three errors,
each found by printing an object rather than a summary: the exempt class does pay
the fixed due, so `ω_a ≡ 0` is false; eastbound is not a price but a flat fee,
since half to two thirds of eastbound voyages on a route pay the identical
number while the westbound mode covers about 1 percent of them, which is a fixed
absolute threshold against a heterogeneous distribution; and the fraction parser
truncated. Corrected, the median falls to 0.2552 and the ceiling disappears
entirely. The three errors together had turned an ordinary reading into one
pinned near its bound.

**A reduction check on the exempt class.** The `t_a ≡ 4` assumption was then
measured directly rather than assumed. Exempt-class medians are 2.104 eastbound
and 5.812 westbound, consistent with paying only the fixed due, while the upper
quartiles are 20.0 and 22.5, so about a quarter of Swedish-flag voyages in the
exemption window did pay a real cargo charge. That is what the treaty language
predicts: the exemption covered Swedish vessels **and** commodities, and a Swedish
ship carrying foreign goods is outside it. Substituting the measured values for
the assumed 4 moves the distribution median from 0.2552 to 0.2422, down 5.1
percent, while individual cells move by a median of 21.7 percent and as much as
118.9. **The median is what carries; the individual cells carry a caveat**, and
the thinnest of them, whose numerator is 3.1 Daler, is not citable alone.

## Arm C: which ports the exemption actually covered

Arm C was registered as three hand-picked pairs. Enumerating instead is cheap
here, because the readings all come off one cached table, and it is a strictly
harder test: three pairs have to agree, ninety-four have to.

The observable is the fill rate of the quantity field on a voyage's cargo lines.
An exempt voyage had nothing to assess, so the clerk left the quantity blank.
Every home port with at least 150 cargo lines in both the pre-window and the
exemption window is printed in ascending order of its exemption-window reading,
with no threshold drawn: 94 ports.

**Eleven ports collapse. All eleven were under the Swedish crown in that window.
None of the other 83 collapses.** The set is not chosen; sorting the 94 and
looking at the largest gaps puts the two biggest at the boundaries of that set,
0.353 to 0.650 and 0.106 to 0.353. What carries is that the 11-against-83
partition coincides with the sovereignty table, not the size of the gap that
separates them.

Two of the eleven are coded to the wrong modern country, and **both mistakes are
ports that were Swedish at the time**: Stralsund, coded Germany, and Stettin,
coded Poland, which reads 0.968 before, 0.029 during and 0.965 after, while the
only other large port sharing its modern code reads 0.944 throughout and never
collapses. A coding that errs on exactly the two points where sovereignty and
modern nationality diverge is itself evidence for reading by sovereignty.
(Stettin's 1720 is doubly caused, since the same year both ended the exemption
and ceded the town to Prussia, so that port cannot separate the two.)

### Widening the threshold, and the statement it forces

The `n ≥ 150` requirement applied to the **pre**-window, and that is still a
selection on the outcome variable, because a port thin in the pre-window is a
small port or an overseas possession, which is the same thing the exemption
question is about. Dropping the pre-window requirement admits 171 ports, of
which 29 were Swedish and 142 were not, classified mechanically: inside
1660–1709 the Swedish homeland is the modern country, so only the possessions
outside it have to be named by hand.

| | ≤ 0.15 | 0.15–0.50 | > 0.50 |
|---|---|---|---|
| Swedish (29) | **21** | 6 | 2 |
| not Swedish (142) | **0** | 1 | 141 |

**No port outside Swedish sovereignty reads below 0.15, and the first 22 in sort
order are all Swedish.** That half is what carries identification: a non-Swedish
port reading like a treated one would end the sovereignty reading, and there is
none. The one non-Swedish port in the middle band reads 0.237 with n = 152 and
also reads 0.213 after 1720, so it is low in every window rather than treated.

The other half is not empty, and it has structure. Eight Swedish ports do not
collapse, and four of them are the Baltic provinces (Riga 0.299, Narva 0.306,
Nyen 0.338, Reval 0.417); one is Bremen-Verden (Stade 0.680, n = 984), which is
a clear exception with no explanation yet, and pointedly not explained by
"possessions inside the Empire", since Swedish Pomerania reads 0.020 to 0.149.

**So the supported statement is that the exemption followed the realm proper,
the homeland with Pomerania and Wismar, rather than every territory under the
Swedish crown.** That is weaker than "the exemption followed sovereignty", and
it converts the Riga anomaly from one odd port into a group of four.

The coverage of a toll exemption is something two negotiators chose, so it is
the kind of quantity that may only be stated conditionally or existentially; the
narrowed form is the admissible one and the universal form was never available,
independently of what widening the threshold showed.

### One registered expectation that did not hold

The eleven ports changed hands on three different dates (Halland 1645, Pomerania
1648, Scania and Bohuslän 1658), so each port's break was expected to sit on its
own treaty. It does not. The two groups with enough observations fall together,
drifting from 1649, clearly down from 1652, and reaching bottom around 1660,
while the never-Swedish control holds between 0.77 and 0.91 throughout. What the
data show is one common administrative transition, not three dated ones.

This does not touch the sovereignty reading; it replaces the timing layer under
it. The legal exemption runs from 1645 and the recording practice from about
1650, spreading until roughly 1660, which is also how the standard monograph puts
it: between 1650 and, practically, 1710. The design's decision to exclude 1645–59
from both windows was necessary rather than cautious. A second, independent
reason to exclude that stretch also showed up: a general dip in archive quality
in the late 1650s that reaches the control ports too, several years wide, which
cannot produce a fifty-year reading of 0.049 confined to one class but does make
the year-by-year break unreadable.

## Arm C bis: the Baltic provinces are a mixture, not a partial exemption

The four provincial ports sit between the treated and control bands. The
monograph says the exemption covered Swedish vessels **and** commodities, and
these were entrepôts where the ship was Swedish and the cargo often Dutch or
Lübeck. That gives a hypothesis with two reachable outcomes: a mixture of exempt
and non-exempt voyages shows up as a bimodal per-voyage fill rate, and a partial
exemption shows up as mass in the middle.

Per voyage, 1660–1709:

| group | voyages | exactly 0 | middle | exactly 1 |
|---|---|---|---|---|
| Baltic provinces | 1,515 | **88.3%** | 1.1% | 10.7% |
| Swedish homeland | 14,109 | **97.9%** | 0.2% | 1.9% |
| Dutch control | 3,954 | 18.4% | 4.1% | 77.6% |

**A voyage is measured whole or not at all.** The middle band is under 1.3
percent in both treated groups. Port by port the four agree to within half a
percentage point: Riga 88.4, Reval 88.2, Narva 88.5, Nyen 88.0, across four
different modern countries. They are one institution read four times.

The per-parcel figure (0.33) and the per-voyage figure (0.107) differ by three,
and the difference is itself explained: the provincial voyages that were assessed
carried three times the median parcel count of those that were not, so
parcel-weighting magnifies them exactly threefold. Both figures are correct at
their own weight.

Normalising against the control group's own 16.61 percent of blank voyages,
which is archive loss rather than exemption, the homeland captures 97.5 percent
of the available range and the provinces 85.9. **The provinces received 88
percent of the treatment the homeland received.**

**The assessed 11 percent is three things, not one.** Split by period it reads
21.2 percent over 1660 to 1689, 8.1 over the 1690s, 17.0 over 1700 to 1702 and
15.1 over 1703 to 1709, so the settled baseline is 8 and the average is raised at
both ends: at the start by the same administrative spread that the entry side
shows, and at the end by the war.

Two candidate causes were tested and one of them fails outright. The exemption is
described in the literature as covering Swedish bottoms carrying cargo to and
from Sweden, which makes the endpoints part of the condition, and that shows up
in the right direction and small: provincial voyages with no endpoint anywhere in
the realm are assessed 17.9 percent of the time against 10.4 for those with one,
and the homeland reads 4.7 against 2.6, while the control moves the other way,
81.9 against 86.7, which is the check that this is not mechanical. A provincial
voyage with no Swedish endpoint at all is still exempt 82 percent of the time, so
the condition is visible and is not the main cause. **Loss of the provinces to
Russia is not the cause of the wartime rise**: the ports fell on different dates,
Nyen in 1703, Narva in 1704, Riga and Reval in 1710, and Riga is already at 38
percent in 1701, nine years early, while Nyen and Narva show no step at their own
dates and instead simply stop appearing.

**The remaining half of the stated condition cannot be read on this carrier at
all.** Whether the cargo was Swedish would settle it, and an unassessed voyage
has no cargo recorded: among provincial voyages, 100 percent of assessed ones
name a commodity and carry a quantity, against 2.0 percent and 0.0 percent of
unassessed ones. The ledger records what it taxed.

## Arm D: the same quantity across 1720

After 1720 both classes pay by cargo, so all four cells can be measured
directly and the exemption-window formula is the algebraic special case of the
same estimator. The two windows are therefore read with one instrument.

The exemption window itself cannot be read this way, and not by accident: an
exempt ship has no cargo charge, so the Swedish cells are empty by construction.
Zero routes clear the four-cell requirement there, which is exactly why the
exemption-window reading had to be derived rather than measured.

| | exemption 1650–1709 | after 1720–1779 |
|---|---|---|
| Swedish against non-Swedish (the treated pair) | **0.2552** (16 routes) | **0.0794** (8 routes) |
| Dutch against the rest (the placebo) | **0.0722** (6) | **0.0858** (24) |

**The floor is composition, not sampling noise, and that is measured.** A
bootstrap standard error answers "how many sampling deviations from zero", and
where the floor is composition the answer is always "many": the treated pair's
`|S−S'|/se` has median 2.99 with 5 of 8 above 2, and the placebo's has median
2.29 with 13 of 24 above 2. Both are "significantly non-zero" and both are the
same thing. So the placebo, not the bootstrap, is the resolution floor for this
quantity, and **the placebo does not move across 1720** (0.0722 to 0.0858), which
is what a floor should do.

**The registered conditional hits as far as "indistinguishable" and no further.**
The registered passing condition was that the treated pair fall *below* the
placebo. It falls *onto* it, and the two cannot be separated: medians give
0.0794 < 0.0858 while means give 0.0858 > 0.0617, so the order is decided by the
choice of aggregator rather than by the data. What is stable under both
aggregators and under a wider route threshold is that both post-1720 figures sit
far below the exemption-window 0.2552.

Printing the four cells rather than the ratio explains the two large post-1720
values immediately, and the explanation is the same for both: on one route the
non-Swedish eastbound median is 2.00, which is the fixed due, so those ships
sailed east essentially empty while the Swedish ships carried 239 Daler of cargo;
on the other all four medians hug the fixed due, so the ratio is large because
the denominator is 30 while the absolute difference is eleven Daler. Both are
cargo composition.

Plainly: before 1720 Swedish ships paid a lighthouse due and everyone else paid
by cargo, and Baltic cargo is one-directional, heavy westbound in timber, grain
and bar iron and light eastbound (Dutch-flag medians in the exemption window are
4.0 eastbound against 48.0 westbound). A class difference that is itself
directional is precisely the circulation this framework measures. After 1720
both classes pay by cargo, the class difference stops being directional, and the
measured circulation drops to what any two differently composed fleets produce.

Theorem 6(4) is a structural check here rather than a finding: `|S−S'| ≤ −(S+S')`
held on every cell of four separate runs, zero violations.

## The treaty says the same thing in its own words

Article 9 of the Peace of Frederiksborg, 3 June 1720, in Schou's edition of the
ordinances (Copenhagen 1822, part 2, pp. 254–255), states that thereafter
**there shall be no difference between the nations** in the Sound and the two
Belts, that Sweden shall pay **on the same footing as the English and the Dutch**,
and adds a most-favoured-nation clause covering any nation more favourably
treated later.

Three things follow, and the third is the useful one.

The first clause is the registered quantity's zero, written by the parties. The
second names the reference class, and the reference class the treaty names ,
English and Dutch, **is the control class this station was already using**, so
the control was not a free choice.

The third is structural. A most-favoured-nation clause pins Sweden to the
English and Dutch rate, so any later change to the tariff is common to both
classes by construction, which means it enters the denominator and not the
numerator. A nineteenth-century source claims the tariff then in force was
introduced in 1745, inside the post window, and that worry was first held off
empirically by a decade-by-decade line with no step at 1745. The treaty makes
the empirical check unnecessary: **a rule read in advance beats a check run
afterwards, because the check says no step was seen this once and the rule says
there cannot be one.**

The tariff itself did not change either. Gøbel (2010) records that the tariffs
published in 1641 for English and 1645 for Dutch cargoes, whose principles came
to apply to other nations as well, remained in force until 1842.

**What may be said is that the treaty removed this difference and that the
station's registered quantity fell, at that date, onto the floor set by cargo
composition. What may not be said is that the station proved the rates equal:
legal equality does not entail measured equality**, and the residual has a
measured source.

## Arm E: pure position loops

Counting the independent directions first (`b₁ = E − V + c` on the doubled
graph) showed the post-1720 route sets are forests, so every obstruction there
is a square and "one route, one independent reading" is exact rather than
assumed. The exemption-window route set is not a forest: it carries three cycles
in the position graph, so the doubled graph has 19 independent directions while
this station had claimed 16. **Reporting everything means reporting those three.**

Those loops answer to a different opponent. The class squares test Theorem 6(4);
a pure position loop tests whether the toll is the gradient of a scalar on
positions, which would force every closed loop to zero exactly.

With `ŵ` on a route equal to half the westbound minus eastbound charge, and
taking **all** four-leg loops rather than a spanning-tree basis:

| group | routes | ports | `b₁(G)` | quads | ratio median | scale `Σ\|ŵ\|` | floor | multiple |
|---|---|---|---|---|---|---|---|---|
| exemption, non-Swedish | 91 | 66 | 26 | 110 | **0.1265** | 74.9 Daler | 0.0491 | **2.6×** |
| post, non-Swedish | 211 | 111 | 101 | 1,147 | **0.2036** | 81.2 Daler | 0.0311 | **6.5×** |
| post, Swedish | 48 | 38 | 11 | 26 | **0.3924** | 12.2 Daler | 0.1084 | **3.6×** |

Three things travel with that table. The family of four-leg loops is redundant,
so 1,147 quads are 1,147 ways of writing 101 independent readings and the median
describes an object rather than summarising 1,147 tests. The ratio and the scale
must be reported together, because a ratio reads full scale when its denominator
approaches zero and that is a degenerate reading rather than a strong one. And
the missing fourth row is the same mechanism a third time: exempt ships have no
cargo charge, so that group is empty by construction.

In words: `ŵ` on a route is half the difference between what a westbound and an
eastbound passage paid. If that were a difference of port-level potentials, it
would cancel exactly around any loop. **About four fifths of it does. The
remaining thirteen to twenty percent does not, and it sits at 2.6 to 6.5 times
the measured floor**, so the remainder is visible. Economically, the west-minus-east charge on a route is mostly "how heavy this Baltic port's exports are" plus
"how heavy this western port's imports are", and a sixth of it is the route's
own and does not decompose that way.

**This is a framework-only quantity, and it is reported as one.** Nobody claims
the Sound Toll is a scalar potential on positions. The economic historians treat
it as a tariff on goods, and a tariff makes no prediction about loop sums, so a
non-zero loop sum refutes nothing. It is reported because the count said three
directions were unclaimed, and silence about them would not be reporting
everything. With them the station now reports 19 of 19.

**The stability criterion here is unresolved at this resolution, and the reason
is measured.** The registered expectation was that the non-Swedish class's loop
sums should not move across 1720, since nothing changed for that class. On the
same set of loops the cross-window difference is 0.018. Rebuilding by decade on
that same set shows the pre-1720 decades ranging over 0.075 to 0.287, a spread of
0.212, which is twelve times the difference to be read; the 1710s read 0.129 and
the 1720s 0.164, both inside the earlier band. **There is no step on the line, and
this instrument cannot separate a change of that size.** The criterion as written
also compared two windows seventy years apart while attributing the change to one
year, which is a scope mismatch between the criterion and its object; deciding it
needs a contrast that does not span seventy years.

**The first version of this arm is withdrawn and its numbers are kept.** It used
a fundamental cycle basis from a spanning tree, which was built by iterating a
set, so it was not reproducible run to run; and, deeper, the statistic was a
function of the basis, and the basis is arbitrary. Fixing the iteration order
would have made it reproducible without making it mean anything. The two versions
disagree on the sign of the cross-window change, which is what a basis-dependent
direction looks like, and they agree on everything else: the remainder is 0.1 to
0.4, above the floor, and inseparable across 1720.

| | first version (cycle basis) | current (all four-leg loops) |
|---|---|---|
| exemption, non-Swedish | 0.1547 | **0.1265** |
| post, non-Swedish | 0.1200 | **0.2036** |
| post, Swedish | 0.2279 | **0.3924** |
| matched set, exemption / post | 0.1962 / 0.1324 | **0.1088 / 0.1268** |

## Arm F: normalising by tonnage is not available on this carrier

The post-1720 floor is cargo composition, and the largest single component of
composition is how big the ship was, so dividing the charge by tonnage would turn
a qualitative statement into a measured one. The `tonnage` field is free text
with ship names and burden mixed together, and a regular expression recovers a
burden for 10.4 percent of exemption-window voyages and 14.4 percent afterwards.
What it recovers is worth having on its own: **Swedish-flag ships are less than
half the size of the others in both windows** (post-1720 medians 10.0 against
24.0 læster; exemption 8.0 against 21.0), which names the scale gap in arm E and
the composition floor in arm D. The median toll per læst is 0.0526 Daler over
48,013 voyages, quartiles 0.0221 and 0.1667.

Measuring the worst cell before computing anything ends the arm in about forty
seconds. **Zero routes have 40 passages in all four cells, for the treated pair in
either window; the placebo has zero routes at every threshold down to five.**

The reason is stronger than thinness. Whether a burden was recorded at all is
collinear with the flag:

| class | voyages in window | burden recoverable |
|---|---|---|
| Dutch | 180,250 | **0.027%** |
| English | 85,377 | **0.091%** |
| Swedish | 60,512 | 20.5% |
| German | 49,237 | 8.4% |
| Danish | 41,122 | 63.4% |
| other | 39,196 | 0.5% |
| Norwegian | 27,047 | **77.9%** |

Highest class to lowest is a factor of 2,865, and by home port the top five at
n ≥ 800 are all Norwegian or Danish (Tjømø 94.9, Køge 94.6, Flekkefjord 93.5,
Nedenæs 92.5, Frederikshald 90.9) while the bottom five are all zero (Joure,
Middelburg, Bristol, Terhorne, Margate). It is not a period effect: the
decade-by-decade range is 0.202 and the between-class range is 0.778, and no
class's own change across the two windows (at most 0.269) reaches the
between-class spread. **Conditioning on a recorded burden is conditioning on
being Scandinavian**, which is instrument coverage collinear with the treatment
variable.

There is a sharper half. The Swedish class's own recording rate steps at the
treatment date: 0 percent in the 1690s and 1 in the 1700s against 34 in the
1720s, while the Danish, Norwegian and German classes are flat across 1720. So
the conditioning variable jumps by thirty points for the treated class in the
year the treatment happens, and the double difference is contaminated between
classes and between windows at once.

**This is structural rather than underpowered**, and the distinction matters for
whoever comes next: the file is the complete run of 2,152,670 passages, so what
is missing is not rows but a field that was never filled for some classes. Every
pair involving Sweden reads zero routes at n ≥ 40. The one well-populated pair,
Danish against Norwegian, has 7 routes after 1720 and 4 in the exemption window,
and it does not bear on the treaty question, since both classes sit on the same
side of 1645 and of 1720. It is registered as an arm that could be opened and
asks a different question.

The field inventory was checked before the arm was declared unavailable:
`doorvaarten.csv` carries 49 columns and only `tonnage` holds a burden; the one
other candidate is empty throughout, and the parcel file has no burden column.

## Evasion, losses, and the direction each one pushes

An objection worth answering with signs rather than assurances: ships sank, ships
were taken, and cargo was smuggled. Which of those can move the registered
quantity, and in which direction?

The mechanism turns out not to be the obvious one. Olsen's 1942 study of Swedish
evasion in the Sound during the exemption years describes a trade in **flag and
papers** rather than under-declaration: municipal authorities issued passes
without oath, to the point of a wholly fictitious ship; foreign goods were
declared Swedish on a note from a Swedish citizen against a fee of a half to one
percent of value; and ship registry was transferred nominally for a sixteenth or
a twenty-fourth of the vessel's value. Contemporary estimates of the scale
disagree wildly and are recorded separately rather than averaged: one 1695
estimate of the annual loss which Olsen himself calls plainly exaggerated,
a 1696 claim of about 2,000 exempt Swedish ships a year against an actual Swedish
tonnage averaging 675 in that decade, and toll revenue falling from an annual
average of 126,629 rigsdaler in 1680–88 to 83,889 in 1689–97. Olsen's own summing
up is that it is of course impossible to compute how much the abuse
amounted to.

The double difference removes most of what any of this could do. A uniform
under-declaration rate, a port-level one, a class-level level shift and a
direction-level level shift all cancel from `S − S'`; only the class-by-direction
interaction survives, and its sign is known in each case.

| channel | what it does | sign on the exemption-window reading |
|---|---|---|
| re-flagging | moves voyages, and the valuable ones, out of the non-exempt class | shrinks `E` and `W` together, and the ratio is decreasing in a common shrink ⇒ **down** |
| under-declaration | only the non-exempt class has a motive, and the worthwhile leg is the expensive westbound one | shrinks `W`, so `\|E−W\|` shrinks ⇒ **down** |
| routing around the Belts | same motive, same leg | **down** |
| sinking, piracy | cargo lost rather than price changed, and risk compensation is already ruled not to be a closed quantity (`docs/b1_theorem.md` §9) | not in the numerator; reaches it only through class-by-direction composition, which is what the placebo measures |

**All three channels that can reach the numerator push it down, so 0.2552 is a
lower bound.**

One further consequence runs the other way from what the objection intends.
Re-flagging means that "Swedish" in this ledger is "treated as Swedish by the
toll office", and that administrative classification **is the treatment variable**.
Arm C reads the classification that actually had causal force, not the
shipowner's nationality. Forged papers do not weaken that reading; they are
evidence the classification was worth something.

## Where this station sits against the alternatives

The class readings are a quantity nobody else has computed on this carrier, and
the position loops likewise. That is the cell this station mostly occupies: the
framework has a number here and the alternatives have no reason to produce one.
The arm that comes closest to a contested prediction is arm C, where reading by
sovereignty rather than by modern nationality is a substantive claim about the
carrier that a modern-nationality coding gets wrong at exactly two ports, and
both of those ports were Swedish at the time.

Nothing here refutes a rival account of the Sound Toll, and no rival account of
the Sound Toll makes a prediction about these quantities. That is stated as a
classification, not as a shortfall.

## Screened out on paper, before any data was read

Three things were settled by reading rather than measuring, and each saved a run.
The most-favoured-nation clause makes any later tariff change common to both
classes, so the 1745 question needs no decade line. The published fee schedule
identifies the fixed component as the lighthouse due at 2 skilling per læst for
laden ships, with the ship tax denominated in nobles and therefore in a currency
column this station does not read at all, so a 448-kroner monograph that had been
booked as necessary is not needed. And the register's own field list answered, in
43 columns this station had never opened, a question that had been hung on
offline literature. The last of those, the name of the fixed component, was then
settled outright by a transcribed ledger page that prints it on its own line, an
archive's public teaching material rather than a specialist monograph.

## Limits worth stating with the numbers

The exemption-window reading rests on 16 route cells and the post-1720 reading on
8, so neither supports inference across cells. Only one route is thick enough in
all four cells to compare the treated pair against the placebo on the same route,
and two at the wider threshold; both point the same way and neither is strong.
Directions are compared as medians over each leg rather than as the two legs of
one voyage, so every reading here is route-level. One route in the post window
sits on a class boundary the mechanical rule gets wrong, since Stralsund remained
Swedish after 1720 while the modern-country rule codes it non-Swedish, and that
error pushes that route toward zero rather than away from it. And the exemption
window's exact break is not readable, for two independent reasons that fall on
the same years: the recording practice spread gradually from about 1650, and a
general archive dip in the late 1650s reaches the control ports as well.

One defect in the register itself, found when a window was widened: a single
amount is written as a fraction with denominator zero. It is the only one in the
whole corpus and the parser now treats it as missing.


## Two questions this station leaves open, with their shape

Neither bears on any reading here. Both are recorded with what has been ruled out
and what would move them, because an open question stated that way is usable and
one stated as an absence is not.

**Why 8 per cent of provincial voyages were assessed in the settled decade.** The
assessed share decomposes into four periods and two of them have causes: the
early figure of 21.2 per cent belongs to the same administrative spread the entry
side shows, and the wartime figures of 15 to 17 belong to the war. The 8.1 per
cent over the 1690s, on 963 voyages, does not. Two candidates are ruled out
rather than untested: the endpoint condition leaves a provincial voyage with no
Swedish endpoint exempt 82 per cent of the time, and the conquest explanation
fails on its own timing, since Riga is at 38 per cent nine years before it fell
while Nyen and Narva show no step at their dates. The leading remaining candidate
is the other half of the stated condition, whether the cargo itself was Swedish,
and **that is unreadable on this carrier by construction**: an unassessed voyage
names a commodity 2.0 per cent of the time and carries a quantity never. Moving
it needs a different document, a toll file that records why a voyage was
exempted, or an archival study of this window. It is not something this carrier
can be made to answer.

**Which skilling the published rate is quoted in.** The measured per-læst figure
and the published one differ by exactly the factor between Lübeck and Danish
skilling, which this station measured independently for its conversion base, and
in Danish the two agree to 1 per cent on the largest ships. Settling it takes one
sentence of the schedule rather than any data. The name of the charge does not
depend on it: a transcribed ledger page prints the charge on its own line, and
the fee is a per-ship, class-common, direction-symmetric amount that cancels from
the index part and was measured directly on the fifteen routes the reading uses.
