# Volume II speedrun, Part 3: B12 through B14

**Part 3 of 3.** Part 1 covers B0 through B6, Part 2 covers B7 through B11. These three stations are
the ones built after the programme knew what it was short of, and two of them were built to be able
to fail.

Same four fields per entry. Figures quoted exactly as the record carries them; where the record
supersedes itself, the later reading is given and the earlier is named.

> **Part 2 ended on an open problem**: no station had produced a prediction that a competing account
> gets *wrong*, as opposed to one a competing account also gets right. **That problem has moved and
> it is not closed.** The section at the end of this part says where it stands, and B13's own record
> is the thing that stops it short.

---

## B12 — grid invariance: the ruler that predicts an exact zero

*Pre-registered, code written, every record `diagnostic_only`.*

**Asked.** B10's holonomy ladder answered the sharpest objection in the programme with "this ruler
cannot measure it". Can the question be re-asked with a ruler whose prediction is an exact zero,
which is what would make it able to fail?

**Answered.** Not yet, in the sense that matters. [`experiments/b12_pullback.py`](../experiments/b12_pullback.py)
exists and runs, and every record it writes carries `diagnostic_only`, so nothing it produces
reaches [RESULTS.md](../RESULTS.md) and nothing published rests on it.

**Retracted / failed.** Nothing yet, because nothing has been claimed yet.

**Caveat that travels.** A stage that writes only diagnostics is a stage that has not decided
anything. It is listed here so that a reader who finds `b12_*` files in `results/` knows they are
not claims, and so that the absence of a B12 section in `RESULTS.md` reads as deliberate rather than
as an oversight.

---

## B13 — the zero domain: the framework says where its own quantity must be zero, and it is

*Closed in a day, on a vendor's free public sample, with no money spent and no data request sent.*

**Asked.** Objection 11 ruled that coverage tests are worth nothing, because they list what a
framework explains and never what it forbids. The repair registered against it was a **zero
domain**: the framework has to say first where its own quantity must be zero, and then go and
measure there. The job went to B9 and B9 could not do it, and said why in structural terms rather
than as an apology: its carrier had no grid to vary, no second member of the same family, and every
edge on it charged a fee. **Where is a family with one member whose edge is derived rather than
quoted?**

**Answered.** CME calendar spreads. The exchange publishes an **implied** book beside the
**directly quoted** one, for the same contract, in the same packet, in the same event. The framework
says a derived edge carries no independent information, so the holonomy on it is zero. Measured:
the published implied price is **never worse than the two-leg derivation, 0 violations in 81,968
states**, over nine products and three channels. On six of the nine it is not merely never worse but
**exactly equal, 18,800 of 18,800**. The same apparatus, same feed, same instruments, same events,
turned on the directly quoted member of that family returns **non-zero in 65 to 96 per cent of
states**, nine products with no exception. It also produced the first measurement anywhere in this
repository of **both halves** of B4 section 5.1's split, which B5 had been able to report one half of
and never the other: the split is available in 49,116 of 50,055 states and the sign constraint
Theorem 6(1) forces has zero counterexamples in all of them.

**Retracted / failed.** **The explanation is withdrawn and the reading is not.** The station first
said the six exactly-equal products were the ones where the two-leg path is the only derivation
path. The instrument listing was then read, and it does not draw that line anywhere:
[`b13_path_multiplicity.py`](../experiments/b13_path_multiplicity.py) finds every root measured
multi-path, on **both** sides of the split — CL 906 of 906, NG 1,124 of 1,127, GC 231 of 231, HG 820
of 820, MHG 780 of 780, QI 55 of 55. **Why six and not nine is now an open question rather than an
answered one.** A registered precondition, that the spread quotes on the same grid as its legs, was
skipped when the gate first ran and passed only when it was performed afterwards, so a day's
readings stood on luck. The pairing rule's original justification, that the implied entry is the last
one in an event, was overturned by measurement and its replacement rests on measurement with no
protocol document behind it. And the expensive one: **reading only the A side of an A+B deduplicated
capture** cost 2 per cent of updates and produced a bid agreement of `0.9229` that looked like a
finding about the exchange; with both sides it is `0.9990`. What caught it was a book monotonicity
check, not any guard written for the purpose.

**Caveat that travels.** **One ten-minute window of one day, and the first hundred seconds of it.**
81,968 states is a thick sample of a thin slice. The station's own record forbids four things by
name: calibrating B9's `λ` against this zero, reading the non-zero side as an economic statement,
claiming that "take the best of all available paths" is CME's written rule rather than a
zero-counterexample relation, and **calling this the answer to the open problem Part 2 ends on.**

---

## B14 — the tick size pilot: a dated, exogenous, symmetric friction change

*The gate passes on the pilot's start, six of six. The mirror on the pilot's end returns three of six,
and the pre-registered reading of that was followed rather than argued with.*

