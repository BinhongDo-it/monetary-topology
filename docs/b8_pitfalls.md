# B8: the pitfalls, each one paid for at least once

Fifty numbered entries, every one of them a mistake that cost at least one full
scan of the archives before it was found. They are kept because the cost of
re-learning any of them is a scan, and because several are not specific to this
stage: roughly two thirds are about measurement practice rather than about
Fannie Mae's files, and they will bite the same way on any dataset large enough
that a full pass is expensive.

**The numbering is frozen.** Entries are cited by number from outside this
repository, so a number is never reused, never renumbered, and never removed.
Entry 5 is a withdrawal, entry 8 is a withdrawal that was itself corrected
twice, and entry 50 is a path this stage knows it has not tested. Those stay in
place with their numbers. A ledger that quietly drops its retracted entries is
worth less than one that keeps them, because the retraction is the part that
tells you which kind of reasoning went wrong.

**Relationship to [`MEASUREMENT.md`](MEASUREMENT.md).** That file carries
nineteen failure modes stated in general form, each with an instance. This file
is the raw incident log those generalisations were distilled from, and it uses
its own numbering. The two do not share a numbering scheme and are told apart by
filename. Where an entry here is an instance of a failure mode there, it says so.

**Where the pointers go.** Section references of the form §N.N are to
[`b8_fannie_slice.md`](b8_fannie_slice.md), the pre-registration, unless the
text names another file. A handful of entries rest on measurements recorded in
B8's inputs-availability register, which is a 259-section deliberation log held
outside this repository; for those the finding is stated here in full rather
than pointed at, so that nothing in this file depends on a document a reader
cannot open.

---

## The entries

1. **The `7` in fields 102 and 106 is a "none of the above" code, not data.**
   An early version tested for truthiness and so read ADR as 62.5% of rows. The
   proof is arithmetic rather than statistical: fields 102 and 106 have
   **identical null counts**, and the difference between their counts of `7`,
   38,356, is exactly the difference between their counts of everything that is
   not `7`. **Only `P`, `C` and `D` count as deferral.**

2. **Field 18 goes blank in the month of modification and does not come back**
   (1.0000 filled the month before, 0.0000 at the modification, at most 0.0056
   the month after). **`omega` therefore takes term from field 17**, which fills
   0.9514 on the worst archive and at least 0.9987 on the other five. Field 19
   agrees with field 17 exactly.

3. **Sampling the head of a file will lie to you.** Field 111 reads 0.0000 in
   every year from 2002 to 2024, 0.0797 in 2025 and 0.9991 in 2026: it was born
   at the end of 2025. The files are sorted by loan, so the head of a file is
   the **earliest calendar months**, and a field with a birth date is
   necessarily empty at the head of an old cohort. **Coverage checks of the C1
   and C6 kind have to run on the full scan.**

4. **Neither field 42 nor field 63 is a durable "has been modified" flag.**
   Field 63 goes blank again on roughly eight tenths of the pre-2008 archives,
   and 2002Q1 contains 1,329 loans that were modified and never carry 63 at all.
   **The first `Y` in field 42 marks the event**, and the `modified` node is
   carried forward from that instant by the analyst rather than by the file. A
   node the data does not label is still a node, and writing that down is the
   honest form.

5. **Withdrawn: "extended to 480 months" does not identify a Flex
   modification.** Cohort and window were confounded in the table that
   suggested it. 2012Q1's modifications straddle HAMP, Flex and COVID and still
   move the maturity date 98.85% of the time, while 2007Q1 sits nine tenths
   inside the HAMP window and moves it only 74% of the time. **What the
   fingerprint actually tracks is the loan's own origination rate**: old
   cohorts originated at 6 to 7% can be rescued by cutting the rate, while newer
   ones originated at 3 to 4.5% can only be rescued by extending the term. The
   consequence is registered at §13.4: **B8-4 has to condition on the cohort's
   rate environment.**

6. **The public files carry no program identifier.** B8-4's restriction to Flex
   can only be proxied by date, and every citation of it has to be labelled a
   proxy. This was ruled on in B8's inputs-availability register, which is held
   outside this repository; the ruling is that the proxy is admissible **only**
   with that label attached.

