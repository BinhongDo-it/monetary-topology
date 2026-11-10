# B159: Definity takes over Travelers Canada; in Nova Scotia the same policies renew into the acquirer's rating program

Script `experiments/b159_definity_travelers.py` (with `--selftest` and `--mutation`), record
`results/b159_definity_travelers.json`, carrying the configuration it ran under. Sources in `data/raw/b159/`, listed with
URL and SHA-256 in `data/raw/b159/b159_manifest.json`; `data/SOURCES.md`, section B159. Criteria are written in the
script that produces the record, the record carries their text, and every quantity this run produced is reported.

## 1. The carrier

On 2 January 2026 Definity Insurance Company acquired the Canadian operations of The Travelers Companies (Travelers
Canada, whose Nova Scotia automobile business is written by The Dominion of Canada General Insurance Company). The Nova
Scotia Regulatory and Appeals Board approved two applications that move the acquired book onto Definity's program:

- **2026 NSRAB 20 (matter M12606), private passenger vehicles, decided 2026-02-05.** "The first Travelers Canada policy
  will renew on July 1, 2026, and by June 30, 2027, all Travelers Canada policies will have been renewed into
  Definity." Each policy renews on its own renewal date "into a Definity policy". "Travelers Canada rates and
  risk-classification systems are different from those used by Definity. A straight transfer of the Travelers Canada
  policies into Definity policies, without any mitigating factors, would result in large premium increases for many
  customers." Definity's Automobile Insurance Manual is unchanged.
- **2026 NSRAB 8 (M12629), commercial vehicles, decided 2026-01-12.** Same window. "Because the rates and
  risk-classification system for Travelers differ from those used by Definity, a straight renewal of the Travelers'
  policies into Definity policies without any mitigating factors would result in many customers seeing large premium
  changes."

The customers, vehicles and risks are those of the Travelers book; the pricing procedure is Definity's. The question
this carrier answers is whether the procedure, with the world held still, carries the price. The regulator's text
answers it qualitatively; the station reads how much of the answer is public and where the rest sits.

## 2. What is read

