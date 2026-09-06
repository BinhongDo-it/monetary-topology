# B0d: the New Keynesian family, and the one place it and this framework disagree

Companion to [`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md),
which asks the same question of Domar-weighted aggregation. **This document runs no
measurement of its own.** Everything empirical in it is a pointer to a criterion in
[RESULTS.md](../RESULTS.md) or to a published record in the empirical arm.

Theorem 1 in [`b1_theorem.md`](b1_theorem.md) gives an exact criterion for when a single
scalar price vector on positions exists. This document asks:

> **Which New Keynesian constructs presuppose that object, has the current frontier
> removed the presupposition, and if not, what is the structural reason it cannot.**

The method is B0b's: **quote the setups, not the proofs.** A row that cannot be answered
by quotation is deleted rather than softened.

---

## 1. The disagreement is one line long

**Every member of the New Keynesian family has `H¹ = 0` identically, by construction.**

### 1.1 The index-set argument

The primitive here is a field on edges. For an agent class `a` and a transition from
position `i` to position `j`,

```
w_a(i, j)  =  log of the rate at which class a can convert i into j
```

Every New Keynesian model, in every variant, writes down a scalar on positions, `p_i(t)`,
together with one intertemporal rate common to all agents. Its edge field is therefore

```
w(i, j)  =  φ(j) − φ(i),        φ(i) = log p_i
```

The same expression for **every** agent. That is the image of `d: C⁰(G) → C¹(G)`, and an
exact form sums to zero on every cycle as an arithmetic identity rather than as a model
prediction. So:

> **For any New Keynesian model, any friction specification, and any shock process,
> `∮ω ≡ 0`.**

**This is Corollary 5.5 of [`b1_theorem.md`](b1_theorem.md)**, added 2026-08-29, whose
proof is one line: the hypothesis is Theorem 1's condition (4) written out, since each
`w_a` is exact because it is a coboundary and all the `w_a` coincide because none of them
carries the index `a`.

The non-zero readings on seven carriers are therefore not evidence that some model fits
badly. They are direct readings of a quantity this account predicts to be **exactly zero**.
That form of disagreement does not require anyone to concede a fit.

### 1.2 The staggered-pricing reply, and three answers

**The reply.** New Keynesian models do carry price dispersion. Under Calvo pricing, firms
reset at different dates, so a cross-section of prices exists at every instant, and B2's
within-cell dispersion is not a counterexample.

**First, the index is on the wrong side.** Calvo dispersion is dispersion across *sellers*:
firm `i` and firm `i'` post different prices. Every buyer faces the same `p_i(t)`. B2
measures dispersion across *buyers* inside one cell: fix census tract, year, lien position,
loan purpose, occupancy and dwelling type, and over 1,103,962 cells and 20,071,740 loans
**78 per cent of the variance in financing terms is still inside those cells**
(`0.7831`; `0.8480` on cells of at least twenty loans, 328,902 cells and 16,177,088 loans).
A single price per position has no slot for the buyer index.

**Second, conditioning should remove it.** Calvo dispersion is a function of time since
last reset, so conditioning on that variable should exhaust it. B2 loop B fixes the
dwelling and varies the entry vintage, which is that design, and the reading survives.

**Third, and this one settles it.** Make Calvo dispersion as large as you like: `p_i` is
still a single-index object, `w = dφ` is still exact, and the cycle sum is still zero.
**Nominal rigidity cannot buy non-integrability.** What it buys is slower dynamics for `φ`.
[`b1_theorem.md`](b1_theorem.md) section 14.5 states the domain fact directly: on a
single-index price field the integrability question dissolves, and it is a real question
exactly for a genuinely two-index field.

### 1.3 Why this shape of disagreement is worth keeping

It needs one inequality on one cycle, which is what
[`b0_claim_scope.md`](b0_claim_scope.md) fixes. It needs no utility function, no
interpersonal comparison, and no claim that the number is large. Anyone rejecting it has to
attack the measurement. The alternative route, arguing that some model fits badly, is an
argument about proxy variables, and on that ground the opposing side has as many free
parameters as it needs.

---

## 2. What the frontier is, in 2026

Ordered by distance from this framework rather than by influence.

### 2.1 Medium-scale DSGE

The workhorse at central banks. A 2025 ECB survey of medium-sized New Keynesian DSGE
models gives the current configuration: seven structural shocks (total factor productivity,
risk premium, exogenous demand, investment-specific technology, monetary policy, price
mark-up, wage mark-up), Bayesian estimation.

Its own statements of limit:

- inflation is "mostly driven by price and wage mark-up shocks", and those mark-up shocks
  "often stand in for other supply and cost-push shocks";
- the baseline "does not directly include features that are commonly regarded as key" to
  recent inflation;
- 2021 to 2023 "is mostly attributed to repeated and persistent cost-push shocks", read as
  "adverse shocks ('bad luck') rather than bad monetary policy";
- the extended model's inflation forecast improves when "having access to the oil price
  data as conditioning information";
- "Some of the parameters in the model that are weakly identified are kept fixed
  throughout the estimation procedure".

### 2.2 Heterogeneous-agent New Keynesian models, and the sequence space

The standard configuration after Kaplan, Moll and Violante, with the sequence-space
Jacobian as the general solution method and the 2025 Annual Review of Auclert, Rognlie and
Straub as the current authoritative statement. Its central object is the intertemporal
Keynesian cross,

```
dY  =  M(dY − dT)  +  dG
```

and its transmission decomposition puts the direct interest-rate effect at "small and
mixed-signed" against a labour income effect "large on impact", concluding that "indirect
effects substantially outweigh direct effects of monetary shocks".

**That conclusion runs toward this framework rather than away from it.** It moves the bulk
of transmission off the Euler equation and onto an income-expenditure loop. Stage A16 here
carries the same mechanism, put on a graph with an absorbing threshold rather than on an
aggregate, and derives a cascade with no balance-sheet linkage and no input dependence at
all.

Its own statements of limit:

- "A mutual fund collects all household savings and invests in government bonds and the
  stock market", delivering **the same** ex-post return `r^p_t` to every household;
- "The distribution at every date only depends on" two time-varying aggregates, ex-post
  returns and the post-tax labour income sequence;
- optimal policy "has not yet reached a comparable level of maturity", and "an unrestricted
  HA model typically lacks a well-defined Ramsey steady state";
- the forward-guidance resolution requires "procyclical income risk", which introduces
  "indeterminacy of equilibria".

A 2024 Federal Reserve working paper in the same literature states the return assumption
more plainly still: "every agent expects (demands) that Rb = Rs".

#### 2.2.1 A measured reading against that state space

The argument in section 4.2 is abstract, and this record contains a measurement of it.

A heterogeneous-agent state is liquid assets, illiquid assets and productivity, and the
price of credit is a function of that state. **What B2's registered placebo reads is a
different object: which price function a household faces at all, selected by an edge that
state does not contain.** Conventional mortgage pricing runs off a published grid in credit
score and loan-to-value. The VA funding fee does not vary with credit score, and VA
eligibility is decided by service history.

The reading, criterion P1: **`within_share(conventional) = 0.8480` against
`within_share(VA) = 0.6666`, a gap of `+0.1814` against a registered margin of `0.05`.**
The premise that carries the placebo was measured rather than argued: the VA pool is
**97.7 per cent as wide as the conventional pool at fixed position**, and wider than FHA
([`b2_placebo_pool_width.md`](b2_placebo_pool_width.md)).

**Four limits travel with that number, and a citation without them is a misreading.**

1. **Caliber disagreement, reported rather than chosen.** The pool-width premise survives
   on the tail-insensitive (ranked) caliber and does not survive on the log caliber, at
   5, 20 and 50 alike in both directions. The placebo-validation station records this as a
   disagreement, six criteria of nine. Any claim of this kind carries "on the
   tail-insensitive caliber".
2. **B2 fixes position, date and contract type, not a wealth state.** The reported data
   carry income and no wealth. So the claim is about **which price function is selected**,
   and not about dispersion at equal wealth. Those are far apart and must not be merged.
3. **The estimate is a lower bound.** An all-cash buyer generates no record and faces no
   financing terms at all, which is the extreme point of the loop being measured, so every
   one of them is a missing observation on the favourable side. The bias runs against the
   reading.
4. **The FHA half is conceded.** Per unit of pool width, FHA rate dispersion is larger than
   conventional, so FHA's low within share is mostly a narrow pool. **Only the conventional
   against VA comparison is load-bearing**; FHA supplies the gradient shape.

**The target was named after the result was known, and that is recorded rather than
smoothed.** B2's design was pinned before any data was retrieved, and it was aimed at
non-integrability. Asking what else that result refutes is explanation and not prediction,
and this record's own accounting rule requires the distinction to be printed.

**The two replies available both carry information.** Saying the gap does not matter
requires an account of `0.1814` at fixed position. Saying "then put programme eligibility
into the state" is putting a graph position index into the state space, which is the layer
this framework says is missing, and the thing to be added is not abstract access but a
named eligibility edge.

**The reply this reading does not answer** is the narrower one, that the state is claimed
sufficient for *aggregate* transmission rather than for every price. That is answered only
by an increment test, and section 2.4.2 is where this record ran one.

#### 2.2.2 That narrower reply was then tested directly, and it survived

**The increment test was run against this literature's own sufficient statistic, and the
graph-layer statistic showed no increment. That is recorded here rather than left out.**

The test gives the rival its statistic **as the rival states it**: not a distribution of
marginal propensities, which no source publishes as a country-year panel, but the two
time-varying aggregates its own authoritative statement names, the ex-post portfolio return
and the post-tax labour income sequence. On an annual panel those are available: labour
income as the labour share times output per head, and the portfolio return as the source
database's own published aggregate, so its weights are not this record's choice. The
baseline carries them at three lags together with the instrument and the revaluation term
the model itself specifies, and the outcome is real consumption per head, which is what the
rival's own transmission decomposition computes.

**Station F25 in the empirical arm, twelve cells, all reported.** The main arm was fixed
before the run as the standard shape on the seam-cleaned panel: `Δ = −0.007361`, permutation
`p = 0.337` against `α = 0.10`, at 2,000 draws. **The reading lands inside the null-information distribution
and closes on the spot without a verdict.** One cell of twelve is positive and it does not
clear `α` either, and it sits at the intersection of the two weak configurations already
known on this data.

**Two readings are barred and both matter.** Not that the graph-layer statistic carries
incremental content for aggregate transmission. **And not that it has been shown to carry
none**: a null-information baseline reports indistinguishability, not absence.

**What this fixes is the map rather than the score.** The measured advantage over this
literature sits where section 2.2.1 puts it, on **which price function a household faces at
all**, and it does not sit on aggregate transmission. That division is not a surprise
imposed by the result: the station that produced the 2.2.1 reading wrote in advance that it
could not answer the aggregate-transmission reply and handed that question to a separate
test. **The separate test ran, and this is what it returned.**

**One limit travels with F25.** The instrument is an instrument and not a structural shock,
so the table is a reduced-form reading; the portfolio return is a national wealth aggregate
rather than a household one; and the labour income series is pre-tax, because no
cross-country annual post-tax series exists to use instead.

### 2.3 Behavioural and bounded-rationality variants

Behavioural New Keynesian models, level-k thinking, incomplete-information formulations,
and behavioural HANK. The common move is to discount the expectation operator applied to
`φ`, which removes the explosive forward-guidance response.

A separate route argues the forward guidance puzzle comes from an unrealistic policy
assumption: the central bank "commits not only to a future interest rate shock but also to
not responding to the joint evolution of inflation and output" in the interim. Under a
standard rule, a distant rate cut moves less than a current one. The same authors record
that the standard model delivers "a 7 percent jump in the output gap and a 3 percent jump
in inflation" from forward guidance in a Great Recession setting, which they treat as
implausible.

### 2.4 Production-network New Keynesian models

**This is the branch nearest to this framework, and it is also the one B0b already
answers.**

Optimal monetary policy in production networks, and the networks-and-Phillips-curves
result: sectoral and aggregate Phillips curve slopes fall with intermediate input shares,
and productivity fluctuations generate an inflation-output tradeoff "except when inflation
is measured according to the novel divine coincidence index", an index that "provides a
better fit in Phillips curve regressions than consumer prices".

**The adjacency matrix is now inside the model.** The ECB survey concedes the same in the
other direction, that a single-sector setup "is not very suited for capturing such network
effects" and that "a richer supply side with a non-trivial input/output structure is
necessary".

**What the branch rests on is an envelope argument, and an envelope needs a function to
envelope.** [`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md)
section 2 treats this in full: Hulten's price vector is *defined as* the normalised
gradient of a social production possibility frontier, `P = ∇F / (∂F/∂Y_1)`; the wedges in
the misallocation literature carry the index `τ_ij`, an **edge** index; and pricing is
stated as "producer i sets a price pi = µiCi/Ai", one price per producer, common to every
purchaser. **Generality on the edge index does not produce an agent index.**

#### 2.4.1 The four questions, put to that branch

[`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md) section 6
states the push against its own section 2.3 in executable form: four questions, to be
answered by quoting setups rather than by characterising a literature. Below they are put
to the two papers that place the adjacency matrix at the centre. The misallocation
framework's answers are already quoted in B0b section 2.3.

| question | optimal policy in production networks | networks and Phillips curves |
|---|---|---|
| one producer per node, or heterogeneous producers inside it? | "Each industry consists of two types of firms: (i) a unit mass of monopolistically-competitive firms, indexed by k ∈ [0, 1], producing differentiated goods" | "Within each sector there is a continuum of firms, producing differentiated varieties." |
| does every buyer of a given good face the same price? | yes. "pik is the nominal price charged by the firm", one price per firm, common to its buyers | yes. Firms set `pi`, and buyers face the sectoral index built from those prices |
| what index set do the wedges carry? | industry. "τi is an industry-specific revenue tax (or subsidy) levied by the government" | sector. "τi is an input subsidy provided by the government", with markup "μ*i = εi/(εi−1)" |
| are households heterogeneous, and if so do they face different terms? | no. "the economy consists of a representative household as well as a government" | no. A representative consumer, a uniform wage, and sectoral price indices |

**The heterogeneity in both is on the seller side and inside the node**, which is the first
branch of B0b section 2.3 rather than an answer to it. A continuum of firms indexed by `k`
still posts one price per variety to every buyer of that variety, so the field stays inside
`C⁰(G)` and Corollary 5.5 applies to both unchanged.

**This is the branch's strongest position, and it is worth putting that way rather than
weaker.** These are the two papers that make the network the object, so if an agent index
were going to appear anywhere in this literature it would appear here. The four questions
are answered by quotation, and it does not appear.

#### 2.4.2 The measurable form of the disagreement was run, and what it returned

**On this branch the argument above is theory against theory, and the record contains the
one form of it that can be measured.** The test is the increment test: put the rival's own
sufficient statistic into the equation and read whether a claims-graph statistic retains
out-of-sample increment. Renaming a friction produces no increment, which is what makes the
test worth running.

**The design gate passed.** On OECD inter-country input-output domestic blocks, 868
country-years over 31 countries, 1995 to 2022, the Domar block and the shape block separate:
condition numbers 3.6 and 3.6 alone and **5.3 combined**, against an inherited threshold of
100, with no new threshold introduced. Given the Domar block, the shape variables retain
`0.7093`, `0.6772` and `0.6466` of their variation.

**The main arm was pinned before the run and it closed without a verdict.** The outcome is
the growth of total factor productivity at constant national prices, which is the literal
object of the aggregation theorem rather than a convenient substitute. With the country-years
ruled to be compilation seams removed, `n = 795`: measured `Δ = 0.001618`, permutation
`p = 0.1360` against `α = 0.10`, **inside the null-information distribution**, closed on the
spot under the register's own rule. The full-sample arms read `p = 0.0364` and `p = 0.0776`,
and what separates them is 73 country-years, 8.4 per cent, that a prior station ruled to be
seams in the table's compilation rather than economic events.

**Neither direction may be written.** Not that the claims-graph shape carries incremental
predictive power for aggregate productivity, and **not that it has been shown not to**: a
null-information baseline reports indistinguishability, not absence. The parallel outcome
variables were deliberately not run, because the main outcome is the only one with a
theoretical source and continuing on outcomes without one is a search.

**One further route on this branch is closed separately.** A reading that turns on the
difference between an existing edge and a vanishing one does not survive on published
input-output tables, whose average out-degree runs from tens to over a hundred, so that
instrument returns a density reading.

**So the live front here is the theory**, which is section 2.4 above together with B0b
section 2, and the record says so rather than implying open empirical ground.


### 2.5 Fiscal theory and equilibrium selection

The fiscal theory of the price level, and a 2025 argument that in the standard model "the
entire force for disinflation is an equilibrium selection jump unrelated to higher interest
rates", so that a Taylor rule conceals an equilibrium selection assumption and one interest
rate path is consistent with different inflation outcomes.

**Nothing here needs to argue this branch.** It is an internal criticism of New Keynesian
determinacy conducted in New Keynesian equations.

### 2.6 Non-linearity and supply constraints

The patches added after 2021: a non-linear Phillips curve, the vacancy-to-unemployment
ratio in place of the unemployment gap, and a steepening slope at capacity. The ECB survey
records that "important nonlinearities such as a steepening of the Phillips curve when
capacity and other supply constraints are reached" remain hard to carry in a linearised
model. An external critique counts the evidence for the steepening at ten quarterly
observations.

---

## 3. Which of the standing problems the frontier closed

| problem | what the frontier does | closed | structural reason |
|---|---|---|---|
| the Euler equation carries all transmission, and micro consumption data do not support it | the intertemporal Keynesian cross, income effects dominant | **mechanically, yes** | every household still faces one `r^p_t`; the field is untouched |
| the forward guidance puzzle | behavioural discounting, bounded depth, procyclical income risk, or a change of policy rule | **no** | the HANK route brings indeterminacy by its authors' own statement; the policy-rule route relocates the assumption |
| the flat or absent Phillips curve | non-linear curve, vacancy ratio, network Phillips curve, mark-up shocks | **no** | mark-up shocks "stand in for" other things; the non-linear segment rests on ten observations |
| latent proxies: output gap, `r*`, natural rate, productivity residual | a time-varying `r*` added explicitly | **worse** | the ECB's own real `r*` range is −½ to +½ per cent, and it records that "the usefulness of r* as an indicator to support the calibration of the monetary policy stance is greatly limited" |
| where determinacy comes from | fiscal theory, equilibrium selection | **no** | the disinflation force is the selection jump |
| single sector, no network | production-network models | **partly** | the adjacency matrix arrives; one price per node remains, and aggregation still runs on an envelope |
| no heterogeneity | HANK | **in the state only** | see section 4 |
| identification | Bayesian estimation | **no** | weakly identified parameters are held fixed |

---

## 4. The family invariant

This is the one proposition in this document that has to be argued rather than pointed at.

### 4.1 Statement

Write `Γ = G □ H` for the product of the position graph with the agent-class graph. The
object here is a field `w_a(i, j)` on `C¹(Γ)`. Every member of the New Keynesian family
sits inside

```
{ ω ∈ C¹(Γ)  :  ω = dφ,  φ ∈ C⁰(G),  φ constant along H }
```

Thirty years of development land in three places, and none of them changes that inclusion:

1. **the time dynamics of `φ`**: staggered contracts, quadratic adjustment, indexation,
   information frictions, behavioural discounting;
2. **a measure laid over `φ`**: the household distribution as a state variable;
3. **edges added to the position graph `G`**: the input-output structure.

Only the third touches a graph, and the graph it touches is `G`, not `H` and not `Γ`.

### 4.2 Portfolio heterogeneity is not field heterogeneity

The literature on heterogeneous returns is the nearest thing to a counterexample. If agent
`a` earns

```
r_a  =  Σ_k θ_ak r_k
```

then every agent still faces the same `r_k`, and every square in `Γ` still closes. **The
heterogeneity lives in the portfolio weights, which are a quantity index.** A square fails
only when `a` and `b` face different terms on the **same** transition, which is what
Corollary 1 of Theorem 1 decides with a single edge.

No member of the frontier crosses that line. HANK's sufficient statistic is two aggregates,
and its dimension does not grow with the number of agent classes. That is a direct answer
to the fourth of the four questions
[`b0b_aggregation_and_the_potential.md`](b0b_aggregation_and_the_potential.md) section 6
puts in executable form, and the answer is that it does not grow, so the second branch of
that document's section 2.3 table stays shut.

### 4.3 Consequence

> **They change `φ`. The quantity measured here is `ω − dφ`.**

That also explains the absence of any real exchange between the two: these are not two
estimates of one quantity. They are two objects, one of which is identically zero in the
other's representable class.

---

## 5. New Keynesian models as a special case

### 5.1 Statement

Impose three restrictions on the framework:

1. **single index**: `w` depends on the position pair only, and is constant along `H`;
2. **exactness**: `ω = dφ`, equivalently every cycle in `Γ` sums to zero, equivalently
   `H¹(Γ) = 0`;
3. **heterogeneity enters the measure, not the field.**

Under these, every statement here degenerates to the corresponding New Keynesian statement,
across the representative-agent, two-agent, heterogeneous-agent, behavioural,
production-network and fiscal-theory variants. **None of them has to be contradicted.**

**The algebra of this is Corollary 5.5 in [`b1_theorem.md`](b1_theorem.md), and it sits
under Corollary 5.4.** Corollary 5.4 identifies the locus on which the enlarged object *is*
the single-price account rather than merely agreeing with it. Corollary 5.5 names the family
that occupies the locus and reads off the consequence, `∮ω = 0` on every cycle identically.
**The containment framing is the stronger of the two available and it is the one this record
takes**, for the reason Corollary 1's reduction paragraph gives: it obliges this account to
be right everywhere the older one is right, by identity, and it can be broken by a single
case where the single price vector is right and this framework is not.

### 5.2 Readings already on file

**On the theorem side**, [`b1_theorem.md`](b1_theorem.md) section 14.5 fixes the domain:
on a single-index price field the question dissolves, and the classical statements are
about exactly that field.

**On the measurement side**, stage A3k is the same limit exhibited inside a model.
`tier_positions` is a star, so `b_1(G) = 0`, so by Theorem 2 every obstruction on that
carrier is a square and an admission threshold is outside the cochain by construction. Its
holonomy share is required to vanish with no constant chosen by anyone. Read off 57 pooled
points: the gate channel is same-sign across seeds at **0** against the terms channel's
**9**; on the eight grid values where A3j measures the gate as mechanically active, at 49
to 107 per cent of the terms channel's work, terms is positive at 8 of 8 with no sign
change and the gate at 4 of 8 with two.

**A third reading, added 2026-09-03, and it is a different kind from the first two.**
Those recover the older account where its **structure** holds: a single index, or a star
carrier whose first Betti number is zero. Stage A26 recovers it where its **behavioural
premise** holds. The premise in question is that arbitrage removes persistent differences,
and the stage grants it as a knob: terms that worsen as flow arrives, swept from zero
upward. The older account predicts no persistent disuse. With the knob off, 36.7 per cent
of routing edges go unreached; with it strong enough, sixteen seeds of twenty read exactly
zero and the older account's prediction is exact. **The boundary is closed form rather than
found by search**: the key multiplies a position factor spanning `[1, 1+k]` by a congestion
factor spanning `[1, 1+e s]`, so the second covers the first when `e s_head > k`, and that
is where the recovery happens. Outside it the prediction is wrong by 20 to 37 points, and
on the side where terms improve rather than worsen with load, which is the sign this
stage's own correspondence carries, it is wrong by the whole 36.7.

**What this adds to the containment claim.** Corollary 5.5 gives the containment by
identity on the theorem side, and A3k exhibits the same limit inside a model. This one
locates a rival's corner in the parameters of a mechanism rather than in the algebra, and
prints the boundary. It is weaker than an identity and it covers something an identity
cannot: a premise about behaviour rather than a restriction on the field.

**On the control side**, stage A22 forces the field exact on A3's live carrier and reports
which readings go with it. The terms differential is set to zero, which is the only value at
which that carrier's field is a gradient, with the mean acquisition cost and the admission
threshold both held at their registered values so that the treatment moves what is paid and
not who may enter. Across five seeds the holonomy goes to exactly zero while the support-set
contraction survives: **74.43 points of contraction under the registered field against 73.44
under the exact one**, so the field carries **1.33 per cent** of it and the graph carries the
rest. Volume rises while support falls in five seeds of five on both arms.

**The half that could have failed is the second one.** The zero is an identity: at zero
dispersion the cycle is a difference of two equal terms, and the treated square is degenerate
outright, so nothing is claimed from it. The support-set half could have gone either way, and
the two arms are separate runs rather than one run read twice, which the opening support
settles at 56.605 against 53.889 on the first seed.

**A3k is the weakest of this record's three zero domains and is reported as such**: it is a
model agreeing with its own theorem, which is a different object from B13's 81,968 states
of a derived book against a quoted one, or B6's arithmetic identity in a published table.
What it does show is that when the topology is trivial the framework's own quantity goes to
zero and the standard reading is recovered.

### 5.3 What the embedding buys, and what it costs

**Buys.** No argument about frictions has to be won, because frictions are dynamics of `φ`
and nothing here disputes them. Every empirical result of the New Keynesian literature
survives unchanged on the subspace. And the dispute moves from which model fits better to
whether the subspace is the world, which is decided by cycle sums against an exact zero.

**Costs.** The normative closure has to go. The quadratic loss function comes from a
second-order expansion of a representative household's utility around an efficient steady
state, which requires the allocation to be the argmax of something. That is B0b section
2.2's envelope argument again: with no potential there is no function to envelope, and the
loss function is not wrong but undefined. [`b0_claim_scope.md`](b0_claim_scope.md) already
fixes this record's normative position at issuing no welfare criterion, so the two are
consistent.

---

## 6. Where each side reads well

### 6.1 One cell already matched, on the other side's own ground

**F13, in the empirical arm.** Controlling for the standard credit benchmark, the five-year
cumulative asset-to-wage wedge enters crisis prediction at `a = +0.1697`, one-sided
country-block bootstrap `p = 0.017`, lifting AUC from **0.677 to 0.705**. The line worth
recording separately: **the wedge alone reaches AUC 0.676 against the credit benchmark's
0.677.** A quantity derived from the framework and constructed without reference to credit
matches the workhorse indicator by one part in a thousand, and broad money growth becomes
insignificant once the wedge is controlled (`p = 0.263`).

**That cell carries its own limits and they travel with it**: AUC 0.705 is moderate
discrimination in absolute terms and the gain of 0.027 is not large. What it supports is a
match on fewer proxies. It does not support a claim of better crisis prediction.

**F12b** is the same line upstream: across 18 countries and 881 country-years, 1970 to
2020, when broad money grows 10 percentage points faster than nominal GDP, nominal house
prices rise about 2.3 points faster than nominal wages (`γ = 0.2319`, `p = 0.002`; with
year fixed effects `γ = 0.1594`, `p = 0.031`). The known contamination in the treatment
variable pushes against the finding rather than for it.

### 6.2 Three things this record does not have

**Nominal price level dynamics.** The A track carries no nominal rigidity and the B track
reads no time series. Inflation persistence is a quantity the New Keynesian literature has
and this one does not. That cell is empty and is not to be written as a match.

**A time dimension in policy transmission.** Every quantity here is a property of a
configuration and nothing is dated forward, which is stated in the repository's scope note.
Impulse responses are not produced.

**Normative closure.** Section 5.3 gives the reason this is declined rather than missing. A
framework that issues no ranking over policies pays for that in the rooms where policy is
ranked, and the payment is deliberate.

The empirical arm scores itself against this framework's own four-part standard and reports
portability as FAIL and prediction as empty. Until the first of the three cells above is
filled, that line stands as written.

### 6.3 Where the representable class runs out

These are not places where a New Keynesian model fits badly. They are quantities its
representation has no slot for.

| carrier | reading |
|---|---|
| B2, mortgage origination terms | 78 per cent of variance retained inside cells over 20,071,740 loans; the registered placebo moves in the predicted direction by 130 times a gap known to be zero |
| B8, mortgage modification | the strongest of the seven: 49,649 modification loops and 35,659 deferral loops over 2,942,295 loans |
| B3, cross-currency funding | 30.9 to 45.6 basis points against a measurement floor of 2.8 to 3.7, on nine of nine tenors over eighteen years |
| B9, the ETF creation triangle | 1.2 to 1.7 basis points at 1.05 to 5.08 times the floor; tick size varies by 15.8 times across the sample while the loop sum varies by 1.42 |
| B5 and B17, Argentina's legal conversion tracks | squares 5 of 5 over 1,457 dates |
| B6 and B15, a central bank's own table | Cuba on 207 publication days, with Bolivia read at 21 of 52 under the same sealed register |
| B13, CME calendar spreads | the zero domain: 81,968 states with no violation, while the directly quoted member of the same family is non-zero in 65 to 96 per cent |
| B21, B23, B24, withholding and dual listings | 14.8 and 30.5 basis points a year over 4,226 leg-years, zero on none; 16.4 basis points median where the two listings can be exchanged, 196 times that where they cannot |

And on the structural side, inside the mechanism models:

- **A2.** With issuance, transaction volume rises 44.87 times while the support set
  contracts to 0.402 times and the production layer falls to 0.51 per cent of all
  circulation. Aggregate volume carries no information about who is reached, and aggregate
  demand has no notion of reach.
- **A2c.** Gross flow rises 97.1 times while net displacement stays flat within 1.62 times;
  realised cycle rank collapses to 0.029 of potential **with no edge deleted**, and one
  autonomous edge restores it to 0.783.
- **A4.** Switching on nothing but the access structure takes the Gini from `0.00711` to
  `0.93673`, sign holding at 5 of 5 seeds (A4-2). The four standard competitors acting
  alone move it by `+0.00007`, `+0.00932`, `+0.00080` and `−0.00006`. **Those four numbers
  belong to A4-3, which is registered as a FAIL** because all four fall under a floor of
  `0.02`: they record that the competitors were given too small a stage, and they are not
  citable as a defeat of the competitors. A4-2 is the citable criterion.
- **A6.** With retention already fair, the stratified graph needs a redistribution rate of
  `0.060` where the flat graph needs `0.000`, which is the cost of the structure stated in
  tax points.
- **A11 and A15.** As the subsistence floor rises the Gini falls from 0.934 to 0.715 while
  182 nodes leave circulation holding 39.5 per cent of the claims outstanding. An economy
  that has moved most of its population out of circulation reports a better Gini.
- **A7.** Adding 350 edges to 1,039 removes 98 per cent of the compounding divergence, and
  **21 of the 350 point downward** against a specification in which that count is zero. Any
  statement that the gap closes as connectivity rises needs that count beside it.

---

## 7. What is given up by refusing the proxies

| proxy | what it does there | why it is not used here |
|---|---|---|
| output gap | left side of the Phillips curve, second term of the loss function | no observable counterpart; without it there is no inflation equation here, which section 6.2 records |
| `r*`, the natural rate | the benchmark for policy stance | the range across models is −½ to +½ per cent, and its usefulness for calibrating stance is recorded as greatly limited by the institution that publishes it |
| price and wage mark-up shocks | the main attribution for 2021 to 2023 inflation | they are recorded as standing in for other shocks, so a residual is being named and then used as a mechanism |
| the productivity residual | supply-side driver | it needs Domar weights, and Domar weights need the potential, which is B0b section 2 |
| weakly identified parameters | held fixed | there is no likelihood here to hold anything fixed in |
| shock autocorrelations | carry persistence | the quantities here are configuration properties with no time-series degrees of freedom |

**One matched cell is not a class.** F13 is currently the only reading that clears the
other side's own ground with these six given up, and making that a class is the first thing
worth doing.

---

## 8. The one direct engagement on file

Station F16 in the empirical arm registered a New Keynesian directional prediction as a
named rival and ran it. **The two sides ended in different registered states, and they are
reported separately.**

The load-bearing quantity is `δm`, the monetary interaction in the decomposition arm.
`n = 881`, 18 countries, 5000 country-block bootstrap draws, `α = 0.10`. The reverse column
is the one-sided p for `δm < 0`, which is the rival's predicted direction.

| arm | `δm` | forward p | reverse p, the rival's direction | verdict |
|---|---|---|---|---|
| state version, no year effects (adjudicating) | **+0.2966** | 0.0202 | 0.9798 | **not adjudicable**, recorded as instrument in doubt, claim untested |
| state version, year effects (adjudicating) | +0.0210 | 0.4538 | 0.5462 | FAIL |
| deceleration version, no year effects (reported alongside) | −0.0306 | 0.5840 | 0.4160 | FAIL |
| deceleration version, year effects (reported alongside) | −0.0487 | 0.6196 | 0.3804 | FAIL |

**This side.** One arm brings the load-bearing quantity inside `α` and then fails on
separation from the pure-denominator placebo (`δ − δp = +0.0771`, `p = 0.2856`, with
`δp = +0.2998` significant on its own), and the jackknife shows it rests on the single year
2020, which flips it to `−0.0129` when dropped. The registered wording is **instrument in
doubt, claim untested**.

**The rival.** The directional prediction was tested four times and **brought the
load-bearing quantity inside `α` in none of them**, the closest being 0.3804. On both
adjudicating arms the point estimate carries the opposite sign.

**One is a statement about an instrument and the other is a statement about a prediction.
They are different states and are not to be collapsed into a symmetric one.**

**Two things this cell does not license, each for its own reason.** The opposite sign of
`+0.2966` is not a refutation of the rival, because the pure-denominator placebo is equally
significant and that positive sign is plausibly the mechanical path. And four unsupported
readings are not an exclusion of the rival, because the deceleration arms' registered
wording is "effect absent, or power insufficient", and the second clause is open to both
sides.

---

## 9. Where a critic should push

**Not at Theorem 1**, for B0b section 6's reason.

**The push specific to this document is at section 4.1.** Breaking it means producing a
member of this family whose price field takes different values for different agents on the
same transition, and whose sufficient statistic does not grow in dimension with the number
of agent classes. **Section 2.4.1 puts B0b section 6's four questions to the two papers
where such a member would most likely be found, and answers them by quotation.** The rest
of the literature has not been put through the same four questions, and a survey is not a
proof, so a nominated paper is a real push. The executable form is the same four questions
applied verbatim: do the producers inside one node face the same input price; what index set
does the wedge carry; are households heterogeneous in the terms they face rather than only
in their holdings; does the sufficient statistic's dimension grow with the number of agents.
**Quote the setup rather than characterising the literature**, which is the standard B0b
section 6 sets and the reason section 2.4.1 is a table of quotations.

**The second push is not at section 5.1's statement, which is a corollary with a one-line
proof, but at section 5.2's evidential weight.** A3k is a model agreeing with its own
theorem, and this record says so in its own scope note. What the corollary settles is the
algebra: an account of that form returns zero. What it does not settle is whether this
framework's own readings separate the way the corollary implies they must, into a part
carried by the field and a part carried by the graph. **The control arm that settles it is
cheap and can fail**: force `w = dφ` on a live carrier and report which readings go to zero
and which survive. The holonomy readings have to vanish and the support-set and
volume-against-reach readings have to survive, because the second pair are properties of the
graph rather than of the field. **If both vanish, the executable form of Corollary 5.5 is
refuted on this carrier.** **That arm has run**, and section 5.2 records what it returned: the holonomy goes to exactly
zero across five seeds while the support-set contraction survives, 74.43 points under the
registered field against 73.44 under the exact one. **It is one carrier**, whose position
graph is a star, so every obstruction on it is a square and it carries no slice cycles. A
carrier that does carry them is where the same question goes next.

---

## 10. Citation status

**Every quotation in sections 2 and 3 was taken from a retrieved copy and must be checked
against the version of record, with section or equation numbers attached, before it is
quoted in a manuscript.** This is B0b section 7's standard, and it applies to this document
at least as strongly.

Sources to be checked:

- Auclert, A., Rognlie, M., Straub, L., *Fiscal and Monetary Policy with Heterogeneous
  Agents*, Annual Review of Economics 17 (2025), 539-562, and its working-paper version.
- *HANK Comes of Age*, Board of Governors of the Federal Reserve System, Finance and
  Economics Discussion Series 2024-052.
- *Inflation and Monetary Policy in Medium-sized New Keynesian DSGE Models*, European
  Central Bank Working Paper 3137 (2025).
- European Central Bank Economic Bulletin 1/2025, box on natural rate estimates for the
  euro area.
- Cochrane, J. H., *New-Keynesian Inflation Control is Equilibrium Selection* (2025).
- Eggertsson, G., Schüle, C., *The Forward Guidance Puzzle is Not a Puzzle*, NBER working
  paper 33180.
- Rubbo, E., *Networks, Phillips Curves, and Monetary Policy*, Econometrica 91(4), 2023.
  **Section 2.4.1 quotes the June 2020 working-paper setup and the published setup must be
  substituted, with the equation numbers attached.**
- La'O, J., Tahbaz-Salehi, A., *Optimal Monetary Policy in Production Networks*.
  **Section 2.4.1 quotes the NBER working-paper setup, and the same substitution is
  required.**
- Storm, S., *The Art of Paradigm Maintenance*, INET working paper 214. A heterodox
  commentary, used here only to count patches and carrying no structural claim.

**Internal to this record and needing no external check**: B0, B0b, B1, B2, B3, B5, B6, B7,
B8, B9, B13, B15, B17, B21, B23, B24, A2, A2c, A3j, A3k, A4, A6, A7, A11, A15, A16, A22, and the
empirical arm's F12b, F13 and F16. Cite by criterion identifier, never by section number,
and citing a passing criterion without its scope limits is a misreading of it.
