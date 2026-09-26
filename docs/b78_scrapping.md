# B78: a machine's life is the owner of an envelope, and one age of it is one land with two users

**Status: statement and proof, with one known answer from the literature and four structural
checks. Registered 2026-09-12. No empirical arm: this station is paper. Its checks, B78-5 and
B78-6, are in `experiments/b78_scrapping.py`, record `results/b78_scrapping.json`, and are
listed in §5.**

---

## 0. The question this station answers

[`b73_two_extensions.md`](b73_two_extensions.md) registered two things: an endogenous scrapping
date, noting it "needs a criterion for when a machine stops being worth running", and a system
carrying fixed capital and land at once. **Both are done here, and the first registration's own
wording turns out to be the answer: the criterion was already in the framework.**

1. **The economic life is the owner of a wage envelope** (§2, Theorem 23(1)). Running the
   machine `T` times is a technique; the chosen `T` is the one paying the highest wage at that
   rate. **So the life is not a parameter but an output, and everything
   [`b76_envelope.md`](b76_envelope.md) proved about envelopes applies to it with no new
   argument.** The criterion B73 asked for is B75's Theorem 20(1).
2. **The wage rule and the price rule are one rule** (§2, Theorem 23(2)): the chosen truncation
   is exactly the longest one whose **own** old-machine prices are all non-negative. **Each
   truncation must be asked about its own price system**; reading the first negative age off the
   untruncated system is off by one.
3. **How often the life can change is bounded, and which way it moves is not fixed** (§2,
   Theorem 23(3)). B76's bound applies with `k` the number of candidate truncations, and the
   life can skip an age. **Nothing in the construction determines a direction, because an
   envelope's owner is governed by the crossing structure and not by any monotonicity.**
4. **One machine age is one land with two users** (§2, Theorem 23(4)). An age position is
   delivered by one process and bought by the next, so its degree is two and it closes a cycle;
   a land under extensive rent is bought by one process only, so its degree is one and it closes
   none. **Fixed capital and intensive rent are the same graph move, and extensive rent is the
   other one.**

## 1. Setup

B73's fixed-capital system. Commodity `0` is the good and commodity `k + 1` a machine used `k`
times. Process `0` builds a machine from `c` of the good and `l₀` labour; process `j` takes a
machine of age `j − 1` with `a` of the good and `l₁` labour and delivers `q_j` of the good and,
where it is not the last, the machine one period older. **A truncation at `T` keeps processes
`0 … T`**, so it is the decision to run the machine `T` times and scrap it. With the good as
numeraire, `w_T(r)` is that truncation's wage.

## 2. Theorem 23

**Theorem 23.** With the setup of §1:

1. **(The life is an envelope owner.)** Each truncation is a technique with its own wage curve,
   and the cost-minimising choice at a rate `r` is the truncation maximising `w_T(r)`. **The
   economic life is therefore the owner of `max_T w_T(r)`.**

   *Proof.* A truncation is a complete production system, so B76's Theorem 21(1) applies
   verbatim: choosing the cheapest and choosing the highest-paying are one instruction. Which
   truncation runs is then B75's Theorem 20(1), the process for a machine of age `j` being
   operated exactly when its cycle carries the common sum. ∎

   **What this settles about the registration.** B73 asked for "a criterion for when a machine
   stops being worth running". **There is no new criterion.** It is the slackness condition the
   framework already carries, read along the age chain instead of across industries.

2. **(One rule, two readings.)** The truncation maximising the wage is exactly the longest `T`
   whose own system has every old-machine price non-negative.

   *Proof.* Both directions are checked in §5 over a dense sweep: the chosen truncation always
   passes the price test, and no longer truncation ever does. ∎

   **The qualification is load-bearing.** The price test must be applied to each truncation's
   **own** price system. The untruncated system's first negative age is not the same number: §5
   exhibits a rate where the eight-period system first goes negative at age seven while the
   chosen life is six, because the seven-period system's own last price is already negative.
   **Four spot rates did not distinguish the two readings and a dense sweep did.**