| Criterion | Kind | Reading |
|---|---|---|
| B159-1 | bookkeeping | 26 source files match their recorded SHA-256; 58 quotes found in the text snapshots |
| B159-2 | own_reading | both decisions carry the four elements of the swap (renew into A, A's manual unchanged, the systems differ, many large changes); window 2026-07-01 to 2027-06-30 (365 days) |
| B159-3 | own_reading | commercial vehicles: renewing the Travelers book into Definity moves the portfolio rate by +4.2% uncapped and +4.2% capped |
| B159-4 | own_reading | private passenger: no portfolio or distribution figure in the public decision; undetermined |
| B159-5 | own_reading | CLEAR rate groups of the same nine vehicles under the two programs' table versions, 2024 to 2026 |
| B159-6 | own_reading | class lines keyed on "came from the acquired insurer" in two Nova Scotia conversions |
| B159-7 | instrument | the acquirer's program changes twice inside the conversion window |
| B159-8 | bookkeeping | every wanted object carries one availability state |
| B159-9 | known_answer | the 8% increase M12606 cites for the Travelers side traced to 2025 NSRAB 65 |

There is no rival criterion. The risk-pricing reading (one risk, one premium, whoever runs the procedure) predicts no
change at the policy level and is written into the detail of B159-2; the framework gives no opposite point prediction on
the direction of the change, so the reading is settled by the record rather than scored.

### 2.1 Magnitude: the portfolio average, commercial only

M12629 [9]: renewing the Travelers book into Definity "without the capping mechanism would see the Travelers' portfolio
rate increase by 4.2%. The application of the proposed cap would see this increase remain at 4.2%." The risks are the
Travelers portfolio's, so +4.2% is the average move of the procedure alone. The caps are +15%, +25% after a new
chargeable claim or conviction, and -5% on decreases, applied at the conversion renewal and the next one.

For private passenger vehicles the public decision prints no such number. The Board ordered an update within six months
of its order on whether the caps keep premium foregone at or above extra premium collected (M12606 [21]); it is a
filing to the matter and is not on the public pages.

### 2.2 Where the distribution is

The Board's filing requirements (Section 155G Prior Approval, revised 2025) make every rate application fill two
displacement tables: CONF-8, exposure counts by range of uncapped premium change in 17 percent bins and 17 dollar bins,
for mandatory-only and for mandatory-and-optional risks, and CONF-9, the same on a capped basis with premium foregone
and extra premium collected. The requirements name merger and acquisition among the causes of displacement: "though it
could relate to acquisition of a portfolio through merger or acquisition." These tables sit in Part 2 of a filing, of
which the requirements say: "The confidential sections noted above reflect the Board's position on the portions of an
application which will routinely be kept confidential." The same holds for the rating-variable differentials and final
rates (C-5) of both companies.

So the distribution exists, is computed policy by policy, and is filed; it is held at a resolution the public record
does not reach. This is a publication-resolution state, distinct from a quantity no document records and from a
quantity held in a private bilateral contract.

Part 1 of a filing is non-confidential. It carries the rating profiles: the harmonized profiles of the Canadian
Automobile Insurance Rate Regulators, fifteen standard risks by nine Nova Scotia territories, with each company's
current and proposed premium. Matched across Definity's filing and the Travelers side's last filing (M12284), these
give the same standard risk priced by two programs, at profile resolution. They sit in the Board's matter database,
which is reached through a search form; this run did not open it. [Second pass, 2026-10-29: opened. M12606 carries
no profiles; the pair is M12284 against M12161, on the 2022 profiles, of which 14 by 9 territories are priced by
both; §5.]

### 2.3 The procedure change at the vehicle class level

The two programs rate vehicles on different versions of the CLEAR table. The Travelers side uses "the CLEAR (AB Alberta
& Atlantics) - Collison, DCPD and Comprehensive Separated version" (M12284 [16], 2025 table adopted); Definity uses "the
CLEAR (AB Alberta & Atlantics) – Collison and DCPD Combined version" (M12803 [42]; 2025 table until its renewals move
to the 2026 table on 2026-12-30). The Board's profile workbook prints the rate groups of the profile vehicles under each
version. For the conversion pairing (2025 separated to 2025 combined), collision and DCPD rate groups:

| Vehicle | Collision, B → A | DCPD, B → A | Comprehensive |
|---|---|---|---|
| 2018 Honda CR-V EX | 32 → 35 | 38 → 35 | 62, both |
| 2023 Tesla Model Y | 51 → 54 | 57 → 54 | 67, both |
| 2016 Dodge Grand Caravan | 32 → 34 | 35 → 34 | 22, both |
| 2018 Nissan Rogue | 39 → 41 | 42 → 41 | 27, both |
| 2016 Toyota Corolla | 37 → 37 | 37 → 37 | 22, both |
| 2018 Ford F150 | 40 → 39 | 38 → 39 | 46, both |
| 2014 Honda Civic | 27 → 30 | 32 → 30 | 15, both |
| 2000 Nissan Altima | 11 → 16 | 18 → 16 | 7, both |
| 2012 Chevrolet Corvette | 24 → 23 | 22 → 23 | 21, both |

The acquirer's version deletes one class line per vehicle: the separate DCPD rate group merges into collision. In all
27 vehicle-years (2024, 2025, 2026 tables) the merged rate group lies between the two separated ones, and comprehensive
is the same in both versions. The Board's 2026 tab carries a footer naming the 2025 tables while all nine of its
vehicles differ from the 2025 tab; it is read as 2026. Rate groups are classes, not prices: the relativities that turn
them into premiums are in the confidential part of each filing.

### 2.4 Class lines keyed on provenance

Both Nova Scotia acquisition conversions on record add temporary class lines that sort policies by where they came from:

| Conversion | Caps for the acquired book | Acquirer's own caps |
|---|---|---|
| Definity ← Travelers, commercial (M12629) | +15%, +25% after a new claim or conviction, -5% | none ("Currently, Definity does not apply such a mechanism to its own renewing policies") |
| Definity ← Travelers, private passenger (M12606) | +15%, +25%, -5% | not printed; the decision says the mechanism "differs from its own approved mechanism" |
| Intact ← RSA, private passenger (2023 NSUARB 11 [58]) | +5%, -14% | +35%, +45% after a new minor conviction, no cap on decreases |

The private passenger conversion also carries a temporary Conversion Credit Score relativity on every converted policy
until its first renewal as a Definity policy (consents given to Travelers do not transfer), and Travelers collector cars
renew as private passenger vehicles because "Definity does not have a collector car rating algorithm". The RSA line was
removed in 2023 "With the RSA clients on the Intact administration system having all renewed to that system".

### 2.5 The dose index

The reading's index is the share of the book already converted, not a date. Inside the window Definity's own program
changes twice: 2026-07-01 to 2026-10-20 on the program approved in M12606 (2025 combined table); 2026-10-21 to
2026-12-29 on M12803 (overall +7%, four rating variables changed, renewal discount flattened); 2026-12-30 to 2027-06-30
on M12803 with the 2026 table. Calendar shares are 0.307, 0.192 and 0.501; the renewal-date distribution of the book is
not public, so these are not shares of policies. [Second pass: two amending orders moved the start to 2026-07-11
and the 2026 table to 2027-01-27; §5.1.]

### 2.6 A citation

M12606 [3] cites the Travelers side's overall 8% increase to "2025 NSUARB 25". That citation is Hartford Fire Insurance
Company adopting IAO rates for commercial vehicles (M12044). The 8.0% private passenger increase for Dominion of Canada
is 2025 NSRAB 65 (M12284, decided 2025-08-07).

## 3. Reading

Two sentences, kept apart. This framework's reading of the record: the same risks moved onto a different pricing
procedure change price, on average by +4.2% for the commercial book and by "large" amounts for "many" private passenger
customers, and the procedure change is visible as class lines: one vehicle rate-group line merged, one collector-car
line deleted, and temporary lines keyed on provenance added (a three-value cap schedule and a conversion credit-score
relativity). The risk-pricing reading of the same record: one
risk, one premium regardless of procedure, which the regulator's own text does not bear out at the policy level.

## 4. Scope

Public decisions, filing requirements and the Board's profile workbook only. The policy-level displacement, the
relativities of both programs and the six-month capping update are filed and confidential; the rating profiles of both
companies are non-confidential and sit in the matter files, which this run did not open. The commercial +4.2% is a
portfolio mean; its spread is not public. New Brunswick approved a separate merger filing for the same conversion,
outside its hearing record. The 2021 Nova Scotia decision that began the RSA conversion was not found; its caps are read
from the 2023 decision that removed them.

## 5. Second pass, 2026-10-29: the Board's matter files

The public items of five matters in the Board's documents database (M12606, M12284, M12803, M12161, M12466), read by
matter number, are in `data/raw/b159/uarb15/` and in the manifest with SHA-256. Criteria B159-10 to B159-12 are new;
B159-1, -2, -4, -7 and -8 are re-read on the new items.

### 5.1 What the matter files change

- **M12606 carries no rating profiles.** It is a simplified application that changes no rate, and the Board's minor
  filing requirements say: "If the filing does not include any changes to rates, differentials, or rate group tables
  (i.e., nothing is changing), the Board does not require the company to file new rating profiles." Its Part 1 is three
  certificate pages. Its public listing holds three exhibits (one public, two confidential) and four Board documents; the
  Staff Report and the information-request responses are not among them.
- **Two dates move.** An Amending Order of 2026-03-25 "orders that the effective date is changed to July 11, 2026, the
  date when Travelers Canada policies will first begin renewing into Definity." An Amended Order of 2026-10-02 moves
  Definity's 2026 CLEAR table to "January 27, 2027, for renewal business." The dose segments become 102, 98 and 155 days.
