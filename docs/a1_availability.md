# A1 availability check: the default cascade, and which of its six targets survive contact with their sources

**Not a pre\-registration. A check, run before deciding whether to open a stage**,
as this project requires before a stage is opened, and the fourth of its kind after
`b3_slice_availability.md`, `b5_orphan_availability.md` and
`b6_cuba_availability.md`. Each of the previous three changed the design of its
stage rather than its budget. This one changes the scoring rule.

Run 2026\-08\-13, before any line of `experiments/a1_*.py` exists.

**No headline quantity is computed here.** Provenance, denominators, retrieval
mechanics and the arms are settled; the estimator and its thresholds belong to
the pre\-registration.

Items that could not be verified from a page actually retrieved are marked
**unverified** in place rather than smoothed over.

* * *

## 1\. Why this stage needs a check more than the others did

The property that makes A1 attractive:

> **This is the only stage attached to real data and therefore the most citable.**

The same property is the exposure. A0, A2, A3, A5 and A6 register *shapes*\:
signs, orders, whether a channel closes. A1 registers **six levels**, and a level
binds to a vintage, a denominator, a threshold in days, and a population. Six
levels are six chances for the retrieved number to be a different quantity than
the model's output while still being a number of the same magnitude.

§5.3 also attaches a termination right to this stage: if A0 and A1 are both
substantively refuted, the A track stops and Volume One is rewritten. A stage
that can end a track is a stage whose targets should be checked before the code
rather than after.

## 2\. The six registered targets, and what each one turns out to be

| \# | Registered target | Plan's attribution | What the source actually publishes | Verdict |
| --- | --- | --- | --- | --- |
| 1 | Credit card 90\+ delinquency `13.12%` | NY Fed HHDC Q1 2026 | Exactly the `CC` column of HHDC Page 12, *percent of outstanding balance* 90\+ days delinquent, 2026Q1 | **In hand, reproducible** |
| 2 | Auto 90\+ serious delinquency `5.6%` | NY Fed CCP Q1 2026 | Exactly the `AUTO` column of the same Page 12 table. The CCP attribution is wrong (§3) | **In hand, reproducible, misattributed** |
| 3 | Subprime auto 60\+ `6.8-6.9%` | Fitch / S&P | Fitch's subprime auto **ABS pool** index, 6.90% (Jan 2026) and 6.80% (Feb 2026). No S&P 2026 value verified anywhere | **Not reproducible, and a different population** |
| 4 | Rent delinquency `11.09%` (May peak) | Hemlane | Vendor production database, 18,938 payment records over five months across 50 states, denominator never stated | **Not reproducible** |
| 5 | Late payment rate `13.5%` (Jan\-Feb peak) | RentRedi / Chandan | Vendor subscriber panel whose sample rule deletes non\-paying units (§6) | **Not reproducible, and biased against the tail** |
| 6 | Eviction filings `1.24 million` (12 months) | Eviction Lab | No such figure located. `1.23 million` filings in calendar 2025 across monitored sites covering about a third of US renter households | **Reproducible with the coverage restated, but it is a count** |

## 3\. Two of the six are one table, and its extraction is already proven in the sibling repository

**Repository boundary, stated first because it changes what "already have it"
means.** A/B track work lives in `monetary-topology`. The HHDC workbook and the
derived series live in `topology-fingerprints`, which is a **separate repository**
with its own CI, its own `RESULTS.md`, and its own retrieval rules. Nothing in
`monetary-topology` references it today, and A1 should not be the stage that
starts. So what this section establishes is that **the retrieval is solved and the
recipe is proven**, rather than that a file sits where A1 can read it. What A1
inherits is a known workbook, a known sheet, and a working extraction method; what
A1 still owes is its own fetcher in its own repository (§8 item 1).

In `topology-fingerprints`, `data/derived/hhdc_delinq90.csv`, produced by
`fingerprints/hhdc_extract.py` from `data/raw/fingerprints/hhdc_report.xlsx`,
last row:

