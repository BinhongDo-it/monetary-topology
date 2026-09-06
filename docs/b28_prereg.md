# B28 preregistration: four posted prices for one object, and who sets each

**The hypothesis is out of sample**, written into the project's framework before
any of this carrier's data was pulled.

**This carrier is the one [`b27_results.md`](b27_results.md) §5 names as the next
screen.** B27's only closable loop had both directions set by one party, which
left a bid-ask reading it could not exclude. **Here one of the legs is set by
nobody.**

---

## 1. Why the object-identity objection does not apply here

The naive version of this carrier fails immediately: buying new and selling used
is not a loop, it is a path through a change of state, and a used object being
worth less is not a reading of anything.

**Two product categories remove the state change, and the seller removes it in its
own words.** A maker-certified refurbished unit is advertised in one sentence as
carrying **"a one-year warranty, full functional testing, and savings up to
15%"**. The warranty term is the seller's assertion that the object is equivalent
to new; the fifteen per cent is the seller's assertion that it is cheaper.
**Both assertions are in the same sentence, about the same object, from the same
party.**

**So the price gap cannot be attributed to the object.** The seller has already
certified that the object is not what differs. **Open-box units, sold by third
party retailers under the same manufacturer warranty, give the same structure
with the discount set by a different party.**

---

## 2. The four prices and who sets each

| price | set by | asserted or cleared | paid in |
|---|---|---|---|
| `P1` new | the maker | asserted | money |
| `P4` certified refurbished | the maker | asserted, at a stated percentage | money |
| `P2` secondary market | **nobody** | cleared by trades | money |
| `P3` trade-in | the maker | asserted per model | **store credit or a gift card, not cash** |

**The deletion mechanism appears here for the third time in this project's
screening.** The trade-in leg terminates in a currency that does not convert back
to money, so the loop through `P3` is not closable by construction, exactly as in
the loyalty and stored-value carriers.

**The admissible cycle is therefore `P4` against `P2`**: acquire the refurbished
unit from the maker at an asserted price, dispose of it on the secondary market at
a cleared price. **One leg asserted by an interested party, one leg set by no
party.** That is the condition B27's carrier failed.

---

## 3. Criteria

**B28-1  is the maker's discount conventional or object-specific.** For a panel of
models, compute `P4 / P1` from the maker's own listings.

- the ratio clusters on a small number of values across models of very different
  age, specification and market performance → **the discount is a posted
  convention**
- the ratio varies continuously and tracks model characteristics → it is
  object-specific and the conventional reading fails
- otherwise → undecided

**B28-2  does the market agree with the maker's certified equivalence.** Compute
`P2 / P4` on the same models and dates.

- `P2 / P4` disperses substantially more than `P4 / P1` → the cleared leg carries
  information the asserted leg does not, and the asserted leg is not tracking it
- the two disperse alike → the asserted discount is tracking the market and the
  conventional reading fails
- otherwise → undecided

**B28-3  the loop.** Report `P2 / P4` as a loop product with its dispersion across
models, alongside magnitudes, and against B27's cross-partner spread of `2.40` as
the only comparable figure this project has.

**B28-5  model existence as the adjustment margin.** *(Added 2026-08-29, after
B28-1 read. It tests a different object rather than recutting B28-1, and the
addition is dated here rather than left to be inferred.)*

If `P4` is a fixed function of `P1`, then the maker cannot reprice a refurbished
unit as its market value falls without breaking the posted rule. **The remaining
margin is whether the model is offered at all.** For each product line, record
each model's presence in the refurbished catalogue over time.

- models leave the catalogue at **widely differing ages across lines**, and the
  exits track the gap between the rule-derived price and the market price → the
  margin of adjustment is existence
- models leave at a **common age** regardless of line → exits are a policy on age
  and this reading fails
- otherwise → undecided

**Data path for this arm, checked 2026-08-29 and currently blocked.** The arm
needs **exit** dates, and three routes were tried. The catalogue itself gives one
date, the present one. A general web archive of the catalogue pages is refused by
this project's fetch path. Trade press covers **entry** reliably and **exit not at
all**, which is a property of what counts as news rather than of the archive:
"the maker now sells refurbished model N" is reported, "the maker quietly stopped"
is not.

**Entry dates are therefore available and are the wrong quantity.** Two firm ones
were collected in passing, one model listed refurbished twenty months after its
launch and another sixteen months after. **Entry lag is plausibly driven by how
fast returned units accumulate, which says nothing about the pricing rule.**

**Corrected 2026-08-30: the quantity was wrong, not only the source.** Catalogue
presence is not a maker-controlled event in the sense this argument needs. The
object keeps trading in the secondary market whether or not the maker lists it,
so a catalogue exit is a fact about one shop window and not about whether the
model still exists to be priced. **The two events the maker does control, and
announces, are the stop of sale and the withdrawal of support.**

Three published instruments, and they are not three independent observations:

1. **Sale stop.** The date the maker ceased distributing a model for sale. Set by
   the maker, and for this maker it is visible as removal from the store at a
   launch event, with trade press coverage the same day.