**Asked.** B4 section 9 left section 5.1's invariance claim untested and named exactly what a test
would need: **a dated, exogenous friction change that hits both agent classes equally.** Naturally
occurring co-movement of two spreads will not serve, because the information that moves them also
moves the index. Does such an event exist, and is it affordable?

**Answered.** The SEC tick size pilot. It is dated, it is imposed by a regulator rather than
triggered by market state, a quoting increment binds bid and offer alike and every venue alike, and
919 securities were never treated. Imposing the 5-cent grid widens the treated groups' spread
against the control on **both NYSE and NYSE Arca, six inequalities of six**, and it survives every
convention tried against it: the order-count weighting, an adversarial reading that admits
zero-spread rows at their true share weight, a second one that additionally forces blank rows to
zero, and the consolidated spread as a cross-check. **Five quantities, thirty inequalities, all
same-signed.** Holding each symbol's order-type mix fixed at its own pre-period shares *widens* the
margins, so composition drift was working against the finding rather than producing it. The data is
free from NYSE's public archive, 1.07 GB, and every file was checked against that archive's own
correction log and is at or beyond the last version it records.

**Retracted / failed.** **The mirror fails.** The pilot's quoting requirements ended at the close on
2018-09-28, and the same gate run on the reversal returns **three of six** on the two venues' own
spreads while returning **six of six** on the consolidated spread. The pre-registered outcome map
sends that to "B14-0 under question, re-examine the 2016 round", and it was followed **rather than
rescued by the cross-check that passed**. Registered at the same time as a defect in the
pre-registration itself: the outcome map had no cell for "primary fails and cross-check passes", so
that branch had a label and no reading. Separately, a first attempt at the 2016 gate returned **zero
of six** for a reason that was code and not world — the file's group column records a security's
status *on that day*, so every treated security reads as a control before the pilot started, and the
rule "the group label must be unique across both windows" discarded all 1,525 of them.

**Caveat that travels.** **Appendix B carries spread widths and no quote levels**, so this carrier
delivers the friction half of section 5.1's split and not the index half. The second stage, which is
where the invariance claim would actually be tested, needs per-venue midpoints and stays locked. The
two venues share one operator. On Arca, two order types out of six do not carry the result while on
NYSE all six do, eighteen of eighteen. And the post-period of the 2018 round sits on a volatility
event large enough that the control group's own spread widened 28 per cent in logs, which a
difference-in-differences removes only to the extent that it hit both arms equally.

---

## What Part 3 adds up to

**Two of these three stations were built to be able to fail, and one of them did.** That is the
point of building them that way. B14's mirror test returned a result its own pre-registration had
mapped in advance to "the earlier round is now under question", and the station took that reading
while a cross-check sat there passing six of six. **A programme that only ever reports the arm that
worked would have reported the six of six.**

### Where the open problem stands

Part 2 ended by saying that no station had produced a prediction a competing account gets *wrong*.
**B13 is the first thing here that bears on it, and the part that bears is not the zero.**

The zero on its own does not discriminate, and B13's record says so before anyone else can. Any
account of what a matching engine does predicts that a derived price tracks the thing it is derived
from. **What discriminates is the sort.** One apparatus, one feed, one day, two members of a single
family that differ in exactly one respect — whether the edge is derived or quoted — and it returns
**exact zero on one and non-zero in 65 to 96 per cent of states on the other, with the framework
naming which before anyone looked.**

An account that calls `ω` measurement noise predicts noise on both, because both are measured by the
same code on the same packets. An account that calls it a bid-ask artefact predicts the non-zero on
both, because both books have spreads. **Neither survives the sort.** The account that does survive
is "the exchange computes the implied price from the legs, so of course it is zero" — and that
sentence is the framework's own mechanism stated in the exchange's vocabulary. A derived edge
carries no independent information. It agrees with the claim and disputes the labelling.

**That is a better position than Part 2's sentence describes, and it is still short of the thing
itself.** What B13 does not have is a case where the framework and a rival each make a prediction
and the rival's comes out false. What it has is a case where the rivals worth naming either fail the
sort or concede the mechanism. B13's own record forbids calling that the answer, and the reason it
gives is exact: **measuring the same quantity better does not turn an undiscriminating prediction
into a discriminating one.** The distance left is not more data on this carrier. It is a second
family where the sort can be called in advance and can come out wrong.

**One thing did over-perform, and it is worth naming.** Section 4.A.2 asked only for an inequality:
the published implied price never *worse* than the two-leg derivation. On six products it came back
an **equality, bit for bit, 18,800 of 18,800.** A prediction that required an inequality returned an
identity. Why on those six and not the other three is the open question B13-2 now carries, and the
first explanation offered for it has already been withdrawn against the instrument listing.
