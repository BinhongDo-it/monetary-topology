# C3. Whether a university's admission difficulty is a number

**Carrier.** The first-tier parallel-choice filing lines (投档线) published by
each Chinese province after the 2015 national college entrance examination. A
province publishes, for every university admitting in its first tier, the score
of the last applicant it filed to that university. Fifteen provinces are here
in the arts track and fifteen in the science track, fourteen in both, 5,771
institution entries in all. The smallest cell holds 75 entries and the largest
304.

**Script** `experiments/c3_admission_reversals.py`.
**Record** `results/c3_admission_reversals.json`.
**Panel** `data/gaokao_provincial.csv`, built by
`data/parse_gaokao_provincial.py` from the provincial tables listed in
`data/SOURCES.md`.

---

## 1. What is being tested

Nobody publishes a national difficulty score for universities. The apparatus
around the examination nonetheless speaks as though one existed, and so does
everyone using it: a university is called harder than another, tiers are named,
and the ordering is treated as a property of the university.

That way of speaking has a content. If a scalar `v` over universities existed,
and each province's filing line were a reading of it, then for any two
universities `A` and `B` every province would place them the same way round.
`v` need not be the score. It need not be in the same units anywhere. It need
not be observable. The commitment is only this: **each province's order is the
restriction of one common order.** A single province pair that reverses one
institution pair refutes it.

This is the same object as a price field, with the cardinal structure removed.
A price field asserts that the pairwise exchange ratios `R(a,b)` factor as
`v(a)/v(b)`. Here the assertion is weaker, that the pairwise orderings factor
through one ranking, and the obstruction is correspondingly cheaper to
demonstrate: an ordinal loop that does not close.

---

## 2. The objection this station was built to answer, and how it is answered

The first thing said against carrying non-integrability out of prices and into
an examination is that a point is not worth the same in two provinces. The
papers differ, the cohorts differ, the curricula differ, the scales differ:
Jiangsu ran to 480 in 2015 and Shanghai to 600. So of course there is no stable
exchange rate between a Jiangsu point and a Henan point, and a finding of
non-integrability would be trivial.

**That objection is answered by construction rather than by argument.** Nothing
in this station compares a score in one province with a score in another. No
exchange rate between provincial scales is ever formed, needed, or estimated.
Only the order inside a province is used, and the comparison is between two
provinces' orders, not between their scores.

The objection, stated precisely, is that province `p`'s scores and province
`q`'s scores are related by an unknown strictly increasing map. **Every such
map leaves this station's reading exactly where it was**, and criterion C3-2
checks that on the panel rather than asserting it: the set of reversing
(institution pair, province pair) tuples is rebuilt under five recodings
applied province by province, including one that gives each province a
different map and one that is piecewise linear with irregular knots, and the
five sets are identical to the original as objects, not merely equal in count.

**The second answer, and why it concedes the point.** A university offers
different programmes and different numbers of seats in different provinces, so
its line is not a property of the university alone. That is the same sentence
as the finding. It says the quantity is indexed by institution and province
jointly and does not factor into a per-institution number. What this station
measures is how far from factoring it is.

---

## 3. Criteria

| | criterion | detail |
|---|---|---|
| PASS | C3-0 panel | 2015 first-tier parallel-choice filing lines: 15 provinces in arts and 15 in science, 14 with both, 5,771 institution entries. Smallest cell 75, largest 304. 0 normalised names dropped as ambiguous inside a cell |
| PASS | C3-1 whether one order fits every province | arts: 105 province pairs, 681,773 determined comparisons, 77,933 reverse, 22,123 tie; **105 of 105 province pairs contain at least one reversal**. science: 105 province pairs, 1,395,601 determined, 160,280 reverse, 42,506 tie; 105 of 105 |
| PASS | C3-2 invariance under a per-province recoding | the reversing tuple set is identical under all five recodings, in both tracks |
| PASS | C3-3 the pairs whose order is not a property of the pair | arts: 7,883 institution pairs reverse in at least one province pair, of 28,935 compared. science: 13,293 of 45,294 |
| PASS | C3-4 replication on the other track | 27,708 institution pairs compared in both tracks; 4,843 reverse in both, 6,864 in exactly one, 16,001 in neither |
| PASS | C3-5 whether counting the provinces resolves it | arts: 17,351 majority edges, **16,341 of them lie on a three-cycle**. science: 28,879 edges, 28,256 on a cycle |
| PASS | C3-6 whether the reversal keeps its direction in the other track | 521,134 comparisons determined in both tracks; 59,672 reverse in arts, 20,213 of those also reverse in science, and **18,240 of those keep the same province on top, 0.9024**. Agreeing comparisons keep their direction 0.9611 of the time |
| PASS | C3-7 the same numbers from a publisher with no common upstream | Tsinghua is in the panel and publishes its own filing lines by province and year. 29 cells comparable, **25 agree to the digit**; the 4 that differ are named |
| PASS | C3-8 how far apart in rank the reversing pairs sit | weaker of the two within-province rank separations. arts reversing deciles 1, 2, 4, 6, 8, 10, 13, 16, 22, 32, max 155 against agreeing 1, 8, 16, 24, 32, 41, 52, 65, 80, 102, max 191; science reversing 1, 3, 5, 7, 9, 12, 16, 20, 27, 39, max 155 against agreeing 1, 11, 21, 32, 43, 56, 70, 88, 109, 140, max 275 |

