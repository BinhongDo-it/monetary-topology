# B43: proposition (i) of the counting law, proved

**Status: proof, with the enumeration it was written against and a closed form
that reproduces that enumeration. Registered 2026-09-03. No empirical arm: this
station is paper.**

---

## 0. What was already known, and what is left

The counting law says that a published procedure shared by all parties draws a
partition on the set of positions, and that the number of values it produces
equals the number of distinct class terms it wrote. It rested on twenty-three
cases and had never been proved.

Before attempting the proof I enumerated. Every configuration on `n = 3, 4, 5`
positions was walked in full, with baselines and class terms each drawn from a
three-value set: 1,539 configurations, then 25,029, then 453,438. The record is
`results/b43_counting_enumerate.json`. Two things came back.

**First, the original statement was false as written.** It said the number of
values equals the number of *classes*, and that has 810, 18,468 and 394,389
counterexamples at the three sizes on the equality arm.

**Second, every counterexample has one shape.** Two classes carrying the same
number. Counterexamples of any other shape: zero, at every size, on all three
arms. Adding the words "distinct class terms" empties the counterexample set.

**So the enumeration did not leave a proof to be found from nothing. It left a
conjecture with its boundary already drawn**, and what a proof has to add is the
step from "no counterexample of any other shape was found up to `n = 5` on a
three-value domain" to "there is none, at any size, over any ordered set". That
is what follows.

This file does not restate the law in full. It proves proposition (i), and it
separates two statements that had been carried as one sentence.

---

## 1. Setup

`V` is a finite non-empty set of **positions**. A published procedure supplies

- a partition `P_written = {A_1, ..., A_k}` of `V` into **classes**,
- a **term** `t_a` in a totally ordered set `T` for each class `a`,

and each position carries a **baseline** `x_v` in `T`: the number it would take
with no procedure in force. Write `c(v)` for the index of the class containing
`v`, which is well defined because `P_written` is a partition.

The procedure produces a value at each position. Three rules:

| | rule | name |
|---|---|---|
| two-sided | `pi(v) = t_{c(v)}` | equality constraint |
| one-sided, lower | `pi(v) = max(x_v, t_{c(v)})` | floor |
| one-sided, upper | `pi(v) = min(x_v, t_{c(v)})` | cap |

`P_read` is the partition of `V` into the fibres of `pi`:

```
P_read = { pi^{-1}(y) : y in pi(V) }
```

This is a partition of `V` for any `pi`: the fibres are disjoint, they cover `V`,
and each is non-empty because `y` ranges over the image.

**Binding sets.** For the floor, `S_a = { v in A_a : x_v < t_a }` and
`S = union_a S_a`. For the cap, `S_a = { v in A_a : x_v > t_a }`. In both cases
`S_a` is the set of positions in class `a` at which the bound actually bites.

**Restriction.** For a partition `Q` of `V` and a subset `S`, write
`Q|_S = { B intersect S : B in Q, B intersect S non-empty }`, a partition of `S`.

### 1.1 One convention, and it is load-bearing

**A class is a block of a partition, so it is non-empty.** A tariff line that
appears in the text of a decree but has no position falling under it is not a
class in this sense.

This is not bookkeeping. It is the second way the counting law can fail in the
world, and it is worth naming: **a procedure that writes three distinct numbers
but has nobody in the third band produces two values, not three.** The law as
proved below counts classes that have members. Whether any of the twenty-three
registered cases writes an empty band is a question about the corpus and has not
been checked; it is registered at the end of this file.

The other known scope limit stands unchanged: **a band whose number is not
written at all** — Kazakhstan 1993, where the amount above the ceiling was
settled by a commission after the fact — is outside the law's premise, which says
*published*. Such a band is neither counted nor a counterexample.

---

## 2. Theorem 1 (two-sided): two statements, and only one of them needs a hypothesis

Throughout this section `pi(v) = t_{c(v)}`.

> **Theorem 1(a), counting form.** `|P_read| = |{ t_a : 1 <= a <= k }|`.
> **No hypothesis.**
>
> **Theorem 1(b), partition form.** `P_read = P_written` **if and only if**
> `a |-> t_a` is injective.

**Proof of 1(a).** Every class is non-empty, so every `t_a` is attained, and no
other value is: `pi(V) = { t_a : a }` as a set. The fibres of `pi` are indexed
bijectively by the elements of `pi(V)`, hence `|P_read| = |pi(V)|`, which is the
number of *distinct* terms. `[]`

