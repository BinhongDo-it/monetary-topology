# B152: app store commission tables read as class-by-position tables

Apple and Google each publish the commission the store takes from a developer class on a position a transaction
sits on. On Apple's pages the positions are payment routes that recent law opened beside the store's own billing:
in-app purchase through the store, an alternative payment processor inside the app, and an external link out of
the app. On Google's pages a position is three things at once: the product (auto-renewing subscription or other
transaction), the install cohort of the buyer (first install before or after the rollout date), and the billing
route (Google Play billing, alternative billing, external link). The classes are the store's own: the standard
rate against the reduced rate on Apple's pages (three programs, and subscriptions after their first year); the
first million dollars of annual earnings, the standard tier and the program tier on Google's. This station reads
each table's exact squares. Script `experiments/b152_appstore_square.py`; record
`results/b152_appstore_square.json`.

## 1. What is read

A table `f(a, c)` has classes `a` as rows and positions `c` as columns, in percentage points. The square on two
rows and two columns is `f(a,c) + f(b,d) - f(a,d) - f(b,c)` in levels, and the same with `log(1 + f)` or
`-log(1 - f)` in place of `f`. Two point predictions are scored:

    L   the commission is a price of the position plus a term for the class: one term per column and one per
        row. Every level square is zero.
    M   a scalar potential on positions with a constant offset per class. Every square in log(1 + f), or in
        -log(1 - f), is zero.

Squares are decided in rationals with no tolerance. Three knobs are swept on every square: the transform; whether
a printed add-on is included (Apple Japan's 5% payment processing fee on Apple In-App Purchase, Google's 5% billing
fee on Google Play billing); and how Google's "reduced by 4%" for alternative billing in South Korea and India is
read (four percentage points, or four per cent of the fee), since the page prints no worked example. A square
non-zero on all twelve settings is read; zero on all is zero; zero on some is not read.

The floor is the printed format. Every rate is a whole percentage, so one percentage point is one tick. A number
printed once is one input and moves every cell it sits in: Apple Japan prints 21% once for in-app purchase and
alternative payment, and its 5% processing fee once for both classes. Google prints the same numbers two ways: its
help page prints "10% + 5% billing fee" in each cell with the first-million row as one cell spanning three columns,
and its June 2026 post states one 10% for the first million and every subscription and one 5% billing fee. The
floor is taken in both layouts. A read square stands above the floor when, with the add-on included and Korea and
India read in points, it exceeds its floor in all three transforms and both layouts.

Each rival is also read in its own units: L on the level square across the four add-on and Korea/India settings,
M on each log square across the same four. A rival fails where its own squares are non-zero on all four of its
settings and above the floor on each of them in both layouts (every square read above the floor meets this for
both rivals); it holds where one of its own squares is zero on all four; anywhere else it carries no verdict.

## 2. The tables

| table | rows | in-app purchase | alternative payment | external link |
|---|---|---|---|---|
| Apple, EU (effective 1 October 2026) | standard / reduced | 26 / 15 | 20 / 10 | 15 / 10 |
| Apple, Japan (17 December 2025) | standard / reduced | 21 + 5 / 10 + 5 | 21 / 10 | 15 / 10 |

| Google, Australia, EEA, Japan, UK, US | subscriptions, Play billing | other, new installs, Play billing | other, existing installs, Play billing | other, existing installs, external link |
|---|---|---|---|---|
| first $1M of annual earnings | 10 + 5 | 10 + 5 | 10 + 5 | 10 |
| standard | 10 + 5 | 20 + 5 | 25 + 5 | 20 |
| Level Up or Apps Experience program | 10 + 5 | 15 + 5 | 20 + 5 | 15 |

| Google, all remaining markets, developers enrolled in the 15% service fee tier | other, Play billing | subscriptions, Play billing | other, Korea/India alternative billing | subscriptions, Korea/India alternative billing |
|---|---|---|---|---|
| first $1M | 15 | 15 | 15 reduced by 4% | 15 reduced by 4% |
| above $1M | 30 | 15 | 30 reduced by 4% | 15 reduced by 4% |