7. **Loan-level NMDB is restricted use.** What sits in `data/raw/nmdb/` is
   FHFA's aggregate statistics. A borrower-linked panel is therefore CRISM or
   nothing. **This stage is unaffected**, because B8's loop happens entirely
   inside a single loan.

8. **Field 44 and the quiet filter: the original entry was withdrawn, and the
   withdrawal then had to be corrected twice.**
   The original text said "field 44 is not in the quiet filter, so the payoff
   month is in the sample". **That sentence is deleted.** Measured: **field 44 is
   set on none of roughly forty million quiet months across all six archives**,
   so payoff months were never in the quiet sample and `b8_omega.py` needs no
   filter for them.
   **The original was inferred from a rows-per-loan ratio and never counted, and
   the inference was wrong. Any entry reached by a ratio should be counted
   before it is trusted.**
   **Second correction, 2026-08-16: the withdrawal was also wrong.** The field 44
   half stands, but **termination is marked by the balance going to zero, not by
   a zero-balance code**. See entry 13.

9. **`sched_principal` recomputes the payment each month from the current
   balance, while the contractual payment is fixed at origination. Confirmed
   empirically.** Any extra principal payment in the loan's history drops the
   recomputed value below the contractual one, the gap is amplified by
   `(1+i)^n` (a factor of 4.47 at 6.5% over 300 months), and **every subsequent
   month stays high**, with the closed form `ratio = 1 + d*(1+i)^n`. **In the top
   decile, a quiet month in which nothing happened contributes a residual as
   large as a missed payment, with the opposite sign.** Anywhere a payment is
   recomputed from the current balance has this disease.

10. **Taking a mode over bins is broken up by rounding at the cent.** The files
    print UPB to the cent, `obs` inherits that rounding at both ends, and one
    real payment is therefore spread across two or three adjacent bins, so
    "more than one candidate" fired on all five segments of the synthetic
    archive. **Cluster instead of binning**, take the cluster mean as the
    estimate, and keep the cent grid out of the estimate entirely.

11. **Taking a minimum as a robust estimator is not robust.** The first version
    of C8-1c used the smallest implied payment inside a segment, so a single
    flat-UPB or interest-only month punched through the whole segment, and the
    run silently dropped 46.5% of months without counting them. **When changing
    an estimator, first ask whether the new one can read an impossible value
    when the hypothesis is true**: that version's `lower bound / recomputed`
    ratio read 0.75, and under the hypothesis it cannot be below 1.

12. **C0b's anchor only reached field 44**, so the sentence "positions 1 to 108
    are unchanged" went past its own evidence at the time; 45 to 108 were
    confirmed later, by behaviour. It is recorded because the same kind of
    overreach has happened three times in this repository.

13. **Every loan's first UPB row is zero, and so is every row after
    termination.** All six archives read 1.0000 with no exceptions, at 6.70 to
    6.94 rows per loan, which is 8.6% to 19.6% of all rows. **This is a
    reporting convention rather than a data quality problem.** It let the
    "positive then zero" pair through the old quiet filter with `obs` equal to
    the entire balance. **The filter now requires `upb[current row] > 0`.**
    **Any table anchored on a loan's first row has to clear this first**: the
    noise-floor table came back empty on all six archives for two consecutive
    rounds because of it.
    **Same-day correction: the sentence "it let the positive-then-zero pairs
    through the old filter" was an inference, and measurement says it is wrong.
    The correction removes zero pairs on all six archives.** What actually
    blocked them is that **the remaining legal term is blank on the payoff row**
    (5 / 2 / 5 / 1 / 0 / 0 slipped through across the six), with a blank note
    rate as the backup. **A termination row reports a zero balance and then
    stops reporting contractual state altogether.** The correction is kept, with
    the status of a guard rather than a fix.

14. **Any property that is safe only because of an incidental precondition will
    blow up at the next stage that does not carry it.** Entry 13 did not blow up
    earlier only because `quiet_pairs` requires the previous row to be positive
    and `find_clean_cures` requires `t0` to be positive. **Every reading was
    saved by accident rather than on purpose**, which is not the same thing and
    does not travel.

15. **Two tolerances from two different sources is a construction defect,
    independently of whether the criterion passes or fails.** B8-0a's first
    round paired a path tolerance of `$0.05` with a conformity bound derived
    from half a cent, and the second is ten times tighter, so a loop off by two
    or three cents necessarily passes the path filter and then breaks a bound
    that allows half a cent. **Every number in a criterion needs a source.**

