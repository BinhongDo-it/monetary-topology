# B92: capital reversing, and why two techniques cannot produce it without reswitching

**RUN: 2026-09-13. Statement and proof below. Checks in
`experiments/b92_capital_reversing.py`, record `results/b92_capital_reversing.json`, which carries
the configuration it ran under. Paper station: zero data. B74's technique generator, Samuelson's
1966 pair and its root finder are imported rather than rewritten.**

## 0. The question this station answers

Capital reversing is the half of the Cambridge controversy that says a lower rate of profit can go
with a less capital-intensive technique, so the rate does not measure a scarcity of capital.
[`b67_prices_of_production.md`](b67_prices_of_production.md)'s Corollary 12.3 already contains it
in general form: **the value advanced is read off the field and the field moves with the rate, so
no quantity read off prices orders techniques independently of the rate.** This station names it,
measures it, and finds where the two-technique case stops short of the general one.

## 1. Setup

A technique is a dated-labour profile, [`b74_roundaboutness.md`](b74_roundaboutness.md)'s object:
`c(x) = sum_t l_t x^t` with `x = 1 + r`. With output as the unit the wage is `w(x) = 1/c(x)`, net
output per worker is `1/L` with `L = sum_t l_t`, and the value of capital per worker is

```
k(x) = (1/L - w(x)) / r
```

**At a crossing the two techniques share the wage**, so `k_A > k_B` exactly when `L_A < L_B`, and
capital reversing at a crossing says the technique adopted at the higher rate carries less labour
in total.

## 2. Theorem 36

**(1) `k` is two-valued at every switch between techniques of different total labour.** Both
techniques are in use at one wage and one rate and
their capital per worker differs. **So `k` is not a coordinate on the field**, and asking it for a
direction is a category error rather than an anomaly. This is Corollary 12.3 at its sharpest.

**(2) With two techniques, reversing requires reswitching, and it is arithmetic.** `c_i(1) = L_i`,
so at a zero rate cheaper means less total labour. With a single crossing above `x = 1`, the
technique cheaper just below it is cheaper all the way down to `x = 1` and so carries the smaller
`L`, which is the opposite of what reversing needs.

**(3) With three or more it does not.** The two techniques meeting on the envelope need not
include the one that owns `x = 1`, so the argument in (2) has nothing to run on.

**(4) Reswitching brings reversing with it**, at one of the two switches and not at both, which is
the textbook reading and follows from (2) read in reverse.

## 3. What the checks read

**Seven criteria, all passing** at `seed 92`, 1,145 two-technique draws that cross and 1,878
families of three to five techniques whose envelope switches.

| | criterion | reading |
|---|---|---|
| `B92-1` `known_answer` | **Samuelson's 1966 pair** | the two crossings come back at `r = 0.5` and `r = 1.0` against the published pair, the wage is equal at each to `0.00e+00`, and **capital reverses at the second and not the first**. `L_A = 7` against `L_B = 8` is what decides it |
| `B92-2` `own_reading` | **two techniques** | `0` of the `1102` single-crossing draws reverse and `43` of the `43` that cross twice or more do. Both counted on the same draws |
| `B92-3` `own_reading` | why that half is arithmetic | on `1102 / 1102` single-crossing draws the technique taken at the higher rate carries the larger `L`, without exception, which is `c_i(1) = L_i` read back |
| `B92-4` `own_reading` | **three techniques break it** | `12` of `1878` families show reversing with no owner returning anywhere, at sizes 3, 4 and 5, against `52` families that do reswitch. On the reversing switches neither side is the technique that owns a zero rate, which is the reason (2) has nothing to run on |
| `B92-5` `own_reading` | **`k` is two-valued, and what makes it two** | the two capital values differ on all `3399` switches drawn, median `0.562` of the smaller, tenth percentile `0.221`, smallest `9.8e-04`. **Every drawn switch has different total labour on the two sides, `3399 / 3399`, so the sample cannot show the other case**: `C_A = 3 + x + 2x²` and `C_B = 1 + 4x + x²` change places at `x = 2` by this station's own root finder, both carry `L = 6`, and their `k` agrees exactly, both being `7/78` |
| `B92-6` `instrument` | crossings, tangencies and direction | envelope switches bisected to `4.4e-16` against a grid step of `7.5e-04`; a technique against itself yields `0` crossings, where counting roots rather than changes would report one everywhere; and **the envelope is checked to run the right way up**, the owner at the lowest rate being the technique with the least total labour on every family |
| `B92-7` `bookkeeping` | write-back | B67 and B74 each name this station |

**`B92-6`'s direction check was added because a mutation needed it.** Reading the envelope owner
as the dearest rather than the cheapest technique still produces switches, still produces reversing
counts, and nothing else in the station noticed. The check that kills it is free and structural:
`c_i(1) = L_i`, so the owner at the lowest rate is the technique with the least labour.

**Eight mutations, all eight caught**, one only after that check was added.

## 4. Placement

**A.** Capital reversing, reswitching, and Samuelson's 1966 pair are the Cambridge literature's,
and so is the statement that reversing can occur without reswitching.

**D.** That reversing without reswitching is a fact about three techniques and not about two, with
the two-technique case closed by one line using `c(1) = L`; and **that the sharp form of the whole
controversy is that `k` takes two values at one price system**, so there is no quantity to have a
direction. The second is Corollary 12.3 named, and it has no place to sit in an account that
treats `k` as a property of a technique.

**C is empty and this station cannot produce it**: it reads no data.

## What a continuum does to these two readings, 2026-09-13

[`b93_continuum_second_pass.md`](b93_continuum_second_pass.md) fills the family in, and the two
readings here part company.

- **Theorem 36(3) carries over and gets easier.** Reversing **with no owner returning anywhere**
  needs three techniques because the
  pair meeting on the envelope must not include the one owning a zero rate; **a continuum is
  always in that regime**, and reversing turns up on about a fifth of drawn families.
- **Theorem 36(1) does not survive in general, and where it does is measurable.** `k` is
  two-valued at a switch, and filling the family in shrinks the jump by a median factor of `0.028`
  where the active set more than doubles and by `1.000` where it does not. **So the two-valuedness
  tracks the owners actually used and not the members on offer**, and B77's bounded active set is
  exactly where it persists however dense the family.

## 5. Scope

Dated labour with output as the unit, B74's generator, lags to six periods, rates to `r = 3`, and
families of three to five techniques. The counts in section 3 are properties of the generator.
**Theorem 36(1), (2) and (4) are algebra; (3) is an existence claim and is shown by the twelve
families found, which is all an existence claim needs.**
