# Carriers

**A carrier is one object in the world that a station took a reading off**: a loan
book, a quote feed, a published price list, a statute, an archive. It is not a
station and not a file. Several stations can share one carrier, and one station
can stand on two.

**[RESULTS.md](RESULTS.md) is the record and the authority**, and the station
column below is where each carrier's readings are. [INDEX.md](INDEX.md) maps the
ledger by station; this file maps it by what was read.

**Two counts come out of the table and they answer different questions.** The
first counts objects in the world, each once, however many stations read it and
however many economies it spans. The second counts the economies, provinces and
separate published schedules inside the carriers that are themselves
cross-sectional. Both are computed from the table by
`scripts/make_carriers.py`, which also checks that every station named here is
one the ledger carries.

**The simulation track has no carrier in this sense.** It builds its own
population, and the stations from B63 to B96, which recover standard price
theories as special cases, read no data at all. What is counted here is the
measurement work.

## What the counts are

| | |
|---|---|
| carriers, each object counted once | **77** |
| economies, jurisdictions and separate schedules inside them | **532** |
| kinds of object | **7** |
| stations standing on them | **85** |

**The first row is the number to use where one is wanted.** The second is larger because several carriers are themselves cross-sections, and it is the reach rather than the count.

## Household and mortgage administrative microdata

| carrier | what the readings ask | stations | what is inside it |
|---|---|---|---|
| US mortgage application and origination records, loan level | loop sum against a scalar field's zero | B2A, B2B, B2c, B1, B7 | 20,071,740 loans in 1,103,962 position-and-date cells |
| One guarantor's single-family loan performance file | loop sum against a scalar field's zero | B8 | 2,942,295 loans; 49,649 modification and 35,659 deferral loops |
| A second guarantor's single-family loan performance file | loop sum against a scalar field's zero | B10, B12 | 1,362,490 loans, 74,937,616 monthly rows, 28 vintages |
| A published household balance-sheet cross-section | loop sum against a scalar field's zero | A1a, A1b, A1c, A1d | the one place the simulation track is asked to meet a measured population |

## Exchange, dealer and posted quotes

| carrier | what the readings ask | stations | what is inside it |
|---|---|---|---|
| One exchange's implied and directly quoted spread markets | the zero domain, where the framework predicts zero | B13, B18 | 81,968 bid and offer readings over eight products and three channels |
| An exchange-traded fund's creation and redemption triangle | loop sum against a scalar field's zero | B9 | the published fee schedule plus the venue quotes on both legs |
| A dated, symmetric tick-size change and its control group | loop sum against a scalar field's zero | B14, L2 | two rounds, 618 and 2,110 symbols, read on the symbols they share |
| Dual-listed A and H share pairs | loop sum against a scalar field's zero | B21, B24 | 62 pairs, 465 same-bell pairings, 4,226 leg-years |
| One country's simultaneously quoted legal conversion tracks | the rank of the obstruction | B5, B17 | daily, several tracks quoted at once and all of them legal |
| A central bank's own published segment table | reachability, and the registration point that opens an edge | B6-A | 207 publication days |
| A peer-collected informal exchange rate for the same country | reachability, and the registration point that opens an edge | B6-B | the instrument B6's reading is calibrated against |
| A central bank's daily reference rate, as an outside referee | reachability, and the registration point that opens an edge | B6-A | the one source in that station it does not own |
| A second country with an official rate and a parallel market | reachability, and the registration point that opens an edge | B15 | B6's zero calibration, judged on B6's own thresholds |
| Covered interest parity legs on government bonds | loop sum against a scalar field's zero | B3 | cycles that never touch one issuer |
| A third party's daily implied-rate posts | an edge cut or restored, and what it rewrites | B48, B62 | 287 daily posts over two years, and three dated removals of its input |
| One agency's corporate long-term issuer ratings | reachability, and the registration point that opens an edge | B11 | 259 issuers carrying the distressed-exchange marker |
| Airline fares | loop sum against a scalar field's zero | B30 | one of three quote carriers opened together |
| A sovereign constant-maturity yield curve | loop sum against a scalar field's zero | B30 | same batch |
| An overnight rate panel | loop sum against a scalar field's zero | B30 | same batch |
| A-share private placements, their unlock batches and daily bars | reachability, and the registration point that opens an edge | B110, B120 | an edge into new shares open to at most 35 named investors |
| Soybean futures and basis on both sides of one tariff | an edge cut or restored, and what it rewrites | B115 | Dalian against the US Gulf, with the currency removed |
| Sorghum and corn free-on-board tables | an edge cut or restored, and what it rewrites | B115 | a deposit imposed and refunded, read against corn |
| Black Sea grain prices on both sides of a corridor loss | an edge cut or restored, and what it rewrites | B111 | 909 cells transcribed by hand, one source URL each |
| An exchange's registered deliverable grain workbooks | reachability, and the registration point that opens an edge | B42 | a published quantity carrying a commodity index |
| State daily cash grain bids | loop sum against a scalar field's zero | B41 | thirty daily reports and four commodities |
| Daily arrivals and prices at regulated agricultural markets | loop sum against a scalar field's zero | B60, B61 | market-level daily series across several states |
| A crowd-sourced international price archive | the rank of the obstruction | B38, B38b, B38c, B38d, B30-5 | 53 items on the 1,263 cities carrying all of them; the bulk packaging covers 64 countries |
| An independently collected posted price, as referee | the rank of the obstruction | B39 | a source with no contact with the first one |
| Public auction results and retail listings for one wine appellation's vintages | loop sum against a scalar field's zero | B126 | 505 vintage pages of 32 wines; squares of two vintages by two auction houses |
| An auction house's handbag sale results, every public lot from 2021 to 2026 | loop sum against a scalar field's zero | B127 | 46 sales; the resale price over the boutique price of one bag at one position |