**Proof of 1(b), sufficiency.** Suppose `a |-> t_a` is injective. Fix `a`. Every
`v in A_a` has `pi(v) = t_a`, so `A_a` is contained in `pi^{-1}(t_a)`. Conversely
let `pi(v) = t_a` and put `b = c(v)`; then `t_b = pi(v) = t_a`, so `b = a` by
injectivity, so `v in A_a`. Hence `pi^{-1}(t_a) = A_a` exactly. Since
`pi(V) = { t_a : a }`, the fibres are exactly the classes, i.e.
`P_read = P_written`. `[]`

**Proof of 1(b), necessity.** Suppose `a != b` with `t_a = t_b = y`. Then
`pi^{-1}(y)` contains `A_a` and `A_b`, which are disjoint and non-empty, so
`pi^{-1}(y)` strictly contains `A_a`. Two partitions are equal only if the block
containing any given point is the same in both; take a point of `A_a`, whose
block is `A_a` on the written side and a strict superset of `A_a` on the read
side. So `P_read != P_written`. `[]`

### 2.1 Why the two halves are stated separately

**They have different hypotheses, and the corpus had been carrying them as one
sentence.** The counting form is an identity: it holds on every configuration,
including all 394,389 at `n = 5` that break the partition form. The partition
form is an equivalence, and the qualifier "distinct" is exactly its content.

**So the word added to section 2.1 on 2026-09-03 does more than empty a
counterexample set on a finite search.** With that word in place, the counting
sentence is a theorem with no side condition at all, at any size, over any
ordered set. The enumeration could only report zero failures inside its own box.
The proof says the box was not doing any work.

**This is checked, not asserted**: criterion B43-5 below evaluates the counting
form on every one of the 480,006 configurations across the three sizes, including
each one that breaks the partition form, and it fails nowhere.

---

## 3. Theorem 2 (one-sided, floor): the two partitions on the binding set

Throughout this section `pi(v) = max(x_v, t_{c(v)})`, `S_a = { v in A_a : x_v < t_a }`
and `S = union_a S_a`.

**Lemma A.** `A_a intersect S = S_a`, for every `a`. **No hypothesis.**

*Proof.* `S_a` is contained in `A_a` and in `S`, giving one inclusion. For the
other, let `v` be in `A_a intersect S`. Since `v in S` there is a `b` with
`v in S_b`, and `S_b` is contained in `A_b`, so `v in A_b`. The classes are
pairwise disjoint and `v in A_a`, so `b = a`, so `v in S_a`. `[]`

Hence `P_written|_S = { S_a : S_a non-empty }`.

**Lemma B.** For `v in S`, `pi(v) = t_{c(v)}`. **No hypothesis.**

*Proof.* By Lemma A, `v in S` implies `v in S_{c(v)}`, i.e. `x_v < t_{c(v)}`,
so the maximum is `t_{c(v)}`. `[]`

> **Theorem 2.** `P_read|_S = P_written|_S` **if and only if** `a |-> t_a` is
> injective **on `{ a : S_a non-empty }`**.
>
> In particular this holds whenever the terms are pairwise distinct, which is the
> hypothesis registered for the two-sided case; but the exact condition is
> weaker, and the difference is visible in the counts.

**Proof of sufficiency.** Let `y` be any value. By Lemma B and Lemma A,

```
pi^{-1}(y) intersect S = { v in S : t_{c(v)} = y } = union { S_a : t_a = y }
```

Only classes with `S_a` non-empty contribute to that union. By hypothesis at most
one such class carries the value `y`, so the union is either empty or equal to a
single non-empty `S_a`. Conversely each non-empty `S_a` arises this way, as
`pi^{-1}(t_a) intersect S`. Therefore
`P_read|_S = { S_a : S_a non-empty } = P_written|_S`. `[]`

**Proof of necessity.** Suppose `a != b`, `t_a = t_b = y`, and both `S_a` and
`S_b` are non-empty. Then `pi^{-1}(y) intersect S` contains
`S_a union S_b`, which strictly contains `S_a` because the two are disjoint and
`S_b` is non-empty. On the written side the block of any point of `S_a` is `S_a`
itself, by Lemma A. So the two restricted partitions differ. `[]`

### 3.1 The complement is outside the claim, and that is not a gap