Apple's reduced row is the same four groups on both pages (Small Business Program, Mini Apps Partner Program,
Video Partner Program, auto-renewable subscriptions after their first year); the EU page states it in one row per
route, the Japan page in two rows at one rate, and both rows' quotes are checked against that rate. Both pages apply
the commission to the price paid by the customer. The first-million external-link cell is from the post's sentence
that the 10% applies "Regardless of whether you use Google Play's billing system, alternative billing, or external
web links". The two program pages print the program rate card in text, and it agrees with the help page cell by
cell. The remaining-markets rows apply to developers enrolled in the 15% service fee tier, and within the tier the
tranche of annual earnings sets the row.

Google's alternative billing in the five named markets is set by printed text: the post introduces the rate card
for "all other transactions" after naming alternative billing, says "For transactions processed via alternative
billing or external web links, the billing fee does not apply", and the program pages print each service fee as
"+billing fee, if applicable" with no separate alternative-billing column. That column is the Google Play billing
column without the billing fee, which the add-on setting "without" already reads, so it is not added as a column:
its squares against Google Play billing would be level zeros made by the billing-fee rule, and its squares against
the other columns would repeat level squares already read.

Not read, each with its reason in the record: the external-link rate on new installs (not printed), the
remaining-markets program row ("15% or lower", a bound), the billing fee in the remaining markets (not yet
announced), Apple Japan's 5% commission on distribution outside the App Store (one rate with no class split), the
Core Technology Commission in the EU (not on the page read), and Apple's rates elsewhere.

## 3. Readings

| table | squares | read, above the floor | read, on the floor | zero | not read |
|---|---|---|---|---|---|
| Apple, EU | 3 | 2 | 1 | 0 | 0 |
| Apple, Japan | 3 | 2 | 0 | 0 | 1 |
| Google, five markets | 18 | 13 | 0 | 0 | 5 |
| Google, remaining markets | 6 | 4 | 0 | 1 | 1 |
| total | 30 | 21 | 1 | 1 | 7 |