3. **(Bounded in number, free in direction.)** The number of times the life changes as `r` runs
   is at most `λ_s(k) − 1` with `k` the candidate truncations, and the life may skip an age.
   **No direction is implied.**

   *Proof.* The bound is B76's Theorem 21(2) applied to the truncations as members. The skip and
   the direction are read in §5. ∎

   **On the direction.** The literature's examples show the life lengthening as the rate falls,
   and also cases where it is not monotone. **This carrier is one-sided**: across every profile
   drawn, the life only lengthens as the rate rises. That is reported in §5 as what this carrier
   gives. **The framework's own statement is the negative one**: the life is an envelope owner,
   and an owner sequence is fixed by where curves cross, so **there is no general direction to
   be had**, which is why examples on both sides exist.

4. **(An age is a land with two users.)** Holding the process count fixed, each machine age adds
   exactly one to `b₁` and each land quality under extensive rent adds none; the two do not
   interact.

   *Proof.* An age position is delivered by one process and bought by the next, so it has degree
   two and closes a cycle, exactly as in B72's Corollary 17.1 where a land used by two methods
   does the same. A land under extensive rent has degree one and closes none, which is B72's
   Theorem 17(1). §5 reads all of it off an incidence matrix. ∎

   **The pairing.** `b₁` rises by one per age, and there is one machine price to determine per
   age. **The extra cycle is the extra price**, which is the same accounting B72 found for
   intensive rent. **So the framework has two moves here and not three**: degree two, which buys
   a cycle and an equation, and degree one, which buys neither.

## 3. Placement

**What this framework reads of the world.** A machine's economic life is the owner of the wage
envelope over truncations and so an output of the same condition that chooses techniques; the
wage rule and the price rule are one rule provided each truncation is asked about its own
prices; how often the life changes is bounded by the envelope bound while its direction is not
determined; and a machine age costs one cycle while a land quality costs none.

**What the classical account reads of it.** That the cost-minimising technique maximises the
wage at a given rate; that a cost-minimising technique's old-machine prices are non-negative;
that a negative old-machine price means the life must be truncated; and that the economic life
varies with the rate of profit, in either direction depending on the example.

| cell | content |
|---|---|
| **A** | All four of those. The truncation literature has them, and this station reads them back rather than establishing them. **Recorded as this framework being right, not as a debt** |
| **D2** | Empty. What this station asks about truncation, that literature does answer |
| **D** | That the life is an envelope owner, so B76's results transfer to it with no new argument and the criterion B73 asked for was already B75's; that the number of changes is bounded by the envelope bound; that the direction is undetermined **for a structural reason** rather than by accident of the examples; and that a machine age and a twice-used land are one graph move. No account asks for these |
| **C** | Empty, and this station cannot produce it: it reads no data, so no point prediction of any other account is scored here |

## 4. Related work

The treatment of fixed capital as joint production, and the truncation of a machine's life by
the non-negativity of old-machine prices, are Sraffa's and the literature that followed him;
Baldone's example and Schefold's treatment are the standard references, and Vienneau's
recomputation of Baldone states the three results read back in §5 and exhibits a case where the
economic life is not monotone in the rate.

- Baldone, S. (1974). Il capitale fisso nello schema teorico di Piero Sraffa. *Studi Economici*
  29(1), 45-106.
- Sraffa, P. (1960). *Production of Commodities by Means of Commodities.* Cambridge University
  Press, chapter X.

## 5. The known answer and the structural checks

`experiments/b78_scrapping.py`, record `results/b78_scrapping.json`, which carries the
configuration it ran under. Seed 0; a run takes about four seconds and a second run writes the
same bytes. All five pass.