```
2026-01-01, mortgage 1.0900, heloc 0.9500, auto 5.6000, cc 13.1200,
            student 10.3400, other 9.7600, all 3.3600
```

`13.12` and `5.60` are the plan's targets 1 and 2 to the digit. They are two
columns of a single sheet, HHDC **Page 12, "Percent of Balance 90\+ Days
Delinquent by Loan Type"**, and every sheet in that workbook is sourced "New York
Fed Consumer Credit Panel/Equifax". The plan lists target 2 as coming from "NY
Fed CCP", which reads as a second, independent source. It is not one: CCP
microdata access is "limited to Federal Reserve System researchers, and their
coauthors, due to contractual limitations with the data provider"
(`newyorkfed.org/microeconomics/faq`). The public artifact is the workbook.

**Stock and flow are both published, they differ by a factor near two, and the
plan's wording points at the wrong one.** From the 2026Q1 workbook, same quarter,
same product:

| 2026Q1 | Page 12, stock: % of *outstanding balance* 90\+ | Page 14, flow: balances *newly* 90\+, annualised |
| --- | --- | --- |
| Auto | **5\.60** | 2\.97 |
| Credit card | **13\.12** | 7\.10 |

The New York Fed's phrase "serious delinquency" attaches to the flow table
(Pages 14, 24\-28). The plan calls target 2 "auto loans 90+ days, seriously delinquent, 5.6 percent", which
takes the number from the stock table and the name from the flow table. Nothing
is wrong with the number. The pre\-registration has to declare which quantity the
model emits, and the target column then follows from that declaration rather than
the reverse. This is checklist item 2 with a factor of 1.9 attached to it.

**One retrieval guard, and it is the part worth porting.** Page 12 and Page 14 do
not share a column order (Page 14 runs auto, card, mortgage, HELOC, student,
other, all). `hhdc_extract.py` locates its sheet by a title substring and keys its
columns by header string rather than by position, and refuses a workbook that
yields fewer than eighty quarters. A1's own reader must do the same three things,
or it will silently return the auto series when asked for the mortgage series the
first time the New York Fed reorders a page.

## 4\. The stratification the shopping list assumed does not exist in public form

The registered source table gives:

> **NY Fed HHDC**，by product **and by income quantile / credit tier** | A1 calibration. **The stratification is the point: the evidence for the K shape is in the split, not in the total**

Full inventory of the workbook in hand (36 data sheets, from its own table of
contents, vintage May 2026 \= 2026Q1):

| Cut | Sheets | Measure |
| --- | --- | --- |
| Product × delinquency | Pages 11, 12, 13, 14 | Balance by status; stock 90\+; flow 30\+; flow 90\+ |
| Credit score | Pages 6\-9 | **Origination only.** Never crossed with delinquency |
| Age × product | Pages 24\-28 | Transition into 90\+ **flow only**, four\-quarter moving sum, from 2000Q1, bands 18\-29 / 30\-39 / 40\-49 / 50\-59 / 60\-69 / 70\+ |
| State | Pages 32\-40 | Stock and flow by state |
| **Income quartile** | **none** |  |

So the public NY Fed stratification of delinquency is **age, and only in the flow
measure**. Example values from Page 26 and Page 27, 2026Q1: auto 18\-29 `4.88`
against 60\-69 `1.65`; card 18\-29 `9.67` against 60\-69 `5.28`.

The Philadelphia Fed's Consumer Credit Explorer does cross delinquency with age,
credit score and neighbourhood income, on the same CCP/Equifax data. Its own
data\-sources page: "Because of data vendor restrictions, we are not able to
provide any series from the tool in spreadsheet format." No API. Its bands are
Nonprime `<660` / Prime `≥660` and its denominator is borrowers rather than
balances. Neither downloadable nor commensurate.

Two one\-off snapshots do carry a credit\-score stratification and are machine
readable:

- **FEDS Note, 2025\-11\-24**, accessible HTML table. Subprime `<620` / near prime
  `620-719` / prime `>719`, share of *balances* 30\+ days past due, CCP source.
  Subprime auto `15.63` (2024Q4), `15.78` (2025Q3).