16. **`nanmax` swallows non-finite values from upstream in silence.** The closed
    form cannot take a logarithm when `f(B0) <= 0`, and those loops were being
    swallowed and not counted (6 / 2 / 1 / 3 / 1 / 0 by archive). **A small
    count is not a reason not to report it.** This is the silent discard that
    this same ledger complains about elsewhere.

17. **Contamination asserted by inference is not contamination until it is
    counted.** This is the mirror of entry 14, committed on the same data a few
    hours apart: going from "rows of this kind exist in the file" to "they will
    enter the sample" skips over "has some other condition already excluded
    them", **and that step can only be measured, never reasoned**. The
    aggravated form: **an existing reading must not be used to retro-fit an
    unverified mechanism.** Saying "p90 reads 2.00 to 2.12, which is exactly the
    shape it would have" is that usage, and it conscripts a coincidence as
    evidence.

18. **A rerun whose output cannot be differenced against the old definition has
    not discharged the obligation to report both.** Four scripts were rerun
    after a definition change and printed the new numbers, and **not one printed
    `n_dropped_cur_zero`**, which the filter computes and returns. The old
    outputs were then overwritten with no `.expired` copy kept. **Print the delta
    in the same change that alters the definition, or expire the old results
    file first.**

19. **A cached test fixture expires, and an equivalence check that does not
    require its two sides to differ passes vacuously.** **Second half, learned by
    stepping on it again the same day: the fixture's name has to hang off the
    source file that writes it, not off some other one.** `b8_triangles.py` named
    its fixture after `b8_core`'s generator hash while the thing being edited was
    its own case table, so the hash did not move, the stale archive was reused,
    and the run reported "1 loans".

20. **The core table's `period` is a month index, not `YYYYMM`.** It stores
    months since 1990-01 packed into a `uint16`, which cannot hold `201701` at
    all. Comparing a `YYYYMM` literal against a window boundary puts every
    record outside every window. **This one at least fails loudly**, rather than
    quietly returning a plausible-looking number.

21. **A published band table for one field cannot share a bander between its
    upper-bound form and its lower-bound form.** The LLPA grid writes its LTV
    columns as `<30.00 / 30.01-60.00 / ...`, which is an upper bound, and its
    FICO rows as `>=780 / 760-779 / ...`, which is a lower bound. One cut
    function for both puts every integer LTV one column too high. **The selftest
    has to use values pressed against the edges**, 29 / 30 / 31 / 60 / 61, not
    random ones.
    A second failure rode on the first. Selftest fixtures stay on disk once
    written, which is a direct consequence of the rule against deleting. After
    the generator changed, machines that had run the old version reused the old
    archive, and the newly added check read "0 of 23,389 removed". **The check
    caught it itself, because it requires the two conventions to actually differ
    on the fixture.** Fixture filenames now carry an eight-character hash of the
    generator's source, so a stale one is unreachable without being deleted.

22. **A table that prints a minimum without printing which stratum it fell in
    cannot separate "the indicator is thin" from "the empty stratum is thin".**
    Those two call for completely different rulings. **§15.5 requires B8-4 to
    print its loadings, and the same requirement holds for C9 itself**, which
    the first version did not do; it was caught by reading its own output.

23. **One numeric value must not mean both "identical" and "nothing to
    compare".** A maximum over an empty set is zero, which prints exactly like
    "the two sides agree"; a range over zero measurable samples is `0.000e+00`,
    which prints exactly like "measured, and it is zero". **Committed twice in
    one round** (the curve cross-check table, and the range over deferral rows),
    now `no overlap` and `not measurable` respectively. This is the other face
    of entry 22.

24. **Do not infer implementation behaviour from design intent without reading
    the code or measuring.** The claim was "term moves in the month of
    modification, `k` differs on the `V` and `V-hat` sides, and the curve enters
    there", whereas `r_month`'s two legs share a single `n_now` and the curve
    enters only through the deferred balloon term. Measuring the wrong object on
    that basis produced a noise floor 267 to 7,110 times too large; the true
    value is eight orders of magnitude lower. **One line of the signature shows
    this.**

