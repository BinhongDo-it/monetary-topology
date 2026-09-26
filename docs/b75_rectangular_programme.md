# B75: choice of technique is complementary slackness read cycle by cycle, and the solution sits on a square block

**Status: statement and proof, with one known answer from the literature and four structural
checks. Registered 2026-09-12. No empirical arm: this station is paper. Its checks, B75-5 and
B75-6, are in `experiments/b75_rectangular_programme.py`, record
`results/b75_rectangular_programme.json`, and are listed in §5.**

---

## 0. The question this station answers

[`b71_von_neumann.md`](b71_von_neumann.md) did the equality half: with as many processes as
goods, `α = β` is the common sum the production cycles carry, and the two complementary
slackness conditions are two sentences about cycles. Its §8 says in as many words that the
general rectangular case is not solved there, because it needs a linear programme. **This
station solves it and asks what shape the solution has.**

1. **Choice of technique is not a second operation performed on the field** (§2, Theorem
   20(1)). A process runs only if its cycle carries the common sum, at a non-degenerate solution
   exactly then, and an idle process's
   cycle falls short. That condition was already present in the square case; with more
   processes than goods there are simply more cycles for it to sort. **Nothing is added to the
   field in order to choose.**
2. **The solution sits on a square block** (§2, Theorem 20(2)). At a non-degenerate solution of
   a connected economy the running processes and the positively-priced goods are equal in
   number, that number is at most `min(n, m)`, and the block they cut out has `α` as its own
   expansion factor. **So a rectangular system needs no theorem of its own: choice of technique
   picks a square block and the factor is read off that block.** **What does not come with the
   block is B71's hypothesis**, which asks for `B^-1 A` to be non-negative and irreducible: on
   the drawn active blocks that holds on `27` of `60`, the most negative entry being `-30.99`.
   The block's factor is read off `det(B - α A) = 0`, which asks for neither, **so the reading
   rests on the eigenproblem rather than on B71 applying**. Corrected 2026-09-13; the
   measurement is unchanged and the sentence claiming B71 transfers is gone.
3. **The growth factor is an upper envelope, and its kink is a tie** (§2, Theorem 20(3)). An
   idle process contributes nothing at all, not a little; the instant it becomes competitive
   the factor starts to move; and at the crossover two cycles carry the common sum at once.
   **That tie is B74's switch point and the programme's degenerate vertex. They are one object
   seen three ways**, and B72's lower envelope of wage curves is the same shape upside down.
4. **The common sum is a connectivity condition, not an accounting identity** (§2, Theorem
   20(4)). When the economy is reducible, `α` and `β` are read off different parts and come
   apart, **and the counting identity of clause 2 fails on the same instance**. One published
   example breaks both halves at once, which is what shows the condition is connectivity rather
   than bookkeeping.

## 1. Setup

`n` processes and `m` goods, input matrix `A` and output matrix `B`, both `n × m` and
non-negative. Intensities `x ≥ 0` over processes, prices `p ≥ 0` over goods, expansion factor
`α` and interest factor `β`. Von Neumann's conditions:

```
(1)  xB ≥ α xA                    no good is used up faster than it is made, at rate α
(2)  Bp ≤ β Ap                    no process earns more than β on what it advances
(3)  x(B − αA)p = 0 = x(B − βA)p  complementary slackness on both sides
```

**On the graph.** Goods are positions. Process `j` is a cycle: it consumes the basket `A_j` and
delivers `B_j`, and at prices `p` the field's sum around that cycle is
`log((B_j · p) / (A_j · p))`, the log of the gross return the process earns. This is the same
reading B67 and B71 use, with the process set now larger than the position set.

**How `α` is found.** The value of the matrix game with payoff `M(γ) = B − γA` is
non-increasing in `γ`, and `α` is the `γ` at which it reaches zero. Each value is a linear
programme; `α` is a bisection on top of it. That is the route the QuantEcon lecture uses, and
§5 reads its two published examples back through it.

