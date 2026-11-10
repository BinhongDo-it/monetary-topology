# B143: where a statute draws the line of a price regulation

A delivered service cannot change hands, so no third party can close a loop through it, and the only loop
that can hold its price is the buyer's own comparison of two offers before buying. This station reads
provisions that regulate the price of part of one line of business, and records in each provision's own
words where the regulated part ends and which side of the line gets a price written by an authority. Script
`experiments/b143_price_control_line.py`; record `results/b143_price_control_line.json`.

## 1. What is recorded

For each provision: the dividing words; the two sides of the line; the side whose price an authority sets,
caps or may regulate; and the kind of thing the dividing words name.

    buyer_act        something the buyer did or could do at this transaction: consent, prior arrangement,
                     a hail, choosing a tariff, renewing
    emergency        an emergency, of the buyer or declared by a government
    good_or_seller   an attribute of the good, the service or the seller

A row is read when its pages were opened for this station and its text names both sides of the line. A row
whose text names only the regulated side is printed and not counted. For a row whose line is an act of the
buyer, the direction is which side has its price written: the side the buyer did not act on, or the side the
buyer acted on.

The corpus is eleven rows. The towing provision was read first. Taxi fares and emergency medical bills were
named before their texts were read. Household goods and air ambulance are the other price provisions met in
the same sections. The British default tariff cap and the insurance renewal rule are cited elsewhere in this
repository from their official texts. The debit interchange rule is a line known to follow the size of the
seller. California's emergency pricing statute was added for the emergency cell. All eleven are printed.

## 2. The rows

| row | issued by | the dividing words | the price is written on | kind |
|---|---|---|---|---|
| tow without consent | United States Congress, 49 U.S.C. 14501(c)(2)(C) | "performed without the prior consent or authorization of the owner or operator of the motor vehicle" | tows without consent; the general rule bars a State from regulating the price of the others | buyer_act |
| household goods | Congress, 49 U.S.C. 14501(c)(2)(B) | "does not apply to the intrastate transportation of household goods" | household goods | good_or_seller |
| emergency medical bill | Congress, 42 U.S.C. 300gg-131(a) | "emergency services (for which benefits are provided under the plan or coverage) with respect to an emergency medical condition" | emergency services: the bill may not exceed in-network cost sharing | emergency |
| medical bill without consent | Congress, 42 U.S.C. 300gg-132 | "if the provider satisfies the notice and consent criteria of subsection (d)" | care given without notice and consent | buyer_act |
| air ambulance | Congress, 42 U.S.C. 300gg-135 | "air ambulance services (for which benefits are available under such plan or coverage) from a nonparticipating provider" | air ambulance; the section does not name the other side, so the row is not counted | good_or_seller |
| hail or pre-arrangement | New York City, Admin. Code 19-507(a)(4); TLC Rules 58-26, 59B-23 | "unless the passengers have engaged the use of the for-hire vehicle on the basis of telephone contract or prearrangement" | street hails, where the Commission writes the fare; a base writes its own fares and files them | buyer_act |
| one vehicle, two trips | New York City, TLC Rules 59B-21, 59B-23(c) | "Fares for Hail Trips in Street Hail Liveries will be as set forth in section 82-26 of these Rules" | the hailed trip; a pre-arranged trip in the same vehicle runs on its base's filed rates | buyer_act |
| declared emergency | California Legislature, Penal Code 396(b) | "Upon the proclamation of a state of emergency declared by the President of the United States or the Governor, or upon the declaration of a local emergency" | sales in the thirty days after: no more than 10 percent above the seller's own prior price | emergency |
| default energy tariff | United Kingdom Parliament, Tariff Cap Act 2018 s.1 | "applies if the customer under the contract fails to choose an alternative rate" | standard variable and default rates | buyer_act |
| insurance renewal | Financial Conduct Authority, ICOBS 6B.2.1R | "A firm must not set a renewal price that is higher than the equivalent new business price." | the renewal price | buyer_act |
| small debit issuers | Congress, 15 U.S.C. 1693o-2(a)(6)(A) | "any issuer that, together with its affiliates, has assets of less than $10,000,000,000" | issuers at or above the threshold | good_or_seller |

## 3. Readings

**B143-1** (bookkeeping): every fragment carries its words, its place in the provision and a page opened
for this station. Eleven rows rest on eleven pages. Three pages opened gave no row and are listed: two
California pages that returned HTTP 403, and the part of the New York code mirror beyond the point read.

**B143-2** (premise): ten of eleven rows name both sides of their line. The air ambulance section names
only what it regulates.

**B143-3**: of the ten rows read, six draw the line on an act of the buyer, two on an emergency, and two
on the good or the seller. The first two kinds come from five issuing bodies: the United States Congress,
New York City, the California Legislature, the United Kingdom Parliament and the Financial Conduct
Authority. In seven rows the same sellers supply the same thing on both sides of the line. A reading that
ties price regulation to an attribute of the seller or of the good fits the two rows of that kind, and has
nothing to hold on to in those seven.

**B143-4**: in all six rows whose line is an act of the buyer, the price written is on the side the buyer
did not act on: the tow nobody consented to, the bill nobody consented to, the street hail (twice), the
tariff nobody chose, the renewal. No row goes the other way.

**B143-5** (instrument): ten seeded faults are caught, among them a fragment without words, a row resting
on a page that was not opened (it must leave every count), a corpus in which no row names both sides (the
two readings then carry no verdict), and one row with its direction reversed (it must be named).

## 4. Three passages

**One vehicle, two writers of the price.** A New York Street Hail Livery may take a street hail and may be
dispatched by its base. On the hailed trip the fare is the Commission's ("Fares for Hail Trips in Street Hail
Liveries will be as set forth in section 82-26 of these Rules"); on the dispatched trip it is the base's own
filed rate ("the Base’s rates for rides dispatched by the Base for Pre-Arranged Trips provided by Street Hail
Liveries"). Vehicle, driver and base are the same. What differs is how the passenger came to be in the car.

**Consent counts only where there is someone else to go to.** 42 U.S.C. 300gg-132 lifts its limit when the
patient consents after notice, and withholds that from "items and services provided by a nonparticipating
provider if there is no participating provider who can furnish such item or service at such facility". The
notice must itself carry "a list of any participating providers at the facility who are able to furnish such
items" and say that the patient "may be referred, at their option, to such a participating provider".

**A legislature's own sentence.** California Penal Code 396(a): "While the pricing of consumer goods and
services is generally best left to the marketplace under ordinary conditions, when a declared state of
emergency or local emergency results in abnormal disruptions of the market, the public interest requires that
excessive and unjustified increases in the prices of essential consumer goods and services be prohibited."

## 5. Scope

The readings say that such provisions exist and give counts over the rows read. Which transactions a
legislature regulates is its own choice, and nothing here predicts it. The level of any written price is not
read. California's statute covers goods and services alike: its line follows the state of the world and not
the kind of thing sold.

The two chapters of the Commission's rules, the British Act, the Financial Conduct Authority's handbook
and the California Attorney General's page are the issuers' own pages. The five sections of the United
States Code are read from the Legal Information Institute's reproduction, the California code from
FindLaw's, and the New York Administrative Code from an unofficial mirror. The wording of the towing
carve-out before 2015 is taken from the amendment note. Section 82-26 of the Commission's rules was not
opened; the sentence pointing to it was. The scope provision of ICOBS 6B was not on the page read. The
British Act is read as enacted.