25. **Contract-term breakpoints are shattered by blank rates.** A blank rate
    stored as the sentinel 65535 fires the breakpoint test twice, splitting
    968,761 loans into 1,944,756 segments and collapsing per-loan coverage to
    0.52%. **Fill field 9 only**: blanks in fields 42 and 63 are state rather
    than gaps, and filling them erases the leading edge of a deferral.
    Attribution has to reconcile exactly, and it does: the excess breakpoint
    count **equals** the blank-rate row count, on all six archives.

26. **Fixing a defect in one place in a file is not fixing the file.** Entry 23,
    the empty set printing zero, had already been changed to `not measurable` in
    §2 of `results/b8_cmt_sensitivity2.md`, **while §3's three columns for loops
    with a balloon, their p50 and their max went on printing `0` and
    `0.000e+00`**. Same round, same file, recurring one section later. **A defect
    of this kind needs a file-wide search for the same written shape, not a fix
    at the point where it was noticed.**

27. **Four decimal places cannot hold a floor of 1e-5.** The `floor` column in
    §1 of `results/b8_c10_contract_move.md` printed `0.0000` for all three
    archives, where 2017Q1 was about five rows (3.98e-5) and the other two were
    **exactly zero**; the only thing separating them was whether an adjacent
    column printed a number or a dash. **Print a count beside every ratio.**
    This is the third appearance of entry 23's family and an instance of entry
    26: that round changed the **empty** arm to `not measurable` and **left the
    arm that rounds to zero alone**. The floor of 6.74e-5 happened to be the
    most load-bearing number in the section.

28. **"The function did not raise" is not "the output is complete".** C10-3's
    window table was computed inside `measure`, and the string substitution that
    was supposed to add that section to `render` **had the escaped quotes wrong
    in its target and so silently changed nothing**, while the patch script
    printed "patched" regardless. The selftest only checked that `render` does
    not throw, so it passed, **and a results file missing an entire section went
    out, wasting a full run.** Two cheap antidotes: **assert after every
    `str.replace`**, and **make the writer's selftest assert that every section
    heading appears in the output**, rather than asserting that it runs. Same
    family as entries 19 and 26: a check that does not require its two sides to
    differ passes vacuously.

29. **A conjunctive criterion, decided after reading half of it.** §14.4 defines
    `deferred` as "the rate does not move **and** the maturity date does not
    move". Seeing post-2022 `rate` read 0.0082, the note written down was "that
    is exactly the shape a payment deferral should have", **while `term` on the
    same row read 0.9950**. **Both columns were printed. The error was in the
    reading, not the measurement.** This repository has other conjunctive
    criteria: B8-0a's two tolerances, and C9's two gates, where §16.12 says
    explicitly that the gates are independent and both must pass. **Antidote:
    print the conjunction itself as a column** (`still`, the share where both
    are unmoved) rather than leaving the reader to conjoin two columns.

30. **A selftest has to take the path `run` takes, configuration included.**
    `defer_amt` was added to `find_loops` and to C10's clean-cure count, all
    three selftests went green, and `census` died on the first real run with
    `KeyError: 'defer_amt'`. The selftest opened `Core` without `cols=` and so
    received every column, while `run` uses an explicit list, **and that list was
    missing the new column where no test could see it**. It happened twice in the
    same round: `against_triangles` is likewise only called by `census`, and the
    first version read the returned key as `["tri"]` when it is `["triangle"]`.
    **Antidote: lift `run`'s configuration into a module constant and have the
    selftest use the same constant.**
    **Third occurrence, 2026-08-17, same entry.** `b8_omega.probe`'s list was
    missing `defer_amt`, and `b8_omega`'s selftest **never enters `probe`**, so it
    could only exercise the `V` and `r_month` properties. A guard did catch it,
    `quiet_pairs` raising an explicit `KeyError`, but it caught it on the real
    archive. **A guard that only fires in production fires too late.** The
    selftest now runs `probe` end to end on `b8_core`'s fixture.
    **Fourth occurrence, same day.** `b8_0a_gate`'s selftest was pure arithmetic
    and never opened `Core`, so `GATE_COLS` had never been checked either.
    **The fix, landed the same day**: the column list of all seven scripts was
    lifted into a module constant with the selftest using the same constant, plus
    `scripts/b8_col_sweep.py`, which **deletes one column at a time and reruns the
    selftest; if it still passes, that column is not covered**. The first sweep
    over 55 columns found two kinds: `b8_c10_4_tier_carrier`'s selftest opened
    every column, a real gap; and once that was fixed, `delinq` and `mod_flag`
    swept out as **dead entries**, present in the list and read by no code. **A
    list with more names than uses is a list nobody can audit.** All 55 columns
    are now covered. **Run `python scripts/b8_col_sweep.py` after adding any
    `cols=`.** Mutation check: delete `defer_amt` from the constant and two
    selftests raise `KeyError` immediately.