## Published price lists, tariffs and fee schedules

| carrier | what the readings ask | stations | what is inside it |
|---|---|---|---|
| An international end-use energy price data set | loop sum against a scalar field's zero | B49 | the two carriers in it that cannot be resold past the meter |
| A bi-annual European energy price panel | loop sum against a scalar field's zero | B50, B52 | every geography the source carries, 38 semesters, three tax bases |
| The residential annex of a global electricity tariff survey | the counting law on written class values | Counting, B58 | 53 national residential schedules |
| Chinese residential block electricity tariffs | the counting law on written class values | B102 | two published block schedules on one position axis |
| A utility's net metering price sheets, two vintages | loop sum against a scalar field's zero | B98 | one kilowatt hour, one meter, one hour, two vintages |
| A wholesale nodal price published with its own components | the zero domain, where the framework predicts zero | B98 | the publisher printed the answer before the station read it |
| Published tuition schedules across a national higher-education census | the counting law on written class values | B53 | three classes per school, figures in whole dollars |
| A state's hunting and fishing licence fee schedule | the counting law on written class values | B55 | 104 cells carrying 45 distinct figures |
| Monument admission priced by nationality | the counting law on written class values | B56, B57 | the class line is checked at the gate |
| Reduced transit fares required as a condition of federal assistance | the counting law on written class values | B56, B57 | three named classes, and the schedules that write fewer figures |
| A national fee schedule's split of a surgical package | the zero domain, where the framework predicts zero | B100 | three published shares that the publisher says sum to one |
| One card network's US interchange schedule | loop sum against a scalar field's zero | B123 | a class line drawn by the statute and one drawn by the network, on one schedule |
| A second card network's US interchange schedule, two editions | loop sum against a scalar field's zero | B123 | the same two class lines drawn by a second designer |
| An airport operator's charges per departure airport | loop sum against a scalar field's zero | B125 | passenger, security and reduced-mobility charges by airport group and season |
| Public service reference fares on inter-island air routes | loop sum against a scalar field's zero | B125 | 13 routes in one archipelago and 3 in the other, with statutory social fare floors |
| Boutique list prices for rationed handbags, from price trackers | loop sum against a scalar field's zero | B127 | two trackers agree on every shared figure; complete for two sizes in one leather |

## Statute, regulation and the official record

