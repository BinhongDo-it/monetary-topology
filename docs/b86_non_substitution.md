# B86: the non-substitution theorem, or demand cannot move this field

**RUN: 2026-09-13. Statement and proof below. Checks in
`experiments/b86_non_substitution.py`, record `results/b86_non_substitution.json`,
which carries the configuration it ran under. Paper station: zero data.**

## 0. The question this station answers

[`b85_simultaneous.md`](b85_simultaneous.md) holds the real wage basket fixed and
reads the rate of profit: a cheaper column raises it. **Hold the rate fixed and read
the prices instead, and the same Perron monotonicity gives a different classical
theorem.**

```
B85   basket fixed, rate read      a cheaper column raises r
B86   rate fixed, prices read      a cheaper column lowers every price
```

The second is the non-substitution theorem of Samuelson, Georgescu-Roegen and Arrow,
in Koopmans's 1951 volume: with one primary factor, no joint production and constant
returns, the cost-minimising technique and therefore the entire price field depend on
the rate and the available methods only, **and not on the composition of final
demand**.

## 1. Setup

`n` goods. For each good `j` a finite set of methods, each a column `(a_j, l_j)` with
`a_j ≥ 0` produced inputs and `l_j > 0` labour, each producing that one good. A
**technique** `T` picks one method per good, giving `(A_T, l_T)`. With labour as
numéraire and the rate `r`,

```
p_T(r) = l_T [ I − (1 + r) A_T ]^{-1}
```

wherever `λ_PF((1+r)A_T) < 1`. Final demand `d` enters nowhere in that expression.

## 2. Theorem 30

**(1) The price expression has no demand in it.** True by inspection, and it is not
the theorem. It leaves open which technique is in use, and that is what a demand
vector could in principle decide.

**(2) The componentwise minimum over techniques is attained by a single technique.**
This is the substantive half, and **it is what makes "the cheapest technique"
definable without naming a demand vector at all**: without it one would have to say
cheapest for whom, and the answer would be a function of what is being bought.

**(3) Hence the technique and the field are demand-free, and demand moves only the
quantity side**, `x = [I − A_{T*}]^{-1} d`.

**(4) Cohomologically: demand cannot create or destroy an obstruction.** Every square,
`rho` and `b₁` are functions of the field, which is a function of `(methods, r)`. **A
theory in which relative prices respond to demand has to break one of the three
hypotheses**, and this station measures what happens when two of them go.

**(5) It is the same monotonicity as B85.** Improving one column weakly lowers every
price at fixed `r`, exactly as it weakly raises `r` at fixed basket. **Two classical
theorems, one monotonicity, two different things held fixed.**

## 3. What the checks read

**Seven criteria, all passing** at `--seed 86 --systems 60`: 240 (system, rate) pairs,
5,512 techniques enumerated, under a second.

| | criterion | reading |
|---|---|---|
| `B86-1` `known_answer` | a hand-checked case | one good: `l/(1−(1+r)a) = 1.2820512821`, solver `1.2820512821`. Two goods, two methods each, built so the cheaper method for the first good carries more labour and less input and cannot be read off either column alone |
| `B86-2` `own_reading` | **the componentwise minimum is attained** | by a single technique on `240 / 240` systems |
| `B86-3` `own_reading` | demand moves quantities, not the field | over `1200` demand pairs the field moves by `0.00e+00` **while the quantity vector moves by at least `0.1576`**. Both halves required |
| `B86-4` `own_reading` | **a second primary factor breaks it** | the cost-minimising technique changes on `53 / 60` drawn method sets when a second factor is repriced. **The same search with one primary factor changes on `0 / 60`** |
| `B86-5` `own_reading` | **joint production breaks it** | the componentwise minimum is attained by no technique on `180 / 199` viable systems |
| `B86-6` `instrument` | the enumeration is complete | the technique count equals the product of the per-good method counts on `240 / 240` |
| `B86-7` `bookkeeping` | the pair with B85 | written into B85's own file, so a reader of either finds the other |

**The two failure modes are measured, not asserted, and each carries its control.**
`B86-4`'s control is the one-factor search, which switches `0` times against the
two-factor search's `53`: a search that switched under one factor too would be
finding its own noise rather than the failure of a hypothesis. `B86-5` had to find
its cases and would have recorded "not found on this family" rather than "does not
exist".

**Why joint production breaks it is already proved elsewhere.** [`b70`](b70_joint_production.md)
showed that under joint production the cycles and the commodities part company. With
more than one good per method there is no lattice of columns for the monotonicity of
Theorem 30(2) to run on, so this failure is derived rather than newly assumed.

## 4. Placement

**A.** The theorem, its three hypotheses and both classical failure modes are
Samuelson's, Georgescu-Roegen's and Arrow's.

**D.** That it is the same Perron monotonicity as Okishio's theorem with a different
thing held fixed; that its content is the attainment of a componentwise minimum
rather than the absence of a demand term; and **that its consequence in this framework
is cohomological: no square, no `rho`, no first Betti number responds to demand**.
The last has no analogue in an account of the theorem that has no field in it.

**C is empty and this station cannot produce it**: it reads no data.

## 4a. What the two-factor failure looks like on the graph

Registered here as "a second primary factor is a second potential, so the field stops
being one function", and **that guess is wrong**. Done on 2026-09-13 at
[`b87_demand_grip.md`](b87_demand_grip.md), Theorem 31, using B72's machinery:

- **The second factor's price is not a free dimension.** B72's Theorem 17(3) pins the
  wage to the lower envelope of the lands' own wage curves, because rents have to be
  non-negative. The field is still one function of the cultivated set.
- **What demand fixes is which lands are in use**, a combinatorial object. So demand's
  action on the field is a step function with at most `k` values, constant between
  thresholds and jumping at them, rather than a continuum.
- **`b1` rises by exactly one per extensive step**, which is Theorem 30(4) reversed:
  with one primary factor demand can neither create nor destroy an obstruction, and
  with a scarce second factor it moves the dimension, one method at a time.
- **The intensive margin costs two.** Once every land is in use the next step puts a
  second method on the best land, which then stops being a pendant vertex and closes
  a cycle, so the count rises by two in one step. **Intensive rent arrives as a step
  of the demand sweep rather than as a separate model**, and the transition is
  visible as a `+2` in a single running count.

## The continuum registration, answered 2026-09-13

"Whether the componentwise minimum survives a continuum of methods per good" is done at
[`b93_continuum_second_pass.md`](b93_continuum_second_pass.md), together with B77's continuum on
the other index.

**It survives exactly when the per-good minimum is attained, and Theorem 30(2) is indifferent to
cardinality.** The argument here is per good, so a continuum changes nothing as long as each
good's cheapest method exists: choosing independently still gives one technique, and 8,000 drawn
techniques beat it in no component.

**When it fails, it fails by the infimum escaping and not by two goods wanting different
techniques.** On a closed method set the minimiser settles to an interior point as the grid is
refined a hundredfold; on a half-open set whose cost falls toward the excluded end it sits at the
end point at every refinement and marches toward it while the cost keeps falling. **That is what
non-attainment looks like on a grid: a minimiser with no limit in the set.**

## 5. Scope

Single-product methods except where `B86-5` deliberately breaks that, one primary
factor except where `B86-4` deliberately breaks that, constant returns throughout.
The counts in section 3 are properties of the generator, not of any economy.
**Theorem 30(1) to (5) are algebra and are not.** Nothing here says which technique
an economy uses or which demand it faces.