31. **A disclaimer block inside a writer expires quietly.** The "What this does
    not decide" block in `b8_c10_contract_move.md` said "Field 63 is used" for an
    entire round in which the cut was on field 108. **That sentence was prose
    baked into the renderer, with nothing watching it.** **Antidote: derive it
    from the constant.** `b8_loops.DEFER_FIELD` and `MOD_FIELDS` are now values,
    the writer renders from them, and the selftest asserts that the field
    actually in use appears in the results file and that the retired sentence
    does not. **Every results file in this repository has a block like this, and
    the same applies to all of them.**

32. **A mode over zero candidates still prints as a number.** §1 of
    `b8_c11_deferred_balance.md` printed modal ratios of 5.12 / 3.40 and so on
    **while the `candidates` column on the same rows was 0**, meaning no cluster
    reached even a tenth. With no mode, `max(clusters, key=len)` returns the
    first single point, **and its value prints exactly like a measured mode**.
    Fourth appearance of entry 23's family in this stage. **Antidote: print
    `no mode` when the candidate count is zero**, and have the selftest assert
    that zero candidates cannot print a number.

33. **After adding a check, verify that it is alive, and the way to verify it is
    to make the thing it should catch happen once.** When
    `check_markdown_tables` was added on 2026-08-17 it appended to `b8_omega`'s
    `fails`, which that function empties further up, so **the checker itself was
    inert**. Injecting a three-column table under a two-column header, two of the
    eight writers reported INERT: one real, and one a false positive from the
    injector cutting inside a string. **The mistake made while adding the checker
    was the kind of mistake the checker exists to catch.**
    `scripts/b8_col_sweep.py` is the other half of the same idea.

34. **A name outlives the fact it names, and no arithmetic test can see a
    name.** `b8_omega.V`'s balloon parameter was called `nib` and read field 63,
    on the strength of one docstring that called field 63 the deferral. After
    C10-4 ruled that field 63 is re-contracting and that the deferral carrier is
    field 108, **that parameter name and the whole reading beneath it survived in
    the file for another day**, while all five of that file's property proofs
    kept passing, **because not one of them opens an archive**. The fix has two
    halves: rename the parameter to `zib`, which is named after no field at all;
    and a **structural** change registered in B8's inputs-availability register,
    collapsing three readings into a single expression with no branch, so that
    "cut the wrong column" stops existing at the implementation level instead of
    being caught by a test. **Eliminating a defect structurally beats measuring
    it.**

35. **When two fields agree to 99.78%, reading the wrong one is invisible in
    every number.** §14.1 attaches the balloon to field 19 and the code attached
    it to field 17, and C11-3 measured their agreement at 0.9978 or better. **No
    reading can expose this error**, and neither can a fixture, because the
    fixture was built from the real file and the two columns agree there too.
    **Two treatments**: `V` raises when the balloon is positive and the balloon
    term is absent, with no silent default permitted; and the fixture gains **one
    loan built specifically with field 19 offset by five months**, with the
    selftest asserting that what is read back is `field 17 + 5`. **When two
    sources agree, the fixture has to make them disagree on purpose, or the test
    is testing a coincidence.**

36. **A checker that cries wolf gets its output skimmed, and skimming is how the
    real warnings are missed.** `check_markdown_tables` split cells on `|`
    without honouring an escaped `\|`, and so raised a false alarm on C12's table
    containing `|dP|/P`. **The worse half**: the same bug miscounts cells in
    **genuinely** wide rows of any table containing an escaped pipe, which hides
    them. Fixed, and the checker now has eight test cases of its own. **A check
    that misreports will have its output skimmed, and skimming is exactly how the
    broken file in entry 33 went out.**