- **Liberty Street Economics, 2025\-02**, chart data xlsx. Subprime `580-619` /
  midprime / prime / very prime auto transitions.

Both are single publications rather than maintained series. Under the project's engineering rule 9 they are usable as literature. They cannot be a measurement leg that gets
re\-run.

**What this does and does not cost A1.** The registered K\-shape criterion is a
contrast *across products* (mortgage below auto and card, with no
mortgage\-specific protection parameter). It runs entirely on Page 12 columns and
needs no stratification at all. What wanted the stratification is the *holding*
side: who owes which product. That side is already available and already in the
repository, from a different source: `calibration.py` records the DFA figures,
bottom 50% holding `51.8%` of consumer credit and `30.4%` of total liabilities
against `2.5%` of net worth. The K shape is therefore assembled from stratified
**holdings** (DFA) and unstratified **delinquency** (HHDC), and the
pre\-registration should say so rather than register a split that no public source
supplies.

## 5\. The subprime auto target is a paywalled index over a securitized population

- `6.90%` (January 2026) and `6.80%` (February 2026) are Fitch's subprime auto
  60\+ index, reported through trade press and Fitch's "North American Auto ABS
  Monitor 2H25" (2026\-03\-11). `fitchratings.com` could not be retrieved
  (**paywall status unverified**); no free machine\-readable file was found.
- **No S&P 2026 value was verified.** The joint attribution "Fitch / S&P" is not
  supported and should become Fitch alone.
- **Population.** The index covers loans inside rated ABS trusts, not subprime
  borrowers. Loans held on balance sheet and buy\-here\-pay\-here paper are outside
  it. Fitch itself attributes part of the level to composition shift as stronger
  vintages amortise away, so the series carries a non\-behavioural trend
  component: the denominator deteriorates by construction.
- **Magnitude is denominator\-specific, not a fact about the world.** For the same
  period the free CCP\-based reading for subprime auto is `15.78%` (30\+ days,
  share of balances, 2025Q3). A model tuned to `6.8` is tuned to a trust pool at a
  60\-day threshold; a model tuned to `15.78` is tuned to a population at a 30\-day
  threshold. They are 2.3 times apart and neither is wrong.
- Nearest free thing at the `6%` magnitude: Philadelphia Fed CFI, April 2026,
  60\+ days, loan counts, subprime defined at origination `<620`, hovering near
  `6%` through 2025Q3. PDF only, no data file.

**Verdict: not available as measurement in the form the plan registered.** The
two options put to the ruling were to drop the rung to a product\-level contrast
that Page 12 already supports, or to keep the subprime cut against a free source
with its own threshold and denominator.

**Ruled 2026\-08\-13: keep the subprime cut, take the CCP figure.** The target for
this rung becomes the FEDS Note series (`15.78%`, 2025Q3; subprime `<620`; 30\+
days; share of balances; New York Fed Consumer Credit Panel/Equifax), with the
threshold and the denominator written into the criterion rather than left
implicit. Fitch's index moves to literature under the project's engineering rule 9, cited with
the ABS\-pool qualifier attached, never fitted. Two consequences the
pre\-registration inherits:

- **This rung is scored at 30 days while rungs one and two are scored at 90.**
  That is a property of what exists rather than a choice, and it belongs in the
  criterion text instead of being smoothed over by calling all three
  "delinquency".
- **The FEDS Note is a single publication, not a maintained series.** Under
  the project's engineering rule 6 the accessible HTML table is snapshotted into
  `data/raw/fingerprints/` on first pull and treated as non\-regenerable; every
  re\-run reads the snapshot rather than the site. The Liberty Street 2025\-02
  chart\-data xlsx is pulled in the same way, as the second reading of the same
  stratification.

## 6\. Both rent numbers are vendor convenience samples, and one deletes the households A1 is about

**Hemlane `11.09%`** (May 2026, from a monthly series running 9.07 / 9.32 / 10.46
/ 11.09 for February through May). Its own method statement: 18,938 qualified
rent payment records across all 50 states, which is roughly 76 records per
state\-month; inclusion requires "a documented history of at least one successful
online rent payment prior to the reference period"; subsidised housing and
institutional portfolios excluded. **The denominator is never defined**\: unit
share, tenant share and dollar share are all consistent with the page. Five
points, no history, no download.

