# B3: the slice summand, on covered interest parity deviations

Pre-registration. **Written before any data was retrieved.** Every filter,
threshold, cycle and criterion below is fixed here.

Availability, sourcing and the ruling that this stage may be opened at all are in
[`b3_slice_availability.md`](b3_slice_availability.md). That document also
carries the two things a reader should see before this one: the data is
**derived, not retrieved by me**, and the deviation is **not a profit**.

---

## 1. What this stage is for, in one sentence

Theorem 2 splits the obstruction on `Γ` into **squares** — two agents, one edge —
and **slice cycles** — one agent, several edges, loop closed. Stage B2 measured
the squares on 20.1 million mortgages. **Corollary 2 says no volume of mortgage
data can ever reach the slice summand.** This stage reaches it.

**It is not a second opinion on B2 and must never be presented as one.** The two
carriers are complements: B2 answers "does the same position carry the same price
for everyone", B3 answers "does a single agent walking a closed loop come back to
where it started". A framework claiming the terrain is not flat needs both, and
neither substitutes for the other.

---

## 2. The graph, and where the cycles are

Fix a maturity `n` and a date `t`. The positions are

- `S` — a dollar today,
- `E` — a dollar at horizon `n`,
- one intermediate node per country `i`, standing for "holding country `i`'s
  local-currency government bond, currency hedged",
- one intermediate node `T` for "holding the US Treasury".

Every intermediate node carries a path from `S` to `E`. With `C` countries there
are `C + 1` parallel paths, `2(C+1)` edges and `C + 3` vertices, so

```
b₁(G)  =  2(C+1) − (C+3) + 1  =  C
```

and the cycle space has `C` independent generators. **This is a genuine cycle
space on the position graph**, which is what stage A3's carrier could not have:
`tier_positions` is a star, a tree, `b₁ = 0`.

### 2.1 The two families of cycle, and only one of them is new

**Treasury cycles.** Out through country `i`, back through `T`. The sum is the
published `cip_govt(i, n, t)`, the deviation itself. These are the literature's
object and this stage does not claim them as its own finding.

**Cross-currency cycles.** Out through country `i`, back through country `j`,
**never touching the Treasury**. The sum is

```
z(i, j, n, t)  =  x(i, n, t) − x(j, n, t)
```

**These are the object of this stage.** They matter because they discriminate
between two accounts that the level of `x` alone cannot separate:

| account | predicts |
|---|---|
| the deviation is one common US Treasury convenience yield | `x(i) ≈ x(j)` for all pairs, so **every cross-currency cycle vanishes** |
| each currency's access to dollar funding is separately obstructed | `z(i, j)` is non-zero and structured |

Under the first account the field **is** exact on the position graph once the
Treasury's own convenience yield is priced in as a node value — the obstruction
collapses to a single scalar and there is no slice obstruction at all. Under the
second it does not. **The first account is the null and it is a live
possibility.**

### 2.2 Maturities are a robustness axis and not a cycle direction

For fixed `i`, `x(i, n, t)` across `n` is tempting to close into a loop. It is
not closed without a rollover convention, and inventing one would put an
assumption where the measurement should be. **Maturity is swept, never cycled.**

---

## 3. The measurement

For each `(n, t)` and each group `g` (§5), over the countries in that group:

```
Z(g, n, t)  :=  (1 / k²) · Σ_{i,j ∈ g} ( x(i,n,t) − x(j,n,t) )²
```

the mean squared cross-currency cycle sum. **This is Theorem 3's quantity with
the agent index replaced by the country index**, and by the same algebra it
equals `2 · Var_i( x(i,n,t) )` within the group. It is computed both ways, by
enumeration over ordered pairs and by the variance, and **they must agree to
machine precision**; that agreement is a check on the code and is reported, not
claimed.

The headline is `Z` expressed in basis points squared, and its square root in
basis points, so that it is readable next to the deviations themselves.

---

## 4. The zero calibration, which the data supplies for free

`MEASUREMENT.md` checklist item 7 requires an arm whose true value is zero,
running through the same machinery. **The dataset provides one and it is better
than a synthetic control.**

During the benchmark transition the publisher supplies `cip_govt_ibor` and
`cip_govt_sofr`: **two constructions of the same economic object** for the same
country, maturity and date. Their difference is measurement, not obstruction. So

```
N(n, t)  :=  mean over countries of ( cip_govt_ibor − cip_govt_sofr )²
```