Off `S` the value is the baseline, and baselines are unconstrained: two positions
in different classes may share one, a position may carry a value equal to some
other class's term, and neither says anything about the procedure. **The claim is
about the binding set and asserts nothing elsewhere.** This is not a weakening
introduced by the proof; it is what section 2.3 already says, that on a one-sided
carrier what is observable is an atom rather than a partition.

### 3.2 Corollary: where the atoms are, and how many

The observable form on a one-sided carrier is a spike in the distribution of
produced values. Theorem 2 makes that precise.

> **Corollary 2.1.** The set of values at which the procedure creates an atom is
> exactly `{ t_a : S_a non-empty }`, and the number of such atoms is
> `|{ t_a : S_a non-empty }|`.
>
> **Corollary 2.2 (the position of an atom).** Each such atom sits at a written
> term. Not near it, not at a transform of it: at it.
>
> **Corollary 2.3 (the mass of an atom).** The mass at `t_a` is at least
> `|S_a|`, with equality iff no position outside `S` carries the value `t_a`.
> If the baseline distribution is atomless, equality holds almost surely.

**These sharpen section 2.3 in three ways, and one of them is a correction.**

Section 2.3 says "the procedure writes some number of bounds, and the
distribution has that many atoms". **That is right only after two amendments**:
bounds whose binding set is empty produce no atom, and two bounds written at the
same number produce one atom rather than two. Corollary 2.1 is the corrected
count.

**Corollary 2.2 is the one worth stating loudly, because the bunching literature
assumes it and this framework can prove it.** That whole family of estimators
rests on the atom sitting where the statute wrote it. Under the model here that
is not an assumption: it is Lemma B, one line, and it holds with no condition on
the terms at all. The condition is needed only to tell two atoms apart, not to
place either one.

**Corollary 2.3 is the limit.** The height of a spike is contaminated by whatever
the complement happens to carry, and the contamination vanishes only when
baselines are atomless. On a discrete baseline it does not vanish, and the
enumeration in this station runs on a discrete baseline precisely so that this
term is visible rather than assumed away.

---

## 4. Theorem 3 (one-sided, cap): order reversal, and why the two arms had to agree

> **Theorem 3.** With `pi(v) = min(x_v, t_{c(v)})` and
> `S_a = { v in A_a : x_v > t_a }`, the statement of Theorem 2 holds verbatim,
> with the same necessary and sufficient condition.

*Proof.* Let `T'` be `T` with the order reversed. Then `min` computed in `T` is
`max` computed in `T'`, and `x_v > t_a` in `T` is `x_v < t_a` in `T'`. Replacing
`T` by `T'` carries every object of the cap setting to the corresponding object
of the floor setting, with the same underlying sets `A_a` and `S_a` and the same
fibres of `pi`. Theorem 2 applies. `[]`

**This settles a question the enumeration had left open in the other direction.**
The upper-bound arm was run rather than argued, and it returned 180, 4,994 and
129,783 — identical to the lower bound at every size. **That identity is now
explained rather than observed.** In the enumerated box the baselines and the
terms are drawn from the same three-value set, and `z |-> 4 - z` is an
order-reversing involution of that set. It permutes the configuration space and
carries cap configurations to floor configurations, so the two counts are forced
to be equal.

**So the upper-bound run is not an independent confirmation of a mathematical
fact, and it should not be reported as one.** What it is, is an implementation
check: had the two columns differed, the code would have been wrong. It passed,
and that is worth exactly what an implementation check is worth. **The
mathematics is carried by the involution, which is free.**

---

## 5. The closed form, and it reproduces the enumeration digit for digit

A proof that says only "no counterexamples when the terms are distinct" leaves
the counterexamples uncounted. The two theorems say more than that: they say
**exactly which configurations fail**, and that is a closed form. Evaluating it
must return the integers already on disk.

The closed form never walks the baselines. It counts them. So this is a second
path to the same numbers, not a rerun of the first.

**Two-sided.** By Theorem 1(b) a configuration fails iff `a |-> t_a` is not
injective, a condition on the terms alone. The baselines are free, so

```
fail(n) = sum over partitions P of ( #{ non-injective term vectors on P } ) * 3^n
```

**One-sided.** By Theorem 2 a configuration fails iff some value is carried by
two classes that **both** have a non-empty binding set. Given `P` and the terms,
the blocks are independent in the baselines. For a class `a` with `|A_a| = m`,
the number of baseline assignments on that block leaving `S_a` empty is

```
e_a = (4 - t_a)^m     (floor)          e_a = t_a^m     (cap)
```