## 2. Theorem 20

**Theorem 20.** With the setup of §1:

1. **(Choice of technique is the slackness condition, read cycle by cycle.)** Under (2) and
   (3), a process carries positive intensity only if its cycle's sum is exactly `log β`, and
   every other process's cycle sums to at most `log β`. **So the operated processes are among
   the cycles attaining the common sum**, and at a non-degenerate solution they are all of
   them. **The converse is not free**: a cycle can attain the sum and carry no intensity, which
   is a degenerate vertex, and §3 below reads exactly that case. The published form of this
   clause said "exactly the set" and was corrected on 2026-09-13; the proof gives one
   direction and this file's own §3 gives the other case.

   *Proof.* By (2) each term of `x(B − βA)p = Σ_j x_j [(Bp)_j − β(Ap)_j]` is non-positive,
   since `x ≥ 0` and each bracket is `≤ 0`. A sum of non-positive terms vanishes only if every
   term vanishes, so `x_j > 0` forces `(Bp)_j = β(Ap)_j`. Taking logarithms turns that into the
   statement about the cycle's sum, and the inequality (2) turns into the statement about the
   others. ∎

   **What this settles.** The classical question "which techniques are in use" is answered here
   by a condition the field already carries. There is no separate comparison of cost curves
   laid on top: the comparison **is** condition (3), one line per cycle.

2. **(The solution sits on a square block.)** Let `J = {j : x_j > 0}` and `I = {i : p_i > 0}`.
   **At a basic optimal solution** `|J| ≤ m` and `|I| ≤ n`, which is the count of the
   programme's rows and is what a vertex solver returns; a degenerate optimum can spread the
   same activity over more processes, **so the bound is on that solution rather than on every
   optimal one**. At a non-degenerate solution of a connected economy `|J| = |I|`, hence both
   are at most `min(n, m)`; and the block `(A_IJ, B_IJ)` has `α` as its own expansion factor.
   The basic-solution qualifier was added 2026-09-13; §3's counts read that solution and are
   unchanged.

   *Proof.* The programme for `x` has `m` inequality rows and one normalisation, so a basic
   optimal solution has at most `m + 1` basic variables, one of which is the value; hence
   `|J| ≤ m`, and the dual argument gives `|I| ≤ n`. For the equality, clause 1 gives
   `(B_IJ − αA_IJ)ᵀ x_J = 0` and the same argument on the quantity side gives
   `(B_IJ − αA_IJ) p_I = 0`, so the block has a strictly positive left null vector and a
   strictly positive right null vector. Non-degeneracy makes both null spaces one-dimensional,
   so the block's rank is `|J| − 1` and also `|I| − 1`, whence `|J| = |I|`. Deleting the idle
   processes and the free goods changes neither side of (1), (2) or (3), so `α` solves the
   block's own problem. ∎

   **The bound belongs to the `D22` family**: a count derived from the solution is capped by a
   count read off the graph before any solving. However many processes are written down, the
   number that can run is held down by the number of positions.

   **The hypotheses are not decoration.** §5 exhibits a published economy where connectivity
   fails and `|J| = 3` against `|I| = 4`.

3. **(An upper envelope whose kink is a tie.)** Along a family of economies, `α` equals the
   largest expansion factor among the sub-economies available; a process with `x_j = 0`
   contributes nothing to it; and at a parameter where the maximiser changes, two cycles attain
   the common sum simultaneously.

   *Proof.* Enlarging the process set enlarges the feasible set of the maximisation, so `α` is
   non-decreasing in it; by clause 2 the solution is unchanged by deleting the idle processes,
   so `α` is the factor of the sub-economy on `J`, and therefore the maximum over
   sub-economies. Where the maximiser changes, two sub-economies attain that maximum, so by
   clause 1 the corresponding cycles both carry `log α`. ∎

   **The same object three ways.** A tie between two cycles is a switch point in B74's sense; a
   solution with more attaining cycles than running processes is a degenerate vertex of the
   programme; and the envelope's kink is where the growth factor stops being flat. **They are
   the same parameter value.** B72's Theorem 17(4) reads the lower envelope of wage curves the
   same way, with the order of the extremum reversed.

