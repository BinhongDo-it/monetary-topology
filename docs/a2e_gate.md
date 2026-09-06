# A2e: is there anything for an instanton to tunnel between?

**A gate, not a station, and it is closed.** This document records a negative
result so that it is not re-derived and so that no manuscript writes a promissory
note against it. It licenses nothing about any economy.

The question came from a neighbouring literature and the placement of that
literature is in
[`b0c_precedent_topological.md`](b0c_precedent_topological.md). Nothing below
depends on it. Kemp-Benedict (2012) obtains endogenous transitions between
critical points on a single-price field; the question here was whether the A2
carrier has anything of that shape on it. It does not.

## 1. The scope, fixed before the work

Kemp-Benedict (2012) has an instanton sector and this framework does not. A
station could be built on the A-track carrier to close it,
and the scope is fixed **here, in advance**, on the same principle as the prereg
documents: a scope written after a result is a defence, and a scope written
before it is a design.

**This station is a pointer sink.** No document in the main chain points into it.
That is checkable by grep rather than by assertion, and if a pointer ever appears,
the rule has been broken and the station has to be re-argued rather than quietly
promoted.

**It is read in two layers, and the conditional applies to one of them.**

*Layer one is unconditional.* On the carrier, the forward and reverse transition
rates between two metastable configurations differ, and the log of their ratio is
compared against the circulation that `topology.py`'s `hodge_decomposition`
already reports. That is a statement about what the model does. It stands
whatever anyone thinks of the interpretation, and it is the layer that carries any
number.

*Layer two is conditional.* Reading that asymmetry as an instanton-mediated
transition requires three things: that the state space carries metastable regions,
that the transition dynamics admits a large-deviation rate, and that the
collective variable separates those regions.

**Those three are weaker than the assumptions this station cites.**
Kemp-Benedict's §3 additionally requires continuous first-order dynamics,
Gaussian white noise with constant `G`, instantaneous adjustment, and no memory in
excess demand. His own §4 concedes that "the assumption of slow and low-amplitude
noise is often not realistic." **The station is therefore not conditioned on his
hypothesis set and must not be written as though it were.** The A-track carrier is
a discrete Markov chain with its own noise; the discrete counterpart of his
instanton is the Freidlin-Wentzell minimiser, and it needs none of the four.

**If layer two fails, what is lost is the name.** The number survives, nothing
outside this document changes, and no result in the main chain moves, because
none of them takes a dynamical input: Theorem 1 is an equivalence with no
economic assumption in it and Theorem 5 is linear algebra on a product Laplacian.
The independence is a fact about the dependency graph and not a promise.

**Known open point, recorded before any work starts.** The A2 state is
node-level balances and is high dimensional. A minimum-action method needs a
collective variable on which the metastable regions separate. A2c's realised cycle
rank and its circulation-to-net-displacement ratio are the candidates and neither
has been tested as a reaction coordinate. If no such variable exists the station
does not get built, and that outcome is reported rather than worked around.

## 2. The gate was run. It is closed.

`experiments/a2e_reaction_coordinate.py`, 48 seeds across ten values of
`financial_to_intermediate_edges` plus three control values, 624 runs of 600
rounds. `results/a2e_reaction_coordinate.json`.

**There is no bistability at any parameter value.** Every cell is a tight
unimodal band and no cell on either live candidate cleared `dBIC > 10` with
Sarle above `5/9` and both mixture weights above `0.10`.

| `edges` | 48 seeds, realised cycle rank / potential |
|---|---|
| 0 | `0.0206` to `0.0296` |
| 1 | `0.7251` to `0.8671` |
| 8 | `0.7564` to `0.8860` |
| 30 | `0.8729` to `0.9012` |

**The two levels A2c reports are two knob settings, not two basins.** Every seed
at `edges = 0` goes low and every seed at `edges = 1` goes high, the two bands
are disjoint, and no seed at either setting lands between them. From `edges = 1`
upward the response is a monotone drift. That is a discontinuous but
deterministic response to a parameter, and it has no barrier in it.

**Refining the sweep cannot change this.** The knob is an integer count of
edges, `0` and `1` are adjacent, and there is no intermediate value at which the
system could go either way.

**A2e-3 returned zero crossings in every run** and was not evaluated further,
there being no pair to cross between. The control knob returned unimodal
throughout, so the estimator was not manufacturing peaks.

**A second reading of the same data, added 2026-08-29, requiring no re-run.**
Watts (2002), PNAS 99(9), 5766-5771, gives a cascade window bounded by two phase
transitions and non-monotone in mean degree: below it cascades are limited by
propagation through vulnerable nodes, above it they are rare but very large, and
only between the two are global cascades possible. A carrier sitting inside that
window would show, at one fixed connectivity, some realisations cascading and
others not, which is a **bimodal** across-seed distribution. That is exactly what
A2e-2 tested and did not find, at any of ten knob values, on either live
candidate. **So this gate also reads as evidence that the A2 carrier is not
inside a cascade window**, which is a stronger and more useful statement than the
absence of instantons alone.

**Consequence.** The station is not built. The precedent file's row recording that Kemp-Benedict has an instanton sector
and this framework does not stands as it is: his paper answers a dynamical
question on a single-price object, and nothing on this carrier answers it back.
A manuscript should not gesture at future dynamical work here.

**Two estimator failures were bought and are recorded in the script rather than
here**, because they are about method and not about economics: energy shares are
useless on this carrier where magnitudes are not, which A2c had already written
down; and bimodality is a within-cell question, so a range filter applied across
a sweep does not protect the mode test inside one cell.

