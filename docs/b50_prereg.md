# B50 pre-registration: a programme change on one leg, and what the class square should do

B49 and B52 read whether the class square is non-zero. This station asks a
different question of the same object: **when a programme changes one leg and
leaves the other alone, does the square move the way the programme says?**

Hungary cut regulated household energy prices in a series of dated rounds from
2013. Each round names a percentage and a date, so the programme is public and
the arithmetic is fixed before anything is read. If a round cuts household
electricity and household gas **by the same proportion**, the household half of
the square is unchanged by construction, and with the industrial legs untouched
the square sum should not move at all. If a round cuts them by different
proportions, the square must move by the difference.

That makes the station a test of the discriminant, not of the square: a shared
programme moves the square in a way the programme predicts, while a shared
environment moves both legs and cancels.

## 1. Criteria

| | asks | kind | FAIL |
|---|---|---|---|
| **B50-1** | the panel is complete: four legs across the semesters, in all three tax bases | `instrument` | a leg or a tax base is missing |
| **B50-2** | the reading uses the per-band series, which carries more semesters than the total band | `instrument` | the sparser aggregate is used |
| **B50-3** | the square does not move with the currency the prices are quoted in | `instrument` | the residual exceeds what one shared scalar can leave behind |
| **B50-4** | the point prediction over the clean window, read in four states | `own_reading` | the square moves when the programme says it should not |
| **B50-5** | the arithmetic premise of B50-4: over that window the two household carriers moved by the same proportion | `premise` | they did not, and B50-4 then has no object to judge |
| **B50-6** | the cut reached the price and not only the tax | `premise` | the household leg moves only with tax included |

**B50-4 has four states, and one of them is the premise failing.** The middle
states carry no verdict: a move smaller than the instrument's floor is
unreadable, and a premise that does not hold leaves nothing to judge. Neither is
a pass and neither is a failure.

**A second yardstick is registered with it.** The floor says whether a move is
visible; it does not say whether a move is unusual. The square's own semester-to-
semester movement over the whole panel is the second yardstick, and both are
required: a change at 65 times the floor that sits at the 22nd percentile of the
series' own steps is visible and ordinary at the same time.

## 2. The four numbers before the run

**No estimator, no band, no power.** The prediction is again a point, this time
"no change", and what stands in for a band is the measured floor: the same
square in euro must return the same number up to what one shared scalar per
semester can leave behind. **The purchasing-power unit is excluded from the
floor and reported separately.** It is not a single scalar per country and
semester, so it is not forced to cancel, and a floor taken from it would be
about seventy times too high.

**Independent count.** `b_1 = 4 - 4 + 1 = 1`. One country, one loop, read
repeatedly.

**Reachability, and the branch that has to exist.** Before the run: the square
can move above the floor, below it, or not at all, and the premise can hold or
fail. **The premise branch is reachable and it is not a failure of anything**,
which is why it is registered as its own state rather than folded into B50-4's
verdict.

## 3. Carrier and basis

Eurostat bi-annual energy prices, `geo=HU`, the four datasets and the standard
reference bands used throughout this family. All three tax codes computed; one
code on both legs, always. Rounds are entered with their date, their named
percentages, the month of the semester they land in and how many months of the
semester they cover, because **a semester price is an average over six months
and a mid-semester rule is diluted in proportion**.

Full source basis in `data/SOURCES.md`. The record
`results/b50_hungary_class_square.json` carries the criteria wording, the
configuration this run used, and every quantity it produced.
