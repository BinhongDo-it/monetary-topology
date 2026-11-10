# B138: the split-share reform

A rule drew a class line inside every Chinese listed company, and the reform that erased it wrote a price
on that line. This document states the conversion from the published consideration to the class-value
ratio, the second reading from market prices, the carriers, and the readings. Script
`experiments/b138_share_split.py`; notices through `experiments/b138_fetch.py` and
`experiments/b138_parse.py`; dates and bars through `experiments/b138_bars.py`; record
`results/b138_share_split.json`. Rerun 2026-10-06: plans are read whole, B and H shares are kept apart from
the A shares, the statement listing is rebuilt month by month where a year is deeper than the platform
pages, and the readings state what they assume about the restricted shares after the reform.

## 1. The object

Before 2005 a typical listed company had tradable A shares, and a majority of shares held by the state and
by legal persons that could not trade on the exchange. The two had the same cash-flow and voting rights. The
difference was a rule: non-tradable shares could change hands only by private transfer or at auction. The
line between the classes was drawn by a third party, not chosen by the holders, so neither class could
leave it.

The 2005-2006 reform gave every share the right to trade. In each company the non-tradable holders paid the
tradable A holders a consideration for it, negotiated company by company and published in an implementation
notice. The former non-tradable shares did not become free on that day: they became tradable shares under
selling restrictions, none to be sold for twelve months and, for the larger holders, no more than five and
ten per cent of the company within the next twelve and twenty-four. One class line was erased and a
narrower one, restricted against free, stood for the following years.

## 2. The conversion

One company: tradable A shares `N_A` at price `P_A`, non-tradable shares `N_N` worth `r P_A` each, and
possibly B or H shares that trade on other markets and are left alone. Let `n = N_A / (N_A + N_N)`; the B and
H shares are not in it. The consideration `c` is stated as "each tradable A share receives `c` shares from
the non-tradable holders". If the reform moves value between the two classes without adding any,

    P_M (N_A + N_N) = P_A N_A + r P_A N_N,

and leaves the tradable holders whole, `(1 + c) P_M = P_A`, then

    c = (1 - n)(1 - r) / (n + (1 - n) r),
    r = ((1 - n) - c n) / ((1 - n)(1 + c)).

`r = 1` gives `c = 0`: one price, nothing to pay. `r = 0` gives `c = (1 - n) / n`: the whole non-tradable
stock handed over.

**The market reading.** With the price before the reform `P_A` and after it `P_M` both observed,
conservation alone gives

    r_m = (P_M N_post - P_A N_A) / (P_A N_N),

where `N_post` is the A and formerly non-tradable total after the reform. `r_m = r` exactly when the
tradable holders come out whole, so `r_m - r` reads whether they came out ahead. Whole is
`(1 + c) P_M = P_A` for a plain transfer. For a directed conversion `P_M` is the price on the enlarged share
count and the holder has `1 + t` shares, so it is `(1 + t) P_M = P_A`; for a transfer and a conversion in
one plan, `(1 + x + t) P_M = P_A`.

**The restricted shares.** Both readings value the former non-tradable holders' shares after the reform at
the free float's price `P_M`. With a restricted share worth `q P_M`, `q ≤ 1`, a share-only plan gives
`r(q) = q r`, and `r_m(q) = r_m − (1 − q) P_M N_F / (P_A N_N)` with `N_F` the former non-tradable holders'
shares after the reform. So `r` and `r_m` are the readings at `q = 1`, the upper ends in `q`. `q` is not
read here.

**The forms a consideration takes.** Shares per tradable share `x`; cash `d` per share; a capital-reserve
conversion `t` to the tradable holders only; a conversion `s` to every holder after which the non-tradable
holders hand over `k` per post-conversion share; a shrink of the non-tradable stock by `z`. The equivalent
transfer in each case:

| form | equivalent `c` |
|---|---|
| shares | `x` |
| shares and cash | `x + d / P_M`, with `P_M` the price after the reform |
| directed conversion | `t (1 - a) / (1 + a t)`, `a = N_A / (N_A + N_N + N_B)` |
| shares and a directed conversion in one plan | `(x + t (1 - a)) / (1 + a t)`; not the sum of each part's own equivalent |
| conversion to every holder, then a hand-over | `k = k_pre / (1 + s)` |
| shrink | `1 / (n + (1 - n)(1 - z)) - 1` |

A directed conversion or a shrink changes the B and H holders' fraction too, so a company with both is kept
out of the reading. B138-1 checks every line of this section against a second path that counts shares and
values holdings directly, on 2,000 synthetic companies, with eight planted faults.

## 3. Carriers

- **The notices.** cninfo's implementation notices, all 1,356 rows of the listing, 2005 to 2015: 1,344 PDFs and
  twelve HTML pages from the June 2005 pilot. 1,214 companies have a notice whose title is the implementation
  notice itself; a company with two takes the later one. From each: the consideration sentence, the
  pre-reform share structure, the record day. Every number carries the sentence it was read from.
- **The whole plan.** The consideration sentence is read to its full stop, so a clause after a semicolon
  counts: shares from the holders and a conversion to the tradable holders in one sentence are one plan. The
  plan's summary is searched for what the company itself receives or gives up as part of the reform (an
  asset swap, donated or injected assets or cash, a debt waived, a buy-back or shares cancelled against a
  debt, a one-way shrink, a new issue for assets). A plan with any of these is named and not converted, with
  the words around it kept, because its share leg is not the whole consideration. An undertaking for after
  the reform, and the clause that adjusts an additional consideration for later share changes, are not
  counted. The 75 notices the search touched among those that would convert were each read by eye: 57 carry
  such a part, 18 do not.
