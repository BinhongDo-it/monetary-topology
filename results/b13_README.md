# B13's products: what each file is, and what made it

**Ten plain-text files, copied here byte for byte** by
[`experiments/b13_verdicts.py`](../experiments/b13_verdicts.py) on every run.
The originals are written under `data/raw/b13/`, which `.gitignore` excludes
because that tree also holds 6.8 GB of CME packet captures. **The captures are
not redistributable and the outputs are**, so the outputs live here, unedited,
and this file is the index rather than a header inside them. A copy that had
been annotated would no longer be the thing the criterion cites.

Every number in [`b13_zero_domain.json`](b13_zero_domain.json) is checked
against these files before that record is written: a quote is backed when some
value printed here, rendered to as many significant digits as the quote carries,
is the quote. No tolerance is invented for that check, and the four numbers it
cannot back are listed in the record's `numbers_not_read_off_a_product`.

**Prices are raw PRICE9 throughout.** `1e9` is one tick, so the tables read in
ticks. `λ` is in the instrument's own tick, and the tick differs by product
(`1e9` for CL, RB, NG, GC; `5e9` for TTF, HG, MHG; `125e9` for QI), so **any
quotation of a `λ` value has to carry the product with it.**

---

## The gate

| file | what it is |
|---|---|
| [`b13_gate0_CLZ3-CLZ4_AB.txt`](b13_gate0_CLZ3-CLZ4_AB.txt) | **B13-0, the opening gate, on one spread.** Before any finding, does a book built from the packet stream reproduce the exchange's own published implied book, and under which convention? |

**What it settles, and it settles more than "the instrument works".** The
exchange publishes an implied book for `CLZ3-CLZ4`. There are two candidate
readings of what it is implied *from*: the two legs' **directly quoted** books,
or the legs' own **implied** books. The file runs both:

| identity | legs read as | checked | exact | share |
|---|---|---:|---:|---:|
| implied bid | direct legs | 2,098 | 2,096 | **0.9990** |
| implied offer | direct legs | 2,098 | 2,003 | **0.9547** |
| implied bid | implied legs | 2,440 | 1,394 | 0.5713 |
| implied offer | implied legs | 2,440 | 1,140 | 0.4672 |

**0.9990 against 0.5713 is the answer to which convention the exchange uses**,
and it is why every later run reads the direct legs. The misses are small and
the file prints their sizes: two misses on the bid side, both one tick; ninety-five
on the offer side, ninety-two of them one tick.

**Two things a reader should not take from this file.**

1. **`0.9547` is not the station's result.** This is a construction check on one
   instrument, run before the criterion was rewritten. The load-bearing
   criterion is the one-sided inequality in the out-of-sample files below, and
   it returns **zero violations in 81,968 states**. A reproduction share and a
   violation count are different objects.
2. **`2,442 of 34,923` is not a 7 per cent sample.** The comparison is defined
   only on events where the implied book was republished; on the others there is
   nothing on the exchange's side to compare against. That is the definition of
   the quantity, not a filter applied to it. The out-of-sample runs below use
   every such state on their channels.

**One more thing this file is evidence of.** An earlier run of the same gate read
only the A side of an A+B deduplicated capture, lost 2 per cent of updates, and
produced `0.9229` on the bid line, which looked like a finding about the
exchange. Both sides give `0.9990`. What caught it was a book monotonicity
check, not any guard written for the purpose. **The `0.9229` is not in any file
here**, because that run's output was never saved, and the record says so.

---

## The load-bearing criterion, out of sample

| file | channel | states | violations |
|---|---|---:|---:|
| [`b13_gate0_oos_20230717.txt`](b13_gate0_oos_20230717.txt) | ch382, NYMEX energy | 63,168 | **0** |
| [`b13_gate0_oos_ch386_NG.txt`](b13_gate0_oos_ch386_NG.txt) | ch386, natural gas | 5,336 | **0** |
| [`b13_gate0_oos_ch360_COMEX.txt`](b13_gate0_oos_ch360_COMEX.txt) | ch360, metals | 13,464 | **0** |