is a **noise floor in the same units as `Z`**, derived from the data rather than
assumed. Registered: `Z` is only reported as non-zero where it exceeds `N` by the
margin in §6.

A second, trivial calibration is also run and must return exactly zero: the cycle
from a country to itself, `z(i, i) = 0`, computed through the same code path as
every other pair rather than short-circuited.

---

## 5. The graded placebo, and which arm is load-bearing

Mirrors `b2_measurement.md` §8.1, where the load-bearing arm was VA rather than
FHA because FHA's low reading had a mundane explanation that pointed the same way
as the framework's.

The data appendix states that emerging-market deviations are driven by **default
risk differentials and capital controls**, while for developed markets with
negligible default risk and open capital accounts they measure **convenience
yield and frictions**.

| arm | mundane account predicts | framework predicts | discriminates? |
|---|---|---|---|
| **G10** | near zero: no default risk, open accounts, deepest markets, arbitrage free to operate for eighteen years | non-zero | **yes — this is the load-bearing arm** |
| EM | large, from default risk and capital controls | non-zero | **no** — both point the same way |

**The headline is the G10 arm.** The EM arm is reported beside it and is
explicitly not evidence: a large `Z` there is what a critic would predict anyway.
Reporting EM as the headline because it is the bigger number would be the error
`b2_loop_b.md` §10 names — handing a reader the larger effect and the weaker
evidence.

---

## 6. Pre-registered predictions

**B3-1 — the code agrees with itself.** Enumeration over ordered pairs and
`2·Var` agree to a relative error below `1e-12`. A floor; a failure here voids
everything after it.

**B3-2 — the trivial cycle is zero.** `z(i,i)` returns exactly `0` through the
full code path.

**B3-3 — the noise floor is below the signal, in G10.** `Z(G10) > 4 · N` in the
transition window where both benchmark constructions exist. Registered at four
rather than at one so that a marginal excess is not read as a result.

**B3-4 — the cross-currency cycles do not vanish in G10.** `√Z(G10)` exceeds
`25` basis points in the majority of quarters over the sample. **This is the
stage's claim.** The number is registered here in advance and is chosen as a
round figure comfortably above quoted bid-ask on G10 forwards, not from any
inspection of the data.

**B3-5 — the cycle is not carried by the bond leg alone.** The publisher supplies
the two legs separately, `x = diff_y − rho`, so the cross-currency cycle splits

```
z(i,j)  =  [ diff_y(i) − diff_y(j) ]  −  [ rho(i) − rho(j) ]
```

into a **bond-yield** part and a **forward-premium** part. Registered: in G10 the
forward-premium leg accounts for at least `25%` of the variance of `z`, by the
decomposition `Var(z) = Var(Δdiff_y) + Var(Δrho) − 2·Cov`.

This is the criterion that discriminates against the one account a G10 reading
still has to answer. If `z` sits entirely in the bond-yield differential, a
critic assigns it to sovereign credit and nothing about funding topology has been
shown. If a material part sits in the **forward premium**, that leg is the price
of hedged dollar funding, which is where balance-sheet capacity is priced and
what `b3_slice_availability.md` §7.2 identifies as the coordinate the price
system does not carry.

`25%` is a round figure registered in advance to separate a negligible
contribution from a material one, and is not taken from any inspection of the
data.

**B3-6 — the sign structure is stable across maturities.** For the country pairs
with the largest `|z|`, the sign of `z(i,j)` agrees across at least five of the
eight maturities. Sign consistency across an axis that was not used to select the
pair, and the same discipline `a3c_load_bearing.py` adopted after quoting a share
one seed contradicted.

**B3-7 — reported, not judged: the level of the Treasury cycles.** `x` itself,
by country and maturity, plotted against `Z`. It is the literature's object and
this stage adds nothing to it; it is shown so a reader can see the two together.

---

## 7. Filters, fixed here

Our filters can act only on the publisher's output. **This is a real limitation
and §4 of the availability check states it.** What I fix now:

| filter | value | why this and not another |
|---|---|---|
| version | `cip_dataset_v4.csv`, October 2025 | pinned; the manifest records the URL and retrieval date, and prior versions are archived by the publisher if a re-check is wanted |
| sample | 2000-01-01 to the file's end | the publisher's own range; no start date is chosen here |
| countries | the publisher's G10 and EM labels, unaltered | choosing a grouping of my own would be choosing the placebo after seeing it |
| maturities | all eight, swept | no maturity is preferred |
| benchmark series | `cip_govt` as the main series, with `_ibor` and `_sofr` used only for §4's noise floor | the publisher fixed the break dates per tenor-currency pair and they are not second-guessed here |
| missing | dropped pairwise, with the count of dropped country-date cells reported per arm | silence about a dropped cell is how a sample becomes a selection |
| **outlier band** | `Z` recomputed at `±100`, `±250`, `±500`, `±1000` bp caps on `x` | **§11.2**: a single unbounded value moves a variance decomposition and the size of the garbage never enters the answer, only the cell it lands in |
| **rank version** | Spearman-style: `Z` recomputed on within-date ranks of `x` | bounded by construction, so a conclusion that survives it does not depend on the band at all |

**The headline is the widest band at which the conclusion is unchanged, and the
rank version is reported beside it.** If the two disagree, the band is doing the
work and the result is reported as band-dependent.

---

## 8. Falsification

| observation | consequence |
|---|---|
| B3-1 or B3-2 fails | the machinery is wrong; nothing else may be read |
| `Z(G10)` is within the noise floor | **the slice obstruction is not detected on this carrier.** Reported at the top of `RESULTS.md`, not in a footnote. It would mean the only obstruction this project has found is the square one, and Volume II's claim rests on half the cycle space |
| B3-5 fails: `z` sits almost entirely in the bond-yield leg | the dispersion is sovereign credit, not funding topology. **The obstruction is real but it is not the one this framework is about**, and the stage reports that rather than the cycle magnitude |
| the rank version and the banded version disagree | the result lives in the band. Reported as such and the headline is withdrawn |
| B3-6 fails: signs scramble across maturities | `z` is not a structural feature of a country pair, and no attribution to any pair may be made |
| EM exceeds G10 and is reported as the headline | a process failure, not a data failure. §5 exists to prevent it |

---

## 9. What this stage cannot establish

**It is not a profit and no sentence may say it is.** The post-2008 account is
that the deviation is the shadow price of balance-sheet capacity. §7.2 of the
availability check sets out why that instantiates the framework rather than
defeating it: the price vector on positions is not a potential, and making it one
needs a coordinate the price system does not carry. **That is the claim. "Free
money in the deepest market in the world" is not, and would be refuted in one
sentence.**

**It is not about stratification.** Theorem 2 says the two summands have
different economic content, and this is the one whose content is arbitrage
capacity rather than who the borrower is. It completes Volume II's mathematics.
It says nothing about Volume I.

**It is not my retrieval.** The construction is auditable through the
publisher's ticker list and reproducible only with a terminal. Every headline
carries that qualification.

**It says nothing about magnitude in any real economy.** As with `R*` in A6 and
the terminal ownership rate in A3b, what transfers is the comparison — G10
against EM, banded against ranked, across maturities — and not the level.

---

## 10. Schema audit, after retrieval and before any computation

**No threshold in §6 moved and no filter in §7 changed.** What follows corrects
the *description* of the file against the file itself. It is recorded because assuming a schema has cost this project four separate
errors — a column name written with an underscore instead of a hyphen silently
dropped a column, and two metropolitan areas returned zero rows.

The real header:

```
group,currency,tenor,date,diff_y,rho,cip_govt,cip_govt_break_date,
rho_ibor,rho_sofr,cip_govt_ibor,cip_govt_sofr
```

**1,513,471 data rows**, 118 MB, source SHA-256 `a6938267a7fe…`, stable across
two independent downloads.

### 10.1 Three corrections to what the appendix says

**Nine tenors, not eight.** `3m, 1y, 2y, 3y, 5y, **7y**, 10y, 20y, 30y`. The
appendix's §2 lists eight and omits `7y`, which carries 174,596 rows. §7's "all
eight, swept" is corrected to **all nine**.

**Nineteen currency codes across eighteen countries.** China appears as both
`CNH` and `CNY`. The appendix says so in passing; the consequence did not reach
§5 and does now, in §10.2.

**Dates are Stata-style strings**, `08feb2007`. Parsed explicitly with a fixed
month table rather than by a locale-dependent inference, because a parser that
silently yields `NaT` on a locale it does not expect would drop rows without
saying so.

### 10.2 A new registered test, and exactly what was known when it was written

**B3-8 — the two Chinese codes.** `CNH` and `CNY` are the same sovereign, the
same bond market and the same default risk, differing in the capital account.
The cycle `z(CNH, CNY)` therefore has **no default-risk component by
construction**, and what remains is market segmentation — the source
manuscript's "洞" (*hole*) in its most literal available form: 法律隔断、资本管制
(*legal partition and capital controls*).