on the three-value domain, and `f_a = 3^m - e_a` is the rest. Grouping the
classes by the term they carry into `C_y`, the non-failing assignments number

```
prod over y [ prod_{a in C_y} e_a  +  sum_{j in C_y} f_j * prod_{a in C_y, a != j} e_a ]
```

— all binding sets in the group empty, or exactly one non-empty — and the failing
count is `3^n` minus that, summed over `P` and the terms. **Note that the cap
`e_a` is the floor `e_a` under `t |-> 4 - t`, which is Theorem 3 showing up in
the arithmetic.**

`experiments/b43_counting_proof_check.py`, record
`results/b43_counting_proof_check.json`:

| `n` | arm | closed form | enumerated |
|---:|---|---:|---:|
| 3 | two-sided | **810** | 810 |
| 3 | one-sided, floor | **180** | 180 |
| 3 | one-sided, cap | **180** | 180 |
| 4 | two-sided | **18,468** | 18,468 |
| 4 | one-sided, floor | **4,994** | 4,994 |
| 4 | one-sided, cap | **4,994** | 4,994 |
| 5 | two-sided | **394,389** | 394,389 |
| 5 | one-sided, floor | **129,783** | 129,783 |
| 5 | one-sided, cap | **129,783** | 129,783 |

**Nine integers, nine matches.** The two-sided column is also reachable by hand:
with `S(n,k)` the Stirling numbers of the second kind, the total configuration
count is `(sum_k S(n,k) 3^k) 3^n` and the injective-term count is
`(sum_k S(n,k) 3!/(3-k)!) 3^n`, giving `1539 - 729 = 810`,
`25029 - 6561 = 18468` and `453438 - 59049 = 394389`.

**And the gap between the two arms is now explained rather than noted.** The
one-sided failure counts are smaller than the two-sided ones — 129,783 against
394,389 at `n = 5` — because a collision between two classes is harmless when one
of their binding sets is empty. That is the difference between the exact
condition of Theorem 2 and the stronger hypothesis of Theorem 1(b), and it is
worth 264,606 configurations at `n = 5`.

### 5.1 The two criteria this file closes

| criterion | what it checks | reading |
|---|---|---|
| **B43-4** | the closed form read off the proof reproduces the enumerated counts | **9 / 9 exact, across three sizes and three arms** |
| **B43-5** | the counting form and the two lemmas hold on **every** configuration, including each one that breaks the partition form | **0 failures out of 480,006 configurations**, against 413,667 failures of the partition form in the same space |

**B43-5 is the one that carries the separation of section 2.1 from section 2.3.**
Same configurations, two statements, and one of them never fails.

---

## 6. What the proof changes in the statements

**Nothing is retracted. Three things become sharper, and two of them become
stronger.**

1. **The counting sentence is unconditional.** With "distinct" in place it is an
   identity with no side condition, not a statement that survived a finite
   search. Theorem 1(a).
2. **The one-sided condition is weaker than the one registered.** Agreement on
   the binding set needs injectivity only across classes whose bound actually
   bites. Two bands written at the same number are harmless if one of them is
   vacuous. Theorem 2.
3. **The atom count needs the same two amendments as the class count**, and the
   atom *position* needs neither. Corollaries 2.1 and 2.2.

**One thing is added as a convention rather than a limit**: a band with no
members is not a class. Section 1.1.

---

## 7. What the proof does not settle

1. **Empty bands in the corpus.** Whether any of the twenty-three registered
   cases writes a band that no position falls into is unchecked. If one does, its
   class count is read from the bands that have members, not from the text of the
   decree. Registered.
2. **The discretionary band stays outside.** Kazakhstan 1993 is not a
   counterexample and not a class; it fails the law's premise, which requires the
   number to be published.
3. **This proof is about a procedure that has already been written down.** It
   says nothing about why a given partition was drawn, nor about the two enabling
   conditions — a registration point and a device that blocks trade between
   classes — which are prior to it and are classical.
4. **The corpus's own ceiling.** Nothing here bounds the number of classes; the
   observation that the registered cases top out at four values is a fact about
   those cases, not a content of the law. Section 8 collects what the proof does
   and does not require.

---

## 8. Scope: what these theorems actually require

**Writing the proofs out shows the hypotheses to be much thinner than the setting
they were read off.** The corpus is currency reform, the terms are conversion
rates, and the values are money. **The theorems know none of that.** What each one
uses, exactly:

| | `V` | `T`, the value set | finiteness | arithmetic |
|---|---|---|---|---|
| **Thm 1(a)**, counting | any non-empty set | **equality only** | for `\|.\|`; else cardinals | none |
| **Thm 1(b)**, partition | any non-empty set | **equality only** | **not used** | none |
| **Thm 2**, one-sided | any non-empty set | **a total order** (for `max`) | **not used** | none |
| **Thm 3**, mirror | same | same, reversed | **not used** | none |

**Four consequences, and the fourth is a new instrument rather than a wider
licence.**

**8.1 The two-sided law does not need the terms to be numbers.** `pi(v) = t_{c(v)}`
uses nothing but "these two labels are the same or they are not". A published
procedure that assigns each class a *rank*, a *band name*, a *queue position*, a
*statutory priority*, a *boarding group*, is under the law exactly as one that
assigns a rate. **Two classes given different labels are two prices in the sense
the law means**, whatever the labels are made of. This is not a stretch of the
statement; it is what the proof uses and no more.

**Be clear about which end widens.** What a procedure partitions *on* was always
arbitrary: `P_written` is any partition, and the coordinates a class line can be
written in — seat pitch, take-off weight, age, itinerary structure — were never
restricted. **What widens here is the type of `t_a`, the thing each class
receives.**

**And the corpus already contains classes whose terms are not numbers.** Wuhan
1949 sorts issuers into three tiers that receive three different *treatments*:
the renminbi is the unit of account; the regional currencies do not circulate in
the city but are redeemable at a published rate; the gold yuan is prohibited and
not redeemed at all. Czechoslovakia 1919 stamps the 10, 20, 50 and 100, prints
the 1000 on the plate, withdraws the 25 and the 200, and leaves the 1, the 2 and
all coin valid without restriction. **Neither list is a list of numbers, and
neither can be ordered.** Under Theorem 1 each is a set of distinct terms and
therefore a set of distinct prices, which is what the law says.

**Only the one-sided case needs an order**, because a bound has to be comparable
to a baseline. It still needs no arithmetic: `max` and `min` are order operations.

**8.2 Nothing bounds the number of classes, and `V` may be infinite.** The
partition form holds on an infinite position set unchanged; only the counting
form needs `V` finite, and only so that `|.|` is a natural number rather than a
cardinal.

**8.3 The positions need not be a monetary carrier at all.** `V` is a set,
`P_written` is a partition of it, and that is the whole of the setup. A tariff
schedule, a freight tariff, a fee table, a fine schedule, a rating scale: each is
an instance of the same object, not an analogy to it.

**8.4 The counting form is an equation, so it reads in both directions — and the
reverse direction is an instrument the forward one is not.**

```
forward:  a procedure writes m distinct class terms  =>  m values are observed
reverse:  m distinct values are observed             =>  the procedure wrote m
                                                          distinct terms on
                                                          classes that have members
```

**The reverse needs no access to the text of the procedure.** Where the decree is
lost, sealed, or never published in full, counting the prices bounds the class
structure from below. **And it can fail**: if the observed value count exceeds
the number of bands the text names, then either a class line exists that the text
does not carry, or a band is discretionary and outside the law's premise. **Both
of those are findings, and neither is reachable from the forward reading.**

**Two conditions on the reverse reading, both cheap and both already registered
elsewhere.** It needs the procedure to be two-sided (on a one-sided carrier the
complement contributes values of its own, so the count is not the class count);
and it returns the number of classes *with members*, not the number of bands the
text names. **The gap between those two numbers is exactly (empty bands) plus
(collisions)** — and collisions are recorded at zero across the registered cases,
so on that corpus the gap is the empty-band count. **That turns the open question
of Section 7.1 from "read twenty-three decrees" into "subtract two numbers", for
any case where both numbers are on record.**

The one-sided reverse reading is the same move on atoms: counting atoms bounds
the number of classes whose bound binds. **That is what the bunching family
already does, and Corollary 2.1 is the count it should be using.**

**8.5 The limit, and it is the one that matters.** *A wider mathematical scope is
not a wider empirical one.* These theorems say what a reading must be **given**
that a procedure is written a certain way. Whether that reading can be taken at
all is a separate question with its own tests: whether the class difference is
written into any retrievable document, whether it lands on two prices between
which there is no cheap exchange, and whether a published rule already ties the
two terms to each other. **The proof supplies necessity. It supplies no
observability, and it should not be cited as if it did.**