37. **An assertion that can fail in principle need not be able to fail under the
    implementation you are about to adopt.** §17.11 registers
    `leg1 + leg2 + leg3 == omega(loop)` with the stated reason that it catches
    window misalignment. All four quantities come from the same prefix-sum array,
    so **the three legs telescope and the identity holds for any `t_M`**: off by
    one row, off by ten, even a row belonging to a different loan. That assertion
    tests the floating-point adder. **How to verify: move `t_M` by one row on
    purpose and assert that it still holds; if it does, the assertion is empty.**
    Only after adding `replay`, which recomputes month by month in Python from
    the window indices, was there something that can actually catch it. **When
    writing an assertion, work out how it fails under the implementation, not how
    it fails in principle.**

38. **Two readings agree bit for bit on quiet months, so the wrong one
    survived.** §14.2's `V-hat` is "the contract as of `t-1`, rolled forward one
    month: same rate, term minus one", while `r_month`'s two legs share
    `note_pct` and `n_now`. On a quiet month the rate does not move and
    `n_now == n_prev - 1`, so **the two readings are identical**, and P1 through
    P5 pass under both. **The only place they part is the month of modification,
    which is the single month leg 2 covers and the dominant term of §14.3.**
    Measured on a 2% rate cut with a 120-month extension: `+1.670e-03` against
    `-1.792e-01`, **two orders of magnitude apart and opposite in sign.** The
    other half of the same entry: the counterfactual needs the payment from the
    **previous** row, the one from the contract term before the modification. **A
    defect that only parts company in the event month is invisible to a property
    set that only exercises quiet months.**

39. **No amount of structural checking pins down a value.** With the loop
    assembly's range helpers, masks, telescoping and `replay` all green, "the
    counterfactual takes this row's payment" and "`V-hat`'s balloon term was not
    rolled forward a month" **both walked straight through**, because both
    produce entirely self-consistent numbers. **Treatment: hand-compute three
    rows against §14.2**, taking the payment directly from the fixture
    generator's constant rather than from anything the code estimates. Three rows
    is the minimum: only the row with the balloon **standing on both sides** makes
    `V-hat`'s own balloon term multiply to something non-zero, **and without it
    that parameter can be written any way at all without changing a single number
    in this repository.** When pinning a value, ask which row makes each
    parameter first multiply to something non-zero.

40. **Entry 30 has a second shape: a "function" that `run` calls and `selftest`
    does not.** `b8_loop_omega` died on its first real run inside `curve_table`,
    because `b8_cmt_fetch.load_treasury()` returns `(dict, filename)` and the
    whole tuple was passed through. **The selftest had never entered that
    function**, since it builds its own table with `_flat_curve`, leaving the
    entire loader boundary at zero coverage. An out-of-date type annotation
    `-> dict` helped it along, which is entry 34 applied to types.
    **`b8_col_sweep.py` cannot find this class: it deletes columns, not calls.**
    **Treatment:** split the pure half into `curve_table_from`, have the selftest
    build a source in the loader's **exact** format, **then call the real loader
    and assert its return shape** (it can be called with no data), and finally run
    `curve_table` end to end against a stub of that same shape. **The first step
    is what makes the second honest: a stub whose shape was imagined will
    faithfully reproduce the very defect it was supposed to catch.**
    **Census method**: for every script with both a `run` and a `selftest` entry
    point, list the calls that appear only on the `run` side and ask of each
    whether the selftest reaches it. **Only this one script has been swept.**
    **Fifth occurrence, same day.** `b8_c13_double_balance`'s `closest` column
    went on printing a winner even when the "none of the four definitions match"
    branch had already fired. **The least bad of four bad readings, printed like a
    measurement.** Now prints `none close (best X)` above the threshold. **A
    threshold needs a source**: C11's criterion B, anchored on the same file,
    reads 0.0000, and the cent grid puts the lower bound at 1e-5, so 1e-2 is a
    defensible boundary.

41. **A statistic that moves by orders of magnitude under defensible population
    choices has a problem in the statistic, not in the population.** B8-0b's
    floor was run four times, and `sqrt(Z)/sqrt(N)` on the modification arm went
    1.45, then 54.70, then 1,008, each time under a justified population
    correction (all clean cures, then the ideal path, then adding balance
    matching). **After the third the question to ask was not which population but
    what the variance is estimating on this distribution.** The convergence table
    answered it: the floor's `2*Var` climbs by a factor of 2,900 from n=100 to
    the full sample and is still climbing, and the p10 to p90 spread grows to
    293x, while the MAD on the same arm is flat from n=100 onward.
    **Diagnostic: resample the statistic at several values of n and see whether
    it settles. Three lines of code, and it should have been run early.**