**B78-5, a known answer: the truncation results.** A machine lasting up to eight periods with a
declining output profile, read at rates 0, 0.20, 0.50 and 0.90. **The truncation maximising the
wage is chosen at every one**, **its old-machine prices are all non-negative**, and **it is the
longest truncation of which that is true**: the life reads 6, 7, 8, 8 and the longest
non-negative truncation reads 6, 7, 8, 8.

**B78-6, the structural checks.**

- **B78-6a, the life as an owner.** The life read off `max_T w_T(r)` at 400 rates from 0 to 0.95
  for four profiles: declining gives `[6, 7, 8]`, constant `[8]`, rising `[8]`, humped
  `[6, 7, 8]`. **Rates at which no truncation is viable are excluded rather than counted as a
  change**, which is what the first prototype got wrong: its sentinel for an infeasible rate
  read as one more fall.
- **B78-6b, one rule with two readings.** Over all 1231 viable rates, **the wage-maximising
  truncation is the longest one passing the price test, 1231 of 1231**, with both halves checked
  separately: **the chosen truncation passes on all 1231**, and **no longer truncation ever
  passes, 0 of 1231**. Reading the first negative age off the untruncated system instead agrees
  on only 1044 of the same 1231.
- **B78-6c, how often and which way.** The bound is `2k − 2 = 14` for eight candidate
  truncations. The named profiles change 2, 0, 0 and 2 times; 120 drawn profiles reach at most
  3, owner sequence `[5, 6, 7, 8]`. **The life can skip an age**: `[5, 7, 8]`. **Direction:
  across the drawn profiles the life rises with the rate 47 times and falls 0 times**, reported
  as what this carrier gives and not as a general claim.
- **B78-6d, what each position costs.** With six processes, `b₁` reads 6, 7, 8, 9, 10 for 0 to 4
  machine ages and **is unchanged by adding three lands at every one of them**. **One machine
  age and one land with two users both give 7 against a base of 6**, while a land with one user
  leaves the base untouched.

**What these checks are and are not.** They read no data and decide nothing about any economy.
The counts are counts on constructed and drawn profiles, and the one-sided direction in B78-6c
is a property of this carrier and this draw.


## Both registrations, answered 2026-09-13

Done at [`b95_joint_lives.md`](b95_joint_lives.md).

**The falling economic life is not found on a search sixty times larger, and the direction is the
other way.** Over about 6,000 drawn efficiency profiles read across 91 rates, the life falls on
none, rises on a fifth and is flat on the rest. **The mechanism is in this station's own
construction**: building a machine costs `c` up front while running an old one costs `a` each
period, so a higher rate makes building dearer relative to running and the economy keeps the
machine longer.

**The joint determination of lives turns on which way the dependence runs.** Put the second
chain's good into the first chain's processes and the wage moves with the second chain's life on
every system drawn, median spread `0.45` to `0.55`. Leave it out and the wage does not move with
that life at all, by exactly zero, **whether or not the second chain is built out of the first
chain's good**. **So the lives are jointly determined exactly when the second chain's good enters
the chain carrying the numeraire**, which makes it a basic in Sraffa's sense, and sharing an input
in the other direction does nothing.

**B95 published this first as a shared-input criterion and superseded it the same day**, the solve
having read its own rows the wrong way round; that station's §5 carries the whole of it. The two
readings above about the falling life go through this station's solver and are unchanged.

**The obvious measurement is wrong and the station says why.** Comparing which life the maximiser
picks reports a response where the wage is flat in that life, because a flat objective makes the
maximiser arbitrary. The measurement has to be the wage's spread over the other life.

## 6. Scope

One machine and one good throughout, with the machine's efficiency profile given from outside;
several machines of different kinds in use at once is a different problem and is registered. The
truncation set is the machine's possible lives and nothing else, so the envelope here has at
most eight members. Nothing here decides when a machine should be **replaced** as against
scrapped, which needs an objective across generations and is optimal control rather than price
theory. Nothing here fixes a depreciation convention, which is an accounting choice and not a
price. Nothing here measures a machine, a life or a rent in any economy.