4. **(The common sum is a connectivity condition.)** If the economy is not connected in the
   sense that its processes and goods do not form one part, `α` and `β` are read off different
   parts and need not agree, **and the counting identity of clause 2 fails at the same time.**

   *Proof.* Both `α` and `β` are defined by conditions that involve only the part a positive
   vector is supported on. When the support of `x` and the support of `p` fall in different
   parts, (3) is satisfied for trivial reasons and the two factors are determined
   independently. §5 exhibits this. ∎

   **What this is doing.** The literature restores agreement by assuming irreducibility, which
   is Kemeny, Morgenstern and Thompson's condition. The reading here says what the assumption
   buys: **"there is one common cycle sum" is a statement about the graph being in one piece.**
   When it is not, the field has two readings and the two numbers are two different readings of
   two different parts.

## 3. Placement

**What this framework reads of the world.** A process runs only if its cycle carries the
common sum; the running processes and the priced goods cut out a square block on which B71's
square theorem holds, and the block's size is capped by the position count; the growth factor
is an upper envelope whose kink is a simultaneous tie of two cycles; and the existence of one
common cycle sum is a connectivity property of the graph.

**What the classical account reads of it.** That `α = β` under irreducibility and that the two
come apart without it; that the model is solved as a zero-sum game or a pair of dual
programmes; that non-operated processes carry zero intensity and slack in the price condition;
and the two worked examples read back in §5.

| cell | content |
|---|---|
| **A** | `α = β`, the irreducibility condition and its failure, the game-theoretic solution, and complementary slackness itself. That account has all of it, and it has had it since 1945 and 1956. **Recorded as this framework being right, not as a debt**: a more general reading that returns the established answer where the established account speaks is doing what it must |
| **D2** | Empty. The questions this station answers about the rectangular case are ones that literature does answer, and answers correctly |
| **D** | The cycle readings: that choice of technique is condition (3) taken one line per cycle rather than a comparison laid on top; that the active block is where B71's square theorem lives, so the rectangular case needs no theorem of its own; that the envelope's kink, B74's switch point and the programme's degenerate vertex are one object; and that `α = β` and the counting identity `\|J\| = \|I\|` are the same connectivity condition and fail together. No account asks for these |
| **C** | Empty, and this station cannot produce it: it reads no data, so no point prediction of any other account is scored here |

## 4. Related work

The model, the two factors and their equality are von Neumann's; the rectangular generalisation
and the irreducibility condition that restores existence and equality are Kemeny, Morgenstern
and Thompson's. The bisection on the value of the game `B − γA` and the two worked examples
read back in §5 are the QuantEcon lecture's.

- Kemeny, J. G., Morgenstern, O. and Thompson, G. L. (1956). A generalization of the von
  Neumann model of an expanding economy. *Econometrica* 24(2), 115-135.
- Neumann, J. von (1945). A model of general economic equilibrium. *Review of Economic Studies*
  13(1), 1-9.
- Sargent, T. J. and Stachurski, J. Von Neumann growth model (and a generalization). *QuantEcon
  lecture*, `python.quantecon.org/von_neumann_model.html`.

## 5. The known answer and the structural checks

`experiments/b75_rectangular_programme.py`, record `results/b75_rectangular_programme.json`,
which carries the configuration it ran under. Seed 0; a run takes under a minute and a second
run writes the same bytes. All five pass.

**A word on the floor, because it decides how three of these are stated.** Anything read
through the bisection carries the linear programme's accuracy, not the bisection's depth: the
solver's feasibility tolerance is `1e-7` and the game value's slope in `γ` measures about
`0.13`, so a root is pinned to roughly `8e-7` however many times the bracket is halved.
**Running 200 halvings instead of 60 buys nothing**, which is why the count is 60. The bound
used below is `1e-6`, taken from that division and not from any run's worst case; the worst gap
actually seen is printed each time.