Registered: `√(z(CNH,CNY)²)` averaged over tenors exceeds the noise floor `N` of
§4 by the same factor of four required in B3-3.

**What was known when this was registered**: that both codes exist, and that
`cip_govt` is populated for 22,716 `CNH` rows and 36,706 `CNY` rows. **No value
of either has been read.** If that seems a thin line, it is the same line B2 drew
when it fixed its cells before computing a variance, and stating where the line
falls is what makes it a line at all.

### 10.3 What the audit says about power

| arm | rows available |
|---|---|
| noise floor, both `cip_govt_ibor` and `cip_govt_sofr`, **g10** | **45,058**, 2012-01-13 to 2025-06-30 |
| noise floor, same, eme | 71,064, same span |
| g10 with `cip_govt`, per tenor | 40,910 (`30y`) to 65,588 (`3m`) |

The noise-floor arm is far wider than a transition window: the publisher computes
both benchmarks across thirteen years, not only across the changeover. **B3-3 is
well powered and its failure, if it comes, will not be for want of rows.**

### 10.4 Missingness, which is uneven and must be reported per arm

Non-empty share of 1,513,471 rows: `diff_y` 96.0%, `rho` 85.8%, **`cip_govt`
82.0%**, `rho_ibor` 75.9%, `cip_govt_ibor` 72.5%, `rho_sofr` 23.6%,
`cip_govt_sofr` 17.3%.

The pattern is not random — early emerging-market years carry `rho` without
`cip_govt`, because the bond leg was not yet priced. §7 already fixes pairwise
dropping with the dropped count reported per arm; this is the number that makes
that requirement bite rather than decorate.

---

## 11. Results

`experiments/b3_cip_slice.py`, `cip_dataset_v4`, 1,513,471 rows. Dropped for a
missing `cip_govt`: 44,480 g10 and 227,944 eme, per §7's pairwise rule.

**Four of the implemented criteria pass. B3-6 and B3-8 are not implemented and
nothing is claimed for them.**

| | |
|---|---|
| **B3-1** enumeration equals `2·Var` | **pass**, worst relative error `7.41e-16` |
| **B3-3** signal above the noise floor, matched cells | **pass**, `Z/N` from `63` to `200` over eight tenors, against `4` |
| **B3-4** cross-currency cycles do not vanish in G10 | **pass**, `9/9` tenors above `25` bp |
| **B3-5** the forward-premium leg carries a material share | **pass**, forward leg `+3.13` of a decomposition summing to `1.000` |

### 11.1 The headline

`√Z` for G10, in basis points, at the registered `±500` band: `30.9` at 3m
rising to `45.6` at 10y and `43.6` at 30y. The noise floor `√N` is `2.8` to
`3.7` across every tenor.

**Cross-currency cycles in G10 run at thirty to forty-six basis points against a
three-basis-point measurement floor.** These loops never touch the Treasury, so
they are not the Treasury premium; they are the statement that hedged dollar
funding is not priced by one scalar on positions.

`3m` has no `Z/N` because the noise-floor arm does not cover it — the publisher's
dual-benchmark series begins at `1y`. B3-3 is therefore evaluated on eight
tenors and says so.

### 11.2 The band scan, which separates the two arms cleanly

| tenor | G10 `√Z` at ±100 | at ±1000 | EM `√Z` at ±100 | at ±1000 |
|---|---|---|---|---|
| 3m | 28.7 | 30.9 | 85.0 | **221.6** |
| 1y | 31.6 | 32.3 | 81.2 | **209.7** |
| 10y | 45.3 | 45.6 | 68.4 | **168.7** |
| 30y | 42.2 | 43.6 | 76.4 | 118.1 |

**G10 moves by one to three basis points across a tenfold change in the band.
EM more than doubles.** `Z/N` on the matched cells is likewise flat: `74.1`,
`63.0`, `85.3`, `145`, `149–150`, `184–186`, `157–166`, `198–200` at ±100 versus
±1000.

So the G10 headline does not live in the band, which is what §7 asked, and **the
EM number does** — it is carried by the tail, which is what a crisis-driven
default-risk story looks like. §5 already declared EM non-evidence on a different
ground; the scan gives a second, independent one.

### 11.3 What the leg decomposition found

