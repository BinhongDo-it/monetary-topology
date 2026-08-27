# E1. Seats, candidates, and nine ways this source will bite you

**What this is.** A count of first-degree places allocated to each province by
each university, against the number of candidates in that province, taken from
a public compilation of Chinese provincial enrolment plans and score-to-rank
tables. **It is a measurement and it draws no conclusion from itself.**

**What it is not.** It is not a reading of this repository's framework. The
framework is about whether the terms of exchange in a system compose, and it
says nothing about how a quota should be allocated or to whom. E1 sits here
because it shares C3's carrier, its parser and its measurement discipline, and
it is kept apart from C3 so that neither is read as the other.

**Why the long first half.** The source is 1.4 GB across 861 files and it is
messy in ways that do not announce themselves. **Every defect below produced a
number that looked like a finding**, and none of them was caught by a
criterion; they were caught by printing an object or by a bound that a real
number cannot cross. Anyone reading this compilation with any method will meet
the same nine, so they are written first and written as a trap list rather than
as caveats on our own arithmetic.

Source: `choucisan/GaokaoCompass`, data at
`huggingface.co/datasets/choucsan/Gaokao-Compass-11M`, MIT, 861 CSVs,
11,327,563 rows, 2017 to 2025.

---

## Part one: nine traps in this source

### 1. A file that exists and carries nothing

`2022/shaanxi/enrollment-plan.csv` is 2 MB and holds 31,375 rows. **Every one
of them has an empty `batch` and an empty `plan_count`.** Counting provinces by
whether the file is present gives 30 for 2022; counting by whether any row
carries a numeric seat count gives 27.

**Detection.** Count usable rows, never files. A presence check on a directory
listing is not a coverage measurement.

### 2. Field fill is province-level all-or-nothing, with exactly one exception

Over 112 province-year cells, the share of undergraduate rows carrying a
numeric `plan_count` is **36 cells between 0.0 and 0.1, 75 cells between 0.9
and 1.0, and one cell in between**: Beijing 2025 at 0.11.

That one cell is the whole problem. A gate written as "the province is usable
if it has at least a hundred rows with a seat count" passes it, because the
gate stops counting once it reaches a hundred. Beijing 2025 then enters the
comparison holding 39 institutions, none of them a 985, **and reads a 985 seat
rate of exactly zero for the province with the highest rate in every other
year**.

**Detection.** Gate on the fill rate, not on a count of usable rows. The
distribution is bimodal, so any cut between 0.15 and 0.9 selects the same set,
and printing the histogram is what shows that.

### 3. Columns that are present and empty

`school_province` is filled in **none** of the 2017 to 2021 rows of
`school-admission.csv`, a fifth to a quarter of 2022 to 2024, and three
quarters of 2025. `control_score` is near-empty throughout. Both are listed as
fields in the source's own description.

**Detection.** Measure the fill rate of every field a plan depends on before
building the plan around it.

**What works instead.** `university_code` is a five-digit national code on 98
per cent of `school-admission.csv` rows, and those codes are assigned in blocks
by province. The administering province is recoverable from a field that is
actually there.

### 4. The code blocks are frozen at the administrative divisions of their year

`重庆大学` is 10611 and sits inside Sichuan's block, because Chongqing was part
of Sichuan until 1997 and kept its number. `海南大学` is 10589 and sits inside
Guangdong's, because Hainan was part of Guangdong until 1988. Running the other
way, `河北工业大学` stands in Tianjin and is administered by Hebei, and it is
Hebei's candidates who receive its local preference.

**So the code gives the administrator of the day it was issued and the name
gives the present one**, and which one a question wants is a question about the
question. For an allocation, the present one.

**Detection.** Hold out half the anchors. Fitting the block edges on the
even-numbered codes and scoring the odd ones agrees on 85.9 per cent of the
assigned, and **every disagreement is a named institution rather than a
statistic**: reading the list is what shows that the failures are divisional
history and not noise.