Each file has three parts: the per-product `equal / better / VIOLATE` table, the
verdict line, and the independent side's distribution.

**The criterion is an inequality, and the files say so on their own verdict
line.** It asks whether the exchange's published implied price is ever *worse*
than the two-leg derivation. `better` is not a defect and is not a near miss: it
is the exchange finding a route the two-leg derivation does not have. On ch386
and ch360 the `better` column is zero and the relation is an exact equality on
every state, **18,800 of 18,800**. On ch382 it is an inequality with `better`
populated. **Why the two channels differ is an open question** and the
explanation first offered for it was withdrawn; see
[`b13_path_multiplicity.txt`](b13_path_multiplicity.txt).

**The line reading `equality rate bid 0.8369, offer 0.8692` on ch382 is labelled
`reported only, not a criterion` in the file itself.** It measures how dense that
product's price grid is. Quoting it as though the zero were 84 per cent would be
quoting a number the file marks as not the criterion.

---

## The precondition, checked late

| file | channel | equal | different | no data |
|---|---|---:|---:|---:|
| [`b13_tick_ch382.txt`](b13_tick_ch382.txt) | ch382 | 10 | **0** | 0 |
| [`b13_tick_ch386.txt`](b13_tick_ch386.txt) | ch386 | 7 | **0** | 0 |
| [`b13_tick_ch360.txt`](b13_tick_ch360.txt) | ch360 | 8 | **0** | 0 |

"Exact equality" between a spread's price and a derivation from its legs is
undefined unless all three sit on the same grid. **This check was registered
before the gate and was run after it**, so a day's readings stood on luck until
it passed. The grid is measured as the gcd of the observed prices rather than
read off the definition field, because the registration asked for the grid the
instrument actually publishes on.

`b13_tick_ch382.txt` was re-run and saved on 2026-08-19: the first pass on that
channel printed to a console and its instrument list was never recorded, so the
earlier count of twenty-three could not be rebuilt. Twenty-five is what three
saved files add up to. **The verdict never moved**: zero different, zero no-data.

---

## B4's split, and the two-classes adjudication

| file | what it is |
|---|---|
| [`b13_b4_split_ch382.txt`](b13_b4_split_ch382.txt) | the first measurement in this repository of **both** halves of `docs/b4_directed_edges.md` section 5.1's split. Available in 49,116 of 50,055 states; Theorem 6(1)'s sign constraint has zero counterexamples in all of them |
| [`b13_two_classes_ch382.txt`](b13_two_classes_ch382.txt) | Theorem 6(4)'s bound `\|S − S'\| ≤ −(S + S')`, zero violations, and section 5.1's own criterion for two agent classes applied per position edge under a parity control |

**The parity control in the second file is why it is longer than it looks.**
Index and friction always share parity, so on 54.4 per cent of states a zero
index is not among the available values and a non-zero one there says nothing.
Restricted to the states where zero was available: `CLU3-CLV3` takes it 716
times out of 716, `RBU3-RBX3` 88 out of 1,978, `RBU3-RBV3` 155 out of 1,895.

---

## The audit that withdrew an explanation

| file | what it is |
|---|---|
| [`b13_path_multiplicity.txt`](b13_path_multiplicity.txt) | the instrument listing, and no price at all |

The station first said the six exactly-equal products were the ones where the
two-leg path is the only derivation path. A listed calendar spread `(A, B)` has
a second route whenever some third month `C` gives both of its cross pairs.
**Every root measured is multi-path, on both sides of the split**: CL 906 of 906,
RB 861 of 861, NG 1,124 of 1,127, TTF 630 of 630, GC 231 of 231, HG 820 of 820,
MHG 780 of 780, QI 55 of 55.

**The reading stands and the attribution is gone.** This file is here because the
withdrawal is part of the record, and because a reader who wants to check the
withdrawal should not have to take it on description.

**Its own limit, printed at the foot of the file**: it tests the listing, not
what the matching engine generates. Implied depth is a per-product configuration
this repository has not read. The data argues the engine does go past two legs on
at least one channel, because on ch382 the published implied price is sometimes
**better** than the two-leg derivation, and a better price cannot come from a
route that does not exist.