Four states, not two. `agree` and `reverse` are the determined ones. A `tie` is
a pair one province cannot be asked about, having filed both schools at the
same line. `absent` is a pair not published by both. The third and fourth
states are counted separately and printed, so that a pair which cannot answer
is never read as a pair that answered no.

---

## 4. C3-6 is the criterion that carries the finding

C3-1 alone is compatible with a defence: a national scalar exists, each
province reads it with error, and a reversal is a pair whose true gap was small
enough for the error to flip it. Under that defence the reversals are noise and
mean nothing about whether `v` exists.

**The defence makes a prediction it cannot escape.** The arts and science
tracks are two disjoint applicant pools. They sit different papers, in the same
provinces, in the same summer, under the same quota policy and the same
admission machinery. If a reversal is cohort error flipping a small gap, then
the two tracks are two draws of the same coin, and which province ends up on
top is decided afresh each time. The direction match would sit near one half.

It is **0.9024**, against a calibration of 0.9611 for comparisons that agree in
both tracks. The reversal is a property of the province pair. It is not a
property of the cohort.

The remaining escape is that one province is simply noisier than the other and
is therefore the flipped one both times. That would show as a degenerate lean:
for a given province pair, nearly every reversal would put the same province on
top. Over the 91 province pairs measured in both tracks the lean runs from
0.3208 to 0.7624, with the bulk near one half. **Which province is on top
depends on which two universities are being compared.**

---

## 4b. C3-8, which cuts both ways and is reported that way

**Reversals do concentrate among schools that sit close together**, and that is
the first thing the separations say. The median reversing comparison in arts
has the two schools 8 places apart in the province that separates them less,
against 41 for a comparison the two provinces agree on. A national scalar read
with error predicts exactly that, since a small true gap is what noise can
flip. Reporting the deciles without reporting that would be reporting half of
them.

**What the same table also says is that the tail is not small and not close.**
The separation printed is the *weaker* of the two provinces' rank distances, so
a value of 32 means both provinces put the two schools at least 32 places
apart. The ninth decile of the arts reversing comparisons is 32 and of the
science ones 39, which is **7,793 arts comparisons and 16,028 science
comparisons in which both provinces separate the two schools decisively and
separate them opposite ways**. The largest is 155 in both tracks.

The widest one, printed rather than summarised:

| | rank | score |
|---|---|---|
| Jiangxi, `中央财经大学` | 10 of 189 | 585 |
| Jiangxi, `对外经济贸易大学` | 173 of 189 | 528 |
| Hunan, `中央财经大学` | 163 of 182 | 544 |
| Hunan, `对外经济贸易大学` | 8 of 182 | 614 |

Jiangxi separates them by 57 points and Hunan by 70, in opposite directions.
**Neither province is undecided about this pair**, and there is no error term
small enough to be doing this.

The widest twenty are dominated by finance and trade schools, `中央财经大学`,
`对外经济贸易大学`, `中南财经政法大学`, `暨南大学`, against each other and
against comprehensive universities. That is a substantive pattern rather than
an artefact: where a province's applicants place a finance school relative to a
comprehensive one is a regional preference, and the value being sought is
supposed to belong to the school.

---

## 4c. C3-7, an independent publisher of the same numbers

Tsinghua is in the panel, and it also keeps its own archive of what it filed at,
by province and by year, on its admissions site. That is the same quantity from
a source with no common upstream: a university's own record against the tables
the provincial authorities issued in July 2015 as the contemporaneous press
carried them.

**Twenty-nine cells are comparable and twenty-five agree to the digit.** The
four that differ are named rather than absorbed:

| province | track | provincial table | own publication | gap |
|---|---|---|---|---|
| Jiangxi | arts | 623 | 622 | −1 |
| Jiangxi | science | 686 | 685 | −1 |
| Heilongjiang | science | 681 | 682 | +1 |
| Guangdong | science | 668 | 687 | **+19** |

The three one-point differences run in inconsistent directions and are a
tie-break or a definitional edge. The nineteen-point one is Guangdong, and it
has a cause: Guangdong's table is `第一志愿组`, the first of two choice groups
inside the first tier rather than the whole tier.

---

## 5. One pair, printed in full

`东北财经大学` against `中国海洋大学`, filing line, 2015, both tracks:

| province | arts | science | | province | arts | science |
|---|---|---|---|---|---|---|
| 上海 | 441 / 436 | 437 / 416 | | 山东 | 610 / 618 | 634 / 637 |
| 北京 | 613 / 612 | 618 / 609 | | 江苏 | 344 / 357 | 355 / 365 |
| 山西 | 555 / 554 | 577 / 571 | | 浙江 | 658 / 665 | 645 / 648 |
| 江西 | 566 / 565 | 599 / 593 | | 福建 | 591 / 604 | 603 / 610 |
| 湖南 | 591 / 584 | 604 / 593 | | 河南 | 558 / 565 | — |
| 贵州 | 604 / 598 | 567 / 548 | | 广东 | — | 595 / 596 |
| 重庆 | 627 / 621 | 632 / 593 | | 广西 | 577 / 579 | 551 / 549 |
| 黑龙江 | 584 / 571 | 616 / 596 | | 陕西 | 561 / 568 | 574 / 571 |

Left block: `东北财经大学` above in both tracks. Right block: `中国海洋大学`
above in both tracks, except that Guangxi and Shaanxi split between the tracks.
The margins are not rounding: Heilongjiang science is 20 points one way and
Jiangsu arts is 13 the other on a 480-point scale.

**Twelve provinces order these two universities in a fixed way that the change
of cohort does not disturb, and they do not order them the same way as each
other.** There is no number `v(东北财经大学)` and `v(中国海洋大学)` that both
blocks are reading.

---

## 6. C3-5, and what its counts do and do not say

A reversal says two provinces disagree. A three-cycle in the majority
tournament says the disagreement does not resolve by counting provinces either:
no ranking agrees with all the pairwise majorities. That is the ordinal form of
a loop product that fails to close, and it is the statement that survives the
answer "just take the average of the provinces".

**The raw three-cycle counts, 63,905 in arts and 156,937 in science, are
reported and are not read as independent findings.** A tournament that is
transitive except for a few upsets produces a cycle for every third vertex
sitting between the ends of each upset, so one contested edge can carry
hundreds. The countable object is the set of edges lying on any three-cycle:
16,341 of 17,351 in arts, 28,256 of 28,879 in science. That the share is near
one is itself the reading. The cyclicity is not a rim of upsets around a
transitive core.

The most cycle-bearing edges are close majorities, which is what a contested
edge looks like: `西南政法大学` over `上海对外经贸大学` at 28 provinces to 27,
`西安交通大学` over `中南财经政法大学` at 35 to 31, `郑州大学` over
`东北师范大学` at 36 to 30 with no ties.

---

## 7. Scope

**What is refuted.** A scalar over institutions whose restriction gives every
province's order.

**What is not touched.** A scalar over institution-and-programme pairs. If a
university offers a different programme mix in two provinces, the two lines
describe different bundles, and a difficulty scalar might exist one level down.
The panel carries institution-level filing lines and cannot separate that.
Note what the rescue costs: it indexes the quantity by the very thing whose
independence was the claim, and a scalar over institution-and-province is the
data written twice.

**Coverage.** Fifteen provinces of thirty-one, one year. The provinces present
are those whose 2015 first-tier tables are on the public record in a form that
carries an institution and a line; five more were located and hold no article
body. The finding is an existence claim, so coverage bounds its generality and
not its validity: one reversing pair settles it, and 105 of 105 province pairs
carry one.

**Guangdong is a sub-round and is marked.** Its table is `第一志愿组`, the
first of two choice groups inside the first tier. A school that filled in the
first group does not reappear in the second, so the table is the main filing for
most schools and a partial one for the tier. It is present in one track only and
is therefore **absent from the fourteen provinces C3-6 uses**, so the criterion
that carries the finding never touched it. On the science side that it does
enter, removing it leaves 91 province pairs of which **91 contain a reversal**,
against 105 of 105 with it.

**Round.** First-round parallel-choice filing only. Supplementary rounds
(征求志愿, 征集志愿) are excluded by name, and the exclusion is printed by the
parser rather than assumed: a supplementary round refills the seats the first
round left empty, so a school that filled in round one is absent from it and a
school that did not files at or near the tier control line. Jiangsu's two arts
pages disagree on 26 of the 43 schools they share, and the supplementary one
puts 15 of them at 342, which was the control line that year.

**Two provinces publish through two outlets.** Shandong's tables appear on both
Sina and eol; the two sources agree on all 80 entries they share, in both
tracks, and the larger is kept.

---

## 8. Where this sits against C1

C1 measured a declared conversion between physical quantities, where an
institution names a number and the number is multivalued around a loop. C3
removes the number. Nothing here is declared as a ratio, nothing is convertible,
and no unit is shared between any two of the fifteen measuring bodies. The claim
under test is only that fifteen independent orderings of the same objects have a
common refinement, and it fails on every one of the 105 pairs, in both cohorts,
with the direction of failure surviving the change of cohort.

**The two stations bound the same result from opposite sides.** C1 shows a
declared exchange rate that does not close. C3 shows that removing the exchange
rate, the units, and the cardinal structure entirely does not rescue the
underlying scalar, because the scalar was never what the institution had.