**B75-5, a known answer: two published rectangular examples, and the one that breaks both
halves at once.**

- **Example one, irreducible, three processes and four goods.** `α = β`, and **the exact value
  is the cube root of two**, matched within `1e-12`. The lecture's own printed figures agree
  within `1e-8`, which is its bisection tolerance and not a disagreement. The intensity and
  price vectors match the printed ones within `0.005`, the fourth good carrying a zero price in
  both. **Three processes run and three goods are priced: equal.**
- **Example two, reducible, five processes and six goods.** `α` is again the cube root of two
  while **`β` is one**, so the two factors come apart exactly where the lecture says they do.
  **Three processes run and four goods are priced: not equal.** One instance breaks clause 4
  and clause 2's counting identity together, which is the evidence that connectivity is the
  condition behind both.

**B75-6, the structural checks.**

- **B75-6a, the square control.** 60 drawn square systems, each process making one unit of its
  own good. **The programme's expansion factor equals `1 / λ_PF(A)` on all 60**, within the
  floor, the worst gap actually seen being `1.2e-13`. The two numbers share no code: one is a
  bisection on a game value solved by linear programming, the other an eigen-decomposition,
  **which is the route B71 used**. This is a second path to B71's number, not a second reading
  of it.
- **B75-6b, the square block.** 60 drawn rectangular systems with more processes than goods.
  **Two statements, and they are not the same kind of statement.** The combinatorial one is
  exact, with no tolerance anywhere: **the running processes and the priced goods are equal in
  number on all 60**, and that number is at most `min(n, m)` on all 60. The numerical one
  carries the floor: **the block's own expansion factor, read off
  `det(B_block − α A_block) = 0` as an eigenproblem rather than off the programme, agrees with
  `α` on all 60** within `1e-6`, worst gap actually seen `3.4e-8`. **Those residual
  disagreements are the bisection's and not the block's**: the largest of them sit on
  one-by-one blocks whose condition number is exactly one, where the block's root is a ratio of
  two entries and cannot be wrong. The bound is not tight, the active count running from 1 to 5
  against `min(n, m)` up to 5.
- **B75-6c, slackness on cycles.** 151 points along a swept parameter, on a system where two
  processes make the first good from different input mixes. **A process attains equality in the
  price condition when and only when it runs, on this sweep**, on all 151 points, equality read
  at `1e-8`. **The forward half is the theorem and the reverse half is the reading**: an idle
  process can attain equality at a degenerate vertex, and the one place on this sweep where that
  could happen is the tie located at `s = 0.797508`, which no grid point lands on. No
  inactive process attains equality by accident anywhere along the sweep.
- **B75-6d, the envelope and the tie.** The same sweep. **The factor is the larger of the two
  single-technique economies' factors at all 151 points**, and **while the second process is
  idle the factor does not move at all**, matching the first technique's own factor at all 101
  such points: an idle cycle contributes nothing, not a little. The active set changes exactly
  once, bisecting to `s = 0.797508`, and **both competing processes attain equality there**.

**What these checks are and are not.** They read no data and decide nothing about any economy.
The counts are counts on drawn or constructed systems; the distribution of active-set sizes is
a property of the drawing, not a fact about any technology in use anywhere.

## 6. Scope

Two factors, one expansion rate, no consumption out of the surplus and no wage: this is von
Neumann's own setting, and it inherits its conditions. The drawn systems are small, with at
most ten processes and five goods; the point of the station is the shape of the solution, not
its behaviour at scale. Which processes are written down at all is given from outside, as it is
at every station in this family. Nothing here says which growth path ought to be taken; optimal
growth and turnpike questions are a different subject. Nothing here measures a process, an
intensity or an expansion factor in any economy.