**Chandan Economics / RentRedi `13.5%`** (late\-payment rate, January\-February
2026\). Sample is RentRedi subscribers; the reported panel falls from about 66,950
(September 2025) to 49,745, a quarter of the panel, with no stated reason. The
disqualifying rule, verbatim from the method note:

> "Units that have not paid any form of rental income (full or partial) in the
> previous 60 days at the time a new rental charge is issued are removed from the
> sample tracking sample."

**Households that stop paying leave the denominator.** They leave it faster when
conditions worsen. A1 is a model of the households that stop paying. The number
is not merely non\-representative; its construction removes the object of the
stage, and its peaks are compressed by exactly the mechanism the stage claims to
find. Separately, "late payment" means paid after the due date, which is a
different rung from arrears.

**Free reproducible substitute, and it is stronger than what it replaces: the
Federal Reserve's SHED.**

|  |  |
| --- | --- |
| Quantity | Share of renters **behind on rent at some point in the prior 12 months** |
| 2025 | `23%` of renters (2024: `21%`) |
| By income, 2025 | `<$25k` **33%**; `$25-49.9k` **31%**; `$50-99.9k` **17%**; `≥$100k` **5%** |
| Sample | About 13,000 adults, national probability sample, fielded October 2025 |
| Format | **CSV and Stata microdata**, every year 2013\-2025 archived with codebooks (SAS discontinued 2026\-02\-09) |
| Lag | Annual, released 2026\-05\-13, about seven months |

This is the income\-stratified arrears reading that the New York Fed does not
publish, on precisely the rent rung, with microdata. **Its time quantifier is
different and must be registered as such**\: SHED is ever\-within\-twelve\-months,
the vendor numbers are a point\-in\-month rate. That difference is the whole reason
`23%` and `11-13%` are not in conflict, and it is checklist item 1.

Monthly cross\-checks exist historically and are both closed: Census Household
Pulse **Housing Table 1b**, renter payment status, 2020\-04 to 2024\-12, xlsx plus
public\-use CSV, superseded by HTOPS (bimonthly, roughly ten\-month publication
lag, and the renter\-payment item was absent from the March 2026 tables, so it is
a rotating topic and cannot be assumed forward); and the **NMHC Rent Payment
Tracker**, discontinued January 2022, final xlsx still downloadable, last point
`92.0%` paying in December 2021.

## 7\. The eviction rung: wrong number, wrong coverage, and the wrong side of the claim/resource line

**The `1.24 million` figure was not located.** What exists:

| Figure | Window | Coverage | Counts |
| --- | --- | --- | --- |
| **1\.23 million** | calendar 2025 | Eviction Tracking System sites: 38\-43 city areas plus 10\-11 states, about **one third** of US renter households, site states it is not nationally representative | eviction case **filings** |
| 1\.26 million | calendar 2024 | same | filings |
| 3\.6 million | 2018 | national | filings, **model\-based estimate** imputing about a million cases for counties without usable records |

`1.24 million` is most plausibly a transcription of `1.23M`. Whatever its origin, the
quantity it names is not national and not a twelve\-month rolling window that the
site publishes.

**Filings are not displacement, and the framework's own vocabulary says so.** The
cascade in Volume One ends at eviction, a physical displacement, a resource\-side event. The Eviction
Lab's 2022 methodology states that its records "do not allow us to measure how
many households were displaced following the case filing". Post\-2018 there is no
judgment or execution series at all. The only source carrying both is the older
2000\-2016 national estimate, where 2016 shows about 2.35M filings against 0.90M
evictions, a ratio near 2.6.

In this framework's terms: rungs one through three are claim\-side defaults, rung
four is a resource\-side displacement, and rung four is the one where the public
series measures the claim side only. The pre\-registration must say which of the
two the model emits, and if it emits displacement, that no current series scores
it.