### 5. One bad pair breaks a whole block

This compilation carries `10035` as `桂林生命与健康职业技术学院`, a Guangxi
vocational college sitting in the middle of Beijing's range, and `18001` as
`天津大学`, whose code is 10056.

Under a rule that assigns a code the province of its nearest anchor on each
side when the two agree, **those two entries alone leave `中国传媒大学`,
`中央财经大学`, `对外经济贸易大学`, `中央民族大学`, `中国政法大学` and
`南开大学` with no province at all.**

**Detection and fix.** A majority of the nearest several anchors cannot be
flipped by one of them. Restrict the block rule to the range where blocks mean
anything: below about 12000 the codes run by division, above it they run by
date of foundation and a neighbour says nothing.

### 6. A join key that is not unique, and an assignment that keeps the last one

**324 institution names are carried by more than one code, and 49 of those
carry inconsistent 985 and 211 flags.** The extra codes are the same
university's cooperative, directed and targeted-programme channels, admitting
under its name with the flag off: `上海交通大学` appears on eight codes,
`北京航空航天大学` on two.

Inverting the code-keyed table onto names by assignment keeps whichever code
came last. `北京航空航天大学` reads as unflagged that way, **and Beijing's 985
seats per ten thousand candidates fall from 690.9 to 342.5** with nothing
raising and every other number unchanged.

**Detection.** Before inverting a map onto a different key, count how often the
new key repeats and how often the repeats disagree. Take the strongest value
rather than the last.

**And a limit this creates.** The narrower reading, counting only the flagged
code, is not computable from the enrolment plans at all: they carry no
institution code before 2022 and carry one on about a quarter of rows in it.
What is computable is the exposure, and **41.4 per cent of the elite seats
counted here sit on a name that is flagged on one code and not on another**.

### 7. The same table published twice under different category labels

Anhui's `score-range.csv` carries four values in `category`: an empty string,
the literal string `<NA>`, `文科` and `理科`. **The empty label's cumulative
counts equal `文科`'s exactly and `<NA>`'s equal `理科`'s.**

Summing the pool over category labels therefore counts Anhui twice, **937,746
against a true 468,873**, and halves its seat rate.

**Detection.** Compare the maximum cumulative count across labels for exact
equality. Prefer labelled categories where any exist; the unlabelled ones
repeat them.

### 8. No batch labels before 2022, and truncated tables after

**No province's `score-range.csv` carries a batch label in 2017 to 2021.** The
batch is what says how deep the table goes, and the depth is what makes one
province's pool the same object as another's, so **the pool cannot be
established at all in those five years**. That is structural: more retrieval
from this source does not fix it.

Where batches do appear, some tables stop at the undergraduate line rather than
running to the vocational one. Shanxi's pool is truncated that way, and it
shows: **0.94 undergraduate seats per candidate**, which is nearly one seat
each.

**Detection.** Require a 专科 batch in the table before comparing a pool
against another. Of 29 provinces with a score-to-rank table in 2022, twelve
have one.

### 9. One bound catches several of these at once

Undergraduate seats over pool has a meaning at both ends. **Above one, a
province seats more undergraduates than it has candidates.** Near zero, its
plan is empty. Over 68 province-year cells the ratio reads

    0.0001  0.0002  0.0007  0.0015  0.0086   then nothing until
    0.3495  ... 62 cells ...        0.9401   then nothing until
    1.1601

**The cuts at 0.1 and 1.0 sit inside those empty stretches**, so no other
choice inside them selects a different set, and the emptiness is what makes
them defensible rather than arbitrary. What the band catches without being
told: Zhejiang in all four years, whose university this source gives 1,355
seats nationally and none at home while an outside compilation of local-intake
shares puts it near half; Beijing 2025, which is trap 2; and Xinjiang 2025,
above the logical bound.

---

## Part two: what was measured