`Var(x) = Cov(x, diff_y) − Cov(x, rho)`, shares summing to one by construction.
G10: bond leg **`−2.13`**, forward-premium leg **`+3.13`**. EM: `−0.23` and
`+1.23`.

**A share above one is arithmetic, not a fault.** In a covariance
decomposition the components are not required to lie in `[0, 1]`; two legs that
move together and nearly cancel produce one share above one and its partner
below zero, and they still sum to one. `+3.13` and `−2.13` is that, and the
next paragraph gives the magnitudes that make it so. Written down because a
reader meeting `313%` for the first time reasonably suspects the code.

**The forward-premium leg drives the cross-currency cycle and the bond leg pulls
against it.** The forward premium is the price of hedging dollar funding, which
is where balance-sheet capacity is priced — §7.2 of the availability check
identifies that as the coordinate the price system does not carry, and this is
the leg it lives in.

**And the legs nearly cancel.** `Var(diff_y)/Var(x) = 20.2` and
`Var(rho)/Var(x) = 25.4` in G10: two series each twenty to twenty-five times the
size of their difference, tracking each other closely, with the deviation as the
small residual. That is worth stating on its own, because it is why the
deviation is small in level and why it is nonetheless not noise: the floor says
measurement accounts for three basis points of it and the cycles run at forty.

### 11.4 What is not claimed

The stage does not claim a profit, does not claim anything about stratification,
and does not claim its own retrieval. §9 states all three and none of them is
softened by the numbers above.

### 11.5 The remaining four, and the stage is complete

**All seven registered criteria are implemented and pass.**

| | |
|---|---|
| **B3-2** trivial cycle | `\|z(i,i)\| = 0.0e+00`, taken off the diagonal of the same difference matrix every other number comes from, not short-circuited on `i == j` |
| **B3-6** sign stable across maturities | ranked on `5y`, tested on the other eight; **nine of the top ten pairs agree on 8/8** and the tenth on 7/8, against a threshold of five |
| **B3-8** CNH against CNY | rms `z` from `66.2` to `169.0` bp over seven tenors, against a floor of `4` to `30` bp; ratios `6.7` to `1198` |
| rank version | `√Z` on within-date ranks runs `3.01` to `4.04` across tenors and is non-zero wherever the banded version is |

**B3-6's selection axis is disjoint from its test axis.** Pairs are ranked by
`|mean z|` at one tenor and the sign is checked on the other eight. Ranking and
testing on the same numbers would make part of the agreement a property of the
selection rather than of the data.

The pairs that come out largest are worth naming because they are not arbitrary:
`JPY/NZD`, `AUD/JPY`, `JPY/SEK`, `JPY/NOK`, `CAD/JPY`, `GBP/JPY` — **the yen is
on one side of six of the top ten**, and the Swiss franc and Danish krone
account for two more. Those are the currencies whose hedged-dollar funding is
most persistently dear or cheap, and the sign holds across every maturity from
`3m` to `30y`.

### 11.6 CNH against CNY is the sharpest reading in the stage

One sovereign, one bond market, one default risk, **two currency codes**. The
cycle carries **no default-risk component by construction**; what is left is the
capital account.

| tenor | rms `z` (bp) | floor (bp) | ratio |
|---|---|---|---|
| 3m | **169.0** | — | — |
| 1y | 137.1 | 3.96 | 1198 |
| 2y | 113.0 | 10.58 | 114 |
| 3y | 100.2 | 5.32 | 355 |
| 5y | 81.8 | 9.66 | 72 |
| 7y | 66.2 | 20.05 | 11 |
| 10y | 78.4 | 30.21 | 6.7 |

Three thousand cells per tenor. **The obstruction is largest at the short end
and decays with maturity**, which is the shape a binding capital account
produces: the constraint bites hardest where the money would move fastest.

This is the source manuscript's Volume II §2 "hole" in its most literal
available form —

> 洞不是「价格太高」或「供不应求」……洞是在价格系统之外的障碍：**无论价格多高，你都无法进入该通道**。
>
> *A hole is not "the price is too high" or "supply falls short of demand". A
> hole is an obstruction outside the price system: **however high the price, you
> cannot enter that channel**.*

— because no price converts an onshore renminbi position into an offshore one.
The two codes price hedged dollar funding one to two percentage points apart and
the gap is not an arbitrage anyone can take.

**It is one country and it is registered as one test, not as the headline.** The
G10 result stands on its own and does not lean on this; B3-8 is what the
framework's own vocabulary predicts should exist somewhere, found where the data
happened to make it visible.