The 21 squares read above the floor hold one sign on every setting; the smallest multiple of the floor among them
is 3.90 (help-page layout; 4.25 in the post's layout), on Google's first-million against standard rows, existing
installs against their external link, in `log(1 + f)`. Apple's EU in-app against alternative square is +1 point,
exactly one tick, and is not counted.

By the two columns they compare, the 21 are: billing route alone, 6 (Apple's in-app and alternative payment each
against external link, on both pages; Google's existing installs against their external link for the first-million
row against the standard and the program rows); product or install cohort on one route, 10; both at once, 5.

Independent squares within the four tables: 2, 2, 6 and 3, 13 in all; the 21 squares read above the floor span all
13. Counting Apple's two jurisdictions as one table of two rows and six columns, the total is 14.

**On all 21, both point predictions fail**: the commission is not a row term plus a column term in levels, nor in
either log. Two designers, Apple and Google, give the reading separately.

**Where the tables are zero.** The zeros come from three sources, and only one of them is shared by every transform.

- **One price printed for two cells.** Subscriptions against subscriptions under Korea/India alternative billing:
  the page prints one 15% for both rows, so the two prices are one price. Zero in all three transforms; both rivals
  hold there.
- **A printed rule.** Apple Japan, in-app purchase against alternative payment: the same 21% in both, and one 5% fee
  added to both classes' in-app cell. Zero in levels on every setting, so L holds; zero in the logs without the fee
  and non-zero with it, so M carries no verdict. Its level floor is zero by construction; its log squares are 5.2
  and 4.6 floors. Korea/India alternative billing against Google Play billing on other transactions: zero in levels
  when "reduced by 4%" is read in points and non-zero when it is read as a share, so L has no verdict; both log
  squares are non-zero on all four settings and stand 3.84 to 4.16 floors above zero, so M fails there. The sign
  of the `log(1 + f)` square turns with the reading (positive in points, negative as a share); M predicts exactly
  zero, so the sign does not enter the verdict.
- **Numbers that happen to be equal.** Five squares on Google's five-market table are zero in levels with no rule
  printed for them: first-million against standard, new installs against the existing-install external link, is zero
  because the standard row prints 20 for both cells; first-million against program on the same columns, because the
  program row prints 15 for both; and standard against program on the three non-subscription columns, because the
  program row is five points below the standard row in each. L holds on all five; the logs are not zero, and M
  carries no verdict on any of them (below the floor, or zero only without the billing fee).

The billing-fee rule makes no zero of its own: it adds the same five points to the same three columns on every row,
so every level square on Google's five-market table is the same with and without it.

Each rival in its own units: L fails on 21 squares, which span all 13 independent squares, holds on 7 (the
one-price square, Apple Japan's in-app against alternative, and the five equal-number squares), which span 5, and
has no verdict on 2; M fails on 22 (the 21 and Korea/India other against other-alternative billing), which span
13, holds on 1, and has no verdict on 7.

**Same writer, two jurisdictions.** Apple's standard-minus-reduced difference, EU against Japan: zero on in-app
purchase (26/15 against 21 + 5 / 10 + 5), zero on external link (15/10 on both), and -1 point on alternative
payment (20/10 against 21/10), which is one tick and not counted. With Japan's processing fee taken off, the in-app
square is zero in levels and of opposite signs in the two logs.

## 4. Checks

Each criterion carries a kind: `instrument` asks about the transcription, `premise` about a fact the squares
depend on, `known_answer` about results fixed by printed rules, `own_reading` about this station's reading, and
`bookkeeping` about the record.

| | criterion | reading |
|---|---|---|
| PASS | PAY1-1 `instrument` | 36 of 36 quotes on the saved pages as printed: 34 inputs, each quote's percentage equal to the value used, and Japan's two second reduced-class rows, each equal to the rate of the row it merges into; 7 cells listed missing and none in any table; the alternative-billing column's rule quoted on its pages; the program pages' rate cards agree with the help page; Google's help page and post give the same value in each of the 12 cells on all four settings |
| PASS | PAY1-2 `premise` | 13 class lines, each with a quoted assignment rule: by prior-year proceeds, by tranche of annual earnings (within the 15% tier where the page says so), by subscription age, or by program; none is a choice on one transaction |
| PASS | PAY1-3 `known_answer` | the printed rules above: Apple Japan's in-app against alternative zero in levels; on the help page's cell-by-cell numbers, the billing fee leaves every level square unchanged and the first-million row is flat at 10%; Korea/India alternative against Play billing zero in levels in points; subscriptions against subscriptions under alternative billing zero in every transform |
| PASS | PAY1-4 `own_reading` | 30 squares: 21 read above the floor, 1 on the floor, 1 zero, 7 not read, square by square as registered; the 21 by columns compared 6 / 10 / 5; 13 independent squares, all spanned; L fails 21, holds 7; M fails 22, holds 1 |
| PASS | PAY1-5 `own_reading` | EU against Japan: in-app zero, alternative payment on the floor, external link zero; the reduced row has the same four groups, worded differently |
| PASS | PAY1-6 `bookkeeping` | 8 pages with address, access date, version sentence (or why none) and hashes; 7 missing cells with reasons; the derived column with its rule |

The self-test plants one error per criterion and checks each flips, checks an additive table reads zero in levels
and a rank-one table zero in `log(1 + f)`, and checks each rival's scoring in its own units: 33 checks. A mutation
run (`--mutate`) breaks one piece of the implementation at a time and reruns the self-test: dropping a transform,
zeroing a floor, splitting a number printed once, ignoring the knobs, letting a merged class row go unchecked,
scoring a rival on the floor or from the joint state, checking Google's rules on the post's own layout. All 14 are
caught. Both runs are written into the record check by check.

## 5. Sources

The eight pages were saved as served on 14 October 2026; addresses, hashes and the sentence each page prints
about its version are in the record's `config.pages`. The Japan page prints no date for its rate tables; their date
is the December 2025 announcement's. Apple: the EU alternative payment options page, the Japan app distribution
page, the December 2025 Japan announcement, the Small Business Program page. Google: Play Console Help answer 112622
(service fees), the Android Developers Blog post of 24 June 2026, and the Games Level Up and Apps Experience program
pages. Related reading on two-sided platform pricing: Rochet and Tirole (2003), "Platform Competition in Two-Sided
Markets", Journal of the European Economic Association 1(4): 990-1029.