42. **A registered suspect is not a suspect either; it also has to be
    measured.** The freeze-as-tail mechanism was registered in B8's
    inputs-availability register and reads entirely plausibly. Measurement says
    freezes produce **positive** residuals while the tail is uniformly large and
    negative, and that the presence of a freeze is actually *higher* in the rest
    of the population (0.989 against 0.939). The real cause is **payoff**: a
    two-hundred-thousand-dollar loan walking down to one cent over nine months
    with the delinquency field reading `00`, with five loans carrying 78% of the
    floor. **A mechanism that is written into the registration and sounds right
    still needs a column of numbers to rule it out.**

43. **A zero calibration has to be drawn on the branch where the true value is
    zero, and the registration text has usually already split that branch out.**
    §14.5 had long since divided B8-0a into (i) the ideal path, where the loop
    sum is an arithmetic zero, and (ii) the path with fees and capitalisation,
    which in §14.5's own words returns non-zero for real reasons. The floor was
    drawn on (ii). **The fix needs no new threshold at all**, because
    `episode_sums` already returns an `ideal` flag. Before looking for a floor,
    ask whether the registration already contains a branch on which the true
    value is zero.

44. **Two sentences in one repository can contradict each other for a long time,
    and you will read the wrong one.** §14.5 says B8-0a(i) "must return zero to
    floating-point tolerance", while P4 in `b8_omega.py` **simultaneously proves
    and asserts** that it does not, its comment reading "The clean-cure round
    trip does NOT return zero, and this is a property of the construction". The
    floor search read §14.5, **so a deterministic quantity was mistaken for
    noise**, at a cost of two extra rounds. Measured `corr(omega, closed)` is
    `+1.0000` across all five bands. **When prose and an assertion disagree, the
    assertion is the one that is right**, because it has run. **Available census**:
    check every "must return X" sentence in the registration against the
    corresponding assertion in the code.

45. **A floor is not necessarily noise. Ask first whether it can be computed.**
    B8-0b's floor measured 2.7e-6 to 1.4e-5, which looks exactly like measurement
    noise, **and is in fact `loop_residual_ideal`, a deterministic function of
    `(B0, i, P, k)`**. Subtracting it leaves 2.68e-08 to 5.22e-08, against a
    median balance on this arm of 165,000, **and half a cent divided by that is
    3.03e-08**. The real floor is the fact that field 12 is written to the cent.
    **Diagnostic: correlate the floor against some known closed-form quantity.
    One line of `np.corrcoef`.**

46. **In a decomposition that sums to a fixed total, every term can be wrong
    while the total stays right.** Leg 2 splits into
    `balance + repricing + remainder`, where the remainder is by definition leg 2
    minus the first two, so "the three sum to leg 2" is **identically true** and
    proves nothing. Only one thing can actually falsify it: **on a loop with no
    zero-interest balance, `V = B*k` is an identity, so the remainder must be zero
    to floating point.** Splitting `repricing` further into `rate` / `term` /
    `cross` makes the same disease worse: two of the terms difference against the
    same baseline and `cross` is the residual, so **computing `rate` as the whole
    repricing, or as identically zero, both reconcile.** A mutation test fired ten
    shots: the core-table checks caught six, **and all three of the `rate` and
    `term` shots survived**, which is exactly what §2.1's reading rests on.
    **Treatment**: split the pure arithmetic out of the table reader into
    `leg2_terms` and drive it from hand-computed numbers in the selftest. Move
    only the rate, and `term` must be exactly zero while `rate` must equal the
    whole repricing; move only the term, and the reverse; move both, and neither
    may be zero while `cross` must be non-zero. **Plus one positive shot**: feed a
    leg 2 whose first two terms leave 0.25 unexplained, and the remainder must be
    exactly 0.25, without which an implementation that returns an identically zero
    remainder passes everything else. After the fix, all ten shots die.
    **This is entry 39 in the shape of a decomposition**: structural checks do not
    pin down numbers, and pinning them down requires a worked example whose answer
    is known in advance.
    **The other half**: `loop_sums` writes `0.0` into `leg2` for months it cannot
    read, and differencing two finite terms against that zero prints an enormous
    false remainder **on precisely the loops that were dropped**. Every downstream
    stage filters on `measurable` first, so nothing exploded, **but a field that
    lies unless it is filtered is the shape of half this ledger**, and the mask has
    been moved inside the function that produces it.
    **One more**: `k`'s two analytic properties (exactly one when `d = i`; greater
    than one and rising in `n` when `d < i`, reversed when `d > i`) are **used to
    interpret the measurement**, so they are asserted rather than left in prose.