**Retrieval.** Fixed\-name CSVs, no authentication, weekly and monthly, at
`eviction-lab-data-downloads.s3.amazonaws.com/ets/` and `evictionlab.org/uploads/`
(**liveness unverified**, robots.txt blocked the checking agent). No API found.
The filenames still read `_2020_2021` while the page is stamped 2026\-08\-08, so
**files are replaced in place with no dated vintage**\: under the project's engineering rule 6
the fetcher must snapshot by retrieval date locally, or the criterion becomes
unreproducible the next time the Lab refreshes. Terms are citation only for ETS
aggregates; the 2000\-2018 national database asks for an email, so it is one
manual pull, then frozen on disk.

**Unit.** `1.23 million` is a count. The registered criterion is "at least four of
six within ±1.5 percentage points". `±1.5pp` is undefined on a count, and it is
also undefined between a twelve\-month\-ever share and a point\-in\-time share. The
scoring rule cannot be applied to the target list as registered, and this is
visible before the stage runs rather than after.

## 8\. What this check hands to the pre\-registration

1. **A1 retrieves for itself, in this repository, pinned to a named vintage.**
   The two HHDC levels exist today only in `topology-fingerprints` (§3). The main
   repository already has the machinery and does not need to borrow: `data/fetch_*.py`
   with `--check` and `--force`, `data/raw/` and `data/processed/`, and a
   `data/SOURCES.md` whose **"Tier 1 — required for A1, A2 and B2"** section is
   waiting for this entry while its "Recorded for stage A1, not yet used" block
   already holds the DFA figures. So the shape of the work is a new
   `data/fetch_hhdc.py` on the existing pattern, writing a **vintage\-suffixed**
   raw file and refusing to overwrite an existing vintage, plus a `SOURCES.md`
   block naming workbook, page, vintage and retrieval date. The sibling repository
   contributes a recipe rather than a file (§3, last paragraph).
   
   - **The vintage constant must be written down before the first pull.** HHDC
     2026Q2 was released 2026\-08\-11, and the six targets were written against
     2026Q1. Inheriting "whatever is newest" silently rewrites the targets.
   - **The six levels themselves belong in `calibration.py`**, beside the DFA
     block that already announces itself as holding A1's targets. Constants in
     source are frozen by git; a workbook on disk is frozen by nobody.
   - **If the shape comparison of `the model correspondence spec` V1 is wanted** (model default
     cascade against the observed K shape), the 5.7 KB derived series is copied
     into `data/processed/` once, with a provenance header naming the sibling
     repository, the extractor and the vintage. A frozen copy, not a live path
     into another working tree.
   - The sibling repository's own fetcher writes every vintage to one filename, so
     its copy of the 2026Q1 workbook is one URL bump away from replacement. That
     is a note for **that** repository under the project's engineering rule 6, and it is not an
     A\-track task.

2. **Declare stock or flow once**, with the two numbers from §3 in the
   declaration, so the choice is auditable rather than implied by which column an
   extractor happened to read.

3. **Rewrite the scoring rule before anything runs.** "Four of six within ±1.5pp"
   cannot score a count, cannot score across incompatible time quantifiers, and
   silently assumes all six targets share a denominator. Suggested replacement,
   to be settled by pre\-registration rather than here: **order across rungs**
   scored as a sequence, plus **levels only where the model's denominator is the
   source's denominator**.

4. **Split measurement from literature explicitly**, per the project's engineering rule 9, as
   amended by the two rulings of 2026\-08\-13:
   
   | Measurement (re\-runnable, machine readable) | Literature (cited, never fitted) |
   | --- | --- |
   | Card 90\+ and auto 90\+, HHDC Page 12, in hand | Fitch subprime auto ABS index, pool qualifier attached |
   | Subprime auto 30\+, FEDS Note table, snapshotted on first pull | Hemlane |
   | Rent arrears by income, SHED CSV 2013\-2025 | Chandan / RentRedi |
   | Eviction filings, ETS, coverage carried in every sentence | Philadelphia Fed CFI April 2026, PDF only |
   | Age × product flow, HHDC Pages 24\-28, if used at all |  |