- **The share structure** is accepted only where the notice checks it: the parts add to the notice's own
  total, or both classes' percentages give one total, or the tradable count follows from the non-tradable
  count and its percentage with no B or H shares in the text. A table's "tradable shares, total" row comes
  before its A, B and H rows; the total and the A row are read apart, and where B or H shares sit inside the
  total the A shares are the A row. Where the notice states the total consideration in shares, `c N_A` is
  checked against it.
- **The dates and prices.** The day the reform statement was first published, from cninfo's statement
  listing. The platform serves 100 pages of a query; 2006 has 3,352 statements, so that year is asked month
  by month, and every window is checked: rows, distinct ids and the platform's own total agree, and no page
  repeats an earlier one (22 windows, 5,134 statements). Daily closes from baostock, unadjusted, since the
  listing day of the consideration carries no
  ex-rights reference price. `P_A` is the last close before the statement, `P_M` the first close after the
  record day. The Shanghai and Shenzhen composites adjust for the market over the same days.
- **Literature.** Zhiwu Chen and Peng Xiong, *Discounts on Illiquid Stocks: Evidence from China*, Yale
  School of Management working paper, September 2001: average discounts of 77.93% at auction and 85.59% in
  private transfers, relative to the contemporaneous tradable A-share price, August 2000 to July 2001, 2,577
  auction trades and 242 private transfers. The Shenzhen Stock Exchange research institute, *股权分置改革的回顾与总结*
  (report 0147, 2006-12-20), p. 20: of 1,125 companies reformed, 954 by shares alone and 1,086 with shares
  in the plan; 791 by shares from the non-tradable holders at a mean of 3.156 per 10.

## 4. Readings

**The consideration and the notices' own equivalents.** Of 1,214 companies, 759 are read and converted: 607
by shares, 120 by a directed conversion, 29 by cash or shares and cash, 3 by shares and a conversion
together. The 16 notices read by eye agree, and so do three further tables read by eye: 4 joint plans, 12
structures with B or H shares, and the 75 plan summaries. 34 directed conversions state their own
equivalent transfer ("equivalent to x shares per 10"); the formula of section 2 is within 1% of it in 33,
median gap zero.

**Against the exchange's tally** (to October 2006, 999 companies): shares from the non-tradable holders in
750 at a mean of 3.110 per 10, against 791 and 3.156; shares in the plan in 92.9%, against 96.5%.

**The rival's two point predictions.** One scalar price at each position makes the two classes of one
company one position. Then a non-tradable share trades at the tradable price, and merging the classes moves
no value, so the consideration is zero. Chen and Xiong's discounts are 78% and 86%; all 759 considerations
are above zero, smallest 0.06 and median 0.30 shares per share. Both land in the B cell.

**The class-value ratio.** From the consideration, `r` has median `0.636`, quartiles `0.595` and `0.676`. From
the prices, against the index, `r_m` has median `0.681` over 733 companies (`0.677` over the 572 whose
window from statement to listing is 70 days or less); on the same companies `r` has median `0.635`. The two
readings meet at about two thirds of the tradable price. Both are read with the restricted shares after the
reform at the float price, `q = 1`, and are upper ends in `q`: per 0.1 that a restricted share is worth less
than a free one, `r` falls by a tenth of itself and `r_m` by a median of `0.071`. Chen and Xiong's transfer
prices four to five years earlier put the ratio at `0.14` to `0.22`; none of the 759 considerations implies a
discount that deep.

**The tradable holders' gain.** Against the index, their wealth over the reform rose by a median of 3.8%, and
458 of 733 came out ahead; `r_m - r` has a median of `+0.048`.

**The consideration is close to one number.** By quintile of `n`, the median consideration is 0.33, 0.32,
0.32, 0.30 and 0.26 shares per share while `(1 - n)/n` runs from 3.00 to 0.98; the rank correlation is
`0.390`, ties at their mean rank. The implied ratio follows the float share: the same consideration writes a
different class value in a company with a small float than in one with a large float.

**The borrowed price.** Shanghai's published total market value priced the non-tradable shares at the float
price: 69% to 81% of the total from 1993 to 2005. Revalued at the median `r`, the excess is largest in yuan
in 2003, about 786 billion (5.7% of GDP), and largest against GDP in 2000, 6.7% (about 671 billion).

## 5. Named, not in the readings

Share structure not verified 234; a plan with a company-level part 126 (57 of them read by eye among the
notices that would otherwise convert; the words that named each are in the record); other forms 33 (an
equivalent the company computed at a price or a book value, a dividend to every holder handed over by the
non-tradable holders); no consideration sentence 21; warrants 15 (no warrant price on this source);
conversions to every holder 13; directed conversions with B or H shares 5; stated total disagrees 4; mixed
conversions 3; amount not read 1. For the market reading, a further 26: no trade in the 45 days before the
statement 23, no record day 3. The plain share plans among the 234 whose structure is not verified have the
same median consideration as those read (0.32 against 0.32).

The search for a company-level part looks at the 500 characters after each summary heading of the notice; a
part stated only elsewhere in the notice is not found by it.