47. **When a criterion's pass rate varies with the coarseness of the strata, it
    is measuring the coarseness of the strata.** §22.4 of B8-5 says the class
    ordering is stable across the follow-up horizon `H`, implemented as the whole
    ordering being identical across five values of `H`. Measured: 51% at two
    strata, 24% at three, 4.4% at five, **and not one of 155 cells passes at seven
    or more**. A `k`-stratum ordering has `k!` arrangements and five readings must
    land on the same one, which is combinatorial; and more strata means thinner
    strata and noisier rates, which is statistical. **Neither is censoring, and
    this criterion exists to detect censoring.**
    **Diagnostic, worth keeping**: plot the criterion's pass rate grouped by the
    degrees of freedom of a cell. **Monotone collapse toward zero means the
    criterion is measuring its own difficulty.**
    Treatment: `range` is `max - min`, so what has to be stable is the two strata
    that attain the highest and lowest rates, and turnover in the middle moves no
    reported digit. **Both ends matter**: turnover at the bottom is a change in
    which class has the lowest access. Old readings are kept side by side under
    R01, with the minimum stratum count printed per cell.
    **The second item in the same round is semantic rather than a typo**: the exit
    was originally taken as the first one in time, so every path of the form
    "cured, then delinquent again, then modified again" was recorded as `cured` and
    fell out of the numerator. §5 asks whether that edge was ever traversed, **not
    whether it was traversed first**. The numerator is now unconditionally "ever
    modified within the window", with the other three competing only for
    descriptive columns. **Mutation testing is blind to both of these**, because
    both are cases of "the code does what it was written to do, and what it was
    written to do was wrong".

48. **`abs(nan - x) > tol` is False, so a check written that way can never
    fail.** A review round found four assertions in freshly written code all of
    this shape. The root cause is not in the assertions but **in the fixture being
    smaller than `MIN_CELL`**: `b8_loops`'s fixture has 5 modification loops and 2
    clean cures against a production floor of 20, so `ratio()` returns NaN on both
    arms and all four comparisons compare NaN against a number.
    **Diagnostic**: any check written as `abs(got - want) > tol` must be preceded
    by an assertion that `got` is finite, or written as `not (abs(...) <= tol)`,
    which does fire on NaN.

49. **When two quantities are identical inside a fixture, no check based on that
    fixture can tell them apart.** B8-1's net arm subtracts `l1_closed`, and
    `b8_loops`'s fixture makes leg 1 equal the closed form row by row **by
    construction** (flat delinquency, which entry 10 introduced and B8-0a needs).
    So "subtract `leg1`" and "subtract `l1_closed`" give the same number on the
    fixture and the mutation survives. On real archives the two differ by 23% to
    57%. **Treatment**: give `analyse` a data injection point and have the
    selftest pass in a copy with `l1_closed` multiplied by three; the net arm has
    to move. **What a fixture cannot prove should not be proved with a fixture.**

50. **Still untested, recorded as such.** Propagating `b8_4_class`'s class gate
    into the permutation null and the equal-`n` recompute is **correct in the
    code and survives mutation**, because the fixture has only 5 loops and 2 cures,
    so the gate can only fire in its no-floor form, and in that form `_blocks`'s
    column count and the observed column count are both zero, leaving the check
    comparing zero against zero. The exposure on real archives is 1 cell out of 22
    (2012Q1 `dti_complement15`, `gated=1`). **No fixture will be built for it**; it
    is registered as a known untested path.
    The invariant that would have to be pinned, for whoever revisits this: the
    `live_cls` selected by the gate has to reach both `perm_null`'s blocks and
    `equal_n`, or the observed statistic and its null are drawn on different class
    sets, which is what B8-5 was fixed for.