5. **Stratification is available on the holdings side and absent on the
   delinquency side.** DFA gives the holding structure and is already in
   `calibration.py`; SHED gives arrears by income on the rent rung only; the New
   York Fed gives delinquency by age and never by income; the FEDS Note gives one
   frozen reading by credit tier. Do not register a criterion that needs a
   maintained delinquency series by income quartile.

6. **A zero calibration is standard equipment** (`MEASUREMENT.md` item 7). The
   natural one here: a cell where income never falls must produce zero defaults on
   every rung, bit for bit, and the cascade code must be the same code in that
   cell.

7. **The representative\-household arm has a theory\-sourced expectation, so it
   needs no invented threshold.** Ruled 2026\-08\-13: A1 runs a stratified
   population and a single representative household, and the second is an arm
   rather than a setting. The source is `b1_theorem.md` Corollary 1, which kills
   the single\-index representation from one inequality on one edge for one pair of
   agents. In A1's carrier, collapsing the household dimension to a single vertex
   leaves Γ as one copy of the position graph: no position\-agent rectangle exists,
   so square holonomy is zero, and the agent\-slice summand `H¹(H)` is zero, both
   by construction rather than by parameter. The registered expectation follows
   without a self\-chosen number, in the same shape as A3\-8′: **the representative
   arm cannot reproduce the stratified arm's cross\-rung structure, and whatever
   cascade it does produce is carried by the income path alone.** Registered both
   ways: if it does reproduce that structure, the finding is that this cascade
   needs no heterogeneity, which is a result about the stage rather than a defect
   in it.

8. **Recount the parameter budget.** §A1 registers a total parameter count of ≤ 12, counted for a
   single household. A stratified population has to recount it before that
   criterion can bind on either arm.

## 9\. What this check does not settle

- **The model setting: settled 2026\-08\-13 by ruling, and recorded here rather
  than removed.** Both arms run. The main arm is a stratified population on the
  DFA 1/9/40/50 grouping already in `calibration.py` and already shared with A0;
  the control arm is the single representative household of §A1, with the
  expectation derived in §8 item 7. The representative household is an arm rather
  than the setting because **this project has already ruled that it does not
  exist**\: `b1_theorem.md` Corollary 1 removes the single\-index representation
  from one inequality on one edge, and the manuscript's own methodological preface
  names the representative individual imposed on a population whose dynamics live
  in its heterogeneity as a category error. What the availability check can add is
  only the arithmetic: a single household emits an order of default, and every
  target in §2 except the order is a rate.
- Whether the age tables can carry any weight at all, given that the model has no
  age dimension. Availability says they exist; relevance is not established here.
- Cost. Every retained source is free. The single manual step is one email for the
  2000\-2018 eviction database.

## 10\. Verdict

**Open the stage, with the target list rewritten from six levels into four
scoreable quantities plus an order test, and with A1's own retrieval written in
this repository against a named vintage before any target is quoted.**

Two of the six targets turn out to be one table rather than two sources, and that
table has been extracted once already, in the sibling repository, so what A1
inherits is a proven recipe rather than a file in place. One rung (rent) gets a
better source than the plan had, with microdata and an income split. One
(eviction) survives with its coverage restated, its number corrected from `1.24M`
to `1.23M`, and its unit changed from a percentage\-point tolerance to something a
count can be scored on. One (subprime auto) survives as a cut but changes source,
threshold and denominator: the Fitch ABS index moves to literature and the
CCP\-based `15.78%` becomes the target. The sixth (vendor late\-payment rate) is
removed, and the reason is not that it comes from a vendor: it is that its sample
rule removes households that stop paying, which is the population the stage exists
to model.

**Two rulings taken 2026\-08\-13, both recorded above where they bite.** The stage
runs two arms, stratified and representative, and the representative arm carries
a registered expectation derived from `b1_theorem.md` Corollary 1 rather than
from a threshold chosen here. The subprime rung keeps its cut at a 30\-day
threshold on a frozen CCP reading.