**Seats rather than filing lines, and there is a reason.** The first design
read the admission line and compared two campuses of one university inside one
province. A line is an equilibrium quantity and two channels move it opposite
ways: seats set aside for local candidates push it down, and local candidates
preferring a campus in their own city push it up. **The measurement returned
the net, at a magnitude that a later check showed was inflated by dividing
through the host province's table length**, and it rests on one brand of three
once that is corrected. A seat count is the allocation itself, fixed before
anybody applies.

Also, and it is the reason a one-year reading cannot be pushed further: 2015 is
the first year Beijing candidates filed after their scores were published and
the first year its top batch used a large parallel structure, while the
comparison provinces had both for years. Both changes let a candidate aim
exactly for the first time.

### 985 seats per ten thousand candidates, 2022

Eleven provinces whose pools pass traps 8 and 9.

| province | pool | undergraduate seats per candidate | 985 per 10k | 211 per 10k |
|---|---|---|---|---|
| 北京 | 44,958 | 0.76 | 690.9 | 1185.1 |
| 天津 | 56,764 | 0.72 | 569.7 | 760.7 |
| 重庆 | 182,326 | 0.57 | 320.1 | 490.4 |
| 辽宁 | 185,433 | 0.60 | 285.1 | 471.1 |
| 宁夏 | 65,062 | 0.48 | 234.1 | 777.6 |
| 江苏 | 297,761 | 0.67 | 226.6 | 549.9 |
| 广东 | 671,412 | 0.42 | 174.3 | 202.5 |
| 湖南 | 429,734 | 0.45 | 165.8 | 285.2 |
| 江西 | 465,722 | 0.35 | 106.5 | 237.4 |
| 贵州 | 341,181 | 0.43 | 99.7 | 311.6 |
| 河南 | 842,585 | 0.38 | 96.6 | 202.7 |

**The pool is the candidates with a published score segment, and it is not the
registration count** that circulating comparisons use. The gap between
registering and sitting the common papers differs most between exactly the
provinces being compared, so the two denominators are not interchangeable and
nothing here should be read against a figure computed the other way.

### Two other quantities, which have to be read together

The share of its seats that a 985 or 211 unit sends to the province that
administers it, 2022, over the provinces the band admits: 北京 0.1129,
天津 0.1383, 湖南 0.1590, 辽宁 0.2543, 重庆 0.3397, 江苏 0.3458, 广东 0.5544.

The count of 985 and 211 admitting units by administering province: 北京 25,
江苏 11, 上海 9, 湖北 8, 陕西 7, 黑龙江 7, and one each for 河南, 河北, 山西,
江西, 云南, 广西, 内蒙古, 贵州, 海南, 宁夏, 青海, 西藏.

**Either number read alone reads backwards.** The low home share alone says the
host takes no advantage. The seat rate alone says the host's universities
favour it. The units are admitting units and not universities, which is why 44
of them carry a 985 flag against 39 universities: campuses and channels are
counted separately, and that is the right unit for an allocation.

### What replicates and what does not

The comparable sets differ every year, because coverage does. The pair at the
two ends of the 2022 table exists in 2022 alone: 2023 and 2024 hold Beijing and
not Henan, and 2025 holds Henan and not Beijing. **What replicates is the
ordering**: over the three years in which it can be compared at all, Beijing
places first of eleven, first of seven and first of eight.

The top of each year's set over its bottom reads 7.15, 5.84, 4.87 and 2.85.
**That is not a trend**, because it is a different set of provinces each year.
A trend needs a fixed set and this source does not give one.

---

## Reproducing it

    python data/e1_home_province.py                # code -> administering province
    python data/e1_seats.py --all                  # one year per call, resumable
    python experiments/e1_seat_rates.py            # -> results/e1_seat_rates.json

The record is byte-identical across runs. Every criterion, including the arm
that returned the opposite sign to its own hypothesis and the arm whose
magnitudes were then marked down, is in `RESULTS.md`.