| carrier | what the readings ask | stations | what is inside it |
|---|---|---|---|
| A national wage supplement scheme's regulations | the counting law on written class values | B33 | five classes, their clause vectors, and where they fold |
| A national tax code's filing statuses, and the table built on them | the counting law on written class values | B33 | five registration classes, four printed cells, and the published aggregate beside them |
| The rule excluding one class from interest on central bank balances | loop sum against a scalar field's zero | B59 | same obligor, same instrument, and a published rate one class cannot earn |
| Regulatory bank call reports | loop sum against a scalar field's zero | B59 | 2009Q1 to 2026Q2, what each size class pays overnight |
| A central bank's discount window loan files | reachability, and the registration point that opens an edge | B113 | 56 quarterly workbooks |
| A bilateral tax treaty network | the counting law on written class values | B23 | sixteen of twenty countries carry a binding wedge |
| A statutory minimum wage with moving age boundaries, and the labour survey under it | the counting law on written class values | B34 | four boundary moves, and the break moves with the statute |
| A city's two parallel allocation legs for one licence | reachability, and the registration point that opens an edge | B45 | a lottery and an auction, same city, same month, no swap |
| A capital control imposed and lifted class of edge by class of edge | an edge cut or restored, and what it rewrites | B97 | eight dated relaxations, sequenced by the authorities themselves |
| An import quota and the plant registrations beside it | reachability, and the registration point that opens an edge | B36 | the quota did not bind and the registration date did |
| A bound import duty schedule across reporters | the counting law on written class values | B30 | 190 reporters on one tariff line |
| A corpus of national currency reforms and their texts | the counting law on written class values | B46, B47, B30 | nine reforms re-coded by what each class receives, and more in the corpus behind them |
| A privatisation agency's firm-level disposal record, released under freedom of information | reachability, and the registration point that opens an edge | B40 | 13,378 firms in seven disposal classes |
| A value added tax law's input deduction by buyer class | loop sum against a scalar field's zero | B122 | three rates by three buyer classes, nine squares, four independent |
| A consumption tax's invoice transition schedule by seller class | loop sum against a scalar field's zero | B122 | one loop read as a dose over five dated steps |
| An island resident air fare discount and the statute that sets its base | loop sum against a scalar field's zero | B125 | a share of the fare with three airport charges taken out of the base, and its dated history |
| A city's rent cap statute and the rent index its table was derived from | the counting law on written class values | B129 | twelve values for one kind of dwelling, each a 2013 rent-index base times one factor |

## Official statistics and administrative panels

| carrier | what the readings ask | stations | what is inside it |
|---|---|---|---|
| A national statistical yearbook's city panel | the rank of the obstruction | B30-5 | an administrative list of cities rather than a selection |
| A multi-country growth and labour accounts database | an index number read as a projection | B101, B106 | 34 countries and 60 industries |
| An international price comparison programme's benchmark rounds | an index number read as a projection | B83 | two published rounds and two published price indices |
| A monetary union's reserve and cross-border payment statistics | where new claims enter, and how long they stay | B112 | 21 national components of one system |
| A community currency's complete transfer archive | where new claims enter, and how long they stay | B114, B117 | every transfer over seventeen months, with timestamps |
| One country's domestic prices against its own border prices | loop sum against a scalar field's zero | B31 | four commodities, 79 commodity-years, 106 writable squares |
| A central bank's average interchange fee by network, as referee | loop sum against a scalar field's zero | B123 | the statutory cap read back on 220 network-years |

## Historical archives

| carrier | what the readings ask | stations | what is inside it |
|---|---|---|---|
| A four-century toll register | the counting law on written class values | B44 | 2,152,670 passages, a flag class recorded on both sides of two treaties |
| A two-tier gold market and the official stock behind it | reachability, and the registration point that opens an edge | B64 | the classes that could still walk the conversion |
| A national population series by single year of age | the counting law on written class values | B46 | read as the difference of two series |

## Declared conversion systems outside money

| carrier | what the readings ask | stations | what is inside it |
|---|---|---|---|
| Global warming potentials across every assessment report | loop sum against a scalar field's zero | C1 | 105 species, 11 published standards, 339 independent loops |
| Provincial admission filing lines after one national examination | the counting law on written class values | C3, E1 | 5,771 institution entries, 2,077,374 determined comparisons |
| A second administrative system of the same kind, as a control | the counting law on written class values | C2 | 115 colleges, 84,018 placements, six parallel schemes at once |
| A storefront's tag directory and its price enumeration | the counting law on written class values | B30 | a price list nobody has to agree with anybody about |