2. **Hardware service withdrawal.** The maker's own vintage and obsolete list.
   The maker states the rule: vintage is *"stopped distributing them for sale more
   than 5 and less than 7 years ago"*, obsolete is *"more than 7 years ago"*
   (support.apple.com/en-us/102772, read 2026-08-30). **This is a deterministic
   function of instrument 1**, so it carries no timing information of its own, and
   that is exactly what makes it usable: the date a model appears on that list
   recovers its sale-stop date, minus five years, for the entire back catalogue,
   from an official page. **It is an instrument for reading instrument 1, not a
   third observation**, and it must not be reported as independent confirmation.
3. **Software support withdrawal.** The last OS release that supports the device.
   This one **is** independent: the maker drops devices from a new release by
   hardware capability, so two models that stopped selling on the same date can
   have support lives years apart. It is the only one of the three that can
   disagree with the other two, and disagreement is informative.

**The branch conditions are not changed by this correction.** They were fixed in
this file on 2026-08-29, before any date under the corrected instruments was
collected, and they are read here exactly as written above with *presence in the
catalogue* replaced by *offered for sale*. **Disclosure required by 8a:** the
analyst holds general prior familiarity with this maker's annual launch cadence.
The criterion shape predates its application, the hypothesis predates both, and
neither was chosen after seeing a sale-life figure.

**Two sub-arms follow.**

- **B28-5a, sale life by line.** For each model, sale life is the sale-stop date
  minus the launch date. Read the dispersion across lines within one product
  family, where launch cadence, category and maker are all held fixed.
- **B28-5b, support life against sale life.** For each model, support life is the
  last supporting OS release date minus the launch date. If support life is a
  near-constant function of launch date while sale life is not, the two margins
  are being operated separately, and only the one the maker prices against is
  moving.

**What would kill the reading.** A common sale life across lines, with the
dispersion sitting between families rather than within them, sends B28-5 to its
second branch: the maker runs a policy on age and the pricing rule has nothing to
do with it.

*Both sub-arms were read on 2026-08-30 and are reported in `b28_results.md`.
B28-5a returns its first branch, B28-5b returns the disagreement it was designed
to look for. Nothing above was edited after the readings.*

**Refresh cadence is the treatment variable and it varies by construction.** Some
lines are renewed annually, others carry one name for years. **A line whose name
does not change has no stale anchor to escape**, and the prediction is that its
models persist while annually renewed lines shed theirs.

**B28-6  does a new name reset the anchor.** For each line, compute each
generation's launch price against the previous generation's launch price.

- the ratio disperses widely across successive generations → each name carries an
  anchor set independently
- the ratio clusters near one → the new name inherits the old anchor and the
  independence reading fails
- otherwise → undecided

**This is the same quantity B25 reads over fourteen years on one line**, cut by
generation rather than by year, and the two readings must be reported together.

**B28-4  the control that must be reachable.** A category where the maker posts no
refurbished price and the market clears freely. If dispersion there matches the
dispersion here, the reading is about the category rather than the posting, and
**this station is void.**

---

## 4. Gates

| gate | number |
|---|---|
| independent cycles | **`b1 >= 1` per model**, from two parallel edges between holding-the-object and holding-money. Unlike every prior carrier this is not a tree |
| single party over the cycle | **passes.** The maker sets one leg; the other is cleared |
| asserted, not derived | `P1`, `P3`, `P4` asserted. `P2` is cleared and is used as the cleared leg, never as an asserted factor |
| resolution floor | posted prices are exact. **The floor is condition grading on the secondary market**, which is not standardised, and bounding it is the open design problem |
| private bilateral contract | passes. All four are publicly posted or publicly transacted |

---

## 5. Reachability

**Both outcomes of B28-1 are available.** A maker that priced refurbished units
by model-specific residual value would produce a continuous distribution, and that
is an ordinary thing for a maker to do. A maker that posts a flat percentage
produces clustering. **Neither is forced by the construction.**

**What is excluded.** Nothing here reads whether any price is correct, fair or
efficient. The subject is the relation between two posted numbers and one cleared
number for one object.

---

## 6a. Scope

**Not one product line.** The refurbished catalogue spans phones, tablets,
laptops, desktops, watches, audio and accessories, and B28-1 has already been read
across two of these categories at once. **The rule under test is a rule about
posting, not about any product**, so the panel is every line the maker publishes
both prices for.

**Other makers are in scope on the same terms** wherever both a list price and a
maker-posted refurbished or open-box price exist.

**One extension is named and explicitly unchecked.** Long-lived vehicle model
names with annual revisions and generation codes have the same shape: a name that
persists, small yearly changes, and a price that moves every year. **Whether the
posted structure there matches has not been looked at**, and it is recorded as a
candidate rather than as support.

---

## 6. Data

Maker's new and refurbished listings, both posted publicly and carrying both
prices on the same page. Maker's trade-in schedule, posted per model. Secondary
market cleared prices from completed listings. **All four are public and none has
been collected yet.** The condition-grading floor in §4 is to be bounded before
`P2` is used.