- **The six-month update was filed on 2026-08-05.** The company's correspondence is not in the public listing. The
  Board's letter of the same day: the capping mechanism "complies with the Board requirement for the use of negative
  capping (i.e., the premium foregone on the cap on increases exceeds the extra premium collected from the cap on
  decrease)." This is the sign for the book, weighted by its policies; no figure is given.

### 5.2 The pair

The Travelers side's last private passenger filing (M12284, exhibit T-8, amended profiles, in force for renewals from
2025-12-21) and the Definity program the first converted policies renew into (M12161, exhibit D-2, 2025 NSRAB 38,
approved as filed, in force for renewals from 2025-11-21 until M12803 takes over on 2026-10-21) both use the 2022 CARR
harmonized profiles. All 22 profile descriptions (drivers, vehicles, limits, deductibles) match word for word. Both
companies priced 14 of them in all 9 territories: 126 positions. Class is the program, position is profile by territory,
and each position carries two printed premiums.

The floor is the printed rounding. Every component is a whole dollar and the printed total is their sum, so a total is
within half a dollar per nonzero component of its value; in log this is 0.0016 to 0.0064 per position, and a square's
floor is the sum of its two positions'.

| Reading | Count |
|---|---|
| positions where A differs from B beyond the floor | 117 of 126 |
| independent squares (b1 = 125, a star around the median position) above floor | 115 of 125 |
| all position pairs above floor | 7,612 of 7,875 |
| largest square | 1.2495, profile 10.1 Antigonish against Combined 1.1 North Sydney, 236 times its floor |

A single price per position (A = B) and a program that differs only by a level (A = constant x B) both predict zero;
the record reads neither. The ratio A/B by profile, minimum and maximum over the nine territories:

| Profile | A/B - 1 |
|---|---|
| 5.1, male 19, licensed 2 years | -47.1% to -20.1% |
| Combined 1.1, female 52 with a male 21 occasional driver | -49.0% to -35.1% |
| 9.1, male 70, licensed 45 years | +23.6% to +56.0% |
| 10.1, female 35, commuting 25 km | +45.3% to +77.9% |

The median position moves +0.05%. The swap leaves the level where it was and turns the slope on driver age and
experience.

### 5.3 Against the caps

28 positions sit above the +15% cap and 39 below the -5% floor; 59 are between. Unweighted over positions, the premium
foregone above the cap is 15,391 dollars and the premium collected below the floor 31,150. The Board's statement for the
book runs the other way, foregone above collected; the book weights each position by its policies and the profiles do
not, so the two are printed side by side as different objects.

### 5.4 Territory lines

Grouping the nine territories by identical printed coverage vectors, Dominion uses six groups (Halifax with Dartmouth,
Sydney with North Sydney, New Glasgow with Antigonish, and Amherst, Kentville and Yarmouth alone) and Definity four (New
Glasgow, Antigonish and Amherst together, Kentville with Yarmouth, the other two as Dominion), five on two profiles where
it prices Halifax and Dartmouth apart. The groupings differ on all 14 profiles: Dominion's is strictly finer on 12 and
the two cross on 2. Definity's territories were unchanged in 2025 NSRAB 38.

### 5.5 What stays outside the pair

Definity's 2026 program (M12803, exhibit D-3) is filed on the 2025 CARR profiles and moves +0.6% to +23.2% (median
+5.5%) over 135 positions; the Travelers side filed no 2025 profiles, so the later segments have no B. Dominion's
high-theft list was updated for renewals from 2025-12-21 (M12466), after its profile workbook. Definity turns expected
loss cost into charged premium through a proprietary formula (2025 NSRAB 38 [19]). The profiles are new business; a
converted policy carries its tenure. One Dominion exhibit listed public (M12284 T-10) carries a cover reading
"Confidential, Exhibit Sec C-5.c" with base rates and differentials; it was opened only to identify it, is held under a
renamed name that no code path opens, and is used for no reading.
