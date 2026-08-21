"""B10 / §24 step one: earn the origination-side class fields by behaviour.

Pre-registered in the B10 availability register §24, **before this file
was written**. §24.6 fixes three steps and this file currently implements the
first two commands only (``--selftest`` and ``--depth``); ``--triangles`` and
``--run`` are the next two chunks and are deliberately absent rather than
stubbed, because a stub that prints nothing reads the same as a step that found
nothing.

The hole this closes
--------------------
§24.1: `experiments/` holds **no Freddie-side triangle script at all**, and
`results/` holds no matching file. §3's per-vintage triangle table, §4's four
window counts, §5's twelve-cell thinnest cell of 57 and §6's nine-cell cross
all came out of one scan that left no code. More precisely, §5 says it binned
by *FICO band x LTV band x DTI band* and **the orig-side positions of FICO, LTV
and DTI are written down nowhere in the repository** (§10 records only orig 11,
13 and 22). Those three positions exist only inside a run that is gone.

So this file does not take them from a layout document either. It earns them.

C0b, and what "earn" means here
-------------------------------
C0b: a field is identified by **behaviour**, not by the look of its values and
not by a layout document. That rule has a seam this file names out loud:

    **Appearance is allowed to enumerate. Only behaviour is allowed to pick.**

So every anchor below runs in two stages. A cheap appearance filter proposes
candidate columns (discipline 12: enumerate before choosing), and then a
behavioural test scores every candidate and the winner is whichever column the
behaviour selects. **The field position is an output of the anchor, not an
input to it.** The runner-up and the margin print beside the winner, because a
winner with no margin is a coincidence wearing an identification.

The four anchors, one per field, all origination-side
-----------------------------------------------------
`--depth` reads the orig member only. That is deliberate: §24.6 step one says
"no triangles, no cells", and an anchor that needed the performance side would
have dragged 74.94M rows into a step whose whole point is to be cheap.

* **FICO -- it prices the loan.** Within a vintage, loans with the lower score
  carry the higher note rate, because that is what the LLPA matrix does. The
  test is run **inside each vintage** and counted across vintages, since the
  coupon level moves with the origination year and pooling would confound the
  two. LTV prices in the opposite direction, so this anchor separates them by
  sign rather than by range.
* **DTI -- the underwriting cap shows up as a cliff.** The GSE maximum DTI was
  45 and later 50, so the histogram has a hard one-step drop there. A policy
  limit appearing as an edge in the distribution is behaviour, not appearance.
* **first-time buyer -- it implies purchase.** A first-time buyer cannot be
  refinancing. So there is a value `y` of one column and a value `p` of another
  with `P(col_B = p | col_A = y)` at essentially one. **This anchor identifies
  both columns and both value codes at once**, which is why it is written as
  one joint search over column pairs rather than two separate ones.
* **purpose -- refinancing is rate-driven.** Across the 28 vintages, the share
  of the refinance levels moves against the vintage's coupon level and the
  purchase level's share moves with it. That is a second anchor for `purpose`,
  independent of the first, and it is here because the joint anchor alone
  pins the pair without saying which member is which on its own.

Usage::

    python experiments/b10_cohort_width.py --selftest
    python experiments/b10_cohort_width.py --depth

Writes ``results/b10_cohort_width_depth.json``, ``diagnostic_only``.
**No `omega`. No B8 prediction. No triangles.** (§24.7)
"""

from __future__ import annotations

import argparse
import ast
import io
import random
import json
import math
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RAW = ROOT / "data" / "raw" / "FreddieMac"

#: Vintages on disk. The range is read from the directory, not asserted, so a
#: missing archive shows up as an absent row instead of a crash.
VINTAGE_RANGE = range(1999, 2027)

#: Confirmed against the files themselves by `b10_c8_1d_freddie.py --depth`,
#: twenty-eight archives all reading 31 (§11.1). Re-checked here.
ORIG_FIELDS = 31

#: Already earned in §10.1 and therefore **excluded from every candidate set**:
#: a column cannot be earned twice, and leaving the note rate in the FICO
#: candidate set would let it win its own anchor trivially.
O_UPB, O_RATE, O_AMORT, O_SEQ, O_TERM = 10, 12, 15, 19, 21
EARNED = {O_UPB: "orig UPB", O_RATE: "note rate", O_AMORT: "amort type",
          O_SEQ: "loan seq", O_TERM: "orig term"}

#: **§24.1's hole, closed.** These four positions existed nowhere in the
#: repository: §5 binned by FICO, LTV and DTI without ever writing down where
#: they are. They are here now, and they are here **because the anchors picked
#: them** on the 2026-08-17 run over twenty-eight vintages, not because a
#: layout document says so:
#:
#:   FICO     col 0   band-ordered coupon in 26/28 vintages, runner-up 4/28
#:   DTI      col 9   the only column whose largest cliff is a GSE cap, and it
#:                    has one at each: 15,492 at 45 and 23,980 at 50
#:   fthb     col 2   `Y` implies purchase with 0 counterexamples on 208,886
#:   purpose  col 20  the consequent of that implication, code `P`
#:
#: `--depth` re-derives them every run and **prints a mismatch loudly** rather
#: than letting the constant quietly win. A constant that the anchor is
#: compared against is only safe while the comparison is printed.
O_FICO, O_DTI, O_FTHB, O_PURPOSE = 0, 9, 2, 20
ANCHORED = {"fico": O_FICO, "dti": O_DTI, "fthb": O_FTHB,
            "purpose": O_PURPOSE}
ANCHORED_CODES = {"fthb_purchase": "Y", "purpose_purchase": "P"}

#: §24.3: borrowed from C9 §2 wholesale, boundaries and all. **These are
#: Fannie's LLPA divisions applied to Freddie loans**, which §24.3 registers as
#: a deliberate choice made for comparability with C9's table. FICO is written
#: with lower bounds; LTV with upper bounds (C9 §2.1, and the first Fannie-side
#: version got that backwards). Only FICO is used in this file.
FICO_CUTS = (780, 760, 740, 720, 700, 680, 660, 640)

#: The GSE underwriting caps the DTI anchor looks for. **Two values, not one**,
#: because the cap moved: 45 for most of the sample, 50 from 2017.
DTI_CAPS = (45, 50)

#: Appearance filters. They enumerate candidates and **never pick** (see the
#: module docstring). Written as constants so the enumeration is auditable.
#:
#: **The first version had range filters here and they were wrong.** It asked
#: FICO's maximum to be at most 850 and DTI's at most 65, and both fields carry
#: a missing code (`9999` and `999`), so both were filtered out of their own
#: candidate sets and `--depth` printed an empty FICO candidate list. A missing
#: code is not a value of the quantity, so those filters were not tight, they
#: were **wrong about what a value is**. They are gone. The candidate sets are
#: now "numeric and not already earned", and the behavioural anchors do all the
#: picking, which is what C0b asks for and is **harder**, not easier: nothing is
#: excluded before the behaviour speaks.
DTI_WINDOW = (1, 65)
FTHB_MAX_LEVELS = 3
PURPOSE_LEVELS = (3, 6)

#: A column blank on this share of rows carries no behaviour to identify it by,
#: so it cannot be a candidate. **Structural, not tuned**: the anchors are
#: statements about how a field's values behave, and a field with no values on
#: 95% of rows has nothing for them to bite on. The excluded columns print.
MAX_BLANK_SHARE = 0.5

#: A level has to carry this share before an implication over it means
#: anything. **Structural**: the implication `A = y  =>  B = p` is vacuous when
#: `A = y` is almost empty, and a vacuous implication scores 1.000.
MIN_LEVEL_SHARE = 0.01


# ---------------------------------------------------------------------------
# Reading. Streamed out of the archives, nothing extracted. Same shape as
# `b10_c8_1d_freddie.py` on purpose: one reader, one place to get it wrong.
# ---------------------------------------------------------------------------

def archive(vintage: int) -> Path:
    return RAW / f"sample_{vintage}.zip"


def orig_rows(vintage: int):
    """Yield the split fields of every origination row of one vintage."""
    with zipfile.ZipFile(archive(vintage)) as zf:
        with zf.open(f"sample_orig_{vintage}.txt") as raw:
            for line in io.TextIOWrapper(raw, encoding="utf-8", newline=""):
                line = line.rstrip("\r\n")
                if line:
                    yield line.split("|")


def vintages_on_disk() -> list:
    return [v for v in VINTAGE_RANGE if archive(v).exists()]


# ---------------------------------------------------------------------------
# Column profile. Appearance only, and labelled as such.
# ---------------------------------------------------------------------------

def profile(vintages, cap_distinct: int = 40) -> list:
    """One record per orig column: counts, range, and the commonest values.

    **This is the enumeration step and nothing else.** Discipline 12 wants the
    whole field set on the table before anything is chosen, and §2 already did
    that for the performance side; the origination side never got it.
    """
    cols = [{"i": i, "rows": 0, "blank": 0, "numeric": 0, "int": 0,
             "lo": None, "hi": None, "vals": Counter(), "over_cap": False,
             "seen": set()}
            for i in range(ORIG_FIELDS)]
    widths = Counter()
    for v in vintages:
        for f in orig_rows(v):
            widths[len(f)] += 1
            for i in range(min(len(f), ORIG_FIELDS)):
                c, s = cols[i], f[i].strip()
                c["rows"] += 1
                if not s:
                    c["blank"] += 1
                    continue
                # **The distinct count has to be its own counter.** The first
                # version read the level count off `most_common(5)`, which is
                # capped at five by construction, so every column with five or
                # more values reported exactly five and the `purpose` candidate
                # set filled up with mortgage-insurance percentages and unit
                # counts. A count that cannot exceed five is not a count.
                if len(c["seen"]) < cap_distinct:
                    c["seen"].add(s)
                elif s not in c["seen"]:
                    c["over_cap"] = True
                c["vals"][s] += 1
                try:
                    x = float(s)
                except ValueError:
                    continue
                c["numeric"] += 1
                if s.lstrip("+-").isdigit():
                    c["int"] += 1
                c["lo"] = x if c["lo"] is None else min(c["lo"], x)
                c["hi"] = x if c["hi"] is None else max(c["hi"], x)
    for c in cols:
        c["top"] = c["vals"].most_common(5)
        c["n_distinct"] = len(c["seen"])
        del c["vals"], c["seen"]
    return cols, widths


# ---------------------------------------------------------------------------
# Anchors. Each returns a score per candidate column; the winner is the column
# the behaviour picks, and the runner-up prints beside it.
# ---------------------------------------------------------------------------

def fico_band(score: int) -> int:
    """Index into C9's nine LLPA bands, 0 = highest score. Lower bounds."""
    for k, cut in enumerate(FICO_CUTS):
        if score >= cut:
            return k
    return len(FICO_CUTS)


#: A band needs this many loans in a vintage before its median rate means
#: anything. **Structural**: it is a median, and the anchor compares medians
#: across bands, so a band of three loans would let one loan flip an ordering.
MIN_BAND_N = 100

#: How many of C9's nine bands a column must populate before the ordering test
#: has anything to order. **Structural, and it is what does the identifying**:
#: the bands are FICO's own pricing divisions (§24.3), so a column whose values
#: collapse into one or two of them is not the field they divide.
MIN_BANDS_POPULATED = 5


def anchor_fico(per_vintage: dict, candidates) -> dict:
    """Median note rate is monotone across **C9's nine LLPA bands**, per vintage.

    **The first version tested a median split and it did not identify anything.**
    On two vintages column 0 (the real field) and column 22 (the number of
    borrowers) both scored 2/2, margin zero, because "lower value, higher rate"
    is true of a great many columns: two-borrower loans price better, and so on.
    A test that many columns pass is not an identification.

    So the test is the **band structure**, not the direction. §24.3 borrows the
    nine LLPA bands from C9 precisely because they are the issuer's own pricing
    divisions of this field; a column whose values fall into one or two of them
    is not the field those divisions divide. `MIN_BANDS_POPULATED` is what
    removes the number of borrowers (values 1 to 4 all land in one band), the
    dates (all above the top cut), LTV and DTI (their bulk in one band plus a
    missing code in another) without any of them being named or filtered by
    range.

    The stratification by vintage stays and is not optional: the coupon level
    moves several hundred basis points across this sample, so a pooled test
    would be reading the vintage and not the field.
    """
    out = {}
    for i in candidates:
        hits, seen, detail = 0, 0, []
        for v, rows in sorted(per_vintage.items()):
            by_band = defaultdict(list)
            for x, r in rows[i]:
                if x is not None and r is not None:
                    by_band[fico_band(x)].append(r)
            big = sorted(b for b, rs in by_band.items() if len(rs) >= MIN_BAND_N)
            if len(big) < MIN_BANDS_POPULATED:
                continue
            seen += 1
            meds = [statistics.median(by_band[b]) for b in big]
            # band index rises as the score falls, so the rate must not fall
            mono = all(a <= b for a, b in zip(meds, meds[1:]))
            if mono:
                hits += 1
            if not mono or len(detail) < 3:
                detail.append({"vintage": v, "bands": big,
                               "median_rate": [round(m, 4) for m in meds],
                               "monotone": mono})
        # **Every failing vintage is kept, whatever the detail budget.** The
        # first full run read 26/28 and the record held three vintages, none of
        # them the two that failed, so "which two" was unanswerable from the
        # output. A score that does not say where it lost is a score you cannot
        # act on.
        out[i] = {"score": hits, "vintages": seen, "detail": detail,
                  "failed_vintages": [d["vintage"] for d in detail
                                      if not d["monotone"]]}
    return out


def anchor_dti(hist_by_col: dict, candidates) -> dict:
    """A policy cap shows up as a one-step cliff in the histogram.

    Reported as the value at which `h(v) - h(v+1)` is largest, and the anchor
    passes when that value is one of the GSE caps. The cliff's own size prints
    beside it so a flat histogram cannot pass by having a largest-of-nothing.
    """
    out = {}
    for i in candidates:
        h = hist_by_col[i]
        best_v, best_drop = None, -1
        for v in range(DTI_WINDOW[0], DTI_WINDOW[1]):
            d = h.get(v, 0) - h.get(v + 1, 0)
            if d > best_drop:
                best_v, best_drop = v, d
        tot = sum(h.values()) or 1
        out[i] = {"cliff_at": best_v, "cliff_size": best_drop,
                  "cliff_frac": round(best_drop / tot, 5),
                  "passes": best_v in DTI_CAPS,
                  # **Both caps print, not just the winning one.** The cap moved
                  # from 45 to 50 in 2017 and the sample straddles that, so the
                  # field should show a cliff at each; reporting only the larger
                  # would hide the fact that there are two and that they sit
                  # exactly where the rule book moved.
                  "drop_at_each_cap": {c: h.get(c, 0) - h.get(c + 1, 0)
                                       for c in DTI_CAPS},
                  "window": {v: h.get(v, 0) for v in range(38, 56)}}
    return out


def anchor_implication(pair_counts: dict, totals: dict,
                       a_cands, b_cands) -> dict:
    """`A = y` implies `B = p`: a first-time buyer cannot be refinancing.

    Searched over ordered column pairs and over the value codes, so it earns
    **both columns and both codes** in one pass.

    **Two vacuity holes, and the first version only closed one of them.**
    `MIN_LEVEL_SHARE` guards the antecedent: an implication whose `A = y` is
    almost empty scores 1.000 while saying nothing. The registration wrote that
    guard and stopped there, and the first run walked straight into the other
    side: it returned ``col 27 = 'N'  =>  col 25 = ''`` at 1.00000 on 99,970
    rows, because **column 25 is blank on every row**, so *everything* implies
    it. A consequent that holds for almost everyone is exactly as vacuous as an
    antecedent that holds for almost no one.

    So the ranking is by **lift**, ``P(B = p | A = y) / P(B = p)``, which is 1.0
    for a vacuous consequent and about 2.0 for the real pair (first-time buyers
    are all purchases and purchases are about half the book). Ranking is not a
    threshold. The implication rate and the **raw counterexample count** print
    beside it: the anchor is a logical claim about mortgage products, so a
    handful of counterexamples is a reporting artefact and hundreds means the
    identification is wrong. **The count is printed rather than a rate**,
    because a rate hides how many rows are actually involved.

    Blank is never accepted as a consequent value: by C0b a field that is not
    reported has no value, so "implies blank" is not a statement about the
    field.
    """
    best, ranked = None, []
    rows = totals["rows"] or 1
    for a in a_cands:
        for b in b_cands:
            if a == b:
                continue
            for (ya, yb), n in pair_counts.get((a, b), {}).items():
                if yb == "" or ya == "":
                    continue
                na = totals[a].get(ya, 0)
                nb = totals[b].get(yb, 0)
                if na == 0 or nb == 0:
                    continue
                if na / rows < MIN_LEVEL_SHARE:
                    continue
                rate = n / na
                ranked.append({"fthb_col": a, "fthb_val": ya,
                               "purpose_col": b, "purpose_val": yb,
                               "implication": round(rate, 5),
                               "lift": round(rate / (nb / rows), 4),
                               "counterexamples": na - n, "n": na})
    # **Counterexamples first, lift second, and that order is the point.**
    # Ranking by lift alone put `occupancy = 'I' => units = '4'` on top with an
    # implication of 0.028 and 7,019 counterexamples, because lift alone
    # rewards a rare consequent. The anchor is a *logical* statement, so a row
    # with 7,019 counterexamples is not a near miss, it is false. Zero
    # counterexamples first; among those, the most informative.
    #
    # A zero-counterexample row bounds its consequent's frequency below by its
    # antecedent's, and the antecedent must clear `MIN_LEVEL_SHARE`, so lift is
    # capped and cannot run away. If two levels above that share do coincide
    # exactly, that is **two encodings of the same thing** and it is a finding
    # about the file, not a defect here.
    ranked.sort(key=lambda d: (d["counterexamples"], -d["lift"], -d["n"]))
    # keep only the strongest row per (fthb_col, purpose_col) so the ranking is
    # over column pairs and not over the value codes of one pair.
    seen, uniq = set(), []
    for r in ranked:
        k = (r["fthb_col"], r["purpose_col"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    if uniq:
        best = uniq[0]
    return {"best": best, "ranked": uniq[:6]}


def anchor_purpose_rate(share_by_vintage: dict, rate_by_vintage: dict) -> dict:
    """Refinancing is rate-driven: refi share moves against the coupon level.

    The second, independent anchor for `purpose`. The joint implication above
    pins the column pair; this one says which level is the purchase level
    without borrowing that answer. Reported as the sign of the covariance
    between a level's share and the vintage's median coupon, per level.
    """
    vs = sorted(set(share_by_vintage) & set(rate_by_vintage))
    if len(vs) < 4:
        return {"vintages": len(vs), "levels": {}}
    r = [rate_by_vintage[v] for v in vs]
    rbar = sum(r) / len(r)
    out = {}
    for lvl in {l for v in vs for l in share_by_vintage[v]}:
        s = [share_by_vintage[v].get(lvl, 0.0) for v in vs]
        sbar = sum(s) / len(s)
        cov = sum((a - sbar) * (b - rbar) for a, b in zip(s, r)) / len(s)
        out[lvl] = {"cov_with_rate": cov, "sign": "+" if cov > 0 else "-",
                    "mean_share": round(sbar, 4)}
    return {"vintages": len(vs), "levels": out}


# ---------------------------------------------------------------------------
# depth
# ---------------------------------------------------------------------------

#: §3's table, transcribed. `(loans, perf_rows, ever_delinq, ever_mod,
#: triangles, roundtrip)`. The gate is **exact equality**, which §26.2 licenses:
#: the triangle column sums to 17,875 and §4's per-modification-year table sums
#: to the same 17,875, so the two published tables are internally consistent and
#: an approximate match would be hiding something.
PUBLISHED_S3 = {
    1999: (50000, 2503335, 8247, 253, 241, 7345),
    2000: (50000, 1442994, 6837, 269, 254, 5715),
    2001: (50000, 1977237, 6726, 265, 254, 5832),
    2002: (50000, 2496389, 6297, 331, 322, 5509),
    2003: (50000, 4078243, 7378, 540, 527, 6696),
    2004: (50000, 3985245, 9500, 1023, 995, 8269),
    2005: (50000, 3877176, 11490, 1834, 1789, 9521),
    2006: (50000, 3203499, 12585, 2589, 2487, 10010),
    2007: (50000, 3012061, 13521, 3081, 2967, 10562),
    2008: (50000, 2456504, 9106, 1712, 1666, 7408),
    2009: (50000, 3160160, 4882, 461, 451, 4324),
    2010: (50000, 3446018, 5054, 440, 431, 4470),
    2011: (50000, 3631696, 5132, 388, 381, 4659),
    2012: (50000, 4510559, 5796, 396, 387, 5320),
    2013: (50000, 4197674, 6751, 422, 417, 6261),
    2014: (50000, 3394276, 6599, 449, 445, 6199),
    2015: (50000, 3467166, 6645, 470, 467, 6311),
    2016: (50000, 3379650, 7285, 500, 493, 6973),
    2017: (50000, 2800219, 7722, 629, 624, 7356),
    2018: (50000, 2059564, 6805, 544, 541, 6467),
    2019: (50000, 1934614, 6638, 405, 404, 6316),
    2020: (50000, 2517857, 4997, 179, 177, 4815),
    2021: (50000, 2537054, 5463, 249, 247, 5168),
    2022: (50000, 2034798, 6732, 560, 548, 6109),
    2023: (50000, 1458169, 4700, 283, 277, 4092),
    2024: (50000, 952865, 2899, 87, 83, 2395),
    2025: (49995, 404946, 1093, 0, 0, 873),
}
S3_COLS = ("loans", "perf_rows", "ever_delinq", "ever_mod", "triangles",
           "roundtrip")

#: §4's per-modification-year table, transcribed. Sums to 17,875.
PUBLISHED_S4_YEAR = {
    2000: 6, 2001: 34, 2002: 113, 2003: 101, 2004: 90, 2005: 85, 2006: 119,
    2007: 136, 2008: 446, 2009: 884, 2010: 2815, 2011: 1953, 2012: 1123,
    2013: 1387, 2014: 1069, 2015: 902, 2016: 570, 2017: 493, 2018: 892,
    2019: 518, 2020: 394, 2021: 569, 2022: 1172, 2023: 435, 2024: 542,
    2025: 791, 2026: 236,
}

#: §4's four windows plus the out-of-window remainder, by modification year.
S4_WINDOWS = (("pre_crisis", 0, 2008, 1130), ("hamp", 2009, 2016, 10703),
              ("flex", 2017, 2019, 1903), ("covid", 2020, 2022, 2135),
              ("post2023", 2023, 9999, 2004))

#: §26.1: §3's table stops at 2025 and the disk carries 2026. The gate runs on
#: §3's own span; 2026 prints and is excluded from every comparison, because a
#: total that differs by an extra vintage is a scope difference and not a defect.
S3_SPAN = (1999, 2025)

MODFLAG_MOD = ("Y", "P")


def is_del_digits(s: str) -> bool:
    """§26.0's `digits` reading of the delinquency field, **the one copy**.

    Lifted out of `classify_loan`'s closure when §8·20·7 needed the same
    predicate for B8's `p_ndq` screen. §8·16·3 forbids writing the round-trip
    finder twice and a one-line predicate is no different: two copies is how
    two screens end up reading two populations while both cite §26.0.

    The extraction is a textual move of a pure expression, and the selftest
    proves the equality against `classify_loan` itself over an exhaustive
    alphabet rather than asserting it.
    """
    return len(s) == 2 and s.isdigit() and s != "00"


def classify_loan(rows) -> dict:
    """One loan's outcome under **every** reading §26.0 enumerates.

    `rows` is ``[(period, delinquency, modflag), ...]`` in file order. Kept a
    module-level pure function rather than a closure inside the scanner so the
    selftest can drive it with hand-built loans whose answers are known before
    the code runs.
    """
    has_mod = any(m in MODFLAG_MOD for _, _, m in rows)
    res = {"ever_mod": has_mod}
    for d in ("digits", "any"):
        def is_del(s, d=d):
            if d == "digits":
                return is_del_digits(s)
            return bool(s) and s != "00"

        seen_cur = seen_del = seen_mod = False
        tri = tri_nolead = rt_between = no_lead = False
        mod_free_since_del = False
        y_row = any_row = None
        #: **§8·16·3's addition, indices only.** The noise floor needs the rows
        #: a round trip actually spans, and §8·16·3 forbids writing a second
        #: round-trip finder to get them: two copies of a window is how two
        #: things end up being measured. So the one finder reports where it
        #: found the trip, and every existing name above is read and written
        #: exactly as before.
        last_cur_i = None
        run_prev_cur = run_start_i = None
        between_window = None
        for i, (p, s, m) in enumerate(rows):
            cur = (s == "00")
            dl = is_del(s)
            md = m in MODFLAG_MOD
            #: A fresh delinquency run starts on a `dl` row whose flag is not
            #: yet up. **Read before the block below sets it**, or every row of
            #: the run would look like a fresh start.
            if dl and not mod_free_since_del:
                run_prev_cur, run_start_i = last_cur_i, i
            # **§29.3 layer two: the triangle's modification, not the loan's
            # first one.** §4's words are "the index is when *that* modification
            # happened", and *that* one is the triangle's. The first version
            # took the first flag anywhere on the loan, so a loan modified in
            # 2009, re-defaulted, and modified again in 2014 was filed under
            # 2009. The per-year table showed it: +4 at 2009 and +4 at 2010
            # while every year from 2011 on came out short, on a population
            # already known to be 16 loans light. Sixteen missing loans cannot
            # produce a surplus; a misfiled cohort can.
            if cur and not seen_del:
                seen_cur = True
            if dl:
                if not seen_del and not seen_cur:
                    no_lead = True
                seen_del = True
                mod_free_since_del = True
            if md and seen_del:
                seen_mod = True
                mod_free_since_del = False
                # **The same test dates the triangle that admits it.** Written
                # here rather than earlier in the loop on purpose: a row that is
                # both the first delinquency and the modification sets
                # `seen_del` above, so this block sees it while a block placed
                # before the `dl` test would not. The first draft had it above
                # and such a loan counted as a triangle with no year, which is a
                # loan the two tallies disagree about.
                if m == "Y" and y_row is None:
                    y_row = p
                if any_row is None:
                    any_row = p
            if cur and seen_del:
                if seen_mod and seen_cur:
                    tri = True
                # §27.3's fourth reading: the chain without its leading
                # `current`. §26.0 tried to make this moot by counting the
                # loans it excludes and finding zero; on 2007 that count is 25,
                # so the mooting failed and §27.3 registers it properly, with a
                # point prediction, **before this line was written**.
                if seen_mod:
                    tri_nolead = True
                if mod_free_since_del:
                    rt_between = True
                    if between_window is None:
                        #: Three indices, no choice buried here: the last
                        #: `current` before the run (None when the loan opens
                        #: delinquent, which is `no_leading_current`), the first
                        #: delinquent row, and the cure. The caller picks.
                        between_window = {"prev_current": run_prev_cur,
                                          "delinq_start": run_start_i,
                                          "cure": i}
            if cur:
                last_cur_i = i
        cured, sd = False, False
        for _, s, _ in rows:
            if is_del(s):
                sd = True
            elif s == "00" and sd:
                cured = True
        res[d] = {"ever_delinq": seen_del, "triangle": tri,
                  "triangle_nolead": tri_nolead,
                  "no_leading_current": no_lead,
                  "whole_loan": cured and not has_mod,
                  "between": rt_between,
                  "between_window": between_window,
                  "first_Y": y_row, "first_any": any_row}
    return res


def scan_vintage(v: int) -> dict:
    """One pass over a vintage's performance file, **all readings at once**.

    §26.0 enumerates three places where §3's prose admits more than one reading
    and requires every one of them to be computed and printed, so that the
    reading which matches is a **discovery about what §3 did** rather than a
    definition tuned until the number came out. All of them are written here
    before the first run and none may be added afterwards.

    * delinquency: `digits` takes §3's "two digits and not 00" literally and so
      excludes `RA`; `any` takes anything not blank and not `00`.
    * round trip: `whole_loan` demands no modification flag anywhere on the
      loan; `between` demands none only between the delinquency and the cure.
    * modification year: `first_Y` takes the first row flagged `Y`; `first_any`
      takes the first row flagged at all, `Y` or `P`.

    A fourth ambiguity is **made moot rather than enumerated**: §3's chain
    starts at `current`, so a loan whose first row is already delinquent cannot
    close a triangle. That reading is implemented and the number of loans it
    excludes is counted, so if the count is zero the question never needed an
    answer.
    """
    dreads = ("digits", "any")
    out = {
        "vintage": v, "loans": 0, "perf_rows": 0,
        "ever_delinq": {d: 0 for d in dreads},
        "ever_mod": 0,
        "triangles": {d: 0 for d in dreads},
        "triangles_nolead": {d: 0 for d in dreads},
        "roundtrip": {(d, r): 0 for d in dreads
                      for r in ("whole_loan", "between")},
        "mod_year": {(d, m): Counter() for d in dreads
                     for m in ("first_Y", "first_any")},
        "mod_year_leadreq": {(d, m): Counter() for d in dreads
                             for m in ("first_Y", "first_any")},
        "triangle_without_year": {(d, m): 0 for d in dreads
                                  for m in ("first_Y", "first_any")},
        "months_of_triangle": {d: 0 for d in dreads},
        "no_leading_current": {d: 0 for d in dreads},
        "odd_modflag": Counter(),
    }

    def finish(rows):
        """`rows` is [(period, delinq, modflag), ...] in file order."""
        out["loans"] += 1
        out["perf_rows"] += len(rows)
        c = classify_loan(rows)
        if c["ever_mod"]:
            out["ever_mod"] += 1
        for d in dreads:
            e = c[d]
            if e["ever_delinq"]:
                out["ever_delinq"][d] += 1
            if e["no_leading_current"]:
                out["no_leading_current"][d] += 1
            # **§29.4: the per-year table runs on the identified population.**
            # §29.1 settled ambiguity four as `not_required` (23/27 exact
            # against 16/27), so tallying the years on the `required`
            # population compares a table built on 16 fewer loans against §4's.
            # Both populations are kept so the comparison stays visible.
            if e["triangle_nolead"]:
                out["triangles_nolead"][d] += 1
                for mkey in ("first_Y", "first_any"):
                    per = e[mkey]
                    if per is not None:
                        out["mod_year"][(d, mkey)][per // 100] += 1
                    else:
                        out["triangle_without_year"][(d, mkey)] += 1
            if e["triangle"]:
                out["triangles"][d] += 1
                out["months_of_triangle"][d] += len(rows)
                for mkey in ("first_Y", "first_any"):
                    per = e[mkey]
                    if per is not None:
                        out["mod_year_leadreq"][(d, mkey)][per // 100] += 1
            for rr in ("whole_loan", "between"):
                out["roundtrip"][(d, rr)] += 1 if e[rr] else 0

    with zipfile.ZipFile(archive(v)) as zf:
        with zf.open(f"sample_perf_{v}.txt") as raw:
            seq, batch = None, []
            for line in io.TextIOWrapper(raw, encoding="utf-8", newline=""):
                if not line.strip():
                    continue
                f = line.split("|", 8)
                if f[0] != seq:
                    if seq is not None:
                        finish(batch)
                    seq, batch = f[0], []
                m = f[7].strip()
                if m and m not in MODFLAG_MOD:
                    out["odd_modflag"][m] += 1
                batch.append((int(f[1]), f[3].strip(), m))
            if seq is not None:
                finish(batch)
    return out


# ---------------------------------------------------------------------------
# --floor. Registered before the code.
#
# The last of §8·13·1's three gaps. `N = MAD(omega - closed)` needs omega and
# this station has none, so **only the construction half is computed here**;
# the measured half arrives with omega and the two must never be quoted as one.
#
# The construction is B8-0a's derivation, not its number:
#
#     0.005 * ( (2 + i)(k + 1) + (1 + i)^(k+1) ) / min(balance in the loop)
#
# On Fannie the 0.005 is half a cent because the UPB is reported to two
# decimals. On Freddie §5·2 and §10·9 measured, over 1,362,490 loans, that ages
# 0-6 sit on a $1,000 grid and age 7 onward report to the cent: **the half-step
# is $500 below and $0.005 above, a factor of 100,000**. So a loop that touches
# the boundary is not noisier, it is unreadable, and the domain starts at age 8
# — `r(t)` reads bal(t) and bal(t-1), so both ends must be on the cent side and
# the first usable t is 8, the same number as §6·1 for a different reason.
#
# The population is the no-modification round trips. §8·16·3 names the producer
# and forbids a second finder, so this walks the same `classify_loan` and asks
# it where the trip was.
# ---------------------------------------------------------------------------

#: Half a cent, from `b8_0a_gate.HALF_CENT`. The derivation travels, the number
#: is re-derived here from Freddie's own reporting precision (§5·2).
FLOOR_HALF_CENT = 0.005

#: §5·2's boundary, measured on 1,362,490 loans (§10·9's table A: two and a half
#: orders of magnitude between age 6 and age 7).
FLOOR_MIN_AGE = 8

#: §8·16·3's hard gate. Producer: `results/b10_cohort_width_triangles.json`,
#: written by `--triangles`, summed over the 28 archives at key
#: `('digits', 'between')`. **Named, not just quoted** (失效模式 18), and this
#: mode re-counts it through the same `classify_loan` rather than re-reading
#: that file, so the two share a population predicate by construction.
PUBLISHED_ROUNDTRIPS = 164_975

#: Samples kept for the exact quantiles. 165k floats is nothing; the cap exists
#: so a mis-specified population cannot silently eat memory, and it is printed.
FLOOR_SAMPLE_CAP = 1_000_000


def floor_bound(k: int, rate_pct: float, min_balance: float) -> float:
    """B8-0a's per-loop bound, with Freddie's half-step in place of Fannie's."""
    i = float(rate_pct) / 1200.0
    return (FLOOR_HALF_CENT
            * ((2.0 + i) * (k + 1) + (1.0 + i) ** (k + 1))
            / float(min_balance))


def floor_new_acc() -> dict:
    return {"loans": 0, "rows": 0, "roundtrips": 0,
            "age_ge_min": 0, "touches_below": 0,
            "no_prev_current": 0,
            "rate_varies": 0, "unreadable": 0,
            "k_hist": {}, "minbal": [], "bounds": [], "minage": {},
            "sample_capped": False}


def floor_window(rows):
    """§8·16's population predicate, once, for every mode that needs it.

    Returns ``(status, span, ages, bals, rates)``. `status` is one of
    ``no_trip / no_prev_current / unreadable / touches_below / rate_varies /
    priced``, in the order §8·16·2 prints them, and `span` is the rows the trip
    actually covers.

    **Lifted out of `floor_absorb` when §8·17 needed the same trips.** Writing
    the gate a second time is the defect §8·16·3 forbids for the finder, and a
    population predicate is no different: two copies is how two modes end up
    reading two populations while both cite the same number.
    """
    c = classify_loan([(t[R_PERIOD], t[R_DELINQ], t[R_MODFLAG]) for t in rows])
    e = c["digits"]
    if not e["between"]:
        return "no_trip", None, None, None, None
    w = e["between_window"]
    if w["prev_current"] is None:
        #: The loan opens delinquent, so there is no `current -> delinquent`
        #: leg to price. Counted, never folded into either side.
        return "no_prev_current", None, None, None, None
    a, b = w["prev_current"], w["cure"]
    span = rows[a:b + 1]
    ages, bals, rates = [], [], []
    for t in span:
        age, upb, rate = t[R_AGE], t[R_UPB], t[R_RATE]
        if age is None or upb is None or rate is None or upb <= 0:
            return "unreadable", span, None, None, None
        ages.append(age)
        bals.append(upb)
        rates.append(rate)
    if min(ages) < FLOOR_MIN_AGE:
        return "touches_below", span, ages, bals, rates
    if len(set(rates)) > 1:
        #: §8·16·4: a loop whose rate moved has no single `i`. Counted apart,
        #: never averaged (§11 item 4's family).
        return "rate_varies", span, ages, bals, rates
    return "priced", span, ages, bals, rates


def floor_absorb(acc: dict, rows) -> None:
    """One loan. `rows` is [(period, delinq, modflag, age, upb, rate), ...].

    The trip is found by `classify_loan` on the projected triples — **the same
    finder the §3 gate uses**, not a second one (§8·16·3).
    """
    acc["loans"] += 1
    acc["rows"] += len(rows)
    st, span, ages, bals, rates = floor_window(rows)
    if st == "no_trip":
        return
    acc["roundtrips"] += 1
    if st == "no_prev_current":
        acc["no_prev_current"] += 1
        return
    if st == "unreadable":
        acc["unreadable"] += 1
        return
    lo = min(ages)
    acc["minage"][lo] = acc["minage"].get(lo, 0) + 1
    if st == "touches_below":
        acc["touches_below"] += 1
        return
    acc["age_ge_min"] += 1
    if st == "rate_varies":
        acc["rate_varies"] += 1
        return
    k = len(span) - 1
    acc["k_hist"][k] = acc["k_hist"].get(k, 0) + 1
    mb = min(bals)
    if len(acc["bounds"]) < FLOOR_SAMPLE_CAP:
        acc["minbal"].append(mb)
        acc["bounds"].append(floor_bound(k, rates[0], mb))
    else:
        acc["sample_capped"] = True


def _q(xs, qs=(10, 50, 90)):
    if not xs:
        return [float("nan")] * len(qs)
    y = sorted(xs)
    out = []
    for q in qs:
        j = min(len(y) - 1, max(0, int(round((q / 100.0) * (len(y) - 1)))))
        out.append(float(y[j]))
    return out


def floor_payload(acc: dict) -> dict:
    b, mb = acc["bounds"], acc["minbal"]
    dec = {}
    for x in b:
        e = int(math.floor(math.log10(x))) if x > 0 else None
        dec[str(e)] = dec.get(str(e), 0) + 1
    return {
        "loans": acc["loans"], "rows": acc["rows"],
        "roundtrips": acc["roundtrips"],
        "age_ge_min": acc["age_ge_min"],
        "touches_below": acc["touches_below"],
        "no_prev_current": acc["no_prev_current"],
        "rate_varies": acc["rate_varies"], "unreadable": acc["unreadable"],
        "priced": len(b), "sample_capped": acc["sample_capped"],
        "k_q": _q(sum(([k] * n for k, n in acc["k_hist"].items()), [])),
        "k_hist": {str(k): v for k, v in
                   sorted(acc["k_hist"].items(), key=lambda kv: -kv[1])[:12]},
        "minbal_q": _q(mb),
        "bound_q": _q(b),
        "bound_decades": dict(sorted(dec.items(), key=lambda kv: int(kv[0]))),
        "half_cent_over_median_minbal":
            (FLOOR_HALF_CENT / _q(mb)[1]) if mb else float("nan"),
        "minage_hist": {str(k): v for k, v in
                        sorted(acc["minage"].items())[:16]},
        "min_age": FLOOR_MIN_AGE, "half_cent": FLOOR_HALF_CENT,
    }


def print_floor(pl: dict, gated: bool) -> None:
    print("\n  A. §8·16·3's gate: the population, against its named producer")
    print(f"     no-modification round trips counted here {pl['roundtrips']:,}")
    if gated:
        ok = pl["roundtrips"] == PUBLISHED_ROUNDTRIPS
        print(f"     results/b10_cohort_width_triangles.json, --triangles,"
              f" ('digits','between'), 28 archives: {PUBLISHED_ROUNDTRIPS:,}")
        print(f"     {'MATCH, bit for bit' if ok else 'MISMATCH'}"
              f"   difference {pl['roundtrips'] - PUBLISHED_ROUNDTRIPS:+,}")
        if not ok:
            print("     The populations are not the same one. Nothing below is")
            print("     quotable (§8·16·3).")
            return
    else:
        print("     --only was given, so the 28-archive gate does not apply."
              " Read nothing as a total.")

    print("\n  B. §8·16·2's domain: where the trips sit against age"
          f" {pl['min_age']}")
    print(f"     whole trip at age >= {pl['min_age']}   {pl['age_ge_min']:>10,}")
    print(f"     touches age <= {pl['min_age'] - 1}       "
          f"{pl['touches_below']:>10,}")
    print(f"     opens delinquent, no leading current  "
          f"{pl['no_prev_current']:>10,}")
    print(f"     a field would not read                {pl['unreadable']:>10,}")
    print(f"     rate moved inside the loop            "
          f"{pl['rate_varies']:>10,}   (counted apart, never averaged)")
    print(f"     priced                                {pl['priced']:>10,}"
          f"   sample capped {pl['sample_capped']}")
    tot = (pl["age_ge_min"] + pl["touches_below"] + pl["no_prev_current"]
           + pl["unreadable"])
    print(f"     the four buckets add to {tot:,}, against"
          f" {pl['roundtrips']:,} round trips"
          f"   {'self-consistent' if tot == pl['roundtrips'] else 'DO NOT ADD UP'}")
    print("     The ones below the boundary are not dropped: the $1,000 grid")
    print("     puts their half-step at $500, a hundred thousand times the")
    print("     cent, so holonomy is not readable on them at all (§8·16·2).")
    print(f"     smallest age in the trip, busiest: "
          f"{list(pl['minage_hist'].items())[:8]}")

    print("\n  C. the construction prediction, a distribution and not a number")
    print(f"     loop length k        p10 {pl['k_q'][0]:,.0f}"
          f"   p50 {pl['k_q'][1]:,.0f}   p90 {pl['k_q'][2]:,.0f}")
    print(f"     busiest k: {list(pl['k_hist'].items())[:8]}")
    print(f"     min balance in loop  p10 {pl['minbal_q'][0]:,.2f}"
          f"   p50 {pl['minbal_q'][1]:,.2f}   p90 {pl['minbal_q'][2]:,.2f}")
    print(f"     **bound**            p10 {pl['bound_q'][0]:.3e}"
          f"   p50 {pl['bound_q'][1]:.3e}   p90 {pl['bound_q'][2]:.3e}")
    print(f"     by decade: {pl['bound_decades']}")
    print(f"     half a cent / median min balance: "
          f"{pl['half_cent_over_median_minbal']:.3e}")
    print("     §8·16·6, written before the run: Fannie's same column reads")
    print("     1e-7 to 1e-8 on a six-figure median balance. Same order here")
    print("     means the two carriers report to the same precision above the")
    print("     boundary; an order or more apart is arithmetic to go check, not")
    print("     a finding. It is a shape and does not touch the branches.")

    print("\n  D. Read, per the criteria fixed before the run, three branches")
    n = pl["age_ge_min"]
    print(f"     whole-trip-above-the-boundary round trips: {n:,}")
    if n == 0:
        print("     THIRD BRANCH. The domain excluded every round trip. Go back")
        print("     to §3 and ask how the 164,975 were counted; instrument")
        print("     before reading.")
    elif n < 20:
        print("     SECOND BRANCH. Fewer than the borrowed floor of 20, so the")
        print("     noise floor is not measurable on this carrier. omega's step")
        print("     needs its power re-estimated; do not build further.")
    else:
        print("     FIRST BRANCH. At or above 20, and **20 is borrowed** — it is")
        print("     C9's and B8's MIN_CELL, set by B8 for its own use, and that")
        print("     travels with any quotation of this branch (§9·2).")
        print("     The construction prediction is delivered. **The measured")
        print("     half is not**: N = MAD(omega - closed) needs an omega this")
        print("     station has never computed, and the two halves may not be")
        print("     quoted as one (§8·16, first line).")


# ---------------------------------------------------------------------------
# --curve. Registered before the code.
#
# The residual instrument's outermost input. `b8_omega.row_residuals` takes
# `disc` from its caller on purpose — its own comment says putting the Treasury
# fetch behind that module's selftest would be wrong — so the first Freddie
# question is not "how is the residual computed" but "does the curve reach".
#
# **A curve gap that lands where Fannie never looks is not the same gap as one
# that lands where Freddie does.** Fannie is six quarterly archives; Freddie is
# 28 vintages covering 1999 to 2026. Measuring that costs no residual at all.
#
# The Treasury import is **inside `cmd_curve`, not at module level**, for the
# same reason `b8_omega` gives: this file's selftest must not need the CSVs.
# ---------------------------------------------------------------------------

#: `b8_omega.MAX_H`. Written here so the selftest needs no Treasury data, and
#: **checked against the import at run time** — two copies of a value with no
#: check between them is MEASUREMENT.md 失效模式 19's shape exactly.
CURVE_MAX_H = 600

#: Horizons and calendar months are bucketed by year for §8·17·3's thinnest
#: cell. Raw months would be a 600 x 330 grid whose thinnest cell is always 0
#: and therefore says nothing.
CURVE_YEAR_BUCKET = 12

#: `b8_core.EPOCH_YEAR`. **The curve table is keyed by month INDEX, not by a
#: period.** `b8_core.month_index` turns Fannie's `MMYYYY` into months since
#: 1990-01, and `curve_table_from`'s own comment calls this boundary "Pit 30's
#: family, at a module boundary rather than a column list". The first version
#: of this mode fed Freddie's `YYYYMM` straight in and **603,552 rows out of
#: 603,609 came back `no_curve_that_month`** — the whole scan, missed by a
#: units error. What caught it was not an assertion: it was the census line
#: printing `from 0 to 439`.
CURVE_EPOCH_YEAR = 1990


def month_index_of(period: int) -> int:
    """Freddie's `YYYYMM` -> `b8_core`'s month index. -1 when unusable."""
    y, m = int(period) // 100, int(period) % 100
    if not (1 <= m <= 12) or y < CURVE_EPOCH_YEAR:
        return -1
    return (y - CURVE_EPOCH_YEAR) * 12 + (m - 1)


def yyyymm_of(index: int) -> int:
    """The inverse, for printing. A month index is unreadable to a human."""
    return (CURVE_EPOCH_YEAR + index // 12) * 100 + (index % 12 + 1)


def curve_cell(period: int, rem: int, pos, tab, max_h: int = CURVE_MAX_H):
    """One row's curve status, with `b8_omega.disc_of_row`'s four names.

    Returns ``(status, value)``. Deliberately the same four labels, so the two
    carriers' coverage tables can be set beside each other without a glossary.

    `period` is Freddie's `YYYYMM`; the conversion to the table's month index
    lives **here and nowhere else**, so there is one place to be wrong.
    """
    mi = month_index_of(period)
    if mi < 0:
        return "no_curve_that_month", None
    k = pos.get(mi)
    if k is None:
        return "no_curve_that_month", None
    if not (1 <= rem <= max_h):
        return "horizon_out_of_table", None
    v = float(tab[k][rem])
    if v != v:                                   # NaN, without importing math
        return "curve_nan", None
    return "usable", v


def curve_new_acc() -> dict:
    return {"loans": 0, "roundtrips": 0, "priced_trips": 0,
            "rows": 0,
            "row_status": {}, "trip_status": {},
            "cell": {}, "bad_month": {}, "bad_period": {},
            "bad_horizon": {},
            "usable_trips": 0}


def curve_absorb(acc: dict, rows, pos, tab, max_h) -> None:
    """One loan, on §8·16's own population predicate (`floor_window`).

    The horizon is §8·14·6·8's: `rem_legal`, on the row itself. A trip is
    usable only when **every** row of it is, because `row_residuals` needs a
    `disc` on each and one NaN takes the loop's sum with it.
    """
    acc["loans"] += 1
    st, span, _ages, _bals, _rates = floor_window(rows)
    if st == "no_trip":
        return
    acc["roundtrips"] += 1
    if st != "priced":
        return
    acc["priced_trips"] += 1
    worst = "usable"
    for t in span:
        per, rem = t[R_PERIOD], t[R_REM]
        acc["rows"] += 1
        if rem is None:
            stat = "horizon_unreadable"
        else:
            stat, _ = curve_cell(per, rem, pos, tab, max_h)
        acc["row_status"][stat] = acc["row_status"].get(stat, 0) + 1
        yb = per // 100
        hb = (rem // CURVE_YEAR_BUCKET) if rem is not None else -1
        key = f"{yb}|{hb}"
        acc["cell"][key] = acc["cell"].get(key, 0) + 1
        if stat != "usable":
            #: **First failure wins the label, and it is not overwritten.** A
            #: "worst" that keeps being reassigned would report whichever row
            #: happened to come last, which is not a property of the trip.
            if worst == "usable":
                worst = stat
            if stat == "no_curve_that_month":
                acc["bad_month"][yb] = acc["bad_month"].get(yb, 0) + 1
                #: The calendar MONTH, not the year: §8·17·2's second branch
                #: asks whether each miss lands in a month the curve itself
                #: does not have, and a year cannot answer that.
                acc["bad_period"][per] = acc["bad_period"].get(per, 0) + 1
            elif stat == "horizon_out_of_table":
                acc["bad_horizon"][rem] = acc["bad_horizon"].get(rem, 0) + 1
    acc["trip_status"][worst] = acc["trip_status"].get(worst, 0) + 1
    if worst == "usable":
        acc["usable_trips"] += 1


def curve_payload(acc: dict, census: dict) -> dict:
    thin = None
    if acc["cell"]:
        k, v = min(acc["cell"].items(), key=lambda kv: kv[1])
        y, h = k.split("|")
        thin = {"calendar_year": int(y), "horizon_year": int(h), "rows": v}
    return {"census": census,
            "loans": acc["loans"], "roundtrips": acc["roundtrips"],
            "priced_trips": acc["priced_trips"], "rows": acc["rows"],
            "row_status": dict(sorted(acc["row_status"].items(),
                                      key=lambda kv: -kv[1])),
            "trip_status": dict(sorted(acc["trip_status"].items(),
                                       key=lambda kv: -kv[1])),
            "usable_trips": acc["usable_trips"],
            "cells": len(acc["cell"]), "thinnest_cell": thin,
            "bad_month": {str(k): v for k, v in
                          sorted(acc["bad_month"].items())},
            "bad_horizon": {str(k): v for k, v in
                            sorted(acc["bad_horizon"].items())[:16]},
            "bad_horizon_distinct": len(acc["bad_horizon"]),
            "bad_periods": sorted(acc["bad_period"]),
            "bad_period_rows": {str(k): v for k, v in
                                sorted(acc["bad_period"].items())[:24]},
            "max_h": CURVE_MAX_H}


def print_curve(pl: dict) -> None:
    cs = pl["census"]
    print("\n  A. §8·17·3 item 1: the curve's own census, before Freddie")
    print(f"     source files: {cs['files']}")
    print(f"     months with a curve  {cs['months']:,}"
          f"   from {cs['first_month']} to {cs['last_month']}")
    print(f"     months missing inside that span: {len(cs['missing'])}"
          f"   {cs['missing'][:12]}"
          + (" ..." if len(cs["missing"]) > 12 else ""))
    print(f"     horizons priced per month: min {cs['h_min']:,}"
          f"   median {cs['h_med']:,}   max {cs['h_max']:,}"
          f"   (table width {pl['max_h']})")
    print("     §8·16·0 taught that a product can be older than its producer,")
    print("     so the file names above travel with every number below.")

    print("\n  B. §8·17·2: the curve read at Freddie's own rows")
    print(f"     round trips {pl['roundtrips']:,}"
          f"   priced by §8·16 {pl['priced_trips']:,}"
          f"   rows in them {pl['rows']:,}")
    print(f"     per row : {pl['row_status']}")
    print(f"     per trip: {pl['trip_status']}")
    print("     A trip is usable only when every row of it is: `row_residuals`")
    print("     wants a `disc` on each, and one NaN takes the loop sum with it.")
    tot = sum(pl["trip_status"].values())
    print(f"     the trip labels add to {tot:,}, against"
          f" {pl['priced_trips']:,} priced"
          f"   {'self-consistent' if tot == pl['priced_trips'] else 'DO NOT ADD UP'}")

    print("\n  C. §8·17·3 item 2: the grid, and its thinnest cell (§3·4)")
    print(f"     non-empty (calendar year x horizon year) cells: {pl['cells']:,}")
    print(f"     thinnest: {pl['thinnest_cell']}")

    print("\n  D. Read, per the criteria fixed before the run, three branches")
    #: **A row whose own horizon will not parse is not evidence about the
    #: curve**: there is no horizon for the curve to be measured against, so it
    #: goes to coverage, beside §8·16's `unreadable` bucket. Registered as a
    #: disambiguation on 2026-08-20 with an argument that does not depend on
    #: the answer (§9·7·2's form). The first version wrote `rows - usable`,
    #: which folded those rows in and would have read the third branch off 57
    #: unreadable fields on a run where the curve reached everything.
    noh = pl["row_status"].get("horizon_unreadable", 0)
    asked = pl["rows"] - noh
    bad = asked - pl["row_status"].get("usable", 0)
    print(f"     rows with no readable horizon (coverage, not the curve): "
          f"{noh:,}")
    print(f"     rows the curve was asked about: {asked:,}")
    print(f"     rows the curve does not reach: {bad:,}")
    if bad == 0:
        print("     FIRST BRANCH. Full coverage. This input of the residual is")
        print("     settled; go to the next one.")
        return
    months = pl["bad_month"]
    hz = pl["bad_horizon_distinct"]
    print(f"     by calendar year: {dict(list(months.items())[:12])}")
    print(f"     distinct horizons that miss: {hz:,}"
          f"   busiest: {dict(list(pl['bad_horizon'].items())[:8])}")
    #: §8·17·2's sharpening, registered before this rewrite: a miss is the
    #: curve's property only when **that month is one the curve census itself
    #: lists as absent**. Structural, no threshold.
    #:
    #: The first version read `(len(bad_month) <= 3) or (hz <= 3)`, and with no
    #: horizon misses at all that `0 <= 3` passed: **an empty set won a test
    #: about concentration**, and a run in which 603,552 of 603,609 rows missed
    #: read as the second branch. Same family as "the overflow bucket may not
    #: win the mode" (§11).
    absent = set(pl["census"]["missing"])
    bad_p = pl.get("bad_periods") or []
    outside = [p for p in bad_p if p not in absent]
    print(f"     distinct calendar months that miss: {len(bad_p):,}")
    print(f"     of them, months the curve census DOES have: {len(outside):,}"
          f"   {outside[:12]}")
    if bad_p and not outside:
        print("     SECOND BRANCH. Every miss lands in a month the curve does")
        print("     not have, so it is the curve's property, the way B8 §2·1")
        print("     read its own 47 missing months. The trips they take out are")
        print("     set aside whole, the way §8·16 sets aside the ones below")
        print("     the grid boundary.")
    else:
        print("     THIRD BRANCH. Misses land in months the curve does have"
              f" ({len(outside):,} of them), or the horizon side missed.")
        print("     That is this file's reading of the curve, not the curve.")
        print("     Go and check it; nothing here is a reading yet.")


# ---------------------------------------------------------------------------
# --resid. Registered before the code.
#
# **B10 writes no residual formula.** `b8_omega.r_month` is a pure numeric
# function — only `row_residuals` needs a core table — so this file imports it
# and feeds it Freddie's columns. §8·11 item 2 ("this station's code may not
# contain a residual formula") is then kept **literally**, not by §8·11·1's
# scope argument, and §8·11·1 limit 1's worry about two implementations does
# not arise: there is one residual in the repository.
#
# What can still diverge is the DRIVER: the eligibility gates and the `_prev`
# wiring. The gates below are named and ordered exactly as
# `b8_omega.row_residuals` names and orders them, so the two coverage tables
# can be set side by side. Side by side, never subtracted (§7·9).
#
# Population: §8·16's priced round trips, through the same `floor_window`.
# `P` is the ORIGINATION contract payment, carried as state and never
# re-derived per month — re-deriving it is the defect `carry_forward`'s comment
# records as C8-1a's median of 1.01 over 140 million months. On this population
# it is valid throughout, because a round trip carries no modification at all.
# ---------------------------------------------------------------------------

#: `r_month`'s gate names, in `row_residuals`' own order. Written out so the
#: two carriers' coverage tables line up row for row.
RESID_GATES = (
    "first row of a loan",
    "no contract payment on the previous row",
    "balance not readable",
    "rate or horizon missing on either row",
    "previous row carries a balloon with no horizon",
    "curve does not reach this month and horizon",
    "the counterfactual balance would be non-positive (near payoff)",
)

#: §8·19·8. Gates 3 and 4 are each a six-way `or`, and a six-way `or` that
#: prints one number cannot say which way it went. **Mutually exclusive, first
#: match in the order written**, and the sum is asserted against the gate's own
#: count. Gate 7 is a single cause and is not split.
RESID_SUB3 = (
    "UPB unreadable on this row",
    "UPB unreadable on the previous row",
    "column 12 unreadable on this row",
    "column 12 unreadable on the previous row",
    "bal_ib non-positive on this row",
    "bal_ib non-positive on the previous row",
)
RESID_SUB4 = (
    "rem unreadable on this row",
    "rem unreadable on the previous row",
    "rate unreadable on either row",
    "period unreadable on this row",
    "rem <= 0 on this row",
    "rem <= 1 on the previous row",
)

#: **Not a filter.** `row_residuals` counts this apart and calls it a defect;
#: so does this file.
RESID_DEFECT = "r came back non-finite on a row we admitted"

#: Samples kept for exact quantiles of `r`. Printed, never silent.
RESID_SAMPLE_CAP = 1_000_000


#: §8·19·3's fixture. A clean cure whose closed form b8_omega already knows.
#: The numbers are a mortgage's, not a toy's, because the bound being checked
#: is a cent-rounding bound and a toy balance would make it trivially loose.
XC_B0 = 180_000.00
XC_NOTE = 6.5
XC_TERM = 360
XC_K = 5
XC_DISC = 4.25

#: §8·19·3 丙's fixture: a modification-shaped month. The rate falls and the
#: legal maturity is extended, which is exactly where r_month's three `_prev`
#: arguments stop agreeing with their defaults.
XC_MOD = {"bal_now": 176_000.00, "bal_prev": 178_000.00,
          "rate_now": 4.0, "rate_prev": 6.5,
          "rem_now": 340, "rem_prev": 300,
          "zib_now": 5_000.00, "zib_prev": 5_000.00}

#: 丙's second half: the same call on a quiet month, where r_month's docstring
#: says omitting the three arguments reproduces the old behaviour bit for bit.
XC_QUIET = {"bal_now": 176_000.00, "bal_prev": 178_000.00,
            "rate_now": 6.5, "rate_prev": 6.5,
            "rem_now": 299, "rem_prev": 300,
            "zib_now": 5_000.00, "zib_prev": 5_000.00}

#: The tolerances, named rather than typed at the comparison. 乙's exact leg is
#: floating point on ~1e-4 quantities; its rounded leg is checked against a
#: bound this file derives, not against a number.
XC_EXACT_TOL = 1e-11
XC_MOD_MIN_GAP = 0.005


def _logs_in_this_file() -> dict:
    """Every logarithm this module's own code calls, counted by name.

    **Structural, not a text scan.** §8·11 item 2 says B10's code may not
    contain a residual formula, and 失效模式 16 says a text match that misses
    is a silent no-op. This walks the parsed tree, so a `np.log` hidden inside
    a nested function or a comprehension is found and one written in a comment
    is not miscounted.
    """
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    names = ("log", "log1p", "log2", "log10")
    out = {}
    for node in ast.walk(tree):
        nm = None
        if isinstance(node, ast.Attribute) and node.attr in names:
            nm = node.attr
        elif isinstance(node, ast.Name) and node.id in names:
            nm = node.id
        if nm:
            out[nm] = out.get(nm, 0) + 1
    return out


def resid_crosscheck(W, G):
    """§8·19·3's three parts plus its side task. Returns [(name, ok, detail)].

    **One copy, two callers.** The selftest runs it when `b8_omega` imports and
    says so loudly when it does not; `cmd_resid` runs it as a hard pre-flight
    and reads nothing off any archive until every line is ok. Writing it twice
    is how the pre-flight and the test end up checking two different things,
    which is the defect `floor_window` was lifted out to avoid.
    """
    out = []

    # --- 甲: the residual is B8's object, and this file has no formula -------
    mod = getattr(W.r_month, "__module__", None)
    out.append(("甲1 r_month is b8_omega's own function",
                mod == "b8_omega", f"__module__ = {mod!r}"))
    logs = _logs_in_this_file()
    out.append(("甲2 the only logarithm in this file is log10, once",
                logs == {"log10": 1}, f"logarithms called: {logs}"))

    # --- 乙: a streamed clean cure reproduces the closed form ---------------
    P = float(W.level_payment(XC_B0, XC_NOTE, XC_TERM))
    closed = float(W.loop_residual_ideal(XC_B0, XC_NOTE, P, XC_K))

    def ideal_path():
        """The clean-cure path `loop_residual_ideal` is the closed form of.

        Stepped with `carry_forward`, which is B8's, so not one arithmetic line
        of the counterfactual is written here either. `k` flat months at the
        reported balance, then one cure that lands where the uninterrupted
        schedule would have put it.
        """
        b = XC_B0
        for _ in range(XC_K + 1):
            b = float(W.carry_forward(b, XC_NOTE, P))
        return [XC_B0] * (XC_K + 1) + [b]

    def stream(path):
        """`episode_sums`' streaming residual, through `r_month` rather than
        through a hand-written pair of logarithms. Returns (sum, b_min)."""
        total, bmin = 0.0, min(path)
        for t in range(1, len(path)):
            b_hat = float(W.carry_forward(path[t - 1], XC_NOTE, P))
            bmin = min(bmin, b_hat)
            n_now = float(XC_TERM - t)
            total += float(W.r_month(
                path[t], path[t - 1], XC_NOTE, P, n_now, XC_DISC,
                zib_now=0.0, zib_prev=0.0, balloon_n=n_now,
                note_prev=XC_NOTE, n_prev=n_now, balloon_n_prev=n_now))
        return total, bmin

    base = ideal_path()
    s_exact, _ = stream(base)
    out.append((f"乙1 the exact path reproduces loop_residual_ideal "
                f"({closed:+.6e})",
                abs(s_exact - closed) <= XC_EXACT_TOL,
                f"streamed {s_exact:+.6e}, gap {abs(s_exact - closed):.3e}, "
                f"tolerance {XC_EXACT_TOL:.1e}"))

    #: **Adversarial, not illustrative.** Rounding the ideal path to cents
    #: moves one balance, and a bound that survives one perturbation has not
    #: been tested. Every reported balance is pushed the full half cent, in
    #: every sign pattern, and the worst of the 2^(k+2) is the one reported.
    #: A bound that is too tight is then a failure here rather than a surprise
    #: on 603,609 rows.
    #:
    #: `closed` moves with the pattern too: `episode_sums` computes it from
    #: `bal[a]`, the **reported** first balance, so perturbing the path without
    #: perturbing the closed form would be comparing two different loops.
    worst, worst_bnd, worst_bmin, n_pat = -1.0, None, None, 0
    for mask in range(1 << len(base)):
        pert = [b + (FLOOR_HALF_CENT if (mask >> k) & 1 else -FLOOR_HALF_CENT)
                for k, b in enumerate(base)]
        tot, bmin = stream(pert)
        cl = float(W.loop_residual_ideal(pert[0], XC_NOTE, P, XC_K))
        gap = abs(tot - cl)
        n_pat += 1
        if gap > worst:
            worst, worst_bmin = gap, bmin
            worst_bnd = floor_bound(XC_K, XC_NOTE, bmin)
    out.append(("乙2 the worst half-cent path of "
                f"{n_pat} stays inside §8·16's own bound",
                worst <= worst_bnd,
                f"worst gap {worst:.4e} against bound {worst_bnd:.4e} "
                f"at b_min {worst_bmin:,.4f}, "
                f"slack x{worst_bnd / worst if worst else float('inf'):.2f}"))
    #: The side task §8·19·3 names: §8·16's bound and B8-0a's are the same
    #: quantity with the arguments in a different order. Two copies of a bound
    #: with no check between them is 失效模式 19, and this file has already
    #: refused to run once on that ground (`W.MAX_H != CURVE_MAX_H`).
    same = all(
        floor_bound(k, nt, bb) == G.rounding_bound(bb, nt, k)
        for k in (0, 1, 5, 17, 60)
        for nt in (3.0, 6.5, 11.25)
        for bb in (1_000.0, 145_972.35, 900_000.0))
    out.append(("乙3 floor_bound is b8_0a_gate.rounding_bound, argument for "
                "argument", same,
                f"HALF_CENT {G.HALF_CENT} against FLOOR_HALF_CENT "
                f"{FLOOR_HALF_CENT}, 45 (k, rate, balance) triples"))

    # --- 丙: the three `_prev` arguments are load-bearing --------------------
    def both(f):
        with_prev = float(W.r_month(
            f["bal_now"], f["bal_prev"], f["rate_now"], P,
            float(f["rem_now"]), XC_DISC,
            zib_now=f["zib_now"], zib_prev=f["zib_prev"],
            balloon_n=float(f["rem_now"]),
            note_prev=f["rate_prev"],
            n_prev=float(f["rem_prev"]) - 1.0,
            balloon_n_prev=float(f["rem_prev"]) - 1.0))
        without = float(W.r_month(
            f["bal_now"], f["bal_prev"], f["rate_now"], P,
            float(f["rem_now"]), XC_DISC,
            zib_now=f["zib_now"], zib_prev=f["zib_prev"],
            balloon_n=float(f["rem_now"])))
        return with_prev, without

    wm, om = both(XC_MOD)
    out.append(("丙1 at a modification month the three `_prev` arguments "
                "change the answer",
                abs(wm - om) > XC_MOD_MIN_GAP,
                f"with {wm:+.6f}, without {om:+.6f}, gap {abs(wm - om):.6f} "
                f"against floor {XC_MOD_MIN_GAP}"))
    wq, oq = both(XC_QUIET)
    out.append(("丙2 on a quiet month they agree, as r_month's docstring says",
                abs(wq - oq) <= XC_EXACT_TOL,
                f"with {wq:+.9f}, without {oq:+.9f}, "
                f"gap {abs(wq - oq):.3e}"))
    #: 丙's own guard. `both` builds the two calls a few lines apart, and a
    #: fixture where the contract does not actually move would let 丙1 pass on
    #: a typo. The fixture is asserted to be modification-shaped.
    moved = (XC_MOD["rate_now"] != XC_MOD["rate_prev"]
             and XC_MOD["rem_now"] != XC_MOD["rem_prev"] - 1)
    quiet = (XC_QUIET["rate_now"] == XC_QUIET["rate_prev"]
             and XC_QUIET["rem_now"] == XC_QUIET["rem_prev"] - 1)
    out.append(("丙3 the two fixtures really are one moved and one quiet",
                moved and quiet,
                f"moved {moved}, quiet {quiet}"))
    return out


def print_crosscheck(rows) -> bool:
    print("  §8·19·3, the construction cross-check. Nothing is read off an\n"
          "  archive until every line here is ok.")
    ok = True
    for name, good, detail in rows:
        ok = ok and good
        print(f"    [{'ok  ' if good else 'FAIL'}] {name}")
        print(f"           {detail}")
    return ok


def resid_new_acc() -> dict:
    return {"loans": 0, "trips": 0, "priced_trips": 0, "pairs": 0,
            "gates": {g: 0 for g in RESID_GATES},
            "sub3": {g: 0 for g in RESID_SUB3},
            "sub4": {g: 0 for g in RESID_SUB4},
            "defect": 0, "ok": 0,
            "no_orig": 0, "no_payment": 0, "rows_no_payment": 0,
            #: §8·19·8 variable two's census, on the priced trips only.
            "rows_rem_bad": 0, "trips_all_rem_bad": 0,
            "rows_all_rem_bad": 0, "pairs_in_all_rem_bad": 0,
            "r": [], "by_vintage": {}, "sample_capped": False}


def pair_residual(prev, now, P, pos, tab, max_h, r_month):
    """One (previous row, this row) pair. **The single copy of the gates.**

    Returns ``(gate, sub, r)``. `gate` is the `RESID_GATES` entry that stopped
    the pair, or None when it went through; `sub` is ``("sub3"|"sub4", name)``
    for the two gates that are split, else None; `r` is the residual or None.

    **Lifted out of `resid_absorb` when §8·20 needed the same walk to make a
    loop sum.** Writing the gates a second time is how the per-month table and
    the loop sum end up measuring two different populations while both cite
    §8·19 — the same reason `floor_window` was lifted out at §8·17.
    """
    if P is None:
        return RESID_GATES[1], None, None

    #: §8·18's identity on both rows: `bal_ib = col 3 - col 12`. A column that
    #: will not read is None here and is refused, never read as zero
    #: (失效模式 20). `rows_for_V` refuses the same way on the other carrier,
    #: and its C13 refusal has no Freddie counterpart at all: §8·14·5 showed
    #: the zero-interest split is column 12 alone, so `bad_c13` is identically
    #: false here.
    u_now, u_prev = now[R_UPB], prev[R_UPB]
    z_now, z_prev = now[R_DEFER], prev[R_DEFER]
    s3 = (u_now is None, u_prev is None, z_now is None, z_prev is None)
    if any(s3):
        return RESID_GATES[2], ("sub3", RESID_SUB3[s3.index(True)]), None
    b_now, b_prev = u_now - z_now, u_prev - z_prev
    if not (b_now > 0) or not (b_prev > 0):
        return (RESID_GATES[2],
                ("sub3", RESID_SUB3[4 if not (b_now > 0) else 5]), None)

    n_now, n_prev = now[R_REM], prev[R_REM]
    i_now, i_prev = now[R_RATE], prev[R_RATE]
    #: `row_residuals`' own thresholds: `rem > 0` on this row, `rem > 1` on the
    #: previous one, and this row's period readable.
    s4 = (n_now is None, n_prev is None,
          i_now is None or i_prev is None, now[R_PERIOD] < 0,
          n_now is not None and n_now <= 0,
          n_prev is not None and n_prev <= 1)
    if any(s4):
        return RESID_GATES[3], ("sub4", RESID_SUB4[s4.index(True)]), None

    #: Written the way `row_residuals` writes it, `bn_prev > 1` and not
    #: `bn_prev - 1 > 1`. On Freddie `bn == n` identically (§8·14·6·8), so gate
    #: 4 has already required `n_prev > 1` and **this gate cannot fire on this
    #: carrier**. Its zero is a carrier fact, not a measurement.
    bn_prev = float(n_prev)
    if z_prev > 0 and not (bn_prev > 1):
        return RESID_GATES[4], None, None

    stat, disc = curve_cell(now[R_PERIOD], n_now, pos, tab, max_h)
    if stat != "usable":
        return RESID_GATES[5], None, None

    #: `row_residuals`' last gate, at the previous row's rate and the contract
    #: payment, both of which `r_month` will use again inside `carry_forward`.
    #: This is a **gate**, not a residual: the value is thrown away.
    if not (b_prev * (1.0 + i_prev / 1200.0) - P > 0):
        return RESID_GATES[6], None, None

    r = float(r_month(
        b_now, b_prev, i_now, P, float(n_now), disc,
        zib_now=z_now, zib_prev=z_prev,
        balloon_n=float(n_now),
        note_prev=i_prev,
        n_prev=float(n_prev) - 1.0,
        balloon_n_prev=bn_prev - 1.0))
    return None, None, r


def resid_payment(acc, orig, span, contract_payment):
    """`P` for one loan, with §8·19's two loan-level censuses. May return None.

    §8·19·1: the **origination** contract payment carried as state, which is
    what `carry_forward`'s docstring demands and what C8-1a punished
    re-deriving with a median of 1.01 on 140 million months.

    **Deliberately not an early return for the caller.** A loan with no orig
    row still walks its rows and fires gate 2 on every one, exactly as
    `row_residuals` drops row by row on `prev_known`.
    """
    P = None
    if orig is None:
        acc["no_orig"] += 1
    else:
        u0, rate0, term = orig
        cand = contract_payment(u0, rate0 / 1200.0, term)
        if cand == cand and cand > 0:
            P = cand
        else:
            acc["no_payment"] += 1
    if P is None:
        acc["rows_no_payment"] += max(0, len(span) - 1)
    return P


def resid_absorb(acc, rows, orig, vintage, pos, tab, max_h, r_month,
                 contract_payment) -> None:
    """One loan. Gates in `row_residuals`' order, then B8's own `r_month`.

    **Not one line of residual arithmetic lives here** (§8·19, §8·11 item 2).
    `pair_residual` marshals the arguments; `r_month` does the arithmetic, and
    it is B8's own function, imported.
    """
    acc["loans"] += 1
    st, span, _a, _b, _c = floor_window(rows)
    if st == "no_trip":
        return
    acc["trips"] += 1
    if st != "priced":
        return
    acc["priced_trips"] += 1
    P = resid_payment(acc, orig, span, contract_payment)

    #: §8·19·8 variable two. Counted on the priced trips, which is the same
    #: population §8·17's row census ran on, so the two are two ways of
    #: counting one set of rows rather than two sets.
    n_bad = sum(1 for t in span if t[R_REM] is None)
    acc["rows_rem_bad"] += n_bad
    if n_bad and n_bad == len(span):
        acc["trips_all_rem_bad"] += 1
        acc["rows_all_rem_bad"] += n_bad
        acc["pairs_in_all_rem_bad"] += len(span) - 1

    for j in range(len(span)):
        acc["pairs"] += 1
        if j == 0:
            acc["gates"][RESID_GATES[0]] += 1
            continue
        gate, sub, r = pair_residual(span[j - 1], span[j], P, pos, tab, max_h,
                                     r_month)
        if sub is not None:
            acc[sub[0]][sub[1]] += 1
        if gate is not None:
            acc["gates"][gate] += 1
            continue
        if r != r or r in (float("inf"), float("-inf")):
            acc["defect"] += 1
            continue
        acc["ok"] += 1
        if len(acc["r"]) < RESID_SAMPLE_CAP:
            acc["r"].append(r)
        else:
            acc["sample_capped"] = True
        v = acc["by_vintage"].setdefault(vintage, {"n": 0, "r": []})
        v["n"] += 1
        if len(v["r"]) < 50_000:
            v["r"].append(r)


def resid_payload(acc) -> dict:
    per_v = {}
    for v, d in sorted(acc["by_vintage"].items()):
        per_v[str(v)] = {"n": d["n"], "q": _q(d["r"]),
                         "absmed": _q([abs(x) for x in d["r"]], (50,))[0]}
    return {"loans": acc["loans"], "trips": acc["trips"],
            "priced_trips": acc["priced_trips"], "pairs": acc["pairs"],
            "gates": dict(acc["gates"]),
            "sub3": dict(acc["sub3"]), "sub4": dict(acc["sub4"]),
            "sub3_total": sum(acc["sub3"].values()),
            "sub4_total": sum(acc["sub4"].values()),
            "rows_rem_bad": acc["rows_rem_bad"],
            "trips_all_rem_bad": acc["trips_all_rem_bad"],
            "rows_all_rem_bad": acc["rows_all_rem_bad"],
            "pairs_in_all_rem_bad": acc["pairs_in_all_rem_bad"],
            "defect": acc["defect"],
            "ok": acc["ok"], "no_orig": acc["no_orig"],
            "no_payment": acc["no_payment"],
            "rows_no_payment": acc["rows_no_payment"],
            "gates_total": sum(acc["gates"].values()),
            "q_r": _q(acc["r"]), "q_absr": _q([abs(x) for x in acc["r"]]),
            "sampled": len(acc["r"]), "sample_capped": acc["sample_capped"],
            "by_vintage": per_v}


#: §8·19·8's third piece. The three modes walk **the same `floor_window`**, so
#: their populations must agree number for number. Naming the producer and
#: reading it is the form §8·16·3 already uses; doing the reconciliation in
#: conversation instead of in the artifact is how 失效模式 18 happens.
RESID_PRODUCERS = (
    ("results/b10_floor.json", (("loans", "loans"), ("roundtrips", "trips"),
                                ("priced", "priced_trips"))),
    ("results/b10_curve.json", (("loans", "loans"),
                                ("priced_trips", "priced_trips"),
                                ("rows", "pairs"))),
)


def resid_producers(root) -> list:
    """Read the two named producers. **A missing one is reported, not skipped.**

    Returns [(path, present, [(field, theirs, ours, ok)])].
    """
    out = []
    for rel, fields in RESID_PRODUCERS:
        f = root / rel
        if not f.exists():
            out.append((rel, False, []))
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            out.append((rel, False, []))
            continue
        out.append((rel, True, [(a, d.get(a), b) for a, b in fields]))
    return out


#: Fields that exist to describe the run rather than to be a reading, and so
#: are not part of 規矩 19's comparison. Kept short and named, because a
#: growing exclusion list is how a comparison stops comparing.
RESID_NOT_COMPARED = ("diagnostic_reason", "stage", "step")


def partial_name(base: str, only, full=None) -> str:
    """`base.json` for a full run, `base.<v>_<v>.json` for a subset.

    **Every `cmd_*` in this file takes `--only` and every one of them used to
    write the plain name regardless.** So one debugging run over a single
    vintage silently replaced a twenty-seven-archive artifact, and nothing in
    the filename said so. That is not hypothetical: `b10_holonomy_ladder.py`
    did exactly that to `b10_holonomy_variance.json` on 2026-08-20 (结果件
    §8·15·5·1), and the six-archive file survived only because a copy had been
    taken by hand minutes earlier.

    B12 set the naming scheme with `b12_ladder.offparam_2019Q1.json` and the
    ladder now follows it. This is the same scheme for this file's carrier.
    **The full run keeps the plain name**, so no existing artifact moves and
    規矩 19's comparison keeps a stable object to compare against.

    The suffix is built from a **sorted** list, so two spellings of the same
    subset are one file rather than two.

    `full` is a parameter so the selftest can ask without a disk.
    """
    have = sorted(str(v) for v in
                  (vintages_on_disk() if full is None else full))
    got = sorted(str(v) for v in (only or []))
    if not got or got == have:
        return f"{base}.json"
    return f"{base}.{'_'.join(got)}.json"


def prior_json(root, name):
    """The previous artifact of this name, or None. **Read before it is
    written**, or the comparison is the file against itself."""
    f = root / "results" / name
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


#: 規矩 19's comparison prints at most this many lines per direction, and
#: says how many it did not print. A silent cap reads as full coverage
#: (B8's own words about `capped_at`), so the count is always printed.
VS_PRIOR_CAP = 40
VS_PRIOR_REPR = 120


def flat_leaves(obj, prefix=""):
    """Every leaf of a JSON payload, keyed by its dotted path.

    A non-empty dict recurses; everything else — scalar, list, **and the
    empty dict** — is a leaf, so a subtree emptying out is news rather than
    silence.

    **規矩 19 has to compare leaves, not top-level keys.** `b10_noise.json`
    keeps this whole station's reading under one key (`coh`, fifty kilobytes),
    so a flat comparison reports a single `MOVED coh` and dumps the old and
    the new subtree beside it. **A check nobody can read is not a check** —
    §11 item 3 from the other side: there a check could not fail, here it
    cannot be read, and both print something that looks like diligence.
    """
    if isinstance(obj, dict) and obj:
        out = {}
        for k, v in obj.items():
            out.update(flat_leaves(v, prefix + str(k) + "."))
        return out
    return {prefix[:-1] if prefix else "": obj}


def _vs_short(v) -> str:
    t = repr(v)
    return t if len(t) <= VS_PRIOR_REPR else t[:VS_PRIOR_REPR] + "..."


def print_vs_prior(old, new, name, cap=VS_PRIOR_CAP) -> bool:
    """規矩 19, as an artifact rather than as a message in a chat.

    Every leaf the previous run wrote must come back identical; the new run
    may only **add**. A leaf that vanished is as much news as one that moved,
    so both directions are printed.

    **One copy, every mode.** Written for `--resid` and generalised the moment
    `--omega` needed it; a second copy is how two artifacts end up compared by
    two rules.
    """
    print(f"\n  A0. 規矩 19: this run against the previous {name}")
    if old is None:
        print("     no previous file on disk. Nothing to compare, and that is")
        print("     said rather than passed over.")
        return True
    o = {k: v for k, v in flat_leaves(old).items()
         if k.split(".")[0] not in RESID_NOT_COMPARED}
    n = flat_leaves(new)
    gone = sorted(k for k in o if k not in n)
    moved = sorted(k for k in o if k in n and o[k] != n[k])
    added = sorted(k for k in n if k not in o)
    print(f"     leaves in the previous file {len(o):,}"
          f"   added by this run {len(added):,}"
          f"   gone {len(gone):,}   moved {len(moved):,}")

    def _lines(tag, keys, fmt):
        for k in keys[:cap]:
            print(f"     {tag} {fmt(k)}")
        if len(keys) > cap:
            print(f"     ... and {len(keys) - cap:,} more under"
                  f" {tag.strip('* ')},"
                  f" not printed (cap {cap}; the count is printed rather"
                  f" than the cap being silent)")

    _lines("added   ", added, lambda k: k)
    _lines("**GONE**", gone, lambda k: f"{k}: was {_vs_short(o[k])}")
    _lines("**MOVED**", moved,
           lambda k: f"{k}: was {_vs_short(o[k])}, now {_vs_short(n[k])}")
    ok = not gone and not moved
    print(f"     every previous leaf reproduced: "
          f"{'YES' if ok else 'NO — read the lines above before anything else'}")
    return ok


def print_resid(pl, prod=None) -> None:
    print("\n  A. §8·19·2's gates, named and ordered as row_residuals names them")
    print(f"     loans {pl['loans']:,}   round trips {pl['trips']:,}"
          f"   priced {pl['priced_trips']:,}")
    print(f"     priced trips with no orig row {pl['no_orig']:,}"
          f"   with no usable contract payment {pl['no_payment']:,}")
    print(f"     rows walked {pl['pairs']:,}")
    for g in RESID_GATES:
        print(f"       {g:<62} {pl['gates'][g]:>10,}")
    print(f"       {'admitted':<62} {pl['ok']:>10,}")
    tot = pl["gates_total"] + pl["ok"] + pl["defect"]
    print(f"     gates + admitted + defect = {tot:,} against rows"
          f" {pl['pairs']:,}"
          f"   {'MATCH' if tot == pl['pairs'] else 'DO NOT ADD UP'}")

    #: **Two of these gates read zero for structural reasons, and a structural
    #: zero must not be allowed to look like a measurement.** Both are declared
    #: here, each with the check that makes it checkable rather than asserted.
    g2 = pl["gates"][RESID_GATES[1]]
    print(f"\n     gate 2 is fireable and its count is checkable: rows on")
    print(f"     loans with no usable payment {pl['rows_no_payment']:,}"
          f" against gate 2's {g2:,}"
          f"   {'MATCH' if g2 == pl['rows_no_payment'] else 'DO NOT MATCH'}")
    print(f"     gate 5 **cannot fire on this carrier**: bn == n identically")
    print(f"     (§8·14·6·8), so gate 4's `n_prev > 1` already implies it. Its")
    print(f"     {pl['gates'][RESID_GATES[4]]:,} is a carrier fact, not a"
          f" reading about deferrals.")
    print(f"     row_residuals' gate 3 also refuses whole loans on C13; that")
    print(f"     refusal has **no Freddie counterpart** (§8·14·5 put the")
    print(f"     zero-interest split in column 12 alone, so bad_c13 is")
    print(f"     identically false), so this table is narrower there by")
    print(f"     construction and not by luck.")

    print("\n  A2. §8·19·8: gates 3 and 4 are each a six-way `or`. Which way.")
    for tag, names, key, tot in (("gate 3", RESID_SUB3, "sub3", 2),
                                 ("gate 4", RESID_SUB4, "sub4", 3)):
        g = pl["gates"][RESID_GATES[tot]]
        print(f"     {tag}, {g:,} in all:")
        for nm in names:
            print(f"       {nm:<48} {pl[key][nm]:>8,}")
        t = pl[f"{key}_total"]
        print(f"       {'sum of the six':<48} {t:>8,}"
              f"   {'MATCH' if t == g else 'DO NOT ADD UP'}")
    print("     **Three of these twelve cannot fire at all**, and that is")
    print("     structural, not measured (§11 item 13). `floor_window` has")
    print("     already refused any trip carrying an unreadable UPB or an")
    print("     unreadable rate, so gate 3's two UPB lines and gate 4's rate")
    print("     line are zero by construction. The selftest proves the")
    print("     implication; it does not observe the zeros and infer it.")

    print("\n  A3. §8·19·8 variable two: the rem census on the priced trips")
    print(f"     rows whose rem will not read {pl['rows_rem_bad']:,}")
    print(f"     trips where EVERY row's rem will not read "
          f"{pl['trips_all_rem_bad']:,}"
          f"   their rows {pl['rows_all_rem_bad']:,}"
          f"   their pairs {pl['pairs_in_all_rem_bad']:,}")

    if prod is not None:
        print("\n  A4. the population, against its named producers (§8·16·3's"
              " form)")
        for rel, present, fields in prod:
            if not present:
                print(f"     {rel}: **not on disk.** The reconciliation was")
                print(f"     not run. A producer that is absent is said so,")
                print(f"     never skipped quietly.")
                continue
            for a, theirs, ours in fields:
                ok = theirs == pl.get(ours)
                print(f"     {rel:<28} {a:<14} {str(theirs):>12} against "
                      f"{ours} {str(pl.get(ours)):>12}   "
                      f"{'MATCH' if ok else 'MISMATCH'}")
    print(f"\n     {RESID_DEFECT}: {pl['defect']:,}")
    print("     **That line is a defect, not a filter** (row_residuals' own")
    print("     words). A non-zero there is something nobody predicted.")
    print("     Fannie's own table is printed beside this one, never")
    print("     subtracted from it (§7·9).")

    print("\n  B. the residual itself. **No omega, no loop sum** (§8·19·5)")
    print(f"     r        p10 {pl['q_r'][0]:+.4e}   p50 {pl['q_r'][1]:+.4e}"
          f"   p90 {pl['q_r'][2]:+.4e}")
    print(f"     |r|      p10 {pl['q_absr'][0]:.4e}   p50 {pl['q_absr'][1]:.4e}"
          f"   p90 {pl['q_absr'][2]:.4e}")
    print(f"     sampled {pl['sampled']:,}   capped {pl['sample_capped']}")

    print("\n  C. by vintage, first eight")
    rows = list(pl["by_vintage"].items())
    for v, d in rows[:8]:
        print(f"       {v}  n {d['n']:>8,}   p50 {d['q'][1]:+.4e}"
              f"   median |r| {d['absmed']:.4e}")
    if len(rows) > 8:
        print(f"       ... {len(rows) - 8} more in the record file")

    print("\n  D0. Read, per the criteria fixed before the run, two variables, three branches each")
    g4 = pl["gates"][RESID_GATES[3]]
    rem_only = pl["sub4"][RESID_SUB4[0]] + pl["sub4"][RESID_SUB4[1]]
    other4 = pl["sub4_total"] - rem_only
    if pl["sub4_total"] != g4:
        print("     variable one: THIRD BRANCH. The six sub-causes do not sum")
        print(f"     to gate 4 ({pl['sub4_total']:,} against {g4:,}). The")
        print("     split is wrong; nothing here is read.")
    elif other4 == 0:
        print("     variable one: FIRST BRANCH. Every one of gate 4's")
        print(f"     {g4:,} is a rem that will not read, on this row or the")
        print("     previous one. No unnamed component.")
    else:
        print("     variable one: SECOND BRANCH. **A population nobody has")
        print(f"     named**: {other4:,} of gate 4's {g4:,} are not a rem")
        print("     that will not read. Set out on its own line, never folded")
        print("     into §8·17's row census:")
        for nm in RESID_SUB4[2:]:
            if pl["sub4"][nm]:
                print(f"       {nm:<48} {pl['sub4'][nm]:>8,}")

    exp = pl["rows_all_rem_bad"] - pl["trips_all_rem_bad"]
    if g4 == pl["pairs_in_all_rem_bad"] == exp and other4 == 0:
        print("     variable two: FIRST BRANCH. Fully explained. §8·17's row")
        print(f"     census and this pair census are two ways of counting one")
        print(f"     set of rows: {pl['trips_all_rem_bad']:,} trips whose every")
        print(f"     row's rem is unreadable, {pl['rows_all_rem_bad']:,} rows,")
        print(f"     {exp:,} pairs, and gate 4 is {g4:,}.")
    elif g4 > pl["pairs_in_all_rem_bad"]:
        print("     variable two: SECOND BRANCH. §8·17's 57 rows do not cover")
        print(f"     gate 4: {g4:,} against {pl['pairs_in_all_rem_bad']:,}")
        print("     pairs inside wholly unreadable trips. The remainder is")
        print("     named by variable one above and stays on its own line.")
    else:
        print("     variable two: THIRD BRANCH, mixed (R01). The counts do not")
        print(f"     line up: gate 4 {g4:,}, pairs inside wholly unreadable")
        print(f"     trips {pl['pairs_in_all_rem_bad']:,}, rows minus trips")
        print(f"     {exp:,}. Not reinterpreted after the fact.")

    print("\n  D. What this section does NOT deliver (§8·19·5)")
    print("     No omega and no loop sum. Three carrier facts travel with any")
    print("     Freddie omega that is ever computed from these rows:")
    print("       bn and n are the SAME column here, so the case where Fannie's")
    print("       two horizons differ cannot occur, and gate 5 cannot fire;")
    print("       forgiven is 0 by absence, not by measurement, and Fannie's")
    print("       zero was measured;")
    print("       P is the ORIGINATION payment carried as state, not the")
    print("       previous contract period's, because Freddie publishes no")
    print("       per-row payment. On Fannie those two differ exactly at a")
    print("       modification month, which is leg 2. This population has no")
    print("       modifications in it (§8·16's round trips are the")
    print("       no-modification ones), so the two agree on every row here")
    print("       — a scope fact, and the scope is why it holds.")


def cmd_resid(only) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    if not vs:
        print(f"  no archives under {RAW}")
        return 1
    sys.path.insert(0, str(ROOT / "experiments"))
    import b8_cmt_fetch as F                      # noqa: E402
    import b8_loop_omega as LO                    # noqa: E402
    import b8_omega as W                          # noqa: E402
    import b8_0a_gate as G                        # noqa: E402
    import b10_c8_1d_freddie as FR                # noqa: E402

    if W.MAX_H != CURVE_MAX_H:
        print(f"  b8_omega.MAX_H is {W.MAX_H} and this file says "
              f"{CURVE_MAX_H}. Two copies of a bound with no check between "
              f"them is 失效模式 19. Fix one; nothing is read until then.")
        return 1

    #: **The pre-flight, before the Treasury load and before any archive.**
    #: A cross-check that runs after the numbers are on screen is a check
    #: nobody fails.
    if not print_crosscheck(resid_crosscheck(W, G)):
        print("\n  §8·19·3 did not pass. Nothing was read. Fix it first.")
        return 1
    print()

    #: **Read before the new one is written** (規矩 19). Doing it after would
    #: compare the file with itself.
    prior = prior_json(ROOT, partial_name("b10_resid", only))

    src, files = F.load_treasury()
    if not src:
        print("  no Treasury curve under data/raw/cmt.")
        return 1
    pos, tab = LO.curve_table_from(src, LO.RULE)

    print("§8·19: the residual driver. **B10 writes no residual formula** —\n"
          "b8_omega.r_month is imported and fed Freddie's columns.\n"
          f"  r_month from {W.__name__}, curve from {len(files)} file(s)\n")
    acc = resid_new_acc()
    for v in vs:
        orig, _ = FR.read_orig(v)
        with zipfile.ZipFile(archive(v)) as zf:
            with zf.open(f"sample_perf_{v}.txt") as raw:
                seq, batch = None, []
                for line in io.TextIOWrapper(raw, encoding="utf-8",
                                             newline=""):
                    if not line.strip():
                        continue
                    f = line.split("|")
                    if f[0] != seq:
                        if seq is not None:
                            resid_absorb(acc, batch, orig.get(seq), v, pos,
                                         tab, CURVE_MAX_H, W.r_month,
                                         FR.contract_payment)
                        seq, batch = f[0], []
                    batch.append(floor_row(f))
                if seq is not None:
                    resid_absorb(acc, batch, orig.get(seq), v, pos, tab,
                                 CURVE_MAX_H, W.r_month, FR.contract_payment)
        print(f"  {v}  done   admitted so far {acc['ok']:,}", flush=True)
    pl = resid_payload(acc)
    print_vs_prior(prior, pl, partial_name("b10_resid", only))
    print_resid(pl, prod=resid_producers(ROOT))

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / partial_name("b10_resid", only)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "resid", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Coverage only: the "
             "driver's gates and the residual's distribution. b8_omega.r_month "
             "is imported, not reimplemented. No omega and no loop sum.",
         "residual_from": "b8_omega.r_month",
         "bn_equals_n": True, "forgiven_is_zero_by_absence": True,
         "sample_cap": RESID_SAMPLE_CAP, **pl}, indent=2, sort_keys=True)
        + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def cmd_curve(only) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    if not vs:
        print(f"  no archives under {RAW}")
        return 1
    #: **Imported here, not at module level.** `b8_omega`'s own comment says
    #: putting the Treasury fetch behind a module's selftest is wrong, and this
    #: file's selftest must keep running with no CSVs on disk.
    sys.path.insert(0, str(ROOT / "experiments"))
    import b8_cmt_fetch as F                     # noqa: E402
    import b8_loop_omega as LO                   # noqa: E402
    import b8_omega as W                         # noqa: E402

    if W.MAX_H != CURVE_MAX_H:
        print(f"  b8_omega.MAX_H is {W.MAX_H} and this file says "
              f"{CURVE_MAX_H}. Two copies of a bound with no check between "
              f"them is 失效模式 19. Fix one; nothing is read until then.")
        return 1
    src, files = F.load_treasury()
    if not src:
        print("  no Treasury curve under data/raw/cmt. Run: python "
              "experiments/b8_cmt_fetch.py fetch")
        return 1
    pos, tab = LO.curve_table_from(src, LO.RULE)

    #: **Indices, not periods.** The gap hunt is plain integer arithmetic on
    #: the index; only the printing converts back, because a month index is
    #: unreadable to a human and a YYYYMM subtraction is wrong arithmetic.
    idx = sorted(pos)
    have = set(idx)
    missing = [yyyymm_of(k) for k in range(idx[0], idx[-1] + 1)
               if k not in have] if idx else []
    counts = sorted(sum(1 for h in range(1, CURVE_MAX_H + 1)
                        if tab[pos[mi]][h] == tab[pos[mi]][h])
                    for mi in idx)
    census = {"files": list(files)[:8], "n_files": len(files),
              "months": len(idx),
              "first_month": yyyymm_of(idx[0]) if idx else None,
              "last_month": yyyymm_of(idx[-1]) if idx else None,
              "first_index": idx[0] if idx else None,
              "last_index": idx[-1] if idx else None,
              "missing": missing,
              "h_min": counts[0] if counts else 0,
              "h_med": counts[len(counts) // 2] if counts else 0,
              "h_max": counts[-1] if counts else 0}

    print("§8·17: does the curve reach Freddie's horizons. No residual is\n"
          "written here, and no omega.\n")
    acc = curve_new_acc()
    for v in vs:
        with zipfile.ZipFile(archive(v)) as zf:
            with zf.open(f"sample_perf_{v}.txt") as raw:
                seq, batch = None, []
                for line in io.TextIOWrapper(raw, encoding="utf-8",
                                             newline=""):
                    if not line.strip():
                        continue
                    f = line.split("|")
                    if f[0] != seq:
                        if seq is not None:
                            curve_absorb(acc, batch, pos, tab, CURVE_MAX_H)
                        seq, batch = f[0], []
                    batch.append(floor_row(f))
                if seq is not None:
                    curve_absorb(acc, batch, pos, tab, CURVE_MAX_H)
        print(f"  {v}  done   priced trips so far {acc['priced_trips']:,}",
              flush=True)
    pl = curve_payload(acc, census)
    print_curve(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / partial_name("b10_curve", only)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "curve", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Coverage only: does "
             "the CMT curve reach the horizons Freddie's priced round trips "
             "need. No residual formula, no omega. Population is §8·16's, via "
             "the same floor_window.",
         "horizon": "rem_legal, per §8·14·6·8",
         **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def cmd_floor(only) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    if not vs:
        print(f"  no archives under {RAW}")
        return 1
    print("§8·16: the noise floor's construction half. No omega is computed,\n"
          "and the measured half is not in this file.\n")
    acc = floor_new_acc()
    for v in vs:
        with zipfile.ZipFile(archive(v)) as zf:
            with zf.open(f"sample_perf_{v}.txt") as raw:
                seq, batch = None, []
                for line in io.TextIOWrapper(raw, encoding="utf-8",
                                             newline=""):
                    if not line.strip():
                        continue
                    f = line.split("|")
                    if f[0] != seq:
                        if seq is not None:
                            floor_absorb(acc, batch)
                        seq, batch = f[0], []
                    batch.append(floor_row(f))
                if seq is not None:
                    floor_absorb(acc, batch)
        print(f"  {v}  done   round trips so far {acc['roundtrips']:,}",
              flush=True)
    pl = floor_payload(acc)
    print_floor(pl, gated=not only)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / partial_name("b10_floor", only)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "floor", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. The construction half "
             "of B8-0b only; N = MAD(omega - closed) needs an omega this "
             "station has not built. Population found by the same "
             "classify_loan the §3 gate uses.",
         "published_roundtrips": PUBLISHED_ROUNDTRIPS,
         "gated": not only, **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --omega. Registered before the code.
# Population: §8·16's priced round trips, through the same `floor_window`.
# Residual: §8·19's driver, through the same `pair_residual`.
# Closed form, path tolerance and half cent: b8_omega and b8_0a_gate, imported.
# ---------------------------------------------------------------------------

#: §8·20·7's four screens, each named after the `find_clean_cures` line it
#: mirrors. **Counted two ways**: a first-match partition that reconciles with
#: the rejection total, and a per-screen independent census that does not
#: depend on the order. §8·19·8 is why: a first-match partition's later members
#: read zero for the ordering, and that zero reads like "it did not happen".
OMEGA_SCREENS = (
    "a positive column 12 in the window (B8's field 108, O28)",
    "a blank column 12 in the window",
    "a period gap in the window (B8's p_gap)",
    "a non-delinquent month inside the window (B8's p_ndq)",
)

#: Samples kept for exact quantiles. Printed, never silent.
OMEGA_SAMPLE_CAP = 1_000_000


def b8_k(span) -> int:
    """**B8's `k`, not §8·16's** (§8·20·6).

    `find_clean_cures` defines `k = end - start`, the number of **missed
    months**, and the residual runs over `t0+1 .. end`, which is `k + 1`
    months. The window `t0..end` is therefore `k + 2` rows.

    §8·16's `k_hist` counts `len(span) - 1`, one higher, and its selftest
    names the option it rejected ("k is the span, not the run length") —
    which is exactly the one B8 uses. `loop_residual_ideal` is written to
    B8's definition, so feeding it the span is not a tolerance question, it
    is a different loop.
    """
    return len(span) - 2


def omega_flags(span):
    """§8·20·7's four screens as independent booleans, in `OMEGA_SCREENS` order.

    Independent, not first-match: the caller does both, so neither the
    ordering nor the total can hide a screen.
    """
    defer_pos = any(t[R_DEFER] is not None and t[R_DEFER] > 0 for t in span)
    defer_blank = any(t[R_DEFER] is None for t in span)
    gap = False
    for a, b in zip(span, span[1:]):
        ia, ib = month_index_of(a[R_PERIOD]), month_index_of(b[R_PERIOD])
        if ia < 0 or ib < 0 or ib != ia + 1:
            gap = True
            break
    #: B8's `rng(p_ndq, starts, ends_p - 1) == 0`: every month from the first
    #: delinquent one to the one before the cure must be delinquent. In this
    #: span that is indices 1 .. len-2.
    inside = any(not is_del_digits(t[R_DELINQ]) for t in span[1:-1])
    return (defer_pos, defer_blank, gap, inside)


def omega_new_acc() -> dict:
    def bucket():
        return {"n": 0, "stream": [], "closed": [], "ratio": [],
                "ideal_loose": 0, "ideal_derived": 0,
                "ratio_loose": [], "ratio_derived": [],
                "pathdev": [], "k": {}, "capped": False,
                #: §8·21·5 needs the qualifying loops' own sums, keyed by `k`,
                #: to set beside the floor at the matched window length.
                #: **Accumulator only**: `omega_payload` does not emit it, so
                #: `b10_omega.json` is byte for byte what it was (規矩 19).
                "stream_derived": {},
                #: §8·21·9. The same sums with **no path filter**, which is
                #: what B8's own (i-b) compares: *the same residual on every
                #: clean-cure loan, whatever its path*. Filtering one side and
                #: not the other is the asymmetry §8·21·6 had to diagnose
                #: after the fact.
                "stream_all": {},
                #: §8·29. The three factors of `|omega| = C * L * mean|r|`,
                #: keyed by `k` exactly as `stream_all` is, so the two are the
                #: same population by construction rather than by care.
                #: **Accumulator only**; `b10_omega.json` does not move.
                "coh": {},
                #: §8·24's two floors. `ambient` is every filed loop,
                #: `resolution` only the derived-path ones — where `P` is
                #: right, so what is left is the quantisation. **Accumulator
                #: only**; `b10_omega.json` does not move (規矩 19).
                "gap_ambient": [], "gap_resolution": []}
    #: §8·20·8. The `P_orig` numbers keep the **top-level** keys they had
    #: before, so 規矩 19's field-by-field comparison against the previous
    #: `b10_omega.json` can only report additions. `P_sub` lives in its own
    #: subtree. **The old P is not replaced and not deleted**, which is the
    #: same double report B8 keeps for its own O28 correction.
    def tree():
        return {"as16": bucket(), "b8like": bucket(),
                "no_P": 0, "not_measurable": 0, "nm_by_gate": {},
                "closed_no_log": 0}
    return {"loans": 0, "trips": 0, "priced_trips": 0,
            "no_orig": 0, "no_payment": 0, "rows_no_payment": 0,
            "no_P": 0, "span_too_short": 0,
            "not_measurable": 0, "nm_by_gate": {},
            "closed_no_log": 0,
            "screen_first": {g: 0 for g in OMEGA_SCREENS},
            "screen_any": {g: 0 for g in OMEGA_SCREENS},
            "screened_out": 0,
            "b16_ratio": [], "b16_k_only": [],
            "p_reldiff": [], "p_sub_unusable": 0,
            #: §8·26. **Accumulator only**: `omega_payload` does not emit it,
            #: so `b10_omega.json` and `b10_noise.json` stay byte for byte
            #: what they were (規矩 19). `--pgrid` reads it in memory.
            "pgrid": pgrid_new_acc(),
            "as16": bucket(), "b8like": bucket(),
            "p_sub": tree()}


def substitution_payment(t0, contract_payment, n_override=None):
    """§12.2's substitution: the payment from a **current** row (§8·20·8).

    `contract_payment`'s own docstring says it: *the original balance cancels,
    so the $1,000 grid it sits on never enters; `rem` is read from perf field
    6.* §8·19·1 fed it the origination balance instead, and Freddie's
    origination UPB is on that grid on every row of every archive checked.

    `t0` is the loop's first row, the last current month. §8·16 has already
    required age >= 8 across the window, so this balance is reported to the
    cent. The balance used is the **interest-bearing** one (§8·18), since that
    is what amortises.

    Returns None when the row cannot support a payment, so the caller counts
    rather than inheriting a silent zero.

    **`n_override` is §8·27's counterfactual horizon and it exists so there is
    still only one body.** §8·27 needs the same payment computed on
    `term - age` instead of on the reported `rem`, and writing that as a second
    function is how two payments end up differing by a balance rule nobody
    meant to change. The default is `None`, `loop_payments` does not pass it,
    and `omega_absorb`'s own call does not either — so §8·23's and §8·20's
    numbers cannot move (規矩 19, compared in the selftest rather than
    asserted here).
    """
    u, z = t0[R_UPB], t0[R_DEFER]
    rem, rate = t0[R_REM], t0[R_RATE]
    if n_override is not None:
        rem = n_override
    if u is None or z is None or rem is None or rate is None or rem <= 0:
        return None
    b = u - z
    if not (b > 0):
        return None
    cand = contract_payment(b, rate / 1200.0, rem)
    return cand if (cand == cand and cand > 0) else None


def omega_measure(span, P, W, G, pos, tab, max_h):
    """One loop's numbers for **one** `P`. No bookkeeping, no accumulator.

    Returns ``(status, payload)``. `status` is ``"ok"``, ``"not_measurable"``
    (payload is the gate that stopped it) or ``"closed_no_log"``.

    **Lifted out so the two payments run the same code.** Two copies is how
    `P_orig` and `P_sub` end up measured by two slightly different procedures
    and the comparison between them stops meaning anything.
    """
    rs = []
    for j in range(1, len(span)):
        gate, _sub, r = pair_residual(span[j - 1], span[j], P, pos, tab,
                                      max_h, W.r_month)
        if gate is None and r != r:
            gate = RESID_DEFECT
        if gate is not None:
            #: §17.10: one unreadable month drops the whole loop, because the
            #: sum is over the window and a partial sum is a different
            #: quantity.
            return "not_measurable", gate
        rs.append(r)

    k = b8_k(span)
    note = span[0][R_RATE]
    ib = [t[R_UPB] - t[R_DEFER] for t in span]
    B0 = ib[0]
    closed = float(W.loop_residual_ideal(B0, note, P, k))
    if closed != closed or closed in (float("inf"), float("-inf")):
        #: `f(B0) <= 0`: a loop within a payment or two of payoff, where the
        #: closed form has no logarithm. B8 counts it apart rather than letting
        #: a later `nanmax` swallow it; so does this.
        return "closed_no_log", None

    bmin = B0
    for j in range(1, len(span)):
        bh = float(W.carry_forward(ib[j - 1], note, P))
        bmin = min(bmin, ib[j], bh)
    bound = floor_bound(k, note, bmin)

    #: B8's own path test, both pieces: flat through the delinquency, and
    #: landing on `f^(k+1)(B0)` at the reinstatement.
    dev_flat = max((abs(x - B0) for x in ib[1:-1]), default=0.0)
    bs = B0
    for _ in range(k + 1):
        bs = float(W.carry_forward(bs, note, P))
    dev = max(dev_flat, abs(ib[-1] - bs))

    stream = sum(rs)
    #: §8·29. **`rs` was always computed here and never left the function.**
    #: The sum is what §8·20 reads; the terms are what §8·29 needs to say why
    #: the sum grows with the window. Adding the key is pure addition: nothing
    #: iterates this dict's keys, and `omega_payload` never sees it.
    return "ok", {"k": k, "note": note, "stream": stream, "closed": closed,
                  "rs": rs,
                  "bmin": bmin, "bound": bound,
                  "ratio": abs(stream - closed) / bound, "dev": dev,
                  "loose": dev <= G.IDEAL_TOL_LOOSE,
                  "derived": dev <= float(G.ideal_tol(note, k))}


#: §8·34·1. Origination fields this file has already named, gathered once so
#: the profile and the classifier read the same row.
CLS_PROFILE_COLS = (("fico", O_FICO), ("dti", O_DTI),
                    ("fthb", O_FTHB), ("purpose", O_PURPOSE))

#: §8·35·1. Two crisis windows, **named before the run from public dates**,
#: never picked out of the data: the subprime modification wave and the CARES
#: forbearance. Everything else is `calm`. A window declared from an external
#: event is a pre-declared reading of a printed object; a window fitted to the
#: series would be a line drawn on an estimator (纪律 11).
CRISIS_WINDOWS = (("gfc", 2008, 2011), ("cares", 2020, 2021))


def crisis_of(year):
    """Which declared window a cure year falls in, or `calm`."""
    if year is None:
        return None
    for name, lo, hi in CRISIS_WINDOWS:
        if lo <= year <= hi:
            return name
    return "calm"


def read_orig_profile(vintage: int, seq_col: int) -> dict:
    """`{loan_seq: {fico, dti, fthb, purpose}}`, unreadable values as None.

    **A second small pass over the origination file, not a widening of
    `b10_c8_1d_freddie.read_orig`.** That function returns the three fields
    the payment needs and is called from four modes; growing it would put a
    dict on every one of them for the sake of one. The origination file is one
    row per loan against seventy-five million performance rows, so a second
    pass over it costs nothing measurable.

    **Unreadable is `None`, never a sentinel.** Freddie writes 9s for missing
    FICO and DTI, and folding those into a band would put "not reported" in
    with "reported low" (§11 item 6).

    `seq_col` comes in rather than being named here: the loan-sequence column
    already has a name in `b10_c8_1d_freddie` and a second copy of a column
    index is how two readers end up keyed on two different fields (§11 item
    11). The caller passes `FR.O_SEQ`.
    """
    out = {}
    for f in orig_rows(vintage):
        if len(f) < ORIG_FIELDS:
            continue
        rec = {}
        for name, col in CLS_PROFILE_COLS:
            v = f[col].strip()
            rec[name] = v if v else None
        out[f[seq_col]] = rec
    return out


def tail_outcome(rows, span):
    """§8·34·1's second delivery: what the loan does **after** the cure.

    Returns `(months, months_to_event, redelinquent, ra, zero_balance)`.

    The rows after the cure are picked by **period**, not by index arithmetic:
    `floor_window` hands back the span and not its bounds, and re-deriving the
    bound by searching for a matching tuple would break on a loan whose two
    months happen to be identical. Periods are one per month within a loan.

    `months_to_event` is the exposure the hazard needs: months until the first
    re-delinquency, or every remaining month when there is none. Counting all
    remaining months for a loan that re-defaults early would hand it exposure
    it never had at risk.
    """
    if not span:
        return 0, 0, False, False, False
    per_b = span[-1][R_PERIOD]
    tail = [t for t in rows if t[R_PERIOD] > per_b]
    redel = ra = zero = False
    to_event = len(tail)
    for j, t in enumerate(tail):
        d = t[R_DELINQ]
        if d == "RA":
            ra = True
        if t[R_UPB] is not None and t[R_UPB] <= 0:
            zero = True
        if not redel and is_del_digits(d):
            redel = True
            to_event = j + 1
    return len(tail), to_event, redel, ra, zero


def cls_of(m):
    """§8·34. `m["cls"]`, read in one place so the key name is one."""
    return m.get("cls")


def over_bound_of(m):
    """§8·32. `m["over_bound"]`, read in one place so the key name is one.

    `None` means the loan had no readable origination balance and the question
    could not be put to it, which is not `False` (§11 item 6).
    """
    return m.get("over_bound")


#: §8·34·1. FICO bands are `fico_band`'s, which C9 §2.1 fixed; the other three
#: fields are kept as their published codes rather than bucketed, because
#: bucketing them would be this file inventing a scheme nobody registered.
def _ib_of(row):
    """§8·18's interest-bearing balance for one row, or None."""
    u, z = row[R_UPB], row[R_DEFER]
    return None if (u is None or z is None) else u - z


def frozen_pair(anchor, delinq):
    """§8·36·2. Is the delinquent month's interest-bearing balance the anchor's.

    **Exact, and no tolerance is available to set.** §8·16 already puts the
    whole window at age >= 8, and §5·2 measured that this carrier reports to
    the cent from age 7. Two numbers reported to the cent are equal or they
    are not.

    `None` means a balance was unreadable, which is **not** `False`
    (§11 item 6). §8·14·5's entire finding was that blank and
    zero are structurally opposite, and folding one into the other is failure
    mode 20. The caller keeps the three states apart: absent = the question
    does not apply (not a window-2 span), `None` = asked and unreadable,
    bool = answered.
    """
    b0, b1 = _ib_of(anchor), _ib_of(delinq)
    return None if (b0 is None or b1 is None) else b0 == b1


#: §8·38·1. Labels for the two values that are not a servicing code. They are
#: kept apart because **blank and "no row" are structurally opposite**: one
#: says the servicer reported no assistance, the other says this file could
#: not be asked. §8·14·5's whole finding, §11 item 6.
ASSIST_BLANK = "(blank)"
ASSIST_NOROW = "(row not found)"
#: §8·38·3 item 3. A listed code on the anchor, on the delinquent month and on
#: the cure month are three different claims, so the position is kept.
ASSIST_POS = ("anchor", "delinq", "cure")


def assist_of(span, amap):
    """§8·38·1. The servicing-assistance codes on a loop's own span rows.

    `amap` is `{period: raw column-30 value}` for this loan, built in
    `cmd_noise` off the raw line — **`floor_row` carries no such column and
    is not touched**, which is §8·25·2's precedent and keeps 規矩 19's surface
    where it is.

    Returns one entry per span row: the stripped value, or `None` when that
    row's period is not in the map at all. **Three states, kept apart**
    (§11 item 6): a listed code, a value that is not listed (blank included),
    and `None` for "the question could not be put to this row".
    """
    out = []
    for row in span:
        per = row[R_PERIOD]
        c = (amap.get(per) if (amap is not None and per is not None
                               and per >= 0) else None)
        out.append(c)
    return tuple(out)


def cls_new() -> dict:
    return {"n": 0, "fico": {}, "fico_bad": 0, "dti": [], "dti_bad": 0,
            "fthb": {}, "purpose": {},
            "months": 0, "exposure": 0, "redel": 0, "ra": 0, "zero": 0,
            "tail_months": [],
            #: §8·35. The calendar year the cure happened in, and which
            #: declared window it falls in. **Not the origination vintage**:
            #: §8·22·5 measured vintage-level movement on this carrier to be a
            #: composition effect, so a vintage cut answers "which loans" and
            #: this section asks "what was happening that year".
            "by_year": {}, "by_window": {},
            #: §8·36. `{year: [loops, frozen, r1_negative]}` and the same by
            #: month for 2019, where the break falls inside the year.
            #: `froz_unread` is the loops the question was PUT to and could not
            #: be answered on (a balance unreadable). They are counted apart:
            #: they do not join "not frozen".
            "froz_year": {}, "froz_month": {}, "froz_unread": 0,
            #: §8·38. `asg_n` is the loops the question was put to at all;
            #: `asg_any` those with at least one listed code; `asg_unk` those
            #: where some span row could not be looked up. `asg_code`是逐取值
            #: 的枚举 (C0b), `asg_pos` which row carried it, `asg_year`
            #: `{year: [loops, assisted]}`.
            "asg_n": 0, "asg_any": 0, "asg_unk": 0,
            "asg_code": {}, "asg_pos": {}, "asg_year": {}}


def cls_file(d, cls) -> None:
    """§8·34's per-loop census for one sign class. Counts only, no estimates."""
    d["n"] += 1
    prof = cls.get("prof") or {}
    f = prof.get("fico")
    try:
        d["fico"][fico_band(int(f))] = d["fico"].get(fico_band(int(f)), 0) + 1
    except (TypeError, ValueError):
        d["fico_bad"] += 1
    try:
        d["dti"].append(int(prof.get("dti")))
    except (TypeError, ValueError):
        d["dti_bad"] += 1
    for k in ("fthb", "purpose"):
        v = prof.get(k) or "?"
        d[k][v] = d[k].get(v, 0) + 1
    d["months"] += cls["months"]
    d["exposure"] += cls["exposure"]
    d["redel"] += 1 if cls["redel"] else 0
    d["ra"] += 1 if cls["ra"] else 0
    d["zero"] += 1 if cls["zero"] else 0
    d["tail_months"].append(cls["months"])
    y = cls.get("cure_year")
    if y is not None:
        d["by_year"][y] = d["by_year"].get(y, 0) + 1
        w = crisis_of(y)
        d["by_window"][w] = d["by_window"].get(w, 0) + 1
        #: §8·36. Three states, kept apart: the key is ABSENT when the loop is
        #: not a window-2 span and the question does not apply; `None` when it
        #: was put and a balance was unreadable; a bool when it was answered.
        if "frozen" in cls:
            fz, r1n = cls["frozen"], cls.get("r1_negative")
            if fz is None:
                d["froz_unread"] += 1
            else:
                for key, box in ((y, d["froz_year"]),
                                 (cls.get("cure_period"), d["froz_month"])):
                    if key is None:
                        continue
                    cell = box.setdefault(key, [0, 0, 0])
                    cell[0] += 1
                    cell[1] += 1 if fz else 0
                    cell[2] += 1 if r1n else 0
        #: §8·38. Same three-state discipline: the key is ABSENT unless the
        #: caller supplied a code map, so `--omega`/`--pgrid`/`--o18join`
        #: carry none of this and their artifacts cannot move.
        if "assist" in cls:
            codes, ok = cls["assist"], cls.get("assist_codes") or ()
            d["asg_n"] += 1
            hit = [c for c in codes if c is not None and c in ok]
            d["asg_any"] += 1 if hit else 0
            if any(c is None for c in codes):
                d["asg_unk"] += 1
            for i, c in enumerate(codes):
                key = (ASSIST_NOROW if c is None
                       else (ASSIST_BLANK if c == "" else c))
                d["asg_code"][key] = d["asg_code"].get(key, 0) + 1
                if c is not None and c in ok and i < len(ASSIST_POS) \
                        and len(codes) == len(ASSIST_POS):
                    nm = ASSIST_POS[i]
                    d["asg_pos"][nm] = d["asg_pos"].get(nm, 0) + 1
            if y is not None:
                cell = d["asg_year"].setdefault(y, [0, 0])
                cell[0] += 1
                cell[1] += 1 if hit else 0


#: §8·37·2's dump is capped, and the cap prints beside the count.
THM_BREAK_CAP = 40

#: The display window for the vintage x cure-month cut: three calendar years
#: straddling both measured breaks (§8·37·2's 201904/05 and §8·36·3's
#: 201906/07). **A window on a table, not a filter on a reading** — every
#: vintage's all-time totals print beside it so nothing is hidden.
VIN_MONTH_LO, VIN_MONTH_HI = 201801, 202012

#: `print_noise`'s chain takes one argument, so the prior artifact reaches
#: `print_vin` through here rather than by rewriting nine signatures. Set in
#: `cmd_noise` beside the 規矩 19 comparison, empty everywhere else.
NOISE_PRIOR = {}


def thm_break_row(cls, rs, pk) -> dict:
    """§8·37·2. One loop that a frozen month left on the negative side.

    Every field the theorem's premise needs, printed rather than argued
    about. §8·36·1 reads `bal(t1)` against `carry_forward(bal(t0), note, P)`,
    and that step only pushes the balance down when **`P` exceeds the month's
    interest**. `P` on this carrier is an estimate, not a published figure
    (§8·20·8), so the comparison is a column here, not an assumption.
    """
    span, P, vintage = cls["dx"]
    a, b = span[0], span[1]
    ib_a, ib_b = _ib_of(a), _ib_of(b)
    note = a[R_RATE]
    interest = (ib_a * note / 1200.0) if (ib_a is not None
                                          and note is not None) else None
    return {"class": pk, "vintage": vintage,
            "period_a": a[R_PERIOD], "period_1": b[R_PERIOD],
            "period_b": span[-1][R_PERIOD],
            "age_a": a[R_AGE], "rem_a": a[R_REM],
            "upb_a": a[R_UPB], "defer_a": a[R_DEFER],
            "upb_1": b[R_UPB], "defer_1": b[R_DEFER],
            "ib_a": ib_a, "ib_1": ib_b, "note": note,
            "P": P, "interest": interest,
            "P_exceeds_interest": (None if (P is None or interest is None)
                                   else P > interest),
            "r": [round(x, 10) for x in rs]}


def coh_file(coh, k, rs, stream, derived, over_bound, cls=None) -> None:
    """§8·29 / §8·31 / §8·32's per-loop accumulation. **One body.**

    Extracted because the selftest had grown a second copy of it in order to
    build fixtures, and a fixture that reimplements the thing it tests tests
    the reimplementation. This station has already paid twice for a stand-in
    diverging from the real code (`b10_support_fannie`'s `SENTINEL`, then
    §8·19·3's gate being invisible in the sandbox), so the fixture now calls
    what the scan calls.
    """
    if not rs:
        return
    tot = sum(abs(x) for x in rs)
    c = coh.setdefault(k, {"C": [], "meanabs": [], "absom": [],
                           "same_sign": [], "n_months": len(rs),
                           "pat": {}, "sgn2x2": {}, "allsame": [],
                           "cvals": {}, "pat2x2": {}, "ideal_pat": 0,
                           "ideal_and_derived": 0, "derived_off_pattern": 0,
                           "ob_unknown": 0,
                           #: §8·33.
                           "npos": {}, "delinq_months": 0, "pos_months": 0,
                           "cure_neg": 0})
    pos = sum(1 for x in rs if x > 0)
    neg = sum(1 for x in rs if x < 0)
    allsame = (pos == len(rs)) or (neg == len(rs))
    c["allsame"].append(1 if allsame else 0)
    key = ("S" if allsame else "s") + ("q" if derived else "n")
    c["sgn2x2"][key] = c["sgn2x2"].get(key, 0) + 1
    pk = "".join("+" if x > 0 else ("-" if x < 0 else "0") for x in rs)
    #: §8·32·1. The ideal pattern generalised to any window, straight out of
    #: §8·31·1's derivation: `L-1` delinquent months reading positive and one
    #: cure month reading negative.
    pat_ok = (pk == ideal_pattern(len(rs)))
    c["ideal_pat"] += 1 if pat_ok else 0
    #: §8·33·1. The pattern is `L-1` delinquent months positive and one cure
    #: month negative, so the two halves are counted apart: how many of the
    #: delinquent months got it right, and whether the cure month did. The
    #: compound prediction needs both rates and they are counts, not fits.
    n_pos = sum(1 for x in rs[:-1] if x > 0)
    c["npos"][n_pos] = c["npos"].get(n_pos, 0) + 1
    c["delinq_months"] += len(rs) - 1
    c["pos_months"] += n_pos
    c["cure_neg"] += 1 if (rs and rs[-1] < 0) else 0
    if derived:
        c["ideal_and_derived" if pat_ok else "derived_off_pattern"] += 1
    #: §8·32·2's 2x2. `over_bound is None` means the question could not be put
    #: to this loan; a third state, counted apart (§11 item 6).
    if over_bound is None:
        c["ob_unknown"] += 1
    else:
        bk = ("P" if not pat_ok else "p") + ("O" if over_bound else "o")
        c["pat2x2"][bk] = c["pat2x2"].get(bk, 0) + 1
    #: §8·31·1. On a two-month window the four patterns are the whole
    #: alphabet, so they are enumerated rather than summarised. Longer windows
    #: would need `2**L` cells, so those get the same-sign split only — and
    #: the cut-off is stated, not silent.
    if len(rs) <= 2:
        p_ = c["pat"].setdefault(pk, {"n": 0, "q": 0, "ma": [], "om": []})
        p_["n"] += 1
        p_["q"] += 1 if derived else 0
        p_["ma"].append(tot / len(rs))
        p_["om"].append(abs(stream))
        #: §8·34. The class census, filed on the same key the alphabet uses.
        #: `cls` is None from every caller except `--noise`, so nothing else
        #: pays for it and no other artifact moves.
        if cls is not None:
            #: §8·36·4 item 1. The sign of the delinquent month lives where
            #: `rs` lives, not in `omega_absorb`, so it is set here rather
            #: than carried in from a place that would have to re-derive it.
            cls["r1_negative"] = bool(rs and rs[0] < 0)
            #: §8·37·2. A frozen loop cannot be `-+` or `--` if §8·36·1's
            #: theorem holds, so every loop that IS one gets dumped field by
            #: field. **The count is separate from the cap** (a silent cap
            #: reads as full coverage), and the class is decided here because
            #: this is where `rs` lives (§8·36·4 item 1).
            #: The vintage x cure-month cut. **No branch and no verdict**:
            #: this is a printed object by design rather than a criterion. A reporting-cycle change lands on every
            #: vintage in the same calendar month; a property of the loans
            #: does not. The reader does that comparison, not this file.
            if cls.get("frozen") is not None and cls.get("vintage") is not None:
                vin, per = cls["vintage"], cls.get("cure_period")
                fz, is_pp = cls["frozen"], (pk == "++")
                allbox = c.setdefault("vin_all", {}).setdefault(str(vin),
                                                               [0, 0, 0])
                allbox[0] += 1
                allbox[1] += 1 if fz else 0
                allbox[2] += 1 if (fz and is_pp) else 0
                if per is not None and VIN_MONTH_LO <= per <= VIN_MONTH_HI:
                    key = "%d|%d" % (vin, per)
                    box = c.setdefault("vin_month", {}).setdefault(key,
                                                                  [0, 0, 0])
                    box[0] += 1
                    box[1] += 1 if fz else 0
                    box[2] += 1 if (fz and is_pp) else 0
            if cls.get("frozen") and pk[:1] == "-":
                c["thm_n"] = c.get("thm_n", 0) + 1
                box = c.setdefault("thm_break", [])
                if len(box) < THM_BREAK_CAP:
                    box.append(thm_break_row(cls, rs, pk))
            cls_file(c.setdefault("cls", {}).setdefault(pk, cls_new()), cls)
    if tot > 0:
        cv = abs(stream) / tot
        c["C"].append(cv)
        #: §8·31·3 item 2. On two months `C` takes finitely many values, so
        #: "exactly 1" is a structural fact and not a quantile artefact.
        if len(rs) <= 2:
            ck = "1" if cv == 1.0 else ("0" if cv == 0.0 else "mid")
            c["cvals"][ck] = c["cvals"].get(ck, 0) + 1
        sgn = 1.0 if stream >= 0 else -1.0
        c["same_sign"].append(
            sum(1 for x in rs if (x >= 0) == (sgn >= 0)) / len(rs))
    c["meanabs"].append(tot / len(rs))
    c["absom"].append(abs(stream))


def omega_file(tree, m, flags) -> None:
    """File one measured loop into `as16` and, when unscreened, `b8like`."""
    for name in ("as16",) + (() if any(flags) else ("b8like",)):
        b = tree[name]
        b["n"] += 1
        b["k"][m["k"]] = b["k"].get(m["k"], 0) + 1
        if len(b["stream"]) < OMEGA_SAMPLE_CAP:
            b["stream"].append(m["stream"])
            b["closed"].append(m["closed"])
            b["ratio"].append(m["ratio"])
            b["pathdev"].append(m["dev"])
        else:
            b["capped"] = True
        if m["loose"]:
            b["ideal_loose"] += 1
            b["ratio_loose"].append(m["ratio"])
        b["stream_all"].setdefault(m["k"], []).append(m["stream"])
        #: §8·29, **filed at the same line as `stream_all` and keyed the same
        #: way**, because §8·21·9's ratio is read off `stream_all` and a
        #: factor measured on any other population explains a different
        #: number.
        coh_file(b["coh"], m["k"], m.get("rs"), m["stream"],
                 m["derived"], over_bound_of(m), cls_of(m))
        if len(b["gap_ambient"]) < OMEGA_SAMPLE_CAP:
            b["gap_ambient"].append(abs(m["stream"] - m["closed"]))
        if m["derived"]:
            if len(b["gap_resolution"]) < OMEGA_SAMPLE_CAP:
                b["gap_resolution"].append(abs(m["stream"] - m["closed"]))
        if m["derived"]:
            b["ideal_derived"] += 1
            b["ratio_derived"].append(m["ratio"])
            b["stream_derived"].setdefault(m["k"], []).append(m["stream"])


def omega_absorb(acc, rows, orig, vintage, pos, tab, max_h, W, G,
                 contract_payment, prof=None, amap=None, acodes=()) -> None:
    """One loan, one loop sum, **two payments** (§8·20·8).

    No second driver and no second finder: the population is `floor_window`'s,
    the residual is `pair_residual`'s, and the two payments run through one
    `omega_measure`.
    """
    acc["loans"] += 1
    st, span, _ages, bals, rates = floor_window(rows)
    if st == "no_trip":
        return
    acc["trips"] += 1
    if st != "priced":
        return
    acc["priced_trips"] += 1

    #: `between_window` puts a delinquent row strictly between the last current
    #: one and the cure, so a span is at least three rows and `b8_k >= 1`.
    #: **Counted rather than assumed**, and the selftest proves the window
    #: cannot be shorter (§11 item 13's third kind).
    if len(span) < 3:
        acc["span_too_short"] += 1
        return

    P_orig = resid_payment(acc, orig, span, contract_payment)
    P_sub = substitution_payment(span[0], contract_payment)
    if P_sub is None:
        acc["p_sub_unusable"] += 1
    if P_orig is not None and P_sub is not None:
        if len(acc["p_reldiff"]) < OMEGA_SAMPLE_CAP:
            acc["p_reldiff"].append(abs(P_sub - P_orig) / P_orig)

    #: **Computed here, counted below.** The four screens are a property of
    #: the window, but the published §8·20 counts them only on loops that
    #: `P_orig` actually measured, and moving that would change three figures
    #: already in the results file. 規矩 19 governs: the counting stays where
    #: it was, and where it is is stated rather than left to be inferred.
    flags = omega_flags(span)

    #: §8·32. Computed once, before the two-tree loop, from the **same**
    #: function `pgrid_file` calls. It is a property of the loan and its two
    #: payments, not of which tree is being filled.
    _, _, over_bound = pgrid_over(P_orig, P_sub,
                                  orig[0] if orig is not None else None)
    #: §8·34. Built once per loan and only when a profile was handed in, so
    #: `--omega`, `--pgrid` and `--o18join` carry none of it.
    cls = None
    if prof is not None:
        mo, ex, rd, ra, zb = tail_outcome(rows, span)
        #: §8·35·0. The cure month is the span's last row; its year is the
        #: period over a hundred. One field, no arithmetic on money.
        cy = None
        if span and span[-1][R_PERIOD] and span[-1][R_PERIOD] > 0:
            cy = span[-1][R_PERIOD] // 100
        #: §8·36·2. Frozen means the delinquent month's **interest-bearing**
        #: balance is exactly the anchor's — §8·18's `col 3 - col 12`, and
        #: exactly, with no tolerance: §8·16 already requires age >= 8 across
        #: the window, where this carrier reports to the cent.
        cls = {"prof": prof, "months": mo, "exposure": ex,
               "redel": rd, "ra": ra, "zero": zb, "cure_year": cy,
               "cure_period": (span[-1][R_PERIOD] if span else None),
               "vintage": vintage}
        #: The key is set **only** on a window-2 span. On any other window the
        #: question is not put at all, and an absent key is not the same thing
        #: as an unanswerable one.
        if len(span) == 3:
            cls["frozen"] = frozen_pair(span[0], span[1])
            #: §8·37·2's gate fired on one loop and its处置 is 回去查, not
            #: "think of a reason". These are **references, not copies**, and
            #: they are read only on the loops that trip the gate.
            cls["dx"] = (span, P_orig, vintage)
        #: §8·38. Set **only** when a code map was handed in, so an absent key
        #: means "no caller asked", never "no code".
        if amap is not None:
            cls["assist"] = assist_of(span, amap)
            cls["assist_codes"] = tuple(acodes)
    for P, tree in ((P_orig, acc), (P_sub, acc["p_sub"])):
        if P is None:
            tree["no_P"] += 1
            continue
        status, m = omega_measure(span, P, W, G, pos, tab, max_h)
        if status == "ok":
            m["over_bound"] = over_bound
            m["cls"] = cls
        if status == "not_measurable":
            tree["not_measurable"] += 1
            tree["nm_by_gate"][m] = tree["nm_by_gate"].get(m, 0) + 1
            continue
        if status == "closed_no_log":
            tree["closed_no_log"] += 1
            continue
        if tree is acc:
            for f, g in zip(flags, OMEGA_SCREENS):
                if f:
                    acc["screen_any"][g] += 1
            if any(flags):
                acc["screen_first"][OMEGA_SCREENS[flags.index(True)]] += 1
                acc["screened_out"] += 1
        omega_file(tree, m, flags)
        #: §8·26. **Filed here and nowhere else**, because this is the one
        #: place where `P_orig`, `P_sub`, the origination balance and the path
        #: verdict are all in scope at once. The `b8like` screen is applied by
        #: the same expression `omega_file` uses, not by a second copy of it.
        if tree is acc and not any(flags):
            pgrid_file(acc["pgrid"], P_orig, P_sub, m["derived"],
                       orig[0] if orig is not None else None,
                       t0=span[0],
                       term=orig[2] if orig is not None else None,
                       contract_payment=contract_payment)
        if tree is acc:
            #: §8·20·6 item 2: how conservative §8·16's bound was, measured
            #: rather than reasoned. Two ratios, because two things differ:
            #: the `k` and the `b_min` (§8·16 took the minimum reported UPB;
            #: B8 takes the minimum over interest-bearing balances **and**
            #: counterfactual ones). Kept on `P_orig` so the figure §8·20·4
            #: already published does not move.
            b16 = floor_bound(len(span) - 1, m["note"], min(bals))
            if len(acc["b16_ratio"]) < OMEGA_SAMPLE_CAP:
                acc["b16_ratio"].append(b16 / m["bound"])
                acc["b16_k_only"].append(
                    floor_bound(len(span) - 1, m["note"], m["bmin"])
                    / m["bound"])


#: `results/b8_0a_gate.md`, the six `derived` rows, transcribed 2026-08-20.
#: **Printed beside, never subtracted** (§7·9). Columns: loops, ideal path,
#: rate, ratio_max, ratio p50, p90, p99.
B8_0A_DERIVED = (
    ("2002Q1", 32_920, 19_807, 0.6017, 0.400, 0.122, 0.280, 0.376),
    ("2006Q1", 10_361, 6_122, 0.5909, 0.399, 0.116, 0.275, 0.366),
    ("2007Q1", 11_124, 6_603, 0.5936, 0.400, 0.120, 0.275, 0.376),
    ("2012Q1", 8_527, 5_644, 0.6619, 0.400, 0.119, 0.273, 0.364),
    ("2017Q1", 16_423, 10_203, 0.6213, 0.400, 0.116, 0.272, 0.365),
    ("2019Q1", 12_079, 6_467, 0.5354, 0.400, 0.115, 0.272, 0.365),
)


def omega_payload(acc) -> dict:
    def b(x):
        return {"n": x["n"],
                "ideal_loose": x["ideal_loose"],
                "ideal_derived": x["ideal_derived"],
                "rate_loose": (x["ideal_loose"] / x["n"]) if x["n"] else None,
                "rate_derived": (x["ideal_derived"] / x["n"]) if x["n"]
                else None,
                "q_stream": _q(x["stream"]),
                "q_absstream": _q([abs(v) for v in x["stream"]]),
                "q_closed": _q(x["closed"]),
                "q_ratio_all": _q(x["ratio"]),
                "q_ratio_loose": _q(x["ratio_loose"], (50, 90, 99)),
                "q_ratio_derived": _q(x["ratio_derived"], (50, 90, 99)),
                "ratio_max_loose": max(x["ratio_loose"]) if x["ratio_loose"]
                else None,
                "ratio_max_derived": (max(x["ratio_derived"])
                                      if x["ratio_derived"] else None),
                "over_one_loose": sum(1 for v in x["ratio_loose"] if v >= 1.0),
                "over_one_derived": sum(1 for v in x["ratio_derived"]
                                        if v >= 1.0),
                "q_pathdev": _q(x["pathdev"]),
                "k_hist": {str(kk): vv for kk, vv in
                           sorted(x["k"].items(), key=lambda kv: -kv[1])[:12]},
                "k_q": _q(sum(([kk] * vv for kk, vv in x["k"].items()), [])),
                "sampled": len(x["stream"]), "capped": x["capped"]}
    return {"loans": acc["loans"], "trips": acc["trips"],
            "priced_trips": acc["priced_trips"],
            "no_orig": acc["no_orig"], "no_payment": acc["no_payment"],
            "no_P": acc["no_P"], "span_too_short": acc["span_too_short"],
            "not_measurable": acc["not_measurable"],
            "nm_by_gate": dict(acc["nm_by_gate"]),
            "closed_no_log": acc["closed_no_log"],
            "screen_first": dict(acc["screen_first"]),
            "screen_any": dict(acc["screen_any"]),
            "screened_out": acc["screened_out"],
            "q_b16_ratio": _q(acc["b16_ratio"]),
            "q_b16_k_only": _q(acc["b16_k_only"]),
            "as16": b(acc["as16"]), "b8like": b(acc["b8like"]),
            #: §8·20·8, added beside the above and never in place of it.
            "p_sub": {"as16": b(acc["p_sub"]["as16"]),
                      "b8like": b(acc["p_sub"]["b8like"]),
                      "no_P": acc["p_sub"]["no_P"],
                      "not_measurable": acc["p_sub"]["not_measurable"],
                      "nm_by_gate": dict(acc["p_sub"]["nm_by_gate"]),
                      "closed_no_log": acc["p_sub"]["closed_no_log"]},
            "q_p_reldiff": _q(acc["p_reldiff"], (10, 50, 90, 99)),
            "p_reldiff_max": (max(acc["p_reldiff"]) if acc["p_reldiff"]
                              else None),
            "p_reldiff_n": len(acc["p_reldiff"]),
            "p_reldiff_tiny": sum(1 for x in acc["p_reldiff"] if x < 1e-6),
            "p_sub_unusable": acc["p_sub_unusable"]}


def print_omega(pl) -> None:
    print("\n  A. the population, and what left it")
    print(f"     loans {pl['loans']:,}   round trips {pl['trips']:,}"
          f"   priced {pl['priced_trips']:,}")
    tot = (pl["no_P"] + pl["span_too_short"] + pl["not_measurable"]
           + pl["closed_no_log"] + pl["as16"]["n"])
    for nm, v in (("no usable contract payment", pl["no_P"]),
                  ("span shorter than three rows", pl["span_too_short"]),
                  ("a month with no computable r (§17.10)",
                   pl["not_measurable"]),
                  ("f(B0) <= 0, the closed form has no log",
                   pl["closed_no_log"]),
                  ("**loops measured (as16)**", pl["as16"]["n"])):
        print(f"       {nm:<48} {v:>9,}")
    print(f"       {'sum':<48} {tot:>9,} against priced"
          f" {pl['priced_trips']:,}"
          f"   {'MATCH' if tot == pl['priced_trips'] else 'DO NOT ADD UP'}")
    if pl["nm_by_gate"]:
        print("     which gate stopped the unmeasurable ones:")
        for g, v in sorted(pl["nm_by_gate"].items(), key=lambda kv: -kv[1]):
            print(f"       {g:<48} {v:>9,}")
    print("     span shorter than three rows is a **structural zero**:")
    print("     `between_window` puts a delinquent row strictly between the")
    print("     last current one and the cure. The selftest proves it.")

    print("\n  B. §8·20·7's four screens, two ways of counting")
    print(f"     {'screen':<52}{'first match':>12}{'independent':>13}")
    for g in OMEGA_SCREENS:
        print(f"     {g:<52}{pl['screen_first'][g]:>12,}"
              f"{pl['screen_any'][g]:>13,}")
    sf = sum(pl["screen_first"].values())
    print(f"     {'sum of first-match':<52}{sf:>12,}"
          f"   against screened out {pl['screened_out']:,}"
          f"   {'MATCH' if sf == pl['screened_out'] else 'DO NOT ADD UP'}")
    print("     **The two columns differ where a loop trips more than one**")
    print("     screen. The independent column is printed because a")
    print("     first-match partition's later members read zero for the")
    print("     ordering (§11 item 13, third kind).")
    print(f"     as16 {pl['as16']['n']:,}   b8like {pl['b8like']['n']:,}"
          f"   difference {pl['as16']['n'] - pl['b8like']['n']:,}")

    print("\n  C. §8·20·6: how conservative §8·16's bound was, measured")
    print(f"     bound(§8·16's k and b_min) / bound(B8's)   "
          f"p10 {pl['q_b16_ratio'][0]:.4f}  p50 {pl['q_b16_ratio'][1]:.4f}"
          f"  p90 {pl['q_b16_ratio'][2]:.4f}")
    print(f"     the k alone, b_min held at B8's         "
          f"   p10 {pl['q_b16_k_only'][0]:.4f}  p50 {pl['q_b16_k_only'][1]:.4f}"
          f"  p90 {pl['q_b16_k_only'][2]:.4f}")
    print("     §8·16's reading does not change: a bound one step conservative")
    print("     is still a bound, and the order-of-magnitude comparison it")
    print("     made against the $1,000 grid does not move. **What moves is")
    print("     that §8·20 uses B8's k, because loop_residual_ideal is written")
    print("     to it.**")

    print("\n  D. omega itself, on both populations")
    for nm in ("as16", "b8like"):
        d = pl[nm]
        print(f"     --- {nm}, {d['n']:,} loops, k p10/p50/p90 "
              f"{d['k_q'][0]:.0f}/{d['k_q'][1]:.0f}/{d['k_q'][2]:.0f} ---")
        if not d["n"]:
            print("       empty.")
            continue
        print(f"       omega      p10 {d['q_stream'][0]:+.4e}"
              f"   p50 {d['q_stream'][1]:+.4e}"
              f"   p90 {d['q_stream'][2]:+.4e}")
        print(f"       closed     p10 {d['q_closed'][0]:+.4e}"
              f"   p50 {d['q_closed'][1]:+.4e}"
              f"   p90 {d['q_closed'][2]:+.4e}")
        print(f"       path dev   p10 {d['q_pathdev'][0]:.4f}"
              f"   p50 {d['q_pathdev'][1]:.4f}"
              f"   p90 {d['q_pathdev'][2]:.4f}   (dollars)")
        for build in ("loose", "derived"):
            n = d[f"ideal_{build}"]
            rt = d[f"rate_{build}"]
            mx = d[f"ratio_max_{build}"]
            q = d[f"q_ratio_{build}"]
            print(f"       {build:<8} ideal path {n:>8,}"
                  f"  rate {('%.4f' % rt) if rt is not None else 'n/a':>7}"
                  f"  ratio_max "
                  f"{('%.4f' % mx) if mx is not None else 'undefined':>9}"
                  f"  p50 {q[0]:.4f}  p90 {q[1]:.4f}  p99 {q[2]:.4f}"
                  f"  over 1: {d[f'over_one_{build}']:,}")
        print(f"       sampled {d['sampled']:,}   capped {d['capped']}")

    print("\n  E. Fannie's own table beside it (results/b8_0a_gate.md,"
          " derived)")
    print(f"     {'archive':<10}{'loops':>9}{'ideal':>9}{'rate':>8}"
          f"{'ratio_max':>11}{'p50':>8}{'p90':>8}{'p99':>8}")
    for a, lo, idp, rt, mx, p50, p90, p99 in B8_0A_DERIVED:
        print(f"     {a:<10}{lo:>9,}{idp:>9,}{rt:>8.4f}{mx:>11.4f}"
              f"{p50:>8.4f}{p90:>8.4f}{p99:>8.4f}")
    print("     **Beside, not subtracted** (§7·9). The registration's")
    print("     prediction, written before this run: ratio_max reads 0.400 on")
    print("     all six Fannie archives, and Freddie was predicted to land in")
    print("     the same neighbourhood. **A prediction, not a criterion.**")

    print("\n  F. Read, per the criteria fixed before the run, one variable, three branches")
    print("     variable: ratio_max on the derived-path loops, b8like"
          " population")
    mx = pl["b8like"]["ratio_max_derived"]
    if mx is None:
        print("     §8·20·3 -> THIRD BRANCH. **The gate is empty**: not one")
        print("     loop's observed path matched the ideal one. By B8-0a's own")
        print("     words that points at P or at the dates, and this carrier's")
        print("     P is the origination payment, not the previous contract")
        print("     period's (§8·20·1). Nothing about omega is read.")
    elif mx < 1.0:
        print(f"     §8·20·3 -> FIRST BRANCH, pass. ratio_max {mx:.4f} < 1.0")
        print(f"     on {pl['b8like']['ideal_derived']:,} loops. Same direction")
        print("     as Fannie's six archives. omega is usable on this carrier.")
    else:
        print(f"     §8·20·3 -> SECOND BRANCH, fail. ratio_max {mx:.4f} >= 1.0")
        print("     on")
        print(f"     {pl['b8like']['over_one_derived']:,} of")
        print(f"     {pl['b8like']['ideal_derived']:,} loops. **The tolerance")
        print("     is not to be widened**: B8-0a's own first run failed this")
        print("     way and the fix was making the path tolerance and the")
        print("     bound share one half cent, which this file did from the")
        print("     start. That road is already taken.")
    print("     loose is printed above for comparability with Fannie's table")
    print("     and **is not read**.")

    print("\n  H. §8·20·8: the two payments, side by side")
    print("     P_orig = contract_payment(orig UPB, i, orig term), which is")
    print("     what §8·19·1 registered. P_sub = §12.2's substitution, from")
    print("     the loop's first row: interest-bearing balance and perf rem.")
    print("     **The old one is not replaced and not deleted.**")
    print(f"     loops with both payments {pl['p_reldiff_n']:,}"
          f"   P_sub unusable {pl['p_sub_unusable']:,}"
          f"   P_sub had no loop {pl['p_sub']['no_P']:,}")
    if pl["p_reldiff_n"]:
        q = pl["q_p_reldiff"]
        print(f"     |P_sub - P_orig| / P_orig"
              f"   p10 {q[0]:.3e}  p50 {q[1]:.3e}  p90 {q[2]:.3e}"
              f"  p99 {q[3]:.3e}  max {pl['p_reldiff_max']:.3e}")
        print(f"     under 1e-6 (the two payments agree): "
              f"{pl['p_reldiff_tiny']:,}"
              f" = {pl['p_reldiff_tiny'] / pl['p_reldiff_n']:.4f}")
        print("     **This line does not go through the path test.** It")
        print("     measures the grid's effect on P directly, so it is")
        print("     evidence independent of the qualifying rate.")
    print(f"     {'':<10}{'loops':>9}{'ideal':>9}{'rate':>8}{'ratio_max':>11}"
          f"{'over 1':>8}")
    for tag, d in (("P_orig", pl["b8like"]), ("P_sub", pl["p_sub"]["b8like"])):
        mx = d["ratio_max_derived"]
        rt = d["rate_derived"]
        print(f"     {tag:<10}{d['n']:>9,}{d['ideal_derived']:>9,}"
              f"{('%.4f' % rt) if rt is not None else 'n/a':>8}"
              f"{('%.4f' % mx) if mx is not None else 'undef':>11}"
              f"{d['over_one_derived']:>8,}")
    print("     (b8like, derived. Fannie's rate is 0.5354 to 0.6619.)")

    print("\n  H2. Read, per the criteria fixed before the run, one variable, three branches")
    ro = pl["b8like"]["rate_derived"]
    rsub = pl["p_sub"]["b8like"]["rate_derived"]
    lo, hi = 0.5354, 0.6619
    if ro is None or rsub is None:
        print("     §8·20·8 -> THIRD BRANCH by default: one of the two")
        print("     rates is")
        print("     undefined, so the comparison has no referent. **Not read**")
        print("     as evidence about P (its own lesson: an empty")
        print("     set must not win a comparison).")
    elif rsub >= lo:
        print(f"     §8·20·8 -> FIRST BRANCH. 甲. The rate rises"
              f" {ro:.4f} -> {rsub:.4f},")
        print(f"     into or above Fannie's own band [{lo}, {hi}]. The")
        print("     payment's provenance was the cause, and §8·19·1's input")
        print("     map is corrected to §12.2's substitution.")
    elif rsub - ro >= 0.10 * ro:
        print(f"     §8·20·8 -> SECOND BRANCH, mixed (R01). The rate rises"
              f" {ro:.4f} -> {rsub:.4f},")
        print(f"     which is more than a tenth, but it does not reach")
        print(f"     Fannie's band [{lo}, {hi}]. **甲 holds in part and")
        print("     something else is also there.** Recorded as measured; a")
        print("     rise is not an explanation.")
    else:
        print(f"     §8·20·8 -> THIRD BRANCH. 乙. The rate does not move"
              f" ({ro:.4f} -> {rsub:.4f},")
        print(f"     under a tenth of {ro:.4f}). The payment was not the")
        print("     cause: the paths are not ideal to begin with, **and that")
        print("     means §8·16's round trips and B8's clean cures are not")
        print("     the same kind of object** — a larger matter than P.")
    print("     The main verdict (§8·20·3, ratio_max) is computed on P_orig")
    print("     and **does not move with this**: its loops are the ones the")
    print("     path test selected, which is to say the ones whose P is right.")

    print("\n  G. What this section does NOT deliver (§8·20·5)")
    print("     B8-0b's measured noise floor, from never-delinquent windows:")
    print("       a population this station has not walked. Left to §8·21, so")
    print("       (i-b) is **not read here** — its comparand does not exist.")
    print("     The triangles' omega, with leg 2 at the modification month:")
    print("       §8·16's round trips carry no modification by definition, so")
    print("       there is no leg 2 in anything above. Left to §8·22.")
    print("     §8·12 re-asked on this carrier: needs both of the above.")
    print("     Three carrier facts still travel with every number here:")
    print("       bn == n identically; forgiven is 0 by absence, not by")
    print("       measurement; P is the origination payment carried as state.")


def cmd_omega(only) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    if not vs:
        print(f"  no archives under {RAW}")
        return 1
    sys.path.insert(0, str(ROOT / "experiments"))
    import b8_cmt_fetch as F                      # noqa: E402
    import b8_loop_omega as LO                    # noqa: E402
    import b8_omega as W                          # noqa: E402
    import b8_0a_gate as G                        # noqa: E402
    import b10_c8_1d_freddie as FR                # noqa: E402

    if W.MAX_H != CURVE_MAX_H:
        print(f"  b8_omega.MAX_H is {W.MAX_H} and this file says "
              f"{CURVE_MAX_H}. Fix one; nothing is read until then.")
        return 1
    if not print_crosscheck(resid_crosscheck(W, G)):
        print("\n  §8·19·3 did not pass. Nothing was read. Fix it first.")
        return 1
    print()

    #: **Read before the new one is written** (規矩 19).
    prior = prior_json(ROOT, partial_name("b10_omega", only))

    src, files = F.load_treasury()
    if not src:
        print("  no Treasury curve under data/raw/cmt.")
        return 1
    pos, tab = LO.curve_table_from(src, LO.RULE)

    print("§8·20: the loop sum. **B8's k, not §8·16's** (§8·20·6).\n"
          f"  r_month and loop_residual_ideal from {W.__name__}, "
          f"path tolerance from {G.__name__}\n")
    acc = omega_new_acc()
    for v in vs:
        orig, _ = FR.read_orig(v)
        with zipfile.ZipFile(archive(v)) as zf:
            with zf.open(f"sample_perf_{v}.txt") as raw:
                seq, batch = None, []
                for line in io.TextIOWrapper(raw, encoding="utf-8",
                                             newline=""):
                    if not line.strip():
                        continue
                    f = line.split("|")
                    if f[0] != seq:
                        if seq is not None:
                            omega_absorb(acc, batch, orig.get(seq), v, pos,
                                         tab, CURVE_MAX_H, W, G,
                                         FR.contract_payment)
                        seq, batch = f[0], []
                    batch.append(floor_row(f))
                if seq is not None:
                    omega_absorb(acc, batch, orig.get(seq), v, pos, tab,
                                 CURVE_MAX_H, W, G, FR.contract_payment)
        print(f"  {v}  done   loops so far {acc['as16']['n']:,}", flush=True)
    pl = omega_payload(acc)
    print_vs_prior(prior, pl, partial_name("b10_omega", only))
    print_omega(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / partial_name("b10_omega", only)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "omega", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. The clean-cure loop "
             "sum on the second carrier, against b8_omega.loop_residual_ideal "
             "within b8_0a_gate's own bound. No never-delinquent floor and no "
             "triangle loop: those are §8·21 and §8·22.",
         "k_convention": "b8_0a_gate.find_clean_cures, missed months, "
                         "len(span) - 2 (§8·20·6)",
         "bn_equals_n": True, "forgiven_is_zero_by_absence": True,
         "payment_source": "origination contract payment carried as state",
         "fannie_beside": [list(r) for r in B8_0A_DERIVED],
         "sample_cap": OMEGA_SAMPLE_CAP, **pl}, indent=2, sort_keys=True)
        + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --noise. Registered before the code.
# B8-0b's floor: the same sum on never-delinquent loans, where `k = 0` and the
# closed form is zero by construction, so the sum IS the floor.
# ---------------------------------------------------------------------------

#: `b8_0a_gate.FLOOR_LENS`, transcribed. §8·21·4: the floor's `L` matches the
#: loop's `k + 1`, because the loop's residual runs over `k + 1` months and the
#: floor's over `L`. **The encoding is written down before it is used**, which
#: is the §8·20·6 lesson.
NOISE_LENS = (2, 3, 4, 7)

#: B8 caps its floor loop and **logs the cap**, because a silent truncation
#: reads as full coverage when it is not.
#:
#: **Per vintage, not global.** B8 iterates six archives and caps each at
#: 30,000. This file walks twenty-seven in one accumulator, so a global cap
#: would fill up on the earliest vintages and read as a floor measured on
#: 1999-2005 — a selection on vintage, silently. 5,000 per vintage gives
#: 27 x 5,000 = 135,000 per cell, the same order as B8's 6 x 30,000.
NOISE_CAP = 5_000

#: The permutation null for §8·21·5's AUC, and its seed. **`zlib.crc32`-free
#: here because the seed is a literal**, but the same discipline as §8·12: a
#: statistic without its own null is a number nobody can place.
NOISE_N_PERM = 999
NOISE_PERM_SEED = 20260820

#: §8·21·8. `r_month` prices both sides with the same note, horizon and curve,
#: so `V`'s factor cancels and what comes back is `log bal - log b_hat`, which
#: is B8's floor sum. **This constant is arbitrary and the selftest proves the
#: answer does not depend on it.** A residual formula is still not written here.
NOISE_DISC = 4.0
NOISE_N = 240.0

#: The three whole-loan screens, named after the `noise_floor` lines they
#: mirror. Field 63 has no Freddie counterpart (§8·14·5).
NOISE_SCREENS = ("ever delinquent", "ever carried a modification flag",
                 "ever carried a positive column 12")

#: Why a candidate window was not summed, in `noise_floor`'s own names.
NOISE_SKIPS = ("no anchor with the window's length after it",
               "period gap in the window", "a row in the window is unusable",
               "no usable rate at the anchor",
               "no usable payment at the anchor",
               "the path leaves b_hat or the balance non-positive")

NOISE_EXAMPLE_CAP = 5
NOISE_SAMPLE_CAP = 200_000


def noise_screens(rows):
    """The three whole-loan screens as independent booleans (§8·21·1).

    Independent, not first-match: §8·19·8's lesson is that a first-match
    partition's later members read zero for the ordering, so both are counted.
    """
    ever_del = any(is_del_digits(t[R_DELINQ]) for t in rows)
    ever_mod = any(t[R_MODFLAG] in MODFLAG_MOD for t in rows)
    ever_zib = any(t[R_DEFER] is not None and t[R_DEFER] > 0 for t in rows)
    return (ever_del, ever_mod, ever_zib)


def noise_anchor(rows, min_age):
    """The first usable row, optionally the first at or past `min_age`.

    `noise_floor`'s own words: the anchor depends only on which fields are
    present, **never on an outcome**, so it introduces no selection on the
    quantity being measured. `min_age` is not an outcome either: §8·16 measured
    that Freddie reports UPB on a $1,000 grid below age 7 and to the cent at
    and above it, so the age floor selects a **reporting precision**, not a
    behaviour. Returns None when the loan has no such row.
    """
    for j, t in enumerate(rows):
        if (t[R_UPB] is not None and t[R_UPB] > 0 and t[R_RATE] is not None
                and t[R_DEFER] is not None and t[R_AGE] is not None
                and (min_age is None or t[R_AGE] >= min_age)):
            return j
    return None


def noise_window(rows, a, L, P, W):
    """One window of length `L` from anchor `a`. `(skip, value)`.

    `skip` is a `NOISE_SKIPS` entry or None. The sum goes through
    `b8_omega.r_month` with the arguments arranged so `V`'s factor cancels
    (§8·21·8): **B10 writes no residual formula, here or anywhere.**
    """
    b = a + L
    if b >= len(rows):
        return NOISE_SKIPS[0], None
    pa, pb = month_index_of(rows[a][R_PERIOD]), month_index_of(rows[b][R_PERIOD])
    if pa < 0 or pb < 0 or pb - pa != L:
        return NOISE_SKIPS[1], None
    for t in rows[a:b + 1]:
        if (t[R_UPB] is None or t[R_UPB] <= 0 or t[R_RATE] is None
                or t[R_DEFER] is None):
            return NOISE_SKIPS[2], None
    note = rows[a][R_RATE]
    if not (note > 0):
        return NOISE_SKIPS[3], None
    if P is None or not (P > 0):
        return NOISE_SKIPS[4], None
    ib = [t[R_UPB] - t[R_DEFER] for t in rows[a:b + 1]]
    total = 0.0
    for j in range(1, len(ib)):
        #: The gate needs `b_hat` explicitly. **It is a gate, the value is
        #: thrown away**, the same handling §8·20 gives its own gate 7.
        bh = float(W.carry_forward(ib[j - 1], note, P))
        if not (bh > 0) or not (ib[j] > 0):
            return NOISE_SKIPS[5], {"t": a + j, "bal_prev": ib[j - 1],
                                    "bal_now": ib[j], "b_hat": bh,
                                    "P": P, "note": note}
        total += float(W.r_month(
            ib[j], ib[j - 1], note, P, NOISE_N, NOISE_DISC,
            zib_now=0.0, zib_prev=0.0, balloon_n=NOISE_N,
            note_prev=note, n_prev=NOISE_N, balloon_n_prev=NOISE_N))
    return None, total


def noise_new_acc() -> dict:
    def cell():
        return {"kept": 0, "kept_v": {}, "vals": [], "capped": False,
                "skips": {g: 0 for g in NOISE_SKIPS}, "examples": []}
    def anch():
        return {L: cell() for L in NOISE_LENS}
    return {"loans": 0, "clean_loans": 0,
            "screen_first": {g: 0 for g in NOISE_SCREENS},
            "screen_any": {g: 0 for g in NOISE_SCREENS},
            "no_anchor": {"cent": 0, "grid": 0},
            "no_P": {"orig": 0, "sub": 0},
            "cells": {(anchor, pname): anch()
                      for anchor in ("cent", "grid")
                      for pname in ("orig", "sub")}}


def noise_absorb(acc, rows, orig, vintage, W, contract_payment) -> None:
    """One loan. Four (anchor, payment) combinations, four window lengths."""
    acc["loans"] += 1
    flags = noise_screens(rows)
    for f, g in zip(flags, NOISE_SCREENS):
        if f:
            acc["screen_any"][g] += 1
    if any(flags):
        acc["screen_first"][NOISE_SCREENS[flags.index(True)]] += 1
        return
    acc["clean_loans"] += 1

    P_orig = None
    if orig is not None:
        u0, rate0, term = orig
        cand = contract_payment(u0, rate0 / 1200.0, term)
        if cand == cand and cand > 0:
            P_orig = cand
    if P_orig is None:
        acc["no_P"]["orig"] += 1

    for aname, min_age in (("cent", FLOOR_MIN_AGE), ("grid", None)):
        a = noise_anchor(rows, min_age)
        if a is None:
            acc["no_anchor"][aname] += 1
            continue
        #: §12.2's substitution is anchored where the window is, so the two
        #: payments are read at the same row the sum starts from.
        P_sub = substitution_payment(rows[a], contract_payment)
        if P_sub is None and aname == "cent":
            acc["no_P"]["sub"] += 1
        for pname, P in (("orig", P_orig), ("sub", P_sub)):
            for L in NOISE_LENS:
                c = acc["cells"][(aname, pname)][L]
                if c["kept_v"].get(vintage, 0) >= NOISE_CAP:
                    c["capped"] = True
                    continue
                skip, val = noise_window(rows, a, L, P, W)
                if skip is not None:
                    c["skips"][skip] += 1
                    #: **Print the values, do not guess at them.** B8's own
                    #: floor table came back empty on all six archives and
                    #: reading the code did not settle why.
                    if (isinstance(val, dict)
                            and len(c["examples"]) < NOISE_EXAMPLE_CAP):
                        c["examples"].append(val)
                    continue
                c["kept"] += 1
                c["kept_v"][vintage] = c["kept_v"].get(vintage, 0) + 1
                if len(c["vals"]) < NOISE_SAMPLE_CAP:
                    c["vals"].append(val)


def _ranks(xs):
    """Mid-ranks of `xs`, ties averaged. One copy, used by the AUC only."""
    order = sorted(range(len(xs)), key=lambda j: xs[j])
    out = [0.0] * len(xs)
    j = 0
    while j < len(order):
        k = j
        while k + 1 < len(order) and xs[order[k + 1]] == xs[order[j]]:
            k += 1
        mid = (j + k) / 2.0 + 1.0
        for m in range(j, k + 1):
            out[order[m]] = mid
        j = k + 1
    return out


def noise_auc(a_vals, b_vals, n_perm=NOISE_N_PERM, seed=NOISE_PERM_SEED):
    """``P(a > b)`` with ties at a half, against a label-permutation null.

    The Mann-Whitney statistic, written through mid-ranks so it is O(N log N)
    rather than O(n*m). **The null is the one §8·12 built**: the labels are
    shuffled and the statistic recomputed, because a number with no null is a
    number nobody can place. Under the null the expectation is 0.5, and that
    is a **structural** referent rather than a line drawn on an estimator
    (纪律 11).

    Returns None when either side is empty: an empty set must not win a
    comparison (§8·17·2's lesson).
    """
    n1, n2 = len(a_vals), len(b_vals)
    if n1 == 0 or n2 == 0:
        return None
    pooled = list(a_vals) + list(b_vals)
    rk = _ranks(pooled)
    obs = (sum(rk[:n1]) - n1 * (n1 + 1) / 2.0) / (n1 * n2)
    rng = random.Random(seed)
    idx = list(range(n1 + n2))
    null = []
    for _ in range(n_perm):
        pick = rng.sample(idx, n1)
        null.append((sum(rk[j] for j in pick) - n1 * (n1 + 1) / 2.0)
                    / (n1 * n2))
    null.sort()
    #: Two-sided placement, counted rather than assumed normal.
    above = sum(1 for v in null if v >= obs)
    below = sum(1 for v in null if v <= obs)
    return {"auc": obs, "n_a": n1, "n_b": n2,
            "null_p05": null[int(0.05 * (n_perm - 1))],
            "null_p50": null[int(0.50 * (n_perm - 1))],
            "null_p95": null[int(0.95 * (n_perm - 1))],
            "null_min": null[0], "null_max": null[-1],
            "frac_null_ge": above / n_perm, "frac_null_le": below / n_perm,
            "outside": bool(obs > null[-1] or obs < null[0]),
            "n_perm": n_perm, "seed": seed}


#: `results/b8_0a_gate.md` section 3, transcribed 2026-08-20. Per window
#: length, the min and max across the six archives of the floor's median
#: absolute value. **Printed beside, never subtracted** (§7·9).
B8_0B_FLOOR_ABSMED = {2: (2.109e-08, 3.923e-08), 3: (2.862e-08, 6.099e-08),
                      4: (3.776e-08, 1.022e-07), 7: (9.360e-08, 7.386e-06)}

#: The same file's (i-b) loop side: `stream - closed` on every clean-cure
#: loop, median absolute, min and max across the six archives.
B8_0A_IB_ABSMED = (1.213e-07, 7.722e-06)


def coh_compound(c, n_all) -> dict:
    """§8·33. The ideal pattern's share against what per-month independence gives.

    **Nothing is fitted.** `p` is the share of delinquent months that read
    positive and `q` the share of loops whose cure month reads negative; both
    are counts over the same loops the observed share is taken on. The
    prediction is `p**(L-1) * q`, which is what those two rates give if the
    months miss independently.

    **The two-month window is not a special case, and the first version said
    it was.** With `L-1 = 1` the prediction is `p*q` — the product of two
    *marginals* — while the observed share is the *joint*. Those are equal
    only under independence, which is exactly what is being tested; the cure
    month is a second event, not the same one. The archives said so at once
    (`obs/pred = 1.0239` at window 2, not 1.0000), and the fixture had missed
    it because it was built with `q = 1`, where `p*q = p = observed` holds
    trivially. **A fixture that can only confirm is §11 item 3 wearing a
    fixture's clothes.** Every window votes.
    """
    dm, pm = c.get("delinq_months", 0), c.get("pos_months", 0)
    L = c.get("n_months", 0)
    if not n_all or not dm or not L:
        return {"npos_hist": {}, "p_month": None, "q_cure": None,
                "predicted": None, "obs_over_pred": None,
                "cmp_exact": None}
    p = pm / dm
    cn = c.get("cure_neg", 0)
    q = cn / n_all
    pred = (p ** (L - 1)) * q
    obs = c.get("ideal_pat", 0) / n_all
    #: **The comparison is exact integer arithmetic, not a float compare.**
    #:
    #: `obs >= pred` is `ideal_pat/n >= (pm/dm)**(L-1) * (cure_neg/n)`, and
    #: multiplying both sides by `n * dm**(L-1)` clears every denominator:
    #: `ideal_pat * dm**(L-1) >= pm**(L-1) * cure_neg`. All integers, exact,
    #: and Python's ints do not overflow.
    #:
    #: **Why it has to be exact.** The branch was first written on the float
    #: ratio and folded the tie into `>=` (§11 item 4). Naming the tie then
    #: made it unreachable: `0.8**3` is not `0.512` in binary, so a fixture
    #: built to sit exactly on it read `0.99999999999999989` and fell to the
    #: other side — a patch for item 4 that manufactured an item 3. **A
    #: tolerance would have been a typed line** (纪律 11); cross-multiplying
    #: is not.
    lhs = c.get("ideal_pat", 0) * (dm ** (L - 1))
    rhs = (pm ** (L - 1)) * cn
    return {"npos_hist": {str(k): v for k, v in sorted(c["npos"].items())},
            "p_month": p, "q_cure": q, "predicted": pred,
            "obs_over_pred": (obs / pred) if pred > 0 else None,
            "cmp_exact": (0 if lhs == rhs else (1 if lhs > rhs else -1))}


def cls_payload(cls) -> dict:
    """§8·34·2. The class census, and the hazard comparison in exact integers.

    `hazard = redel / exposure` per class. The comparison is cross-multiplied
    — `redel(A) * exposure(B)` against `redel(B) * exposure(A)` — for the same
    reason §8·33's was: a tie is a branch of its own and floats cannot express
    one (§11 item 4, then item 3 in the patch for it).
    """
    if not cls:
        return {"classes": {}, "hazard_verdict": None}
    out = {}
    for k, d in sorted(cls.items()):
        out[k] = {
            "n": d["n"],
            "fico_bands": {str(b): n for b, n in sorted(d["fico"].items())},
            "fico_unreadable": d["fico_bad"],
            "dti_q": _q(d["dti"], (10, 50, 90)) if d["dti"] else None,
            "dti_unreadable": d["dti_bad"],
            "fthb": dict(sorted(d["fthb"].items())),
            "purpose": dict(sorted(d["purpose"].items())),
            "months_total": d["months"], "exposure": d["exposure"],
            "redelinquent": d["redel"], "ra": d["ra"], "zero_balance": d["zero"],
            "redel_share": (d["redel"] / d["n"]) if d["n"] else None,
            "hazard": (d["redel"] / d["exposure"]) if d["exposure"] else None,
            #: §8·34·3 item 1. The right-censoring fairness check: if the two
            #: classes are observed for very different lengths, the hazard is
            #: still exposure-normalised but the reading says so.
            "tail_months_p50": (_q(d["tail_months"], (50,))[0]
                                if d["tail_months"] else None),
            "by_year": {str(y): n for y, n in sorted(d["by_year"].items())},
            "by_window": dict(sorted(d["by_window"].items())),
            "froz_year": {str(y): v for y, v in sorted(d["froz_year"].items())},
            "froz_month": {str(m): v
                           for m, v in sorted(d["froz_month"].items())},
            "froz_unreadable": d["froz_unread"],
            "assist_asked": d["asg_n"], "assist_any": d["asg_any"],
            "assist_unknown_row": d["asg_unk"],
            "assist_codes": dict(sorted(d["asg_code"].items())),
            "assist_position": dict(sorted(d["asg_pos"].items())),
            "assist_year": {str(y): v
                            for y, v in sorted(d["asg_year"].items())},
        }
    a, b = out.get("++"), out.get("+-")
    verdict, cmp_i = None, None
    if a and b and a["exposure"] and b["exposure"]:
        lhs = cls["++"]["redel"] * cls["+-"]["exposure"]
        rhs = cls["+-"]["redel"] * cls["++"]["exposure"]
        cmp_i = 0 if lhs == rhs else (1 if lhs > rhs else -1)
        verdict = {1: "plus_plus_riskier", -1: "plus_plus_safer",
                   0: "identical"}[cmp_i]
    return {"classes": out, "hazard_verdict": verdict, "hazard_cmp": cmp_i,
            **crisis_read(cls)}


def crisis_read(cls) -> dict:
    """§8·35·2. The `++` share inside the declared windows against outside.

    Cross-multiplied to integers for the same reason §8·33 and §8·34 were: the
    third branch here says the class is **institutional rather than a crisis
    artefact**, and that branch is exactly the tie. A branch that cannot be
    reached is not a branch (§11 items 3 and 4).
    """
    pp, pm = cls.get("++"), cls.get("+-")
    if not pp or not pm:
        return {"crisis": {}, "crisis_verdict": None, "crisis_cmp": None}
    out, wins = {}, {}
    for w in set(list(pp["by_window"]) + list(pm["by_window"])):
        a = pp["by_window"].get(w, 0)
        b = pm["by_window"].get(w, 0)
        wins[w] = {"pp": a, "pm": b, "total": a + b,
                   "pp_share": (a / (a + b)) if (a + b) else None}
    #: The main reading pools the two windows: §8·35·2 says the question is
    #: "was the servicer busy", not "which of the two crises". The separate
    #: windows are delivered beside it.
    crisis_pp = sum(v["pp"] for w, v in wins.items() if w != "calm")
    crisis_tot = sum(v["total"] for w, v in wins.items() if w != "calm")
    calm_pp = wins.get("calm", {}).get("pp", 0)
    calm_tot = wins.get("calm", {}).get("total", 0)
    cmp_i = verdict = None
    if crisis_tot and calm_tot:
        lhs, rhs = crisis_pp * calm_tot, calm_pp * crisis_tot
        cmp_i = 0 if lhs == rhs else (1 if lhs > rhs else -1)
        verdict = {1: "crisis_higher", -1: "crisis_lower",
                   0: "institutional"}[cmp_i]
    out = {"windows": wins,
           "crisis_pp": crisis_pp, "crisis_total": crisis_tot,
           "calm_pp": calm_pp, "calm_total": calm_tot,
           "crisis_share": (crisis_pp / crisis_tot) if crisis_tot else None,
           "calm_share": (calm_pp / calm_tot) if calm_tot else None,
           "declared": [list(w) for w in CRISIS_WINDOWS]}
    #: §8·35·3 item 1: every cure year prints, none filtered (C0b).
    #: **String keys, the same as `classes[k]["by_year"]`.** `crisis_read`
    #: takes the raw accumulator, whose year keys are ints, while the class
    #: payload stringifies them; leaving both alive would hand a reader two
    #: key types for one set of years, and json.dumps would then quietly make
    #: them agree on disk while they disagreed in memory.
    years = {}
    for y in sorted(set(list(pp["by_year"]) + list(pm["by_year"])),
                    key=int):
        a, b = pp["by_year"].get(y, 0), pm["by_year"].get(y, 0)
        years[str(y)] = {"pp": a, "pm": b, "total": a + b,
                         "pp_share": (a / (a + b)) if (a + b) else None,
                         "window": crisis_of(int(y))}
    out["years"] = years
    return {"crisis": out, "crisis_verdict": verdict, "crisis_cmp": cmp_i,
            **frozen_read(cls), **r2_read(cls), **assist_read(cls)}


#: §8·36·3. The year the sign classes collapse. Named here rather than
#: rediscovered in the branch: it comes from the four-class year table already
#: on disk, where `--` and `-+` are **exactly** zero from this year on.
FROZEN_BREAK_YEAR = 2020


def frozen_read(cls) -> dict:
    """§8·36. The frozen share by cure year, pooled across the sign classes.

    Pooled because a loop's class is downstream of the very thing being
    measured: `--` and `-+` **cannot exist** once every delinquent month is
    frozen, so counting the frozen share inside a class would condition on the
    outcome. The population is every window-2 loop in that cure year.
    """
    years, months, unread = {}, {}, 0
    for d in cls.values():
        for y, v in d.get("froz_year", {}).items():
            c = years.setdefault(int(y), [0, 0, 0])
            for i in range(3):
                c[i] += v[i]
        for m, v in d.get("froz_month", {}).items():
            c = months.setdefault(int(m), [0, 0, 0])
            for i in range(3):
                c[i] += v[i]
        unread += d.get("froz_unread", 0)
    if not years and not unread:
        return {"frozen": {}, "frozen_verdict": None}
    #: **Counts, never a float share against 1.0** (§11: a tie has to be
    #: expressible). "Every loop frozen" is `frozen == loops`.
    post = [(y, v) for y, v in years.items() if y >= FROZEN_BREAK_YEAR]
    pre = [(y, v) for y, v in years.items() if y < FROZEN_BREAK_YEAR]
    post_all = bool(post) and all(v[1] == v[0] for _y, v in post)
    pre_all = bool(pre) and all(v[1] == v[0] for _y, v in pre)
    if not post:
        verdict = "no_reading"
    elif not post_all:
        verdict = "frozen_not_total"
    elif pre_all:
        verdict = "frozen_always_total"
    else:
        verdict = "convention_changed"
    #: §8·36·1's structural cross-check: frozen implies `r1 > 0`, so a
    #: negative `r1` can only come from an unfrozen month. **A theorem, so it
    #: is printed as a check and never read as a finding.**
    bad = [y for y, v in years.items() if v[2] > (v[0] - v[1])]
    return {"frozen": {
        "years": {str(y): {"loops": v[0], "frozen": v[1], "r1_neg": v[2],
                           "frozen_share": (v[1] / v[0]) if v[0] else None,
                           "all_frozen": v[1] == v[0]}
                  for y, v in sorted(years.items())},
        "months_2019": {str(m): {"loops": v[0], "frozen": v[1],
                                 "r1_neg": v[2],
                                 "frozen_share": (v[1] / v[0]) if v[0] else None}
                        for m, v in sorted(months.items())
                        if 201901 <= m <= 201912},
        "break_year": FROZEN_BREAK_YEAR,
        "post_all_frozen": post_all, "pre_all_frozen": pre_all,
        #: Fixed before the run: loops the question was put to and could not be
        #: answered on. **单列**, never folded into "not frozen".
        "unreadable": unread,
        "theorem_violations": sorted(bad)},
        "frozen_verdict": verdict}


def _seg_sum(d, lo, hi, i):
    return sum(v[i] for y, v in d.get("froz_year", {}).items()
               if lo <= int(y) <= hi)


def r2_read(cls) -> dict:
    """§8·37. `++ | frozen`, which **is** r2's margin.

    §8·36·1 proved frozen implies `r1 > 0`, so a frozen loop's class can only
    be `++` or `+-` and the only thing separating them is the sign of the cure
    month. Conditioning on frozen therefore takes the reporting change out by
    construction: this is a conditional count, not a control variable.
    """
    pp, pm = cls.get("++"), cls.get("+-")
    if not pp or not pm:
        return {"r2": {}, "r2_verdict": None}
    #: §8·37·2's hard check. A frozen `-+` or `--` contradicts §8·36·1, which
    #: is a theorem, so it is an instrument error and never a finding.
    theorem = {k: sum(v[1] for v in (cls.get(k) or {}).get("froz_year",
                                                           {}).values())
               for k in ("-+", "--")}
    years = {}
    for k, d in (("++", pp), ("+-", pm)):
        for y, v in d.get("froz_year", {}).items():
            c = years.setdefault(int(y), {"++": [0, 0], "+-": [0, 0]})
            c[k][0] += v[0]
            c[k][1] += v[1]
    months = {}
    for k, d in (("++", pp), ("+-", pm)):
        for m, v in d.get("froz_month", {}).items():
            if not 201901 <= int(m) <= 201912:
                continue
            c = months.setdefault(int(m), {"++": [0, 0], "+-": [0, 0]})
            c[k][0] += v[0]
            c[k][1] += v[1]

    pre = tuple(_seg_sum(d, 0, FROZEN_BREAK_YEAR - 2, 1) for d in (pp, pm))
    post = tuple(_seg_sum(d, FROZEN_BREAK_YEAR, 9999, 1) for d in (pp, pm))
    #: The straddling year is in neither segment and prints on its own
    #: (§8·36·3 put the break inside it).
    mid = tuple(_seg_sum(d, FROZEN_BREAK_YEAR - 1, FROZEN_BREAK_YEAR - 1, 1)
                for d in (pp, pm))
    a, b = sum(pre), sum(post)
    cmp_i = verdict = None
    if a and b:
        lhs, rhs = post[0] * a, pre[0] * b
        cmp_i = 0 if lhs == rhs else (1 if lhs > rhs else -1)
        verdict = {-1: "r2_moved_too", 1: "r2_moved_up",
                   0: "composition_only"}[cmp_i]

    def _tab(box):
        out = {}
        for key, c in sorted(box.items()):
            fz = c["++"][1] + c["+-"][1]
            uf = ((c["++"][0] - c["++"][1]) + (c["+-"][0] - c["+-"][1]))
            out[str(key)] = {
                "frozen_pp": c["++"][1], "frozen_total": fz,
                "frozen_pp_share": (c["++"][1] / fz) if fz else None,
                "unfrozen_pp": c["++"][0] - c["++"][1],
                "unfrozen_total": uf,
                "unfrozen_pp_share": ((c["++"][0] - c["++"][1]) / uf)
                                     if uf else None}
        return out

    return {"r2": {
        "years": _tab(years), "months_2019": _tab(months),
        "pre": {"pp": pre[0], "total": a,
                "share": (pre[0] / a) if a else None},
        "post": {"pp": post[0], "total": b,
                 "share": (post[0] / b) if b else None},
        "straddle_year": {"year": FROZEN_BREAK_YEAR - 1, "pp": mid[0],
                          "total": sum(mid)},
        "theorem_frozen_in_neg_classes": theorem},
        "r2_verdict": verdict, "r2_cmp": cmp_i}


def assist_read(cls) -> dict:
    """§8·38. Is `++` enriched in loans the servicer flagged as assisted.

    Cross-multiplied to integers because the third branch — **the code does
    not separate the two classes** — is exactly the tie, and a branch that
    cannot be expressed is not a branch (§11 item 4).
    """
    pp, pm = cls.get("++"), cls.get("+-")
    if not pp or not pm:
        return {"assist": {}, "assist_verdict": None}
    out = {}
    for k, d in (("++", pp), ("+-", pm)):
        out[k] = {"asked": d["asg_n"], "assisted": d["asg_any"],
                  "unknown_row": d["asg_unk"],
                  "share": (d["asg_any"] / d["asg_n"]) if d["asg_n"] else None,
                  "codes": dict(sorted(d["asg_code"].items())),
                  "position": dict(sorted(d["asg_pos"].items())),
                  "by_year": {str(y): v
                              for y, v in sorted(d["asg_year"].items())}}
    na, nb = pp["asg_n"], pm["asg_n"]
    ha, hb = pp["asg_any"], pm["asg_any"]
    cmp_i = verdict = None
    if not na or not nb:
        verdict = "not_asked"
    elif ha == 0 and hb == 0:
        verdict = "no_assisted_loops"
    else:
        lhs, rhs = ha * nb, hb * na
        cmp_i = 0 if lhs == rhs else (1 if lhs > rhs else -1)
        verdict = {1: "pp_more_assisted", -1: "pp_less_assisted",
                   0: "code_does_not_separate"}[cmp_i]
    return {"assist": out, "assist_verdict": verdict, "assist_cmp": cmp_i}


def coh_signs(c) -> dict:
    """§8·31. The sign alphabet, and same-sign against B8's path verdict.

    The 2x2 is read by `overlap_read` — the **third** caller, which is what
    made extracting it from `pgrid_payload` worth doing rather than a guess
    that it would be. Same three structural branches, same two margin-derived
    lift anchors, same reachability count (§11 item 20).
    """
    t = c.get("sgn2x2", {})
    n = sum(t.values())
    n_S = t.get("Sq", 0) + t.get("Sn", 0)
    n_q = t.get("Sq", 0) + t.get("sq", 0)
    r = overlap_read(n, n_S, n_q, t.get("Sq", 0),
                     "same-sign inside path-qualifying",
                     "path-qualifying inside same-sign",
                     "the two sets are identical")
    pats = {}
    for k, v in sorted(c.get("pat", {}).items()):
        pats[k] = {"n": v["n"], "qualifying": v["q"],
                   "qualify_rate": (v["q"] / v["n"]) if v["n"] else None,
                   "meanabs_p50": _q(v["ma"], (50,))[0] if v["ma"] else None,
                   "absomega_p50": _q(v["om"], (50,))[0] if v["om"] else None}
    #: §8·32·2. The same three structural branches on a different pair of
    #: edges, and §8·32·0 recorded the §11 item 15 check that clears it to be
    #: a criterion rather than a structural cross-check: A is about the
    #: window's motion, B about the anchor row's level, and neither implies
    #: the other.
    q2 = c.get("pat2x2", {})
    n2 = sum(q2.values())
    n_P = q2.get("PO", 0) + q2.get("Po", 0)
    n_O = q2.get("PO", 0) + q2.get("pO", 0)
    r2 = overlap_read(n2, n_P, n_O, q2.get("PO", 0),
                      "off-pattern inside over-bound",
                      "over-bound inside off-pattern",
                      "the two sets are identical")
    n_all = len(c.get("allsame", []))
    return {"sign_cell": dict(t), "sign_n": n, "n_same_sign": n_S,
            "ideal_pat": c.get("ideal_pat", 0),
            "ideal_pat_share": (c.get("ideal_pat", 0) / n_all)
            if n_all else None,
            "ideal_and_derived": c.get("ideal_and_derived", 0),
            "derived_off_pattern": c.get("derived_off_pattern", 0),
            "ob_unknown": c.get("ob_unknown", 0),
            **coh_compound(c, n_all),
            "pat_cell": dict(q2), "pat_n": n2,
            "n_off_pattern": n_P, "n_over_bound": n_O,
            "pat_overlap": {k: r2[k] for k in
                            ("a", "p_x", "p_y", "lift",
                             "lift_if_independent", "lift_if_contained",
                             "lift_nearer", "overlap_verdict",
                             "contained_direction", "a_floor", "a_ceiling",
                             "disjoint_reachable", "contained_reachable",
                             "branches_reachable")},
            "n_qualifying": n_q,
            "same_sign_share": (n_S / n) if n else None,
            "sign_patterns": pats,
            **cls_payload(c.get("cls", {})),
            "C_exact_values": dict(c.get("cvals", {})),
            "sign_overlap": {k: r[k] for k in
                             ("a", "p_x", "p_y", "lift",
                              "lift_if_independent", "lift_if_contained",
                              "lift_nearer", "overlap_verdict",
                              "contained_direction", "a_floor", "a_ceiling",
                              "disjoint_reachable", "contained_reachable",
                              "branches_reachable")}}


def coh_joint(c) -> list:
    """§8·30·1 item 2. `mean|r|` and `|omega|` inside tertiles of `C`.

    **This is the front view of the thing §8·29 could only see edge-on.**
    `|omega| = C * L * mean|r|` holds loop by loop and fails between medians;
    the reason is that `C` and `mean|r|` are not independent across loops, and
    a table of one inside bins of the other is where that shows.

    Tertiles rather than a grid, because the thinnest window carries 1,603
    loops and a 3x3 would put a hundred-odd in a cell (§3·4).
    """
    cs = c["C"]
    n = len(cs)
    if n < 3:
        return []
    cuts = _q(cs, (33, 67))
    bins = [[], [], []]
    for i, x in enumerate(cs):
        j = 0 if x <= cuts[0] else (1 if x <= cuts[1] else 2)
        bins[j].append(i)
    out = []
    for j, idx in enumerate(bins):
        if not idx:
            out.append({"bin": j, "n": 0, "cuts": cuts})
            continue
        vals = [cs[i] for i in idx]
        out.append({
            "bin": j, "n": len(idx), "cuts": cuts,
            #: **The bin's own range, not just its ordinal.** `C` is heavily
            #: tied on short windows — two months either agree or nearly
            #: cancel — so both tertile cuts can land on real values and the
            #: `<=` on each side puts the TOP mode into the middle bin. The
            #: ordinal then lies: "mid" holds the high mode and "high" is
            #: empty. Printing the range makes the label unnecessary.
            "C_lo": min(vals), "C_hi": max(vals),
            "C_p50": _q(vals, (50,))[0],
            "meanabs_p50": _q([c["meanabs"][i] for i in idx], (50,))[0],
            "absomega_p50": _q([c["absom"][i] for i in idx], (50,))[0],
        })
    return out


def coh_payload(coh, sizes_all) -> dict:
    """§8·29. `|omega| = C * L * mean|r|`, each factor's median, per window.

    **Nothing is fitted.** The two anchors for `C` are computed from the number
    of months: fully aligned residuals give `C = 1`, and residuals whose signs
    are independent land near `L**-0.5`. The boundary between them is their
    geometric mean `L**-0.25`, which is where §8·26·1's lift comparison puts
    its boundary too — derived from the margins, never typed.
    """
    rows, factors = {}, ("C", "meanabs", "absom", "same_sign")
    for L in NOISE_LENS:
        c = coh.get(L - 1)
        if not c or not c["C"]:
            rows[str(L)] = {"n": 0, "k": L - 1, "months": L,
                            "theorem_break_n": 0, "theorem_break": [],
                            "theorem_break_cap": THM_BREAK_CAP,
                            "vin_all": {}, "vin_month": {},
                            "vin_window": [VIN_MONTH_LO, VIN_MONTH_HI]}
            continue
        med = {f: _q(c[f], (50,))[0] for f in factors}
        thm_n, thm_rows = c.get("thm_n", 0), c.get("thm_break", [])
        anchor_ind = float(L) ** -0.5
        #: §8·30·1 items 1 and 3. The quantiles the median hid, and a **count**
        #: against the anchor rather than a comparison of medians against it:
        #: §8·29·2 saw every window's median C sitting under `L**-0.5`, and a
        #: median under an anchor is not the same statement as most loops
        #: under it.
        quart = {f: _q(c[f], (10, 50, 90, 99)) for f in factors}
        below = sum(1 for x in c["C"] if x < anchor_ind)
        rows[str(L)] = {
            "n": len(c["C"]), "k": L - 1, "months": L,
            "C_p50": med["C"], "meanabs_p50": med["meanabs"],
            "absomega_p50": med["absom"], "same_sign_p50": med["same_sign"],
            "C_if_aligned": 1.0, "C_if_independent": anchor_ind,
            "C_boundary": float(L) ** -0.25,
            "C_nearer": ("aligned" if med["C"] > float(L) ** -0.25
                         else ("independent" if med["C"] < float(L) ** -0.25
                               else "equidistant")),
            #: §8·29·2's last line. The median of a product is not the product
            #: of the medians, and the gap between them is printed rather than
            #: left for a reader to assume away.
            "product_of_medians": med["C"] * L * med["meanabs"],
            "floor_p50": sizes_all.get(str(L), {}).get("floor_absmed"),
            "q": {f: quart[f] for f in factors},
            "C_below_independent": below,
            "C_below_independent_share": below / len(c["C"]),
            #: §8·30·2 item 2. On the thinnest window `p99` is a handful of
            #: points, and a quantile on a handful is those points. The rank
            #: prints so nobody reads it as a distributional statement.
            "p99_rank": max(0, int(round(0.99 * (len(c["C"]) - 1)))),
            "p90_rank": max(0, int(round(0.90 * (len(c["C"]) - 1)))),
            "joint": coh_joint(c),
            #: §8·37·2's dump. `theorem_break_n` is the count and
            #: `theorem_break` the capped sample; **a cap that does not print
            #: its own count reads as full coverage** (B8's words about
            #: `capped_at`).
            "theorem_break_n": thm_n,
            "theorem_break_cap": THM_BREAK_CAP,
            "theorem_break": thm_rows,
            "vin_all": dict(sorted(c.get("vin_all", {}).items())),
            "vin_month": dict(sorted(c.get("vin_month", {}).items())),
            "vin_window": [VIN_MONTH_LO, VIN_MONTH_HI],
            **coh_signs(c),
        }
    live = [rows[str(L)] for L in NOISE_LENS if rows[str(L)]["n"]]

    def series(key):
        vals = [r.get(key) for r in live]
        if len(vals) < 2 or any(v is None for v in vals):
            return None
        return vals

    def rises(vals):
        """Non-decreasing **and** stepping up at least once.

        **A constant series is not a rise, and the first version said it
        was.** `all(b >= a)` is true of a flat series, so `C` sitting at
        exactly 1.0 across every window read as "coherence rises" — the
        second branch — when the registered second branch is `C` 涨. Flat is
        a tie between rising and falling, and putting a tie on one side is
        §11 item 4, the same defect as a `+0.000` judged into `mixed`.
        """
        return (all(b >= a for a, b in zip(vals, vals[1:]))
                and any(b > a for a, b in zip(vals, vals[1:])))

    def falls(vals):
        return (all(b <= a for a, b in zip(vals, vals[1:]))
                and any(b < a for a, b in zip(vals, vals[1:])))

    cs = series("C_p50")
    arith = [r["months"] * r["meanabs_p50"] for r in live] if live else []
    fs = series("floor_p50")
    c_rise = rises(cs) if cs else None
    lm_rise = rises(arith) if len(arith) >= 2 else None
    if c_rise is None or lm_rise is None:
        verdict = "no_reading"
    elif lm_rise and not c_rise:
        verdict = "arithmetic_only"
    elif c_rise:
        verdict = "coherence_rises"
    else:
        verdict = "mixed"
    #: **`C_flat` was the wrong name and it fired on the wrong thing.** It
    #: read `not rises and not falls`, which is true of a constant series AND
    #: of any non-monotone one; the archives gave 0.3319, 0.3288, 0.2155,
    #: 0.3128 — not flat, just not monotone — and the field said `flat`. Two
    #: shapes under one name is §11 item 6, and the fix is two names.
    c_const = (cs is not None and len(set(cs)) == 1)
    c_nonmono = (cs is not None and not c_rise and not falls(cs)
                 and not c_const)
    #: §8·29·1. **A structural criterion cannot carry a quantitative claim.**
    #: The first branch's registered prose says the rise is arithmetic; the
    #: criterion behind it only says which factor's median is monotone. On the
    #: archives the factor medians predict 2.57x and `|omega|`'s median moved
    #: 20.86x, so the prose was false while the branch was right. The check is
    #: computed here and printed beside the branch so the sentence can never
    #: stand on its own again.
    pred = obs = None
    if len(arith) >= 2 and arith[0]:
        pred = arith[-1] / arith[0]
    oms = series("absomega_p50")
    if oms and oms[0]:
        obs = oms[-1] / oms[0]
    #: §8·30·0. The growth factor of `|omega|` at each quantile, longest window
    #: over shortest, and the branch on whether that sequence drifts. **The
    #: mapping from §8·29·3's words to this shape was fixed before the run**:
    #: "much the same at every quantile" becomes "no systematic drift", which
    #: needs no tolerance, and a perfectly uniform shift lands in the first
    #: branch because four float ratios will not be monotone by accident.
    gq, gq_verdict = None, "no_reading"
    if len(live) >= 2:
        lo, hi = live[0], live[-1]
        ql, qh = lo.get("q", {}).get("absom"), hi.get("q", {}).get("absom")
        if ql and qh and all(x > 0 for x in ql):
            gq = [b / a for a, b in zip(ql, qh)]
            if rises(gq):
                gq_verdict = "tail_carries_it"
            elif falls(gq):
                gq_verdict = "bottom_carries_it"
            elif len(set(gq)) == 1:
                gq_verdict = "uniform_shift"
            elif gq.index(max(gq)) not in (0, len(gq) - 1):
                gq_verdict = "peaked_in_the_middle"
            elif gq.index(min(gq)) not in (0, len(gq) - 1):
                gq_verdict = "troughed_in_the_middle"
            else:
                gq_verdict = "irregular"
    #: §8·33·2. Direction only, per window, and the two-month window is left
    #: out of the vote because its prediction is an identity (§8·33·3 item 3):
    #: with one delinquent month `p**(L-1)*q` **is** the observed share, so a
    #: ratio of exactly 1 there is arithmetic and not agreement. Counting it
    #: as a vote would be §11 item 3 — a check that cannot fail.
    ratios = [(r["months"], r.get("obs_over_pred"))
              for r in live if r.get("obs_over_pred")]
    #: **The vote runs on `cmp_exact`, the integer comparison**, never on the
    #: float ratio printed beside it. Two defects were paid for here: the tie
    #: (observed exactly equal to predicted, which is the null itself) was
    #: first folded into `>=` (§11 item 4), and naming it in floats then made
    #: it unreachable (§11 item 3). Same windows, same filter, exact
    #: arithmetic.
    cmps = [r["cmp_exact"] for r in live
            if r.get("cmp_exact") is not None and r.get("obs_over_pred")]
    if len(cmps) < 2:
        comp_verdict = "no_reading"
    elif all(x == 0 for x in cmps):
        comp_verdict = "independent"
    elif all(x >= 0 for x in cmps):
        comp_verdict = "clustered"
    elif all(x <= 0 for x in cmps):
        comp_verdict = "anti_clustered"
    else:
        comp_verdict = "mixed"
    return {"rows": rows, "verdict": verdict, "C_rises": c_rise,
            "growth_by_quantile": gq, "growth_quantiles": (10, 50, 90, 99),
            "shift_verdict": gq_verdict,
            "compound_verdict": comp_verdict,
            "compound_ratios": {str(L): x for L, x in ratios},
            "C_nondecreasing": (all(b >= a for a, b in zip(cs, cs[1:]))
                                if cs else None),
            "C_constant": c_const, "C_non_monotone": c_nonmono,
            "L_meanabs_rises": lm_rise,
            "floor_falls": falls(fs) if fs else None,
            "L_meanabs": arith,
            "growth_predicted_by_factor_medians": pred,
            "growth_observed_absomega": obs,
            "prediction_over_observed": (pred / obs)
            if (pred and obs) else None,
            "windows_read": [L for L in NOISE_LENS if rows[str(L)]["n"]]}


def print_coh(pl) -> None:
    """§8·29's table and its one branch. Called from `print_noise`."""
    d = pl.get("coh")
    if not d:
        return
    print("\n  §8·29: why the ratio rises with the window. Three factors of")
    print("  |omega| = C * L * mean|r|, each measured, none fitted.")
    print(f"     {'win':<5}{'n':>8}{'C p50':>9}{'anchors ind/bnd':>18}"
          f"{'nearer':>13}{'mean|r| p50':>14}{'L*mean|r|':>12}"
          f"{'|om| p50':>12}{'floor p50':>12}{'same-sign':>11}")
    for L in NOISE_LENS:
        r = d["rows"][str(L)]
        if not r["n"]:
            print(f"     {L:<5}{0:>8}   empty")
            continue
        fl = r["floor_p50"]
        print(f"     {L:<5}{r['n']:>8,}{r['C_p50']:>9.4f}"
              f"{r['C_if_independent']:>9.4f}/{r['C_boundary']:<8.4f}"
              f"{r['C_nearer']:>13}{r['meanabs_p50']:>14.4e}"
              f"{r['months'] * r['meanabs_p50']:>12.4e}"
              f"{r['absomega_p50']:>12.4e}"
              f"{(f'{fl:.4e}' if fl is not None else '-'):>12}"
              f"{r['same_sign_p50']:>11.4f}")
    print("     (C = |sum r| / sum|r|, exact per loop. The two anchors come")
    print("      from the month count: 1 if the residuals all share a sign,")
    print("      L**-0.5 if their signs are independent. Neither is typed.)")
    for L in NOISE_LENS:
        r = d["rows"][str(L)]
        if r["n"]:
            print(f"     window {L}: product of medians "
                  f"{r['product_of_medians']:.4e} against median of the "
                  f"product {r['absomega_p50']:.4e}")
    print("     (a median of a product is not the product of the medians;")
    print("      the gap above is what that costs, printed not assumed away)")

    print(f"\n     C rises across windows: {d['C_rises']}"
          f"   (constant: {d['C_constant']},"
          f" non-monotone: {d['C_non_monotone']},"
          f" non-decreasing: {d['C_nondecreasing']})")
    print(f"     L*mean|r| rises: {d['L_meanabs_rises']}"
          f"    floor falls: {d['floor_falls']}")
    print("     (**flat is not a rise.** A constant series satisfies")
    print("      `all(b >= a)` and the first version read it as the second")
    print("      branch. §11 item 4: a tie does not get put on one side.)")
    #: §8·29·1's guard, printed **before** the branch so nobody reads the
    #: branch's prose without it.
    if d.get("growth_predicted_by_factor_medians") is not None:
        print(f"\n     factor medians predict |omega| p50 to grow "
              f"{d['growth_predicted_by_factor_medians']:.2f}x across the "
              f"windows read;")
        print(f"     it actually grew {d['growth_observed_absomega']:.2f}x."
              f"   prediction / observed = "
              f"{d['prediction_over_observed']:.3f}")
        print("     **A median of a product is not the product of the")
        print("     medians, so the factor table can be right about which")
        print("     factor is monotone and wrong about the size of the rise.**")
        print("     The branch below is about monotonicity only. Where these")
        print("     two numbers disagree, the branch's own prose does not")
        print("     carry the quantity (结果件 §8·29·1).")
    v = d["verdict"]
    print()
    if v == "no_reading":
        print("     §8·29·3 -> NO READING. Fewer than two windows carry a")
        print("     factor, so monotonicity is not a question yet.")
    elif v == "arithmetic_only":
        print("     §8·29·3 -> FIRST BRANCH. L*mean|r| rises and C does not.")
        print("     **This is a statement about monotonicity and nothing")
        print("     else.** Whether it also accounts for the SIZE of the rise")
        print("     is the two numbers printed above, not this branch.")
        print("     §8·21·9's four first branches still stand: they were")
        print("     measured, not inferred. What travels with them from here")
        print("     is that the short windows' margin over the floor is the")
        print("     smaller one, and the two growth numbers above say how much")
        print("     of that the factor medians do and do not account for.")
    elif v == "coherence_rises":
        print("     §8·29·3 -> SECOND BRANCH. C itself rises with the window:")
        print("     the monthly residuals line up more at long windows.")
        print("     **That is a real thing**, and omega on a long window is")
        print("     more of a signal than the count alone would give.")
    else:
        print("     §8·29·3 -> THIRD BRANCH, mixed (R01). Name which factor")
        print("     moved from the three booleans above; do not tell it as")
        print("     either of the other two.")
    print("     **§8·21's readings are not re-judged here**.")
    print_coh_shape(d)


def print_coh_shape(d) -> None:
    """§8·30. Where in the distribution the rise lives, and the C census."""
    print("\n  §8·30: the quantiles the medians hid.")
    print(f"     {'win':<5}{'n':>8}{'rank p90/p99':>14}"
          f"{'|om| p10':>12}{'p50':>12}{'p90':>12}{'p99':>12}"
          f"{'C p10':>9}{'C p50':>9}{'C p90':>9}{'C<anchor':>10}")
    for L in NOISE_LENS:
        r = d["rows"][str(L)]
        if not r["n"]:
            print(f"     {L:<5}{0:>8}   empty")
            continue
        qo, qc = r["q"]["absom"], r["q"]["C"]
        ranks = "{}/{}".format(r["p90_rank"], r["p99_rank"])
        print(f"     {L:<5}{r['n']:>8,}{ranks:>14}"
              f"{qo[0]:>12.3e}{qo[1]:>12.3e}{qo[2]:>12.3e}{qo[3]:>12.3e}"
              f"{qc[0]:>9.4f}{qc[1]:>9.4f}{qc[2]:>9.4f}"
              f"{r['C_below_independent_share']:>10.4f}")
    print("     (§8·30·2 item 2: the ranks say which point p90 and p99 ARE.")
    print("      On the thinnest window a quantile is a handful of loops.)")
    print("     (§8·30·1 item 3: `C<anchor` is a COUNT of loops under")
    print("      L**-0.5, not a comparison of medians against it. §8·29·2 saw")
    print("      every median under the anchor; this says how many loops are.)")

    print("\n     §8·30·1 item 2: mean|r| and |omega| inside tertiles of C")
    print(f"     {'win':<5}{'bin':<5}{'n':>9}{'C range':>21}{'C p50':>9}"
          f"{'mean|r| p50':>14}{'|om| p50':>13}")
    for L in NOISE_LENS:
        r = d["rows"][str(L)]
        for b in r.get("joint", []):
            if not b["n"]:
                print(f"     {L:<5}{b['bin']:<5}{0:>9}   (empty)")
                continue
            rng = "[{:.4f}, {:.4f}]".format(b["C_lo"], b["C_hi"])
            print(f"     {L:<5}{b['bin']:<5}{b['n']:>9,}{rng:>21}"
                  f"{b['C_p50']:>9.4f}{b['meanabs_p50']:>14.4e}"
                  f"{b['absomega_p50']:>13.4e}")
    print("     (bins are C tertiles, and the RANGE prints rather than a")
    print("      low/mid/high label: C ties heavily on short windows, both")
    print("      cuts can land on real values, and then the top mode sits in")
    print("      the middle bin while the top bin is empty. The label would")
    print("      lie; the range cannot.)")
    print("     (this is the front view of what §8·29 saw edge-on: the")
    print("      identity holds loop by loop and fails between medians")
    print("      because C and mean|r| are not independent across loops.)")
    g = d.get("growth_by_quantile")
    if g:
        print(f"\n     |omega| growth, longest window over shortest, by"
              f" quantile {d['growth_quantiles']}:")
        print("     " + "   ".join(f"p{q}: {x:.2f}x" for q, x
                                   in zip(d["growth_quantiles"], g)))
    print()
    v = d.get("shift_verdict")
    if v == "no_reading":
        print("     §8·30·0 -> NO READING. Fewer than two windows carry a")
        print("     quantile vector, so there is no growth sequence to read.")
    elif v in ("uniform_shift", "peaked_in_the_middle",
               "troughed_in_the_middle", "irregular"):
        print("     §8·30·0 -> FIRST BRANCH. The growth factor does not drift")
        print("     monotonically across the quantiles.")
        #: **The branch is defined by two negations and must not be named by
        #: an affirmation.** The first version called this whole state
        #: `whole_distribution_shifts`, and the archives handed it 10.30,
        #: 20.86, 6.08, 3.22 — peaked at the median, spread 6.49x — which is
        #: about as far from a uniform shift as a non-monotone sequence gets.
        #: Third time this family has bitten (`C_flat`, then the first
        #: branch's quantitative prose in §8·29·1). §11 item 14.
        if v == "uniform_shift":
            print("     Every quantile grew by the SAME factor: **the whole")
            print("     distribution moves**, rigidly.")
            print("     Written before the run: this")
            print("     does NOT establish `the population, not the window`.")
            print("     The four windows are four different sets of loans, and")
            print("     on this data a uniform shift and a change of")
            print("     population are the same picture.")
        elif v == "peaked_in_the_middle":
            print("     **But it is not uniform either: it PEAKS in the")
            print("     middle.** The largest growth is at an interior")
            print("     quantile, so the body of the distribution moved more")
            print("     than either end. That is a third shape, and the")
            print("     branch admits it without being named for it.")
        elif v == "troughed_in_the_middle":
            print("     **But it is not uniform either: it TROUGHS in the")
            print("     middle.** Both ends moved more than the body.")
        else:
            print("     **And it is not uniform either.** The sequence is")
            print("     irregular: no monotone drift, no single interior")
            print("     extremum, and not constant.")
        if g:
            print(f"     spread of the growth factors: max/min ="
                  f" {max(g) / min(g):.2f}   (1.00 would be a rigid shift)")
    elif v == "tail_carries_it":
        print("     §8·30·0 -> SECOND BRANCH. The growth factor rises with the")
        print("     quantile: **the long windows' extra omega is a tail**, and")
        print("     the extreme loops are what the ratio is made of.")
    else:
        print("     §8·30·0 -> THIRD BRANCH, mixed (R01). The growth factor")
        print("     falls with the quantile: the low end grew most, which is")
        print("     neither of the other two.")

    print_coh_signs(d)


def print_coh_signs(d) -> None:
    """§8·31. The sign alphabet and the same-sign / path-qualifying 2x2."""
    print("\n  §8·31: the sign alphabet, and whether C's two modes are two")
    print("  kinds of loan.")
    for L in NOISE_LENS:
        r = d["rows"][str(L)]
        if not r["n"] or not r.get("sign_patterns"):
            continue
        print(f"     window {L}, the whole alphabet (C0b, every pattern):")
        print(f"       {'pat':<6}{'n':>9}{'share':>9}{'qualify':>9}"
              f"{'mean|r| p50':>14}{'|om| p50':>13}")
        tot = sum(v["n"] for v in r["sign_patterns"].values())
        for k, v in sorted(r["sign_patterns"].items(),
                           key=lambda kv: -kv[1]["n"]):
            print(f"       {k:<6}{v['n']:>9,}{v['n'] / tot:>9.4f}"
                  f"{(v['qualify_rate'] if v['qualify_rate'] is not None else float('nan')):>9.4f}"
                  f"{v['meanabs_p50']:>14.4e}{v['absomega_p50']:>13.4e}")
        cv = r.get("C_exact_values", {})
        if cv:
            print(f"       C exactly 1: {cv.get('1', 0):,}"
                  f"   exactly 0: {cv.get('0', 0):,}"
                  f"   in between: {cv.get('mid', 0):,}")
            print("       (§8·31·3 item 2: on two months C takes finitely")
            print("        many values, so `exactly 1` is structural.)")

    print(f"\n     {'win':<5}{'n':>9}{'same-sign':>11}{'qualifying':>12}"
          f"{'both':>9}{'lift':>8}{'nearer':>14}{'live':>6}{'verdict':>12}")
    for L in NOISE_LENS:
        r = d["rows"][str(L)]
        o = r.get("sign_overlap")
        if not o or not r["n"]:
            continue
        print(f"     {L:<5}{r['sign_n']:>9,}{r['n_same_sign']:>11,}"
              f"{r['n_qualifying']:>12,}{o['a']:>9,}"
              f"{(o['lift'] if o['lift'] is not None else float('nan')):>8.3f}"
              f"{str(o['lift_nearer']):>14}"
              f"{str(o['branches_reachable']):>6}"
              f"{o['overlap_verdict']:>12}")
    print("     (`live` is how many of the three branches the margins allow,")
    print("      §11 item 20. §8·28 read `mixed` with one branch")
    print("      arithmetically excluded and nobody saw it at the time.)")

    L0 = NOISE_LENS[0]
    o0 = d["rows"][str(L0)].get("sign_overlap")
    if not o0:
        return
    print()
    v = o0["overlap_verdict"]
    if v == "contained":
        print(f"     §8·31·2 -> FIRST BRANCH at window {L0}. One side sits")
        print(f"     inside the other: {o0['contained_direction']}. The")
        print("     same-sign loops and the path-qualifying loops are one set.")
    elif v == "disjoint":
        print(f"     §8·31·2 -> SECOND BRANCH at window {L0}. No loop is both")
        print("     same-sign and path-qualifying.")
    else:
        print(f"     §8·31·2 -> THIRD BRANCH at window {L0}, mixed (R01).")
        print("     Neither containment nor disjointness; the lift and its two")
        print("     margin-derived anchors above are the reading.")
    print("     **§8·31·0 is a motive, not a conclusion**:")
    print("     this station does not rule on whether a same-sign loop is a")
    print("     cure that never caught up, a default, or a bookkeeping")
    print("     artefact. It measures signs and overlap.")
    print_pat_overlap(d)


def print_pat_overlap(d) -> None:
    """§8·32. The ideal pattern per window, and off-pattern against over-bound."""
    print("\n  §8·32: the ideal clean-cure sign pattern, generalised.")
    print(f"     {'win':<5}{'pattern':<12}{'n':>9}{'on pattern':>12}"
          f"{'share':>9}{'derived on':>12}{'derived off':>13}{'no u0':>8}")
    for L in NOISE_LENS:
        r = d["rows"][str(L)]
        if not r["n"]:
            continue
        print(f"     {L:<5}{ideal_pattern(L):<12}{r['sign_n']:>9,}"
              f"{r['ideal_pat']:>12,}"
              f"{(r['ideal_pat_share'] if r['ideal_pat_share'] is not None else float('nan')):>9.4f}"
              f"{r['ideal_and_derived']:>12,}{r['derived_off_pattern']:>13,}"
              f"{r['ob_unknown']:>8,}")
    print("     (`derived off` must be 0 at every window: §8·31·1 derives that")
    print("      an ideal path forces this pattern, so it is a **structural")
    print("      cross-check** and not a reading. A non-zero there means the")
    print("      derivation is wrong, which is worth knowing.)")

    print(f"\n     {'win':<5}{'n':>9}{'off-pat':>9}{'over':>9}{'both':>9}"
          f"{'lift':>8}{'nearer':>14}{'live':>6}{'verdict':>12}")
    for L in NOISE_LENS:
        r = d["rows"][str(L)]
        o = r.get("pat_overlap")
        if not o or not r["pat_n"]:
            continue
        print(f"     {L:<5}{r['pat_n']:>9,}{r['n_off_pattern']:>9,}"
              f"{r['n_over_bound']:>9,}{o['a']:>9,}"
              f"{(o['lift'] if o['lift'] is not None else float('nan')):>8.3f}"
              f"{str(o['lift_nearer']):>14}"
              f"{str(o['branches_reachable']):>6}{o['overlap_verdict']:>12}")

    L0 = NOISE_LENS[0]
    o0 = d["rows"][str(L0)].get("pat_overlap")
    if not o0 or not d["rows"][str(L0)]["pat_n"]:
        return
    print()
    v = o0["overlap_verdict"]
    if v == "contained":
        print(f"     §8·32·2 -> FIRST BRANCH at window {L0}:"
              f" {o0['contained_direction']}.")
    elif v == "disjoint":
        print(f"     §8·32·2 -> SECOND BRANCH at window {L0}. No loop is both")
        print("     off-pattern and over the grid bound.")
    else:
        print(f"     §8·32·2 -> THIRD BRANCH at window {L0}, mixed (R01).")
    if o0["lift"] is not None:
        print(f"     lift {o0['lift']:.4f}   anchors: independent 1.0000,"
              f" contained {o0['lift_if_contained']:.4f}"
              f"   nearer: {o0['lift_nearer']}")
        print("     **A large lift is not `the same set`** (fixed before the run")
        print("     item 3): §8·26·1 read a lift of 3.68 with each side only")
        print("     four tenths inside the other.")
    print("     The other three windows are delivered, not read"
          " (§3·4).")
    print_compound(d)


def print_compound(d) -> None:
    """§8·33. Does the ideal pattern's share collapse faster or slower than
    per-month independence would give."""
    print("\n  §8·33: why the ideal pattern's share collapses with the window.")
    print(f"     {'win':<5}{'n':>9}{'observed':>10}{'p (month)':>11}"
          f"{'q (cure)':>10}{'predicted':>11}{'obs/pred':>10}"
          f"{'npos histogram':>28}")
    for L in NOISE_LENS:
        r = d["rows"][str(L)]
        if not r["n"] or r.get("p_month") is None:
            continue
        obs = r["ideal_pat_share"]
        hist = ", ".join(f"{k}:{v:,}"
                         for k, v in sorted(r["npos_hist"].items(),
                                            key=lambda kv: int(kv[0])))
        #: `obs_over_pred` is None when the prediction is zero — no cure month
        #: in the whole window read negative, so `q` is 0. **That is a real
        #: state and it prints as a dash**, not as a crash and not as 0.0000:
        #: a ratio against a zero prediction is no ratio, and it does not vote
        #: (`coh_payload` filters on truthiness).
        ratio = (f"{r['obs_over_pred']:.4f}"
                 if r["obs_over_pred"] is not None else "-")
        print(f"     {L:<5}{r['sign_n']:>9,}{obs:>10.4f}{r['p_month']:>11.4f}"
              f"{r['q_cure']:>10.4f}{r['predicted']:>11.4f}"
              f"{ratio:>10}{hist:>28}")
    print("     (`npos` is how many of the L-1 delinquent months read")
    print("      positive, so it says whether a loop misses one month or")
    print("      most of them. §8·33·3 item 1.)")
    print("     (**every window votes, including window 2.** An earlier")
    print("      version excluded it on the claim that `p*q` is the observed")
    print("      share identically. It is not: `p*q` is the product of two")
    print("      marginals and the observed share is the joint, and they")
    print("      agree only under the independence being tested. The cure")
    print("      month is a second event.)")
    v = d.get("compound_verdict")
    print()
    if v == "no_reading":
        print("     §8·33·2 -> NO READING. Fewer than two windows carry a")
        print("     prediction that is not an identity.")
    elif v == "independent":
        print("     §8·33·2 -> NO BRANCH: observed equals predicted exactly")
        print("     at every voting window. **That is the null itself**, and")
        print("     none of the three registered branches claims it: `>=` and")
        print("     `<=` both hold, and putting the tie on either side would")
        print("     be §11 item 4. The misses are independent across months.")
    elif v == "clustered":
        print("     §8·33·2 -> FIRST BRANCH. Observed is at or above the")
        print("     compound prediction at every window that votes: **the")
        print("     misses cluster**. A loop that gets one delinquent month")
        print("     wrong tends to get others wrong, so the share collapses")
        print("     more slowly than independence would give.")
    elif v == "anti_clustered":
        print("     §8·33·2 -> SECOND BRANCH. Observed is at or below the")
        print("     compound prediction everywhere: **the misses spread**,")
        print("     and the share collapses faster than independence gives.")
    else:
        print("     §8·33·2 -> THIRD BRANCH, mixed (R01). The sign of")
        print("     `obs/pred - 1` is not the same at every voting window;")
        print("     the per-window ratios above are the reading.")
    print("     **This does not explain why a month reads wrong** (fixed")
    print("     before the run) — only whether the wrong months pile onto")
    print("     the same loops.")
    print_classes(d)


def print_classes(d) -> None:
    """§8·34. Who the four sign classes are, and how they fare afterwards."""
    r = d["rows"][str(NOISE_LENS[0])]
    cls = r.get("classes")
    if not cls:
        return
    L0 = NOISE_LENS[0]
    print(f"\n  §8·34: who the window-{L0} sign classes are.")
    print(f"     {'class':<7}{'n':>9}{'FICO p50 band':>15}{'FICO n/a':>10}"
          f"{'DTI p50':>9}{'DTI n/a':>9}{'FTHB Y':>8}{'purpose P':>11}")
    for k in ("+-", "++", "--", "-+"):
        c = cls.get(k)
        if not c:
            continue
        bands = sorted((int(b), n) for b, n in c["fico_bands"].items())
        tot = sum(n for _b, n in bands)
        med, run = "-", 0
        for b, n in bands:
            run += n
            if run * 2 >= tot:
                med = b
                break
        dti = (f"{c['dti_q'][1]:.0f}" if c["dti_q"] else "-")
        fthb = c["fthb"].get("Y", 0)
        purp = c["purpose"].get("P", 0)
        print(f"     {k:<7}{c['n']:>9,}{str(med):>15}{c['fico_unreadable']:>10,}"
              f"{dti:>9}{c['dti_unreadable']:>9,}"
              f"{(fthb / c['n'] if c['n'] else 0):>8.4f}"
              f"{(purp / c['n'] if c['n'] else 0):>11.4f}")
    print("     (FICO band is `fico_band`'s, C9 §2.1's boundaries, band 0")
    print("      highest. Unreadable is counted apart from any band: Freddie")
    print("      writes 9s for missing and folding those in would put `not")
    print("      reported` with `reported low`. §11 item 6.)")

    print(f"\n     {'class':<7}{'n':>9}{'tail p50':>10}{'exposure':>11}"
          f"{'redelinq':>10}{'share':>9}{'hazard':>10}{'RA':>8}{'zero bal':>10}")
    for k in ("+-", "++", "--", "-+"):
        c = cls.get(k)
        if not c:
            continue
        print(f"     {k:<7}{c['n']:>9,}"
              f"{(c['tail_months_p50'] if c['tail_months_p50'] is not None else float('nan')):>10.0f}"
              f"{c['exposure']:>11,}{c['redelinquent']:>10,}"
              f"{(c['redel_share'] if c['redel_share'] is not None else float('nan')):>9.4f}"
              f"{(c['hazard'] if c['hazard'] is not None else float('nan')):>10.6f}"
              f"{c['ra']:>8,}{c['zero_balance']:>10,}")
    print("     (`zero bal` is a zero UPB row, which on this carrier covers")
    print("      payoff, repurchase, short sale and REO disposition alike. It")
    print("      is `the loan left the pool`, **not** `the borrower paid it")
    print("      off`, and the column was mislabelled `paid off` once.)")
    print("     (exposure is months to the FIRST re-delinquency, or every")
    print("      remaining month when there is none. Counting all remaining")
    print("      months would hand an early re-defaulter exposure it never")
    print("      had at risk. §8·34·2 chose a hazard over a share precisely")
    print("      so no observation window had to be typed.)")
    a, b = cls.get("++"), cls.get("+-")
    if a and b and a["tail_months_p50"] is not None:
        print(f"     §8·34·3 item 1, the censoring check: tail medians"
              f" {b['tail_months_p50']:.0f} (`+-`) against"
              f" {a['tail_months_p50']:.0f} (`++`).")
        if a["tail_months_p50"] > b["tail_months_p50"]:
            print("     **The longer-observed class is `++`, and that runs")
            print("     against a `++ is riskier` reading rather than for it**:")
            print("     a hazard averaged over a longer window is pulled down")
            print("     wherever risk decays with time since the cure. The")
            print("     share column is not exposure-normalised and IS")
            print("     confounded by this; the hazard is what the branch")
            print("     reads, and the confound runs the wrong way to have")
            print("     manufactured it.")

    v = d["rows"][str(L0)].get("hazard_verdict")
    print()
    if v is None:
        print("     §8·34·2 -> NO READING. One of the two classes carries no")
        print("     exposure.")
    elif v == "plus_plus_riskier":
        print("     §8·34·2 -> FIRST BRANCH. `++` re-delinquents at a strictly")
        print("     higher monthly hazard than `+-`. **It is a real economic")
        print("     state**: the money that was never caught up is still owed")
        print("     and the risk is still there. On those loans the cure flag")
        print("     does not mean the arrears were repaid.")
    elif v == "plus_plus_safer":
        print("     §8·34·2 -> SECOND BRANCH. `++` re-delinquents at a strictly")
        print("     LOWER hazard. **Not to be told as the first branch's")
        print("     opposite**: a lower hazard can come from")
        print("     a different mechanism entirely.")
    else:
        print("     §8·34·2 -> THIRD BRANCH. The two hazards are identical in")
        print("     exact integers: on later risk `++` and `+-` do not differ,")
        print("     and the sign class is a status-field artefact.")
    print("     **This station does not say what `++` IS**:")
    print("     default, servicer forbearance and a bookkeeping artefact all")
    print("     fit these numbers. Telling them apart needs contract-level")
    print("     data this carrier does not publish.")
    print_crisis(d)


def print_crisis(d) -> None:
    """§8·35. Is `++` a crisis-year phenomenon or an institutional one."""
    r = d["rows"][str(NOISE_LENS[0])]
    cr = r.get("crisis")
    if not cr or not cr.get("years"):
        return
    print("\n  §8·35: `++` by the calendar year the cure happened in.")
    print("     windows declared before the run from public dates: "
          + ", ".join(f"{n} {a}-{b}" for n, a, b in CRISIS_WINDOWS))
    print("     (**not the origination vintage**: §8·22·5 measured vintage")
    print("      movement on this carrier to be a composition effect, so a")
    print("      vintage cut answers `which loans` and this asks `what was")
    print("      happening that year`.)")
    print(f"     {'year':<6}{'window':<8}{'++':>8}{'+-':>9}{'total':>9}"
          f"{'++ share':>10}")
    thin = None
    for y, v in cr["years"].items():
        if v["total"] and (thin is None or v["total"] < thin[1]):
            thin = (y, v["total"])
        sh = (f"{v['pp_share']:.4f}" if v["pp_share"] is not None else "-")
        print(f"     {y:<6}{v['window']:<8}{v['pp']:>8,}{v['pm']:>9,}"
              f"{v['total']:>9,}{sh:>10}")
    if thin:
        print(f"     §3·4's thinnest cure year: {thin[0]} with {thin[1]:,}"
              f" loops across the two classes.")
    print("     (§8·35·3 item 2: the HAZARD is deliberately not split by cure")
    print("      year — a re-delinquency can land years later, and charging it")
    print("      to the cure's year would be reading one year's outcome onto")
    print("      another's. Shares only.)")

    print(f"\n     {'window':<8}{'++':>9}{'total':>9}{'++ share':>10}")
    for w in sorted(cr["windows"]):
        v = cr["windows"][w]
        sh = (f"{v['pp_share']:.4f}" if v["pp_share"] is not None else "-")
        print(f"     {w:<8}{v['pp']:>9,}{v['total']:>9,}{sh:>10}")
    if cr["crisis_share"] is not None:
        print(f"     pooled crisis {cr['crisis_share']:.4f}"
              f" ({cr['crisis_pp']:,}/{cr['crisis_total']:,})"
              f"   against calm {cr['calm_share']:.4f}"
              f" ({cr['calm_pp']:,}/{cr['calm_total']:,})")

    v = r.get("crisis_verdict")
    print()
    if v is None:
        print("     §8·35·2 -> NO READING. One side carries no loops.")
    elif v == "crisis_higher":
        print("     §8·35·2 -> FIRST BRANCH. The `++` share is strictly higher")
        print("     inside the declared windows. **`++` is a disposition")
        print("     behaviour**: in the years the servicers were swamped, the")
        print("     status flag and the cash came apart more often.")
    elif v == "crisis_lower":
        print("     §8·35·2 -> SECOND BRANCH. Strictly LOWER inside the")
        print("     windows. **Not the first branch's opposite** (fixed")
        print("     before the run): a lower share can come from another mechanism.")
    else:
        print("     §8·35·2 -> THIRD BRANCH. Identical in exact integers:")
        print("     **`++` is institutional, not a crisis artefact.** The")
        print("     literature that treats `cured` as repayment is biased")
        print("     throughout, not only in the crisis years.")
    print("     The two windows are printed apart and read together"
          ":")
    print("     pooled asks `was the servicer busy`, split asks `which")
    print("     crisis`, and this station asks the first.")
    print("     **What `++` IS remains unsaid** (§8·34·4, inherited).")
    print_frozen(d)


def print_frozen(d) -> None:
    """§8·36. Is the break a reporting convention: was the balance frozen."""
    r = d["rows"][str(NOISE_LENS[0])]
    fr = r.get("frozen")
    if not fr:
        return
    print("\n  §8·36: was the delinquent month's balance reported frozen.")
    print("     frozen means bal_ib(t1) == bal_ib(t0) **exactly** (§8·18's")
    print("     col 3 - col 12; age >= 8 across the window, reported to the")
    print("     cent, so no tolerance is needed and none is used).")
    print(f"     {'year':<6}{'loops':>9}{'frozen':>9}{'share':>9}"
          f"{'r1 < 0':>9}{'unfrozen':>10}")
    for y, v in fr["years"].items():
        sh = (f"{v['frozen_share']:.4f}" if v["frozen_share"] is not None
              else "-")
        mark = "  <- all" if v["all_frozen"] else ""
        print(f"     {y:<6}{v['loops']:>9,}{v['frozen']:>9,}{sh:>9}"
              f"{v['r1_neg']:>9,}{v['loops'] - v['frozen']:>10,}{mark}")
    print("     (`r1 < 0` must never exceed `unfrozen`: a frozen balance makes")
    print("      carry_forward drop it, so r1 > 0 follows. **That is a")
    print("      theorem and the column is a structural cross-check, not a")
    print("      reading** — §11 item 15, which §8·31 paid a full scan to")
    print("      learn.)")
    bad = fr.get("theorem_violations")
    print(f"     theorem violations: {bad if bad else 'none'}")
    print(f"     loops the question could not be answered on:"
          f" {fr.get('unreadable', 0):,}")
    print("     (a balance unreadable is **not** `not frozen` —")
    print("      §11 item 6. §8·14·5's whole finding was that blank and zero")
    print("      are structurally opposite.)")

    if fr.get("months_2019"):
        print("\n     §8·36·4 item 2: 2019 by cure month, the break falls")
        print("     inside the year.")
        print(f"     {'month':<8}{'loops':>9}{'frozen':>9}{'share':>9}"
              f"{'r1 < 0':>9}")
        thin = None
        for m, v in fr["months_2019"].items():
            if v["loops"] and (thin is None or v["loops"] < thin[1]):
                thin = (m, v["loops"])
            sh = (f"{v['frozen_share']:.4f}" if v["frozen_share"] is not None
                  else "-")
            print(f"     {m:<8}{v['loops']:>9,}{v['frozen']:>9,}{sh:>9}"
                  f"{v['r1_neg']:>9,}")
        if thin:
            print(f"     §3·4's thinnest 2019 month: {thin[0]} with"
                  f" {thin[1]:,} loops.")

    v = r.get("frozen_verdict")
    print()
    if v == "no_reading":
        print("     §8·36·3 -> NO READING. No cure year at or after")
        print(f"     {fr['break_year']} carries a loop.")
    elif v == "convention_changed":
        print(f"     §8·36·3 -> FIRST BRANCH. From {fr['break_year']} every")
        print("     loop's delinquent month is frozen, and before it some")
        print("     years are not. **The reporting convention changed, and it")
        print("     accounts for the sign collapse**: a frozen month forces")
        print("     r1 > 0, so `--` and `-+` stop being possible.")
    elif v == "frozen_not_total":
        print(f"     §8·36·3 -> SECOND BRANCH. Some year at or after")
        print(f"     {fr['break_year']} has unfrozen months, yet no loop reads")
        print("     r1 < 0. **Freezing is not the whole mechanism**; something")
        print("     else is holding the sign positive, and it is unnamed.")
    else:
        print("     §8·36·3 -> THIRD BRANCH. Every year is fully frozen,")
        print("     before and after. **Then freezing explains nothing about")
        print("     the change** and the break is somewhere else.")
    print("     **Whose convention this is, this station does not say**")
    print("     (fixed before the run): the carrier's reporting rule and the")
    print("     servicers' practice look the same in this file.")
    print_r2(d)


def print_r2(d) -> None:
    """§8·37. Conditioned on frozen, did r2 move as well."""
    r = d["rows"][str(NOISE_LENS[0])]
    q = r.get("r2")
    if not q or not q.get("years"):
        print_assist(d)
        return
    print("\n  §8·37: `++` among FROZEN loops, which is r2's own margin.")
    print("     frozen implies r1 > 0 (§8·36·1, a theorem), so a frozen loop")
    print("     is `++` or `+-` and only the cure month's sign separates")
    print("     them. Conditioning on frozen takes the reporting change out")
    print("     **by construction**: a conditional count, not a control.")
    bad = q["theorem_frozen_in_neg_classes"]
    print(f"     frozen loops filed under `-+`/`--`: {bad}"
          f"  {'(theorem holds)' if not any(bad.values()) else '**VIOLATION**'}")
    print_thm_break(r)
    print(f"     {'year':<6}{'frozen ++':>11}{'frozen tot':>12}{'share':>9}"
          f"{'unfroz ++':>11}{'unfroz tot':>12}{'share':>9}")
    thin = None
    for y, v in q["years"].items():
        if v["frozen_total"] and (thin is None or
                                  v["frozen_total"] < thin[1]):
            thin = (y, v["frozen_total"])
        fs = (f"{v['frozen_pp_share']:.4f}"
              if v["frozen_pp_share"] is not None else "-")
        us = (f"{v['unfrozen_pp_share']:.4f}"
              if v["unfrozen_pp_share"] is not None else "-")
        print(f"     {y:<6}{v['frozen_pp']:>11,}{v['frozen_total']:>12,}"
              f"{fs:>9}{v['unfrozen_pp']:>11,}{v['unfrozen_total']:>12,}"
              f"{us:>9}")
    if thin:
        print(f"     §3·4's thinnest frozen year: {thin[0]}"
              f" with {thin[1]:,} loops.")
    if q.get("months_2019"):
        print("\n     §8·37·3 item 2: 2019 by cure month, because §8·36·3 put")
        print("     the break inside that year.")
        print(f"     {'month':<8}{'frozen ++':>11}{'frozen tot':>12}"
              f"{'share':>9}")
        for m, v in q["months_2019"].items():
            fs = (f"{v['frozen_pp_share']:.4f}"
                  if v["frozen_pp_share"] is not None else "-")
            print(f"     {m:<8}{v['frozen_pp']:>11,}"
                  f"{v['frozen_total']:>12,}{fs:>9}")
    pre, post, mid = q["pre"], q["post"], q["straddle_year"]
    ps = f"{pre['share']:.4f}" if pre["share"] is not None else "-"
    qs = f"{post['share']:.4f}" if post["share"] is not None else "-"
    print(f"\n     pre  {pre['pp']:,} / {pre['total']:,} = {ps}"
          f"   post {post['pp']:,} / {post['total']:,} = {qs}")
    print(f"     the straddling year {mid['year']} is in neither segment:"
          f" {mid['pp']:,} / {mid['total']:,}")
    v = r.get("r2_verdict")
    print()
    if v is None:
        print("     §8·37·2 -> NO READING. One side carries no frozen loops.")
    elif v == "r2_moved_too":
        print("     §8·37·2 -> FIRST BRANCH. Strictly LOWER after the break,")
        print("     in exact integers. **r2 moved as well, so the collapse of")
        print("     `++` is not a composition effect of freezing.** That")
        print("     unnamed second thing now has a size, and it still has no")
        print("     name, and this station does not give it one.")
    elif v == "r2_moved_up":
        print("     §8·37·2 -> SECOND BRANCH. Strictly HIGHER. Set apart, and")
        print("     **not to be told as the reverse of the first branch**:")
        print("     higher can come from another mechanism.")
    else:
        print("     §8·37·2 -> THIRD BRANCH. Identical in exact integers:")
        print("     **the collapse of `++` is entirely a composition effect**.")
        print("     Freezing changed the mix and r2 itself did not move, which")
        print("     is what §8·36·4's 13.0x was.")
    print_assist(d)


def print_thm_break(r) -> None:
    """§8·37·2's处置: the loops that trip the gate, printed field by field.

    **Not a verdict and not a branch.** The registered处置 is 回去查, so this
    prints what the theorem's premise needs and says nothing about what it
    means. `P_exceeds_interest` is the premise: §8·36·1 pushes the balance
    down through `carry_forward`, which only lowers it when the payment
    covers the month's interest, and `P` on this carrier is an estimate
    (§8·20·8).
    """
    n = r.get("theorem_break_n") or 0
    rows = r.get("theorem_break") or []
    print(f"\n     §8·37·2's处置 (回去查): loops a frozen month left on the"
          f" negative side")
    print(f"     count {n:,}   printed {len(rows):,}"
          f"   cap {r.get('theorem_break_cap')}")
    if n and len(rows) < n:
        print(f"     ... {n - len(rows):,} not printed. The count is printed"
              f" rather than the cap being silent.")
    if not n:
        print("     none. **The gate did not fire on this population**, which"
              " is not")
        print("     the same statement as `the theorem holds everywhere`: this"
              " run")
        print("     covers the vintages it was given, and the header says"
              " which.")
        return
    for i, b in enumerate(rows):
        pe = b["P_exceeds_interest"]
        print(f"     [{i + 1}] class {b['class']}  vintage {b['vintage']}"
              f"  periods {b['period_a']} -> {b['period_1']}"
              f" -> {b['period_b']}")
        print(f"         age {b['age_a']}  rem {b['rem_a']}"
              f"  note {b['note']}")
        print(f"         t_A  col3 {b['upb_a']}  col12 {b['defer_a']}"
              f"  bal_ib {b['ib_a']}")
        print(f"         t_1  col3 {b['upb_1']}  col12 {b['defer_1']}"
              f"  bal_ib {b['ib_1']}")
        print(f"         P {b['P']}   month's interest {b['interest']}"
              f"   P > interest: {pe}")
        print(f"         r {b['r']}")
    anyfalse = [b for b in rows if b["P_exceeds_interest"] is False]
    print(f"     of the printed rows, {len(anyfalse):,} have a payment that"
          f" does NOT")
    print("     cover the month's interest. **That column is the theorem's")
    print("     unstated premise, and this station prints it rather than")
    print("     ruling on it**: whether §8·36·1 gets amended or the driver")
    print("     gets fixed is a decision, not a reading.")


def vin_split(r):
    """The vintage x cure-month cut, reshaped for printing.

    **Returns tables, not a verdict.** Nothing here has a branch, and that is
    deliberate. Whether a one-month step that lands on every vintage at
    once is a calendar shock or a property of the loans is the reader's
    comparison, and this file does not make it.
    """
    va = r.get("vin_all") or {}
    vm = r.get("vin_month") or {}
    months, byvin = set(), {}
    for key, box in vm.items():
        vin, per = key.split("|")
        months.add(int(per))
        byvin.setdefault(vin, {})[int(per)] = box
    return va, byvin, sorted(months)


def _share(a, b):
    return ("%.3f" % (a / b)) if b else "  -  "


def print_vin(d, prod=None) -> None:
    """The vintage x cure-month tables. No branch, no verdict."""
    r = d["rows"][str(NOISE_LENS[0])]
    va, byvin, months = vin_split(r)
    if not va:
        return
    lo, hi = r.get("vin_window", [VIN_MONTH_LO, VIN_MONTH_HI])
    print(f"\n  The vintage x cure-month cut. Window {lo}..{hi};"
          f" every vintage's all-time totals print beside it.")
    print("  **No branch and no verdict here.** These are printed objects.")

    print(f"\n  A. per vintage, all cure months")
    print(f"     {'vintage':<9}{'loops':>9}{'frozen':>9}{'froz rate':>11}"
          f"{'++|froz':>9}{'share':>8}")
    thin = None
    for vin, b in sorted(va.items()):
        if b[1] and (thin is None or b[1] < thin[1]):
            thin = (vin, b[1])
        print(f"     {vin:<9}{b[0]:>9,}{b[1]:>9,}{_share(b[1], b[0]):>11}"
              f"{b[2]:>9,}{_share(b[2], b[1]):>8}")
    if thin:
        print(f"     §3·4's thinnest vintage by frozen loops:"
              f" {thin[0]} with {thin[1]:,}")

    m19 = [m for m in months if 201900 < m < 202000]
    for title, num, den in (
            ("B. `++` among FROZEN loops, by vintage x 2019 month"
             "  (§8·37·2's break sits at 201904/05)", 2, 1),
            ("C. frozen rate, by vintage x 2019 month"
             "  (§8·36·3's break sits at 201906/07)", 1, 0)):
        print(f"\n  {title}")
        print("     vintage  " + "".join("%7s" % str(m)[4:] for m in m19))
        for vin in sorted(byvin):
            row = byvin[vin]
            cells = "".join("%7s" % _share(row[m][num], row[m][den])
                            if m in row else "%7s" % "  -  " for m in m19)
            print(f"     {vin:<9}" + cells)
        pooled = []
        for m in m19:
            a = sum(byvin[v][m][num] for v in byvin if m in byvin[v])
            b = sum(byvin[v][m][den] for v in byvin if m in byvin[v])
            pooled.append((m, a, b))
        print("     " + "-" * 76)
        print("     pooled  " + "".join("%7s" % _share(a, b)
                                        for _m, a, b in pooled))
        print("     n       " + "".join("%7d" % b for _m, _a, b in pooled))

    #: 失效模式 18 done right: the pooled 2019 row must reproduce §8·37's own
    #: table, which has a named producer on disk. Same population or the cut
    #: is measuring something else.
    old = (prod or {}).get("r2", {}).get("months_2019") or {}
    if not old:
        print("\n     cross-check against b10_noise.json's §8·37 table:"
              " no previous file, and that is said rather than passed over.")
        return
    bad = []
    for m in m19:
        a = sum(byvin[v][m][2] for v in byvin if m in byvin[v])
        b = sum(byvin[v][m][1] for v in byvin if m in byvin[v])
        o = old.get(str(m))
        if not o or o["frozen_pp"] != a or o["frozen_total"] != b:
            bad.append((m, a, b, o and (o["frozen_pp"], o["frozen_total"])))
    print(f"\n     cross-check against b10_noise.json's §8·37 2019 table:"
          f" {'MATCH' if not bad else '**DO NOT MATCH**'}")
    for row in bad:
        print(f"       {row[0]}: this run {row[1]}/{row[2]}, prior {row[3]}")
    if bad:
        print("     The two are not the same population. Read nothing off")
        print("     these tables until that is cleared (失效模式 18).")


def print_assist(d) -> None:
    """§8·38. Is `++` enriched in loans the servicer flagged as assisted."""
    r = d["rows"][str(NOISE_LENS[0])]
    a = r.get("assist")
    if not a:
        return
    print("\n  §8·38: servicing assistance on the loop's own span rows.")
    print("     perf column 30, codes imported from b10_o18_null rather than")
    print("     retyped (§8·38·1; §8·28·1 already paid for a copied")
    print("     constant). `floor_row` carries no such column and was not")
    print("     touched, so 規矩 19's surface stays where it is.")
    print(f"     {'class':<7}{'asked':>10}{'assisted':>10}{'share':>9}"
          f"{'unknown row':>13}")
    for k in ("++", "+-"):
        v = a.get(k)
        if not v:
            continue
        sh = f"{v['share']:.4f}" if v["share"] is not None else "-"
        print(f"     {k:<7}{v['asked']:>10,}{v['assisted']:>10,}{sh:>9}"
              f"{v['unknown_row']:>13,}")
    for k in ("++", "+-"):
        v = a.get(k)
        if not v:
            continue
        print(f"     {k} codes (C0b, every value seen): {v['codes']}")
        print(f"     {k} which span row carried it: {v['position']}")
    print("     ((blank) and (row not found) are separate keys: one says the")
    print("      servicer reported no assistance, the other says this file")
    print("      could not be asked. §11 item 6, §8·14·5's finding.)")
    yrs = sorted(set(list(a.get("++", {}).get("by_year", {}))
                     + list(a.get("+-", {}).get("by_year", {}))), key=int)
    if yrs:
        print("\n     §8·38·3 item 1: assisted share by cure year, because of")
        print("     the 2019-07 break (§8·36·3).")
        print(f"     {'year':<6}{'++ n':>8}{'++ asg':>8}{'+- n':>9}"
              f"{'+- asg':>8}")
        for y in yrs:
            u = a.get("++", {}).get("by_year", {}).get(y, [0, 0])
            w = a.get("+-", {}).get("by_year", {}).get(y, [0, 0])
            print(f"     {y:<6}{u[0]:>8,}{u[1]:>8,}{w[0]:>9,}{w[1]:>8,}")
    v = r.get("assist_verdict")
    print()
    if v == "not_asked":
        print("     §8·38·2 -> NO READING. The code map never reached this")
        print("     accumulator, so the question was not put.")
    elif v == "no_assisted_loops":
        print("     §8·38·2 -> FOURTH BRANCH. **Neither class carries a single")
        print("     assisted loop.** The population was never screened on the")
        print("     code, so this had to stay a live branch, and it fired.")
        print("     No verdict, coverage only.")
    elif v == "pp_more_assisted":
        print("     §8·38·2 -> FIRST BRANCH. `++` is strictly more assisted,")
        print("     in exact integers. **The forbearance / repayment-plan")
        print("     family is now a candidate earned by behaviour**, not a")
        print("     line copied out of an issuer's glossary.")
        print("     **`++` is still not equal to it** (fixed before the run,")
        print("     inheriting §8·34·4): this buys the candidate a number, not")
        print("     an identity.")
    elif v == "pp_less_assisted":
        print("     §8·38·2 -> SECOND BRANCH. Strictly LESS assisted. Set")
        print("     apart, and **not to be told as the reverse of the first**:")
        print("     lower can come from another mechanism.")
    else:
        print("     §8·38·2 -> THIRD BRANCH. Identical in exact integers:")
        print("     **the code does not separate the two classes**, so the")
        print("     candidate got no behavioural support. Registered.")
    print("     **Nothing here connects the code to §8·34's 1.79x hazard**")
    print("     (fixed before the run): two different quantities, and")
    print("     joining them needs its own registration.")
    print_vin(d, NOISE_PRIOR.get("prior"))
def noise_payload(acc, omega_acc) -> dict:
    cells = {}
    for (aname, pname), lens in acc["cells"].items():
        for L, c in lens.items():
            v = c["vals"]
            cells[f"{aname}|{pname}|{L}"] = {
                "anchor": aname, "payment": pname, "L": L,
                "kept": c["kept"], "sampled": len(v), "capped": c["capped"],
                "skips": dict(c["skips"]),
                "skip_total": sum(c["skips"].values()),
                "examples": c["examples"][:NOISE_EXAMPLE_CAP],
                "q": _q(v, (10, 50, 90)),
                "absmed": _q([abs(x) for x in v], (50,))[0],
                "absq": _q([abs(x) for x in v], (50, 90, 99)),
                "vintages": len(c["kept_v"])}

    #: §8·21·5. `omega` is §8·20's own `b8like` x derived-qualifying loops,
    #: matched by `L = k + 1` (§8·21·4). The floor is `cent` x `P_orig`,
    #: **the same payment §8·20 published on** — using `P_sub` for one side
    #: and `P_orig` for the other is 失效模式 18 on the arguments (§11 item 11).
    aucs, sizes, aucs_all, sizes_all = {}, {}, {}, {}
    sd = omega_acc["b8like"]["stream_derived"] if omega_acc else {}
    sa = omega_acc["b8like"]["stream_all"] if omega_acc else {}
    for L in NOISE_LENS:
        fl = [abs(x) for x in acc["cells"][("cent", "orig")][L]["vals"]]
        om = [abs(x) for x in sd.get(L - 1, [])]
        sizes[str(L)] = {"omega": len(om), "floor": len(fl), "k": L - 1}
        aucs[str(L)] = noise_auc(om, fl)
        #: §8·21·9: the same comparison with the path filter off on the omega
        #: side, which is what B8's own (i-b) reads.
        oa = [abs(x) for x in sa.get(L - 1, [])]
        sizes_all[str(L)] = {"omega": len(oa), "floor": len(fl), "k": L - 1,
                             "omega_absmed": _q(oa, (50,))[0] if oa else None,
                             "floor_absmed": _q(fl, (50,))[0] if fl else None}
        aucs_all[str(L)] = noise_auc(oa, fl)
    coh = coh_payload(omega_acc["b8like"]["coh"] if omega_acc else {},
                      sizes_all)
    return {"coh": coh,
            "loans": acc["loans"], "clean_loans": acc["clean_loans"],
            "screen_first": dict(acc["screen_first"]),
            "screen_any": dict(acc["screen_any"]),
            "no_anchor": dict(acc["no_anchor"]), "no_P": dict(acc["no_P"]),
            "cap_per_vintage": NOISE_CAP, "sample_cap": NOISE_SAMPLE_CAP,
            "cells": cells, "auc": aucs, "auc_sizes": sizes,
            "auc_all": aucs_all, "auc_all_sizes": sizes_all,
            "fannie_floor_absmed": {str(k): list(v) for k, v
                                    in B8_0B_FLOOR_ABSMED.items()},
            "fannie_ib_absmed": list(B8_0A_IB_ABSMED)}


def print_noise(pl) -> None:
    print("\n  A. the population, and the three whole-loan screens")
    print(f"     loans {pl['loans']:,}   never delinquent, never modified,"
          f" never deferred {pl['clean_loans']:,}")
    print(f"     {'screen':<44}{'first match':>12}{'independent':>13}")
    for g in NOISE_SCREENS:
        print(f"     {g:<44}{pl['screen_first'][g]:>12,}"
              f"{pl['screen_any'][g]:>13,}")
    sf = sum(pl["screen_first"].values())
    print(f"     {'sum of first-match':<44}{sf:>12,}   + clean"
          f" {pl['clean_loans']:,} = {sf + pl['clean_loans']:,}"
          f" against loans {pl['loans']:,}"
          f"   {'MATCH' if sf + pl['clean_loans'] == pl['loans'] else 'NO'}")
    print(f"     no anchor: cent {pl['no_anchor']['cent']:,}"
          f"   grid {pl['no_anchor']['grid']:,}")
    print(f"     no payment: P_orig {pl['no_P']['orig']:,}"
          f"   P_sub at the cent anchor {pl['no_P']['sub']:,}")

    print(f"\n  B. every candidate accounted for. cap {pl['cap_per_vintage']:,}"
          f" per vintage per cell, **logged**")
    print(f"     {'cell':<18}{'kept':>9}{'capped':>8}{'vint':>6}"
          + "".join(f"{g[:13]:>15}" for g in NOISE_SKIPS))
    for key in sorted(pl["cells"]):
        c = pl["cells"][key]
        print(f"     {key:<18}{c['kept']:>9,}{str(c['capped']):>8}"
              f"{c['vintages']:>6}"
              + "".join(f"{c['skips'][g]:>15,}" for g in NOISE_SKIPS))
    print("     A silent truncation reads as full coverage when it is not")
    print("     (B8's own words). `capped True` means this cell hit the")
    print("     per-vintage cap on at least one vintage.")

    ex = [(k, c) for k, c in sorted(pl["cells"].items()) if c["examples"]]
    print(f"\n  C. failing paths, printed verbatim, up to"
          f" {NOISE_EXAMPLE_CAP} per cell")
    if not ex:
        print("     none.")
    for k, c in ex[:6]:
        for e in c["examples"][:2]:
            print(f"     {k:<18} t {e['t']:>8}  bal_prev {e['bal_prev']:>14,.2f}"
                  f"  bal_now {e['bal_now']:>14,.2f}"
                  f"  b_hat {e['b_hat']:>14,.2f}"
                  f"  P {e['P']:>10,.2f}  note {e['note']:.3f}")
    print("     B8's floor table came back empty on all six archives on its")
    print("     first run and reading the code did not settle why. The values")
    print("     are shown rather than reasoned about.")

    print("\n  D. the floor itself")
    print(f"     {'cell':<18}{'kept':>9}{'p10':>13}{'p50':>13}{'p90':>13}"
          f"{'median |.|':>13}")
    for key in sorted(pl["cells"]):
        c = pl["cells"][key]
        if not c["kept"]:
            print(f"     {key:<18}{0:>9}   empty")
            continue
        print(f"     {key:<18}{c['kept']:>9,}{c['q'][0]:>+13.4e}"
              f"{c['q'][1]:>+13.4e}{c['q'][2]:>+13.4e}{c['absmed']:>13.4e}")

    print("\n  E. §8·21·2: what the $1,000 grid does to a holonomy reading")
    print("     The two anchors differ in one thing: `cent` starts at age >= "
          f"{FLOOR_MIN_AGE},")
    print("     where Freddie reports to the cent; `grid` starts wherever the")
    print("     loan does, which for most loans is inside the $1,000 grid")
    print("     (§8·16). Half a step is $500 against $0.005, a factor of")
    print("     100,000, and the prediction registered before this run was")
    print("     that `grid` reads orders of magnitude higher.")
    print(f"     {'L':<4}{'cent |.|':>14}{'grid |.|':>14}{'ratio':>14}")
    for L in NOISE_LENS:
        cc = pl["cells"][f"cent|orig|{L}"]
        gc = pl["cells"][f"grid|orig|{L}"]
        rr = (gc["absmed"] / cc["absmed"]) if cc["absmed"] else float("nan")
        print(f"     {L:<4}{cc['absmed']:>14.4e}{gc['absmed']:>14.4e}"
              f"{rr:>14.4e}")

    print("\n  F. Fannie's floor beside it (results/b8_0a_gate.md section 3)")
    print(f"     {'L':<4}{'Freddie cent':>15}{'Fannie min':>15}"
          f"{'Fannie max':>15}")
    for L in NOISE_LENS:
        lo, hi = B8_0B_FLOOR_ABSMED[L]
        print(f"     {L:<4}{pl['cells'][f'cent|orig|{L}']['absmed']:>15.4e}"
              f"{lo:>15.4e}{hi:>15.4e}")
    print(f"     Fannie's (i-b) loop side, median |.|:"
          f" {B8_0A_IB_ABSMED[0]:.4e} to {B8_0A_IB_ABSMED[1]:.4e}")
    print("     **Beside, not subtracted** (§7·9).")

    print("\n  G. Read, per the criteria fixed before the run, one variable, three branches,")
    print("     **once per window length, not pooled** (§3·4)")
    print(f"     {'L':<4}{'k':>3}{'n omega':>9}{'n floor':>9}{'AUC':>9}"
          f"{'null p5':>9}{'null p95':>9}{'outside':>9}  branch")
    for L in NOISE_LENS:
        r = pl["auc"][str(L)]
        z = pl["auc_sizes"][str(L)]
        if r is None:
            print(f"     {L:<4}{L-1:>3}{z['omega']:>9,}{z['floor']:>9,}"
                  f"{'n/a':>9}{'':>9}{'':>9}{'':>9}  NO REFERENT: one side is"
                  f" empty, and an empty set must not win a comparison")
            continue
        if not r["outside"]:
            br = ("§8·21·5 SECOND: same distribution, the floor is too high "
                  "to gate on")
        elif r["auc"] > 0.5:
            br = "§8·21·5 FIRST: omega sits above the floor"
        else:
            br = "§8·21·5 THIRD: omega sits BELOW the floor, nobody predicted"
        print(f"     {L:<4}{L-1:>3}{z['omega']:>9,}{z['floor']:>9,}"
              f"{r['auc']:>9.4f}{r['null_p05']:>9.4f}{r['null_p95']:>9.4f}"
              f"{str(r['outside']):>9}  {br}")
    print(f"     null: {NOISE_N_PERM} label permutations, seed"
          f" {NOISE_PERM_SEED}. Expectation 0.5 under the null, which is")
    print("     structural rather than a line drawn on an estimator (纪律 11).")
    print("     omega is §8·20's b8like x derived-qualifying loops; the floor")
    print("     is cent x P_orig, **the same payment §8·20 published on**.")
    print("     Mixing P_sub into one side would be 失效模式 18 on the")
    print("     arguments (§11 item 11's second shape).")

    print("\n  G2. Read, per the criteria fixed before the run: the same comparison with the")
    print("      path filter **off** on the omega side, which is what B8's")
    print("      own (i-b) reads: *the same residual on every clean-cure")
    print("      loan, whatever its path*.")
    print(f"     {'L':<4}{'k':>3}{'n omega':>9}{'n floor':>9}"
          f"{'|w| p50':>12}{'floor p50':>12}{'AUC':>9}"
          f"{'null p5':>9}{'null p95':>9}{'out':>6}  branch")
    for L in NOISE_LENS:
        r = pl["auc_all"][str(L)]
        z = pl["auc_all_sizes"][str(L)]
        om = z["omega_absmed"]
        flm = z["floor_absmed"]
        if r is None:
            print(f"     {L:<4}{L-1:>3}{z['omega']:>9,}{z['floor']:>9,}"
                  f"{'':>12}{'':>12}{'n/a':>9}  NO REFERENT: one side is empty")
            continue
        if not r["outside"]:
            br = ("§8·21·9 SECOND: same distribution, the floor is too high "
                  "to gate on")
        elif r["auc"] > 0.5:
            br = "§8·21·9 FIRST: omega sits above the floor"
        else:
            br = ("§8·21·9 THIRD: omega BELOW the floor, the asymmetry was "
                  "not the cause")
        print(f"     {L:<4}{L-1:>3}{z['omega']:>9,}{z['floor']:>9,}"
              f"{om:>12.4e}{flm:>12.4e}{r['auc']:>9.4f}"
              f"{r['null_p05']:>9.4f}{r['null_p95']:>9.4f}"
              f"{str(r['outside'])[0]:>6}  {br}")
    print("     **G's reading is not withdrawn.** It fell where its own")
    print("     registration put it; §8·21·6 records why, and this line is")
    print("     the check on that record, not a replacement for it.")

    print("\n  H. What this section does NOT deliver (§8·21·7)")
    print("     The triangles' omega, with leg 2 at the modification month:")
    print("       §8·22. Nothing above has a leg 2 in it.")
    print("     §8·12 re-asked on this carrier: needs §8·22 as well.")
    print("     No claim that §1.1 has an answer on this carrier.")

    print_coh(pl)


def cmd_noise(only) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    if not vs:
        print(f"  no archives under {RAW}")
        return 1
    sys.path.insert(0, str(ROOT / "experiments"))
    import b8_cmt_fetch as F                      # noqa: E402
    import b8_loop_omega as LO                    # noqa: E402
    import b8_omega as W                          # noqa: E402
    import b8_0a_gate as G                        # noqa: E402
    import b10_c8_1d_freddie as FR                # noqa: E402
    #: §8·38·1. The assistance column and its code set are **imported**, not
    #: retyped: §8·28·1 already paid for a copied constant on this station.
    import b10_o18_null as O                      # noqa: E402

    if W.MAX_H != CURVE_MAX_H:
        print(f"  b8_omega.MAX_H is {W.MAX_H} and this file says "
              f"{CURVE_MAX_H}. Fix one; nothing is read until then.")
        return 1
    if tuple(G.FLOOR_LENS) != NOISE_LENS:
        print(f"  b8_0a_gate.FLOOR_LENS is {G.FLOOR_LENS} and this file says "
              f"{NOISE_LENS}. Two copies of a window list with no check "
              f"between them is 失效模式 19.")
        return 1
    if not print_crosscheck(resid_crosscheck(W, G)):
        print("\n  §8·19·3 did not pass. Nothing was read. Fix it first.")
        return 1
    print()

    prior = prior_json(ROOT, partial_name("b10_noise", only))
    src, files = F.load_treasury()
    if not src:
        print("  no Treasury curve under data/raw/cmt.")
        return 1
    pos, tab = LO.curve_table_from(src, LO.RULE)

    print(f"  §8·38's constants are imported: assistance column"
          f" {O.P_ASSIST + 1} (one-based), codes {O.ASSIST_CODES}.")
    print("§8·21: the noise floor, from never-delinquent windows.\n"
          "  **One scan, two populations.** The loops are recomputed on the\n"
          "  same pass so §8·20's own figures come back beside the floor;\n"
          "  they must reproduce, and the check is printed (§8·21·5 needs the\n"
          "  two samples in one place, and reproducing §8·20 costs nothing\n"
          "  extra once the archive is open).\n")
    acc = noise_new_acc()
    oacc = omega_new_acc()
    for v in vs:
        orig, _ = FR.read_orig(v)
        #: §8·34. A second pass over the origination file, this mode only.
        #: `FR.O_SEQ` rather than a second copy of the column index.
        prof = read_orig_profile(v, FR.O_SEQ)
        with zipfile.ZipFile(archive(v)) as zf:
            with zf.open(f"sample_perf_{v}.txt") as raw:
                seq, batch, amap = None, [], {}
                for line in io.TextIOWrapper(raw, encoding="utf-8",
                                             newline=""):
                    if not line.strip():
                        continue
                    f = line.split("|")
                    if f[0] != seq:
                        if seq is not None:
                            noise_absorb(acc, batch, orig.get(seq), v, W,
                                         FR.contract_payment)
                            omega_absorb(oacc, batch, orig.get(seq), v, pos,
                                         tab, CURVE_MAX_H, W, G,
                                         FR.contract_payment,
                                         prof=prof.get(seq), amap=amap,
                                         acodes=O.ASSIST_CODES)
                        seq, batch, amap = f[0], [], {}
                    row = floor_row(f)
                    batch.append(row)
                    #: §8·25·2's precedent: a field `floor_row` does not carry
                    #: is read off the raw line, keyed by the period so that
                    #: no index has to be threaded through the finder.
                    if row[R_PERIOD] >= 0:
                        amap[row[R_PERIOD]] = (
                            f[O.P_ASSIST].strip()
                            if len(f) > O.P_ASSIST else "")
                if seq is not None:
                    noise_absorb(acc, batch, orig.get(seq), v, W,
                                 FR.contract_payment)
                    #: **The last loan of each vintage goes through here**,
                    #: and the first version of §8·34 passed `prof` only at
                    #: the key-change site — twenty-seven loans dropped from
                    #: the class census with nothing saying so.
                    omega_absorb(oacc, batch, orig.get(seq), v, pos, tab,
                                 CURVE_MAX_H, W, G, FR.contract_payment,
                                 prof=prof.get(seq), amap=amap,
                                 acodes=O.ASSIST_CODES)
        print(f"  {v}  done   clean loans {acc['clean_loans']:,}"
              f"   loops {oacc['b8like']['n']:,}", flush=True)

    #: **§8·20 must come back identical on this pass.** Same finder, same
    #: driver, same payment; a difference here would mean one of the three
    #: depends on something other than the rows, which is exactly what 規矩 19
    #: exists to catch.
    opl = omega_payload(oacc)
    print("\n  A00. §8·20 recomputed on this scan, against its own artifact")
    print_vs_prior(prior_json(ROOT, partial_name("b10_omega", only)), opl,
                   partial_name("b10_omega", only))

    pl = noise_payload(acc, oacc)
    #: The cross-check in `print_vin` reads the previous artifact, which was
    #: loaded **before** anything was written (`prior_json`'s own rule).
    NOISE_PRIOR["prior"] = ((prior or {}).get("coh", {})
                            .get("rows", {}).get(str(NOISE_LENS[0]), {}))
    print_vs_prior(prior, pl, partial_name("b10_noise", only))
    print_noise(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / partial_name("b10_noise", only)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "noise", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. B8-0b's floor on the "
             "second carrier: the same sum on never-delinquent windows, where "
             "k = 0 and the closed form is zero by construction. No triangle "
             "loop and no re-asking of §8·12: those are §8·22 and later.",
         "residual_from": "b8_omega.r_month with V's factor cancelled "
                          "(§8·21·8); no residual formula is written here",
         "payment_for_the_main_reading": "P_orig, the same one §8·20 "
                                         "published on (§8·21·3)",
         "window_to_k": "L = k + 1 (§8·21·4)",
         **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --loops. Registered before the code.
# B8's `b8_loops.find_loops` (§17), mapped column by column onto Freddie.
# **No omega and no residual**: that is §8·23. B8 split it here for a reason
# it states in its own census file — a window off by one row is invisible in a
# residual and obvious in a count.
# ---------------------------------------------------------------------------

#: §8·22·3. B8's field 42 reads only `Y`; Freddie's flag carries `Y` and `P`,
#: and this station's §3 has used both throughout. **Both cuts are run and
#: both are printed**; the main reading is `YP`, because otherwise this
#: section's loops and §3's triangles are not comparable.
LOOPS_MODSETS = (("YP", ("Y", "P")), ("Y", ("Y",)))

#: §8·22·9's buckets, **fixed before the run**. `gap == 1` means the row
#: before `t_A` is delinquent, that is, `t_A` is that delinquency's cure row.
#: `unreadable` is a real value and stands for election like any other; the
#: rule that bars a bucket from the contest applies to non-values ("the rest"),
#: not to a value that says the periods would not parse.
PRIOR_DEL_BUCKETS = ("<=0", "1", "2", "3", "4-6", "7-12", "13+", "never",
                     "unreadable")


def prior_del_bucket(gap):
    """`None` -> never, `"unreadable"` -> unreadable, else the month bucket.

    **`<=0` is a bucket, not an error.** The first version used `-1` as the
    unreadable sentinel and tested `gap < 0`, which quietly relabelled a
    genuinely out-of-order pair of periods as an unparseable one — two
    different things in one bucket, which §11 item 6 forbids. Periods do go
    out of order on this carrier: `gap_in_window` exists for that reason.
    """
    if gap is None:
        return "never"
    if gap == "unreadable":
        return "unreadable"
    if gap <= 0:
        return "<=0"
    if gap <= 3:
        return str(gap)
    if gap <= 6:
        return "4-6"
    if gap <= 12:
        return "7-12"
    return "13+"


#: The conditions in `find_loops`' own order and names. Order matters: the
#: marginal column is cumulative, so a different order is a different table.
LOOPS_TESTS = ("two_arms", "no_delinquency", "vertex_rem_blank",
               "vertex_upb_zero", "departure_is_first_row", "gap_in_window")

#: §8·22·2, transcribed from `results/b8_loops_census.md` §1.1: modification
#: onsets that field 63 contributes **alone**, as a share of that archive's
#: modification onsets. Freddie has no field 63 (§8·14·5), so its modification
#: arm is narrower by construction and this is how much, measured on the other
#: carrier. **Printed with every modification-arm count.**
B8_FIELD63_ONLY_SHARE = (0.032, 0.099, 0.112, 0.059, 0.055, 0.064)

#: `results/b8_loops_census.md` §1, transcribed 2026-08-20. Printed beside,
#: never subtracted (§7·9). (archive, onsets, candidates, loops, mod, defer,
#: t_M == t_B).
B8_LOOPS_CENSUS = (
    ("2002Q1", 7_267, 7_262, 6_457, 6_005, 452, 5_252),
    ("2006Q1", 14_586, 14_577, 14_194, 13_323, 871, 10_471),
    ("2007Q1", 18_958, 18_946, 18_414, 17_336, 1_078, 13_333),
    ("2012Q1", 7_967, 7_954, 7_794, 2_950, 4_844, 6_894),
    ("2017Q1", 19_988, 19_902, 19_262, 5_399, 13_863, 17_551),
    ("2019Q1", 19_816, 19_706, 19_187, 4_636, 14_551, 17_815),
)


def find_loops_rows(rows, mod_set):
    """`b8_loops.find_loops` on one loan. Returns `(loops, counts)`.

    Each loop is a dict carrying `t_A`, `t_M`, `t_B`, `arm`, `n_mod`,
    `n_defer`, and the six conditions as booleans **each evaluated on its own**
    so the caller can report `marginal` and `alone` (§8·22·5). Nothing is
    dropped here: the caller decides, and the census counts.
    """
    n = len(rows)
    c = {"left_truncated_mod": 0, "left_truncated_defer": 0,
         "unknown_status_rows": 0, "onsets_raw": 0, "onsets_mod": 0,
         "onsets_defer": 0, "drop_no_current_before": 0,
         "candidate_loops": 0}
    if n == 0:
        return [], c

    dq = [t[R_DELINQ] for t in rows]
    is_cur = [x == "00" for x in dq]
    is_del = [is_del_digits(x) for x in dq]
    #: Anything that is neither `00` nor a two-digit non-zero code. B8's 253 /
    #: 254 / 255 family, named rather than folded into either side.
    is_unk = [not a and not b for a, b in zip(is_cur, is_del)]
    c["unknown_status_rows"] = sum(is_unk)

    mod_on = [t[R_MODFLAG] in mod_set for t in rows]
    dfr_on = [t[R_DEFER] is not None and t[R_DEFER] > 0 for t in rows]
    #: A loan whose FIRST row already carries the state has no observable
    #: onset. **That is left truncation, not an absent event**, and merging
    #: the two is B8's pit 5 in another guise.
    if mod_on[0]:
        c["left_truncated_mod"] = 1
    if dfr_on[0]:
        c["left_truncated_defer"] = 1

    mod_edge = [False] + [mod_on[i] and not mod_on[i - 1] for i in range(1, n)]
    defer_edge = [False] + [dfr_on[i] and not dfr_on[i - 1]
                            for i in range(1, n)]
    onset = [a or b for a, b in zip(mod_edge, defer_edge)]
    idx = [i for i in range(n) if onset[i]]
    c["onsets_raw"] = len(idx)
    c["onsets_mod"] = sum(mod_edge)
    c["onsets_defer"] = sum(defer_edge)
    if not idx:
        return [], c

    #: `t_A` is the last current row **strictly before** the onset.
    last_cur, seen = [-1] * n, -1
    for i in range(n):
        last_cur[i] = seen
        if is_cur[i]:
            seen = i
    #: §8·22·9: the last **delinquent** row strictly before each row, so a
    #: candidate can be asked what happened before its own window opened.
    last_del, seend = [-1] * n, -1
    for i in range(n):
        last_del[i] = seend
        if is_del[i]:
            seend = i
    #: `t_B` is the first current row **at or after** `t_M`.
    first_cur, nxt = [-1] * n, -1
    for i in range(n - 1, -1, -1):
        if is_cur[i]:
            nxt = i
        first_cur[i] = nxt

    groups = {}
    for i in idx:
        a = last_cur[i]
        if a < 0:
            c["drop_no_current_before"] += 1
            continue
        g = groups.setdefault(a, {"t_M": i, "n_mod": 0, "n_defer": 0})
        g["t_M"] = min(g["t_M"], i)
        g["n_mod"] += 1 if mod_edge[i] else 0
        g["n_defer"] += 1 if defer_edge[i] else 0
    c["candidate_loops"] = len(groups)

    out = []
    for a, g in sorted(groups.items()):
        t_M = g["t_M"]
        t_B = first_cur[t_M]
        closed = t_B >= 0
        rec = {"t_A": a, "t_M": t_M, "t_B": t_B, "closed": closed,
               "n_mod": g["n_mod"], "n_defer": g["n_defer"],
               "arm": "mod" if g["n_mod"] > 0 else "defer",
               "n_onsets": g["n_mod"] + g["n_defer"],
               "period_M": rows[t_M][R_PERIOD],
               "last_period": rows[n - 1][R_PERIOD]}
        if not closed:
            out.append(rec)
            continue
        span = range(a + 1, t_B + 1)
        gap = False
        for i in range(a + 1, t_B + 1):
            pa = month_index_of(rows[i - 1][R_PERIOD])
            pb = month_index_of(rows[i][R_PERIOD])
            if pa < 0 or pb < 0 or pb - pa != 1:
                gap = True
                break
        rem_ok = (rows[a][R_REM] is not None and rows[t_B][R_REM] is not None)
        upb_ok = (rows[a][R_UPB] is not None and rows[a][R_UPB] > 0
                  and rows[t_B][R_UPB] is not None and rows[t_B][R_UPB] > 0)
        rec["ok"] = {
            "two_arms": not (g["n_mod"] > 0 and g["n_defer"] > 0),
            "no_delinquency": any(is_del[i] for i in span),
            "vertex_rem_blank": rem_ok,
            "vertex_upb_zero": upb_ok,
            "departure_is_first_row": a != 0,
            "gap_in_window": not gap,
        }
        #: §8·22·8. Carried on every closed candidate, read only on the ones
        #: `no_delinquency` refuses. **A window with no delinquent month is
        #: not the same object as a window whose states will not read**, and
        #: §11 item 6 forbids one bucket for the two.
        rec["win_cur"] = sum(1 for i in span if is_cur[i])
        rec["win_unk"] = sum(1 for i in span if is_unk[i])
        rec["gap_M"] = t_M - a
        #: §8·22·9. **Months, not rows**: the periods may have a gap, and
        #: counting rows would quietly turn a two-year hole into two months.
        j = last_del[a]
        if j < 0:
            rec["prior_del_gap"] = None
        else:
            ia = month_index_of(rows[a][R_PERIOD])
            ij = month_index_of(rows[j][R_PERIOD])
            rec["prior_del_gap"] = ((ia - ij) if (ia >= 0 and ij >= 0)
                                    else "unreadable")
        rec["win_len"] = t_B - a
        rec["empty_leg3"] = (t_M == t_B)
        out.append(rec)
    return out, c


def loops_new_acc() -> dict:
    def one():
        return {"loans": 0, "onsets_raw": 0, "onsets_mod": 0,
                "onsets_defer": 0, "drop_no_current_before": 0,
                "candidate_loops": 0, "left_truncated_mod": 0,
                "left_truncated_defer": 0, "unknown_status_rows": 0,
                "not_closed": 0, "closed_candidates": 0,
                "marginal": {g: 0 for g in LOOPS_TESTS},
                "alone": {g: 0 for g in LOOPS_TESTS},
                "loops": 0, "arm": {"mod": 0, "defer": 0},
                "empty_leg3": 0, "multi_onset": 0, "win_len": [],
                #: §8·22·8, on the `alone` set: every closed candidate that
                #: fails `no_delinquency`, whatever else it fails.
                "nd": {"n": 0, "gapM": {}, "empty3": 0, "both": 0,
                       "any_unk": 0, "rows_cur": 0, "rows_unk": 0,
                       "arm": {"mod": 0, "defer": 0},
                       #: §8·22·9, split by arm, on the refused set.
                       "prior": {"mod": {b: 0 for b in PRIOR_DEL_BUCKETS},
                                 "defer": {b: 0 for b in PRIOR_DEL_BUCKETS}}},
                #: §8·22·9's background table: the same buckets on the loops
                #: that survived. Delivered, never read.
                "kept_prior": {"mod": {b: 0 for b in PRIOR_DEL_BUCKETS},
                               "defer": {b: 0 for b in PRIOR_DEL_BUCKETS}},
                "by_vintage": {}, "by_onset_year": {},
                "nc_last_period": {}, "vintage_max_period": {}}
    return {name: one() for name, _ in LOOPS_MODSETS}


def loops_absorb(acc, rows, vintage) -> None:
    """One loan, both modification cuts (§8·22·3)."""
    for name, mset in LOOPS_MODSETS:
        a = acc[name]
        a["loans"] += 1
        found, c = find_loops_rows(rows, mset)
        for k in ("onsets_raw", "onsets_mod", "onsets_defer",
                  "drop_no_current_before", "candidate_loops",
                  "left_truncated_mod", "left_truncated_defer",
                  "unknown_status_rows"):
            a[k] += c[k]
        if rows:
            mp = month_index_of(rows[-1][R_PERIOD])
            if mp >= 0:
                a["vintage_max_period"][vintage] = max(
                    a["vintage_max_period"].get(vintage, -1), mp)
        for rec in found:
            if not rec["closed"]:
                a["not_closed"] += 1
                key = (vintage, rec["last_period"])
                a["nc_last_period"][key] = a["nc_last_period"].get(key, 0) + 1
                continue
            a["closed_candidates"] += 1
            #: **Two columns per reason** (§8·22·5). `alone` is what this
            #: condition removes by itself, on the closed candidates only;
            #: `marginal` is what it removes given every condition before it.
            #: A bare marginal cannot be read without its load.
            if not rec["ok"]["no_delinquency"]:
                nd = a["nd"]
                nd["n"] += 1
                nd["gapM"][rec["gap_M"]] = nd["gapM"].get(rec["gap_M"], 0) + 1
                nd["empty3"] += 1 if rec["empty_leg3"] else 0
                nd["both"] += 1 if (rec["empty_leg3"]
                                    and rec["gap_M"] == 1) else 0
                nd["any_unk"] += 1 if rec["win_unk"] else 0
                nd["rows_cur"] += rec["win_cur"]
                nd["rows_unk"] += rec["win_unk"]
                nd["arm"][rec["arm"]] += 1
                nd["prior"][rec["arm"]][
                    prior_del_bucket(rec["prior_del_gap"])] += 1
            passed = True
            for g in LOOPS_TESTS:
                if not rec["ok"][g]:
                    a["alone"][g] += 1
                    if passed:
                        a["marginal"][g] += 1
                        passed = False
            if not passed:
                continue
            a["loops"] += 1
            a["arm"][rec["arm"]] += 1
            a["kept_prior"][rec["arm"]][
                prior_del_bucket(rec["prior_del_gap"])] += 1
            a["empty_leg3"] += 1 if rec["empty_leg3"] else 0
            a["multi_onset"] += 1 if rec["n_onsets"] > 1 else 0
            a["win_len"].append(rec["win_len"])
            v = a["by_vintage"].setdefault(vintage,
                                           {"mod": 0, "defer": 0, "n": 0})
            v[rec["arm"]] += 1
            v["n"] += 1
            yr = rec["period_M"] // 100
            y = a["by_onset_year"].setdefault(yr, {"mod": 0, "defer": 0,
                                                   "n": 0})
            y[rec["arm"]] += 1
            y["n"] += 1


def _pearson(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((u - ma) * (v - mb) for u, v in zip(a, b))
    da = math.sqrt(sum((u - ma) ** 2 for u in a))
    db = math.sqrt(sum((v - mb) ** 2 for v in b))
    return (num / (da * db)) if da > 0 and db > 0 else None


def rank_corr(xs, ys, n_perm=NOISE_N_PERM, seed=NOISE_PERM_SEED):
    """Spearman, against a label-permutation null. **The same ruler again.**

    Returns None when there are fewer than three points or either side is
    constant: a correlation on two points is not a reading, and a constant has
    no rank order. Saying so beats returning a number.
    """
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    rx, ry = _ranks(xs), _ranks(ys)
    obs = _pearson(rx, ry)
    if obs is None:
        return None
    rng = random.Random(seed)
    null = []
    for _ in range(n_perm):
        sh = ry[:]
        rng.shuffle(sh)
        v = _pearson(rx, sh)
        if v is not None:
            null.append(v)
    null.sort()
    return {"rho": obs, "n": len(xs), "n_perm": len(null), "seed": seed,
            "null_p05": null[int(0.05 * (len(null) - 1))],
            "null_p95": null[int(0.95 * (len(null) - 1))],
            "null_min": null[0], "null_max": null[-1],
            "outside": bool(obs > null[-1] or obs < null[0])}


def loops_payload(acc) -> dict:
    out = {}
    for name, _mset in LOOPS_MODSETS:
        a = acc[name]
        vint = {str(v): dict(d) for v, d in sorted(a["by_vintage"].items())}
        for d in vint.values():
            d["defer_share"] = d["defer"] / d["n"] if d["n"] else None
        yrs = {str(y): dict(d) for y, d in sorted(a["by_onset_year"].items())}
        for d in yrs.values():
            d["defer_share"] = d["defer"] / d["n"] if d["n"] else None
        #: `not_closed` splits two ways and they are different objects: a loan
        #: still reporting at the end of the archive is **right censored**, one
        #: that stopped has terminated (B8's pit 13).
        rc = term = 0
        for (v, per), cnt in a["nc_last_period"].items():
            mx = a["vintage_max_period"].get(v)
            mi = month_index_of(per)
            if mx is not None and mi == mx:
                rc += cnt
            else:
                term += cnt
        xs = [int(v) for v in vint if vint[v]["defer_share"] is not None]
        ys = [vint[str(v)]["defer_share"] for v in xs]
        out[name] = {
            "loans": a["loans"], "onsets_raw": a["onsets_raw"],
            "onsets_mod": a["onsets_mod"], "onsets_defer": a["onsets_defer"],
            "drop_no_current_before": a["drop_no_current_before"],
            "candidate_loops": a["candidate_loops"],
            "left_truncated_mod": a["left_truncated_mod"],
            "left_truncated_defer": a["left_truncated_defer"],
            "unknown_status_rows": a["unknown_status_rows"],
            "not_closed": a["not_closed"],
            "right_censored": rc, "terminated": term,
            "closed_candidates": a["closed_candidates"],
            "marginal": dict(a["marginal"]), "alone": dict(a["alone"]),
            "marginal_total": sum(a["marginal"].values()),
            "loops": a["loops"], "arm": dict(a["arm"]),
            "defer_share": (a["arm"]["defer"] / a["loops"]
                            if a["loops"] else None),
            "empty_leg3": a["empty_leg3"], "multi_onset": a["multi_onset"],
            "win_len_q": _q(a["win_len"]),
            "kept_prior_del": {k: dict(v) for k, v
                               in a["kept_prior"].items()},
            "no_delinq_census": {
                "n": a["nd"]["n"], "empty_leg3": a["nd"]["empty3"],
                "gapM_eq1_and_empty_leg3": a["nd"]["both"],
                "windows_with_unknown_row": a["nd"]["any_unk"],
                "rows_current": a["nd"]["rows_cur"],
                "rows_unknown": a["nd"]["rows_unk"],
                "arm": dict(a["nd"]["arm"]),
                "gapM_hist": {str(k): v for k, v in
                              sorted(a["nd"]["gapM"].items(),
                                     key=lambda kv: -kv[1])[:12]},
                "gapM_q": _q(sum(([k] * v for k, v
                                  in a["nd"]["gapM"].items()), [])),
                "share_both": (a["nd"]["both"] / a["nd"]["n"]
                               if a["nd"]["n"] else None),
                "prior_del": {k: dict(v) for k, v
                              in a["nd"]["prior"].items()},
                "prior_del_mode": {
                    k: (max(v, key=v.get) if sum(v.values()) else None)
                    for k, v in a["nd"]["prior"].items()},
                "top_gapM": (max(a["nd"]["gapM"], key=a["nd"]["gapM"].get)
                             if a["nd"]["gapM"] else None)},
            "by_vintage": vint, "by_onset_year": yrs,
            "rho_vintage_defer_share": rank_corr(xs, ys),
        }
    return {"cuts": out,
            "fannie_census": [list(r) for r in B8_LOOPS_CENSUS],
            "fannie_field63_only_share": list(B8_FIELD63_ONLY_SHARE),
            "published_s3_triangles": {str(v): p[4] for v, p
                                       in sorted(PUBLISHED_S3.items())}}


def print_loops(pl) -> None:
    main = pl["cuts"]["YP"]
    print("\n  A. loops found, both modification cuts (§8·22·3)")
    print(f"     {'cut':<5}{'loans':>10}{'onsets':>9}{'candidates':>12}"
          f"{'not closed':>11}{'**loops**':>11}{'mod':>9}{'defer':>9}"
          f"{'defer share':>13}")
    for name, _m in LOOPS_MODSETS:
        d = pl["cuts"][name]
        ds = d["defer_share"]
        print(f"     {name:<5}{d['loans']:>10,}{d['onsets_raw']:>9,}"
              f"{d['candidate_loops']:>12,}{d['not_closed']:>11,}"
              f"{d['loops']:>11,}{d['arm']['mod']:>9,}"
              f"{d['arm']['defer']:>9,}"
              f"{('%.4f' % ds) if ds is not None else 'n/a':>13}")
    print("     The main reading is `YP`, because §3 has used both values")
    print("     throughout and otherwise these loops and §3's triangles are")
    print("     not comparable. `Y` is here for comparability with Fannie.")
    yp, yy = pl["cuts"]["YP"]["onsets_mod"], pl["cuts"]["Y"]["onsets_mod"]
    print(f"     **Neither cut dominates.** modification onsets:"
          f" YP {yp:,}, Y {yy:,}.")
    print("     An onset is a **rising edge**, so a flag that alternates")
    print("     `P, Y, P, Y` is continuously on under the wider set and")
    print("     switches every row under the narrower one. The wider value")
    print("     set is not the wider population, and assuming it is was a")
    print("     defect in this file's own selftest until 2026-08-20.")

    print("\n  A2. §8·22·2: what Freddie's modification arm cannot see")
    lo = min(B8_FIELD63_ONLY_SHARE)
    hi = max(B8_FIELD63_ONLY_SHARE)
    print(f"     B8's modification onset is field 42 **or** field 63,")
    print(f"     whichever comes first. Freddie has no field 63 (§8·14·5), so")
    print(f"     its modification arm is narrower **by construction**. On")
    print(f"     Fannie the onsets field 63 contributes alone are")
    print(f"     {lo:.1%} to {hi:.1%} of that archive's modification onsets.")
    print(f"     Freddie's {main['arm']['mod']:,} modification loops carry")
    print(f"     that caveat wherever they are quoted.")

    print("\n  B. the census, in b8_loops' own names (cut YP)")
    for k in ("loans", "unknown_status_rows", "left_truncated_mod",
              "left_truncated_defer", "onsets_raw", "onsets_mod",
              "onsets_defer", "drop_no_current_before", "candidate_loops",
              "not_closed", "right_censored", "terminated",
              "closed_candidates", "loops", "empty_leg3", "multi_onset"):
        print(f"       {k:<28} {main[k]:>12,}")
    print(f"       {'window length p10/p50/p90':<28} "
          f"{main['win_len_q'][0]:>4.0f} /{main['win_len_q'][1]:>4.0f} /"
          f"{main['win_len_q'][2]:>4.0f}")
    tot = main["not_closed"] + main["marginal_total"] + main["loops"]
    print(f"       {'not closed + dropped + loops':<28} {tot:>12,}"
          f"   against candidates {main['candidate_loops']:,}"
          f"   {'MATCH' if tot == main['candidate_loops'] else 'DO NOT ADD UP'}")
    print(f"       right censored + terminated = "
          f"{main['right_censored'] + main['terminated']:,}"
          f" against not closed {main['not_closed']:,}"
          f"   {'MATCH' if main['right_censored'] + main['terminated'] == main['not_closed'] else 'NO'}")
    print("     `empty_leg3` is §17.3: the flag turns on and the row already")
    print("     reads `00`, so leg 3 is empty **by construction**. Those loops")
    print("     must not be pooled into any omega_3 reading (§8·23's problem,")
    print("     flagged here because the count belongs with the window).")

    print("\n  C. §8·22·5: every candidate's exit, two columns per reason")
    print(f"     {'condition':<26}{'marginal':>10}{'alone':>10}")
    print(f"     {'not_closed (precondition)':<26}"
          f"{main['not_closed']:>10,}{main['not_closed']:>10,}")
    for g in LOOPS_TESTS:
        print(f"     {g:<26}{main['marginal'][g]:>10,}{main['alone'][g]:>10,}")
    print("     `alone` for every interior condition is computed on the")
    print("     **closed** candidates only: with no t_B the window does not")
    print("     exist and an interior test applied to it fails for a reason")
    print("     that is not its own. B8 found that by reading its own table.")

    nd = main["no_delinq_census"]
    print("\n  C2. §8·22·8: what the no_delinquency refusals are")
    print(f"     the `alone` set: {nd['n']:,} closed candidates fail this")
    print(f"     condition, against {main['marginal']['no_delinquency']:,}")
    print(f"     removed by it in order. arm: mod {nd['arm']['mod']:,},"
          f" defer {nd['arm']['defer']:,}")
    print(f"     t_M == t_B on {nd['empty_leg3']:,}"
          f"   t_M - t_A == 1 AND t_M == t_B on {nd['gapM_eq1_and_empty_leg3']:,}"
          + (f" = {nd['share_both']:.4f}" if nd["share_both"] is not None
             else ""))
    print(f"     t_M - t_A  p10/p50/p90 {nd['gapM_q'][0]:.0f} /"
          f" {nd['gapM_q'][1]:.0f} / {nd['gapM_q'][2]:.0f}"
          f"   top value {nd['top_gapM']}")
    print(f"     histogram: " + ", ".join(f"{k}:{v:,}" for k, v
                                          in nd["gapM_hist"].items()))
    print(f"     rows inside those windows: current {nd['rows_current']:,},"
          f"   **unreadable state {nd['rows_unknown']:,}**"
          f"   windows carrying one {nd['windows_with_unknown_row']:,}")
    print("\n     Read, per the criteria fixed before the run, one variable, three branches")
    if nd["n"] == 0:
        print("     NO REFERENT: the condition refused nothing. Not read.")
    elif nd["windows_with_unknown_row"] > 0:
        print("     §8·22·8 -> SECOND BRANCH. **Not `all current`**:")
        print(f"     {nd['windows_with_unknown_row']:,} of these windows carry")
        print(f"     a row whose state will not read ({nd['rows_unknown']:,}")
        print("     rows in all). A window whose states are unreadable is a")
        print("     different object from one with no delinquency, and §11")
        print("     item 6 forbids one bucket for the two. Set out on its own")
        print("     line, never folded into the first branch.")
    elif nd["top_gapM"] == 1 and nd["gapM_eq1_and_empty_leg3"] * 2 > nd["n"]:
        print("     §8·22·8 -> FIRST BRANCH. The mechanism holds: the flag is")
        print("     recorded on a **current** row whose predecessor is also")
        print(f"     current, so the window is that one row. {nd['share_both']:.1%}")
        print("     of the refusals are exactly that, and no window carries an")
        print("     unreadable state. **That is this carrier's bookkeeping")
        print("     habit, not a missing delinquency.**")
    else:
        print("     §8·22·8 -> THIRD BRANCH, mixed (R01). `t_M - t_A` does not")
        print(f"     concentrate at 1 (top value {nd['top_gapM']}, and the")
        print(f"     joint case is {nd['gapM_eq1_and_empty_leg3']:,} of")
        print(f"     {nd['n']:,}). The mechanism does not hold; something else")
        print("     is here. Not reinterpreted after the fact.")
    print("\n  C3. §8·22·9: did those loans go delinquent BEFORE t_A")
    print("      months from the last delinquent row to t_A. `1` means the")
    print("      row before t_A is delinquent, so t_A is that cure.")
    print(f"     {'set':<22}" + "".join(f"{b:>9}" for b in
                                        PRIOR_DEL_BUCKETS) + f"{'mode':>10}")
    for arm in ("mod", "defer"):
        d = nd["prior_del"][arm]
        print(f"     {'refused, ' + arm:<22}"
              + "".join(f"{d[b]:>9,}" for b in PRIOR_DEL_BUCKETS)
              + f"{str(nd['prior_del_mode'][arm]):>10}")
    for arm in ("mod", "defer"):
        d = main["kept_prior_del"][arm]
        print(f"     {'kept loops, ' + arm:<22}"
              + "".join(f"{d[b]:>9,}" for b in PRIOR_DEL_BUCKETS)
              + f"{'':>10}")
    print("     The `kept loops` rows are **delivered, never read** (fixed")
    print("     before the run): those windows carry a delinquency by definition, so")
    print("     this says what was outside the window, which is background.")

    print("\n     Read, per the criteria fixed before the run, one variable, three branches")
    mo = nd["prior_del_mode"]["mod"]
    if mo is None:
        print("     NO REFERENT: no modification-arm candidate was refused.")
    elif mo in ("1", "2", "3"):
        tot = sum(nd["prior_del"]["mod"].values())
        near = sum(nd["prior_del"]["mod"][b] for b in ("1", "2", "3"))
        print(f"     §8·22·9 -> FIRST BRANCH. The modal bucket is `{mo}`:")
        print(f"     the flag is written up within a quarter of the cure")
        print(f"     ({near:,} of {tot:,} inside three months). **The same")
        print("     event as Fannie's, recorded at a different moment.**")
        print("     §8·23's modification arm may be quoted, and must carry")
        print("     this caveat wherever it is.")
    elif mo == "never":
        print("     §8·22·9 -> SECOND BRANCH. The modal bucket is `never`:")
        print("     these are current loans re-contracted without any prior")
        print("     delinquency at all. **A different class of event from")
        print("     Fannie's modification arm**, and §8·23's modification arm")
        print("     must not be set in one sentence with the other carrier's.")
    else:
        print("     §8·22·9 -> THIRD BRANCH, mixed (R01). The modal bucket is")
        print(f"     `{mo}`: neither hard on the heels of a cure nor never")
        print("     delinquent. Something else is here, and it is not")
        print("     reinterpreted after the fact.")
    print("     The buckets were fixed before the run and `unreadable` stands")
    print("     for election like any other value: if it wins, that is news")
    print("     about the instrument, not a bucket to exclude.")

    print("     **The condition is not relaxed.** B8's rule is `at least one")
    print("     delinquent month in the window` and this file copies it; a")
    print("     rule is not widened to keep a sample (§8·22·8 item 2).")

    print("\n  D. §8·22·4: against §3's published triangles. **A comparison,")
    print("     not a gate** — three things differ (§3 requires the")
    print("     modification after the first delinquency; §3 has no deferral")
    print("     arm; this section adds five conditions).")
    pub = pl["published_s3_triangles"]
    got = {v: d["mod"] for v, d in main["by_vintage"].items()}
    shared = sorted(set(pub) & set(got), key=int)
    bad = [v for v in shared if got[v] > pub[v]]
    print(f"     {'vintage':<9}{'mod loops':>11}{'§3 triangles':>14}"
          f"{'<=':>5}")
    for v in shared[:10]:
        print(f"     {v:<9}{got[v]:>11,}{pub[v]:>14,}"
              f"{('yes' if got[v] <= pub[v] else 'NO'):>5}")
    if len(shared) > 10:
        print(f"     ... {len(shared) - 10} more in the record file")
    print(f"     the registered relation is `mod loops <= §3 triangles`:")
    print(f"     holds on {len(shared) - len(bad)}/{len(shared)} vintages"
          + (f".  **{len(bad)} do not, and that is news**: "
             f"{', '.join(bad[:8])}" if bad else "."))

    print("\n  E. Fannie's census beside it (results/b8_loops_census.md §1)")
    print(f"     {'archive':<9}{'onsets':>9}{'cand':>9}{'loops':>9}"
          f"{'mod':>9}{'defer':>9}{'tM==tB':>9}{'defer share':>13}")
    for a, on, ca, lp, md, df, tb in B8_LOOPS_CENSUS:
        print(f"     {a:<9}{on:>9,}{ca:>9,}{lp:>9,}{md:>9,}{df:>9,}"
              f"{tb:>9,}{df / lp:>13.4f}")
    print("     **Beside, not subtracted** (§7·9).")

    print("\n  F. Read, per the criteria fixed before the run, one variable, three branches")
    r = main["rho_vintage_defer_share"]
    if r is None:
        print("     NO REFERENT: fewer than three vintages carry a defer")
        print("     share, or it is constant. Not read.")
    else:
        print(f"     Spearman(vintage, defer share) = {r['rho']:+.4f}"
              f"   on {r['n']} vintages")
        print(f"     null [{r['null_min']:+.4f}, {r['null_p05']:+.4f},"
              f" {r['null_p95']:+.4f}, {r['null_max']:+.4f}]"
              f"   {r['n_perm']} permutations, seed {r['seed']}")
        if not r["outside"]:
            print("     §8·22·6 -> SECOND BRANCH. No monotone drift in the arm")
            print("     mix across vintages.")
        elif r["rho"] > 0:
            print("     §8·22·6 -> FIRST BRANCH. Same direction as Fannie: the")
            print("     later the vintage, the heavier the deferral arm.")
            print("     Fannie's six run 7.0% -> 75.8% across 2002Q1..2019Q1.")
        else:
            print("     §8·22·6 -> THIRD BRANCH. The drift runs the **other**")
            print("     way from Fannie's. Nobody predicted this. Set out on")
            print("     its own line, not folded into the second branch.")
    print("     **The limitation registered before the run**: a vintage is an")
    print("     origination year and a deferral happens in calendar time, so")
    print("     this correlation mixes cohort with calendar. **Fannie's mixes")
    print("     the same two**, which is why the comparison is fair; it is")
    print("     **not** evidence that later-originated loans defer more.")

    print("\n  G. the arm mix by ONSET calendar year (§8·22·6's separation)")
    print("     **A deliverable, not a reading.**")
    print(f"     {'year':<7}{'loops':>9}{'mod':>9}{'defer':>9}"
          f"{'defer share':>13}")
    for y, d in sorted(main["by_onset_year"].items(), key=lambda kv: kv[0]):
        if d["n"] < 50:
            continue
        print(f"     {y:<7}{d['n']:>9,}{d['mod']:>9,}{d['defer']:>9,}"
              f"{d['defer_share']:>13.4f}")
    print("     years with fewer than 50 loops are omitted from this print")
    print("     and are all in the record file (§3·4: the thin cells exist).")

    print("\n  H. What this section does NOT deliver (§8·22·7)")
    print("     **No omega and no residual.** B8 split its own block here for")
    print("     the reason it states: a window off by one row is invisible in")
    print("     a residual and obvious in a count. §8·23 is the residual.")
    print("     §8·12 is not re-asked; that needs §8·23.")


def cmd_loops(only) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    if not vs:
        print(f"  no archives under {RAW}")
        return 1
    prior = prior_json(ROOT, partial_name("b10_loops", only))
    print("§8·22: the triangle loop windows. **No omega** (§8·22·7).\n"
          "  b8_loops.find_loops mapped column by column; field 63 has no\n"
          "  Freddie counterpart and how much that costs is printed.\n")
    acc = loops_new_acc()
    for v in vs:
        with zipfile.ZipFile(archive(v)) as zf:
            with zf.open(f"sample_perf_{v}.txt") as raw:
                seq, batch = None, []
                for line in io.TextIOWrapper(raw, encoding="utf-8",
                                             newline=""):
                    if not line.strip():
                        continue
                    f = line.split("|")
                    if f[0] != seq:
                        if seq is not None:
                            loops_absorb(acc, batch, v)
                        seq, batch = f[0], []
                    batch.append(floor_row(f))
                if seq is not None:
                    loops_absorb(acc, batch, v)
        print(f"  {v}  done   loops {acc['YP']['loops']:,}", flush=True)
    pl = loops_payload(acc)
    print_vs_prior(prior, pl, partial_name("b10_loops", only))
    print_loops(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / partial_name("b10_loops", only)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "loops", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. The loop windows "
             "only, no omega and no residual: B8 splits its own block here "
             "because a window off by one row is invisible in a residual and "
             "obvious in a count.",
         "modification_onset": "the flag alone; field 63 has no Freddie "
                               "counterpart (§8·14·5, §8·22·2)",
         "deferral_onset": "column 12 positive (§8·14·5, §8·18)",
         **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --legs. Registered before the code.
# B8's block two (`b8_loop_omega.py`): omega on the loop windows, split into
# the three legs. **Read against no floor** — that is §8·24, and B8 draws the
# same line in its own file.
# ---------------------------------------------------------------------------

#: §8·23·0's two payment schemes. `sub` is the main reading: `orig` cannot
#: know about the modification, so on leg 3 it is wrong by construction.
LEG_SCHEMES = ("sub", "orig")

LEG_SAMPLE_CAP = 200_000


def loop_payments(rows, rec, orig, contract_payment):
    """§8·23·0. `{scheme: (P_before_t_M, P_after_t_M)}`.

    The contract period's boundary **is** `t_M`, so a triangle's window
    straddles one. `carry_forward` wants the payment of row `t-1`'s period,
    which is the pre-modification one up to and including `t_M` and the
    post-modification one after it.

    `orig` returns the same value on both sides on purpose: it is the
    origination payment and it cannot know a modification happened. **That is
    its defect and it is printed, not hidden.**
    """
    P_o = None
    if orig is not None:
        u0, rate0, term = orig
        cand = contract_payment(u0, rate0 / 1200.0, term)
        if cand == cand and cand > 0:
            P_o = cand
    #: §8·23·0·1. **The rear anchor is `t_B`, not `t_M`.** `t_M` is usually a
    #: delinquent month, and during a delinquency the balance is frozen while
    #: `rem` keeps falling, so `contract_payment(frozen, i, falling)` changes
    #: every month and is nobody's contract payment. `t_A` and `t_B` are both
    #: **current** rows by definition, which is the premise §12.2's
    #: substitution needs. Reading `t_B` is a look-back, and what it reads is
    #: a contract parameter rather than an outcome — the same ground
    #: `noise_anchor` stands on.
    return {"orig": (P_o, P_o),
            "sub": (substitution_payment(rows[rec["t_A"]], contract_payment),
                    substitution_payment(rows[rec["t_B"]], contract_payment))}


def loop_omega(rows, rec, pays, pos, tab, max_h, r_month):
    """One loop, one payment scheme. `(status, payload)`.

    `status` is `"ok"` or the gate that stopped it; on a gate the payload says
    whether the month sat **before or after `t_M`**, which §17.10 requires
    counted apart because the two arms have different contract-period
    structure.
    """
    t_A, t_M, t_B = rec["t_A"], rec["t_M"], rec["t_B"]
    P_pre, P_post = pays
    if P_pre is None or P_post is None:
        return "no payment for the window", {"before": P_pre is None}
    rs = []
    for t in range(t_A + 1, t_B + 1):
        P = P_pre if t <= t_M else P_post
        gate, _sub, r = pair_residual(rows[t - 1], rows[t], P, pos, tab,
                                      max_h, r_month)
        if gate is None and (r != r or r in (float("inf"), float("-inf"))):
            gate = RESID_DEFECT
        if gate is not None:
            return gate, {"before": t <= t_M}
        rs.append(r)

    #: `rs[j]` is the residual at row `t_A + 1 + j`, so `t_M` sits at `i_M`.
    #: §17: leg 1 is `(t_A, t_M)`, leg 2 is the single month `t_M`, leg 3 is
    #: `(t_M, t_B]`.
    i_M = t_M - t_A - 1
    leg1, leg2, leg3 = sum(rs[:i_M]), rs[i_M], sum(rs[i_M + 1:])

    #: §8·24·5. **Nothing before `t_M` knows a modification is coming**, so
    #: leg 1 on the modification arm is the same object the clean-cure arm
    #: carries, and it has the same closed form: `n1` copies of one flat
    #: delinquent month. Written through `r_month` with the arguments arranged
    #: so `V`'s factor cancels (§8·21·8), so **no residual formula is written
    #: here either**.
    bA = rows[t_A][R_UPB] - rows[t_A][R_DEFER]
    note_A = rows[t_A][R_RATE]
    l1c = None
    if bA is not None and bA > 0 and note_A is not None and note_A > 0:
        one = float(r_month(bA, bA, note_A, P_pre, NOISE_N, NOISE_DISC,
                            zib_now=0.0, zib_prev=0.0, balloon_n=NOISE_N,
                            note_prev=note_A, n_prev=NOISE_N,
                            balloon_n_prev=NOISE_N))
        if one == one and one not in (float("inf"), float("-inf")):
            l1c = i_M * one
    #: `eff` is B8's diagnostic: **how many months the data actually behaved
    #: like a flat delinquent run**. `eff == n1` is flat; a whole number below
    #: `n1` means specific months are not; a fraction means the balance moved.
    eff = (i_M * leg1 / l1c) if (l1c not in (None, 0.0) and i_M) else None
    return "ok", {"omega": sum(rs), "leg1": leg1, "leg2": leg2, "leg3": leg3,
                  "n1": i_M, "n2": 1, "n3": t_B - t_M, "n_win": t_B - t_A,
                  "P_pre": P_pre, "P_post": P_post,
                  "l1_closed": l1c, "eff": eff,
                  "omega_net": (sum(rs) - l1c) if l1c is not None
                  else sum(rs)}


def legs_new_acc() -> dict:
    def scheme():
        return {"n": 0, "ok": 0, "drop": {}, "miss_before": 0,
                "miss_after": 0, "identity_bad": 0, "empty3_nonzero": 0,
                "omega": [], "leg1": [], "leg2": [], "leg3": [],
                "share": {"leg1": [], "leg2": [], "leg3": []},
                "share3": {"leg1": [], "leg2": [], "leg3": []},
                "n3_zero": 0, "all3": 0, "by_arm": {}, "capped": False,
                "p_reldiff": [],
                #: §8·24. **Accumulator only**: `legs_payload` does not emit
                #: these, so `b10_legs.json` stays byte for byte what it was
                #: (規矩 19). The signal station reads them in memory.
                "sig": {"omega": [], "omega_net": [], "l1c": [], "eff": [],
                        "n1": [], "l1_exact_in": [], "by_arm": {}}}
    return {"loans": 0, "loops": 0, "arm": {"mod": 0, "defer": 0},
            "schemes": {k: scheme() for k in LEG_SCHEMES}}


def legs_absorb(acc, rows, orig, pos, tab, max_h, r_month,
                contract_payment) -> None:
    """One loan. Every closed loop that passed §8·22's six conditions."""
    acc["loans"] += 1
    found, _c = find_loops_rows(rows, ("Y", "P"))
    for rec in found:
        if not rec["closed"] or not all(rec["ok"].values()):
            continue
        acc["loops"] += 1
        acc["arm"][rec["arm"]] += 1
        pays = loop_payments(rows, rec, orig, contract_payment)
        for name in LEG_SCHEMES:
            sc = acc["schemes"][name]
            sc["n"] += 1
            pp = pays[name]
            if (name == "sub" and pp[0] is not None and pp[1] is not None
                    and pp[0] > 0):
                sc["p_reldiff"].append(abs(pp[1] - pp[0]) / pp[0])
            status, m = loop_omega(rows, rec, pp, pos, tab, max_h, r_month)
            if status != "ok":
                sc["drop"][status] = sc["drop"].get(status, 0) + 1
                if m.get("before"):
                    sc["miss_before"] += 1
                else:
                    sc["miss_after"] += 1
                continue
            sc["ok"] += 1
            #: §8·23·1 item 1. **This is vacuous** and B8 says so: the four
            #: quantities come from one list sliced three ways, so they
            #: telescope whatever `t_M` is. Kept because it still catches a
            #: broken range helper, and printed **with its vacuity stated**.
            if (m["n1"] + m["n2"] + m["n3"] != m["n_win"]
                    or abs(m["leg1"] + m["leg2"] + m["leg3"] - m["omega"])
                    > 1e-9):
                sc["identity_bad"] += 1
            #: §8·23·1 item 2. **This one is not vacuous.** `t_M == t_B` on
            #: 87.2 per cent of loops, and their leg 3 spans no months, so it
            #: must be exactly zero. A range helper off by one row shows up
            #: here and nowhere else.
            if m["n3"] == 0:
                sc["n3_zero"] += 1
                if m["leg3"] != 0.0:
                    sc["empty3_nonzero"] += 1
            else:
                sc["all3"] += 1
            if len(sc["omega"]) < LEG_SAMPLE_CAP:
                sc["omega"].append(m["omega"])
                sc["leg1"].append(m["leg1"])
                sc["leg2"].append(m["leg2"])
                sc["leg3"].append(m["leg3"])
            else:
                sc["capped"] = True
            aw = abs(m["omega"])
            if aw > 0:
                for g in ("leg1", "leg2", "leg3"):
                    sc["share"][g].append(abs(m[g]) / aw)
                    if m["n3"] > 0:
                        sc["share3"][g].append(abs(m[g]) / aw)
            b = sc["by_arm"].setdefault(rec["arm"], {"n": 0, "omega": []})
            b["n"] += 1
            if len(b["omega"]) < LEG_SAMPLE_CAP:
                b["omega"].append(m["omega"])
            sg = sc["sig"]
            if len(sg["omega"]) < LEG_SAMPLE_CAP:
                sg["omega"].append(m["omega"])
                sg["omega_net"].append(m["omega_net"])
                sg["n1"].append(m["n1"])
                sg["l1c"].append(m["l1_closed"])
                sg["eff"].append(m["eff"])
                if m["l1_closed"] is not None:
                    sg["l1_exact_in"].append(abs(m["leg1"] - m["l1_closed"]))
                sa = sg["by_arm"].setdefault(rec["arm"],
                                             {"omega": [], "omega_net": []})
                sa["omega"].append(m["omega"])
                sa["omega_net"].append(m["omega_net"])


def legs_payload(acc) -> dict:
    out = {}
    for name in LEG_SCHEMES:
        sc = acc["schemes"][name]
        med = {g: (_q(sc["share"][g], (50,))[0] if sc["share"][g] else None)
               for g in ("leg1", "leg2", "leg3")}
        med3 = {g: (_q(sc["share3"][g], (50,))[0] if sc["share3"][g] else None)
                for g in ("leg1", "leg2", "leg3")}
        live = {g: v for g, v in med3.items() if v is not None}
        out[name] = {
            "n": sc["n"], "ok": sc["ok"],
            "drop": dict(sc["drop"]), "drop_total": sum(sc["drop"].values()),
            "miss_before": sc["miss_before"], "miss_after": sc["miss_after"],
            "identity_bad": sc["identity_bad"],
            "n3_zero": sc["n3_zero"], "all3": sc["all3"],
            "empty3_nonzero": sc["empty3_nonzero"],
            "q_omega": _q(sc["omega"]),
            "q_absomega": _q([abs(x) for x in sc["omega"]]),
            "q_leg1": _q(sc["leg1"]), "q_leg2": _q(sc["leg2"]),
            "q_leg3": _q(sc["leg3"]),
            "share_med_all": med, "share_med_all3": med3,
            "dominant_leg": (max(live, key=live.get) if live else None),
            "by_arm": {k: {"n": v["n"], "q": _q(v["omega"]),
                           "absmed": (_q([abs(x) for x in v["omega"]],
                                         (50,))[0] if v["omega"] else None)}
                       for k, v in sorted(sc["by_arm"].items())},
            "q_p_reldiff": (_q(sc["p_reldiff"], (10, 50, 90, 99))
                            if sc["p_reldiff"] else None),
            "p_reldiff_tiny": sum(1 for x in sc["p_reldiff"] if x < 1e-6),
            "p_reldiff_n": len(sc["p_reldiff"]),
            "sampled": len(sc["omega"]), "capped": sc["capped"]}
    return {"loans": acc["loans"], "loops": acc["loops"],
            "arm": dict(acc["arm"]), "schemes": out}


def print_legs(pl) -> None:
    main = pl["schemes"]["sub"]
    print("\n  A. coverage. §17.10: one unreadable month drops the whole loop,")
    print("     and the drop is counted apart before and after t_M.")
    print(f"     loans {pl['loans']:,}   loops {pl['loops']:,}"
          f"   mod {pl['arm']['mod']:,}   defer {pl['arm']['defer']:,}")
    for name in LEG_SCHEMES:
        d = pl["schemes"][name]
        print(f"     --- scheme `{name}` ---   loops {d['n']:,}"
              f"   **measurable {d['ok']:,}**"
              f"   dropped {d['drop_total']:,}"
              f"   before t_M {d['miss_before']:,}"
              f"   after {d['miss_after']:,}")
        for g, v in sorted(d["drop"].items(), key=lambda kv: -kv[1]):
            print(f"       {g:<58} {v:>8,}")
        tot = d["ok"] + d["drop_total"]
        print(f"       {'measurable + dropped':<58} {tot:>8,}"
              f"   {'MATCH' if tot == d['n'] else 'DO NOT ADD UP'}")

    print("\n  B. §8·23·1's three consistency checks")
    print(f"     1. legs telescope to omega: {main['identity_bad']:,} bad")
    print("        **This check is vacuous and B8 says so**: the four")
    print("        quantities come from one list sliced three ways, so they")
    print("        telescope whatever t_M is — including a t_M off by ten")
    print("        rows. Kept because it still catches a broken range helper,")
    print("        and printed with its vacuity stated rather than counted as")
    print("        evidence.")
    print(f"     2. empty leg 3 is exactly zero: {main['n3_zero']:,} loops have")
    print(f"        n3 == 0, of which {main['empty3_nonzero']:,} carry a")
    print("        non-zero leg 3. **This one is not vacuous**: a range helper")
    print("        off by one row shows up here and nowhere else.")
    print("     3. a null modification reproduces the clean-cure closed form:")
    print("        in the selftest, on constructed data (§8·23·1 item 3).")

    print("\n  C. §8·23·0: the two payments, and how far apart they are")
    if main["q_p_reldiff"]:
        q = main["q_p_reldiff"]
        print(f"     |P_after - P_before| / P_before, scheme `sub`,"
              f" {main['p_reldiff_n']:,} loops")
        print(f"       p10 {q[0]:.3e}  p50 {q[1]:.3e}  p90 {q[2]:.3e}"
              f"  p99 {q[3]:.3e}")
        print(f"       under 1e-6 (the modification did not move the payment):"
              f" {main['p_reldiff_tiny']:,}"
              f" = {main['p_reldiff_tiny'] / main['p_reldiff_n']:.4f}")
        print("     `orig` cannot move at t_M by construction: it is the")
        print("     origination payment and knows nothing of a modification.")
        print("     The rear anchor is **t_B, not t_M** (§8·23·0·1): t_M is")
        print("     usually delinquent, and during a delinquency the balance")
        print("     is frozen while rem keeps falling, so the substitution")
        print("     there is nobody's contract payment. t_A and t_B are both")
        print("     current rows by definition.")
        print("     **That is why `sub` is the main reading here**, the")
        print("     opposite choice from §8·21·3 and for the opposite reason:")
        print("     there no published triangle omega existed to match.")

    print("\n  D. omega and the three legs (scheme `sub`)")
    print(f"     {'':<8}{'p10':>14}{'p50':>14}{'p90':>14}")
    for g, k in (("omega", "q_omega"), ("leg1", "q_leg1"),
                 ("leg2", "q_leg2"), ("leg3", "q_leg3")):
        v = main[k]
        print(f"     {g:<8}{v[0]:>+14.4e}{v[1]:>+14.4e}{v[2]:>+14.4e}")
    print(f"     |omega|  p10 {main['q_absomega'][0]:.4e}"
          f"   p50 {main['q_absomega'][1]:.4e}"
          f"   p90 {main['q_absomega'][2]:.4e}")
    print(f"     sampled {main['sampled']:,}   capped {main['capped']}")
    print("     by arm:")
    for arm, d in main["by_arm"].items():
        print(f"       {arm:<8} n {d['n']:>8,}   omega p50 {d['q'][1]:+.4e}"
              f"   median |omega| "
              f"{('%.4e' % d['absmed']) if d['absmed'] is not None else 'n/a'}")

    print("\n  E. Read, per the criteria fixed before the run, coverage, three branches")
    outcomes = {"measurable": main["ok"], **main["drop"]}
    if not sum(outcomes.values()):
        print("     NO REFERENT: no loop reached this stage.")
    else:
        mode = max(outcomes, key=outcomes.get)
        if mode == "measurable":
            print(f"     §8·23·2 -> FIRST BRANCH. The modal outcome is")
            print(f"     `measurable`, {main['ok']:,} of {main['n']:,}. The")
            print("     assembly stands; the distribution goes to §8·24.")
        elif mode == RESID_DEFECT:
            print("     §8·23·2 -> THIRD BRANCH. The modal outcome is a")
            print("     **defect, not a filter** (row_residuals' own words).")
            print("     Nothing about the distribution is discussed until it")
            print("     is understood.")
        else:
            print(f"     §8·23·2 -> SECOND BRANCH. The modal outcome is a")
            print(f"     gate: `{mode}`, {outcomes[mode]:,} of {main['n']:,}.")
            print("     The distribution is still delivered and carries this")
            print("     line wherever it is quoted.")

    print("\n  F. Read, per the criteria fixed before the run, which leg dominates")
    print("     **On the loops with all three legs non-empty**"
          f" ({main['all3']:,});")
    print(f"     the {main['n3_zero']:,} with an empty leg 3 are set aside")
    print("     whole (§17.3), never pooled into an omega_3 reading.")
    print(f"     {'':<8}{'median share of |omega|, all3':>32}"
          f"{'all loops':>14}")
    for g in ("leg1", "leg2", "leg3"):
        a3 = main["share_med_all3"][g]
        al = main["share_med_all"][g]
        print(f"     {g:<8}"
              f"{('%.4f' % a3) if a3 is not None else 'n/a':>32}"
              f"{('%.4f' % al) if al is not None else 'n/a':>14}")
    dom = main["dominant_leg"]
    if dom is None:
        print("     NO REFERENT: no loop carries all three legs.")
    elif dom == "leg2":
        print("     §8·23·3 -> FIRST BRANCH. leg 2 dominates, as §14.3 says")
        print("     on the other carrier.")
    elif dom == "leg1":
        print("     §8·23·3 -> SECOND BRANCH. **leg 1 dominates**: the")
        print("     `current -> delinquent` stretch, not the modification")
        print("     month. Not the same direction as §14.3.")
    else:
        print("     §8·23·3 -> THIRD BRANCH. **leg 3 dominates**: the")
        print("     `modified -> current` stretch. Not the same direction as")
        print("     §14.3.")
    print("     The `all loops` column is a deliverable, not a reading: it")
    print("     includes the empty-leg-3 loops, where leg 3 is zero by")
    print("     construction and would drag any comparison.")

    print("\n  G. What travels with every number above (§8·23·4)")
    print("     1. the modification arm's loops are **not a random sample** of")
    print("        this carrier's modifications: they are the ones whose flag")
    print("        was written up early, and 95.5% of the ones B8's window")
    print("        rule excludes were flagged within a quarter of the cure")
    print("        (§8·22·8).")
    print("     2. bn == n identically; forgiven is 0 by absence, not by")
    print("        measurement; P is an estimate, not a published column.")
    print("     3. the modification arm is narrower than Fannie's **by")
    print("        construction**: field 63 has no counterpart here, and on")
    print("        Fannie it contributes 3.2% to 11.2% of modification onsets.")

    print("\n  H. What this section does NOT deliver (§8·23·5)")
    print("     omega is **not read against any floor**. B8 draws the same")
    print("     line in its own block two. That is §8·24.")
    print("     §8·12 is not re-asked, and nothing here says §1.1 has an")
    print("     answer on this carrier.")


def cmd_legs(only) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    if not vs:
        print(f"  no archives under {RAW}")
        return 1
    sys.path.insert(0, str(ROOT / "experiments"))
    import b8_cmt_fetch as F                      # noqa: E402
    import b8_loop_omega as LO                    # noqa: E402
    import b8_omega as W                          # noqa: E402
    import b8_0a_gate as G                        # noqa: E402
    import b10_c8_1d_freddie as FR                # noqa: E402

    if W.MAX_H != CURVE_MAX_H:
        print(f"  b8_omega.MAX_H is {W.MAX_H} and this file says "
              f"{CURVE_MAX_H}. Fix one; nothing is read until then.")
        return 1
    if not print_crosscheck(resid_crosscheck(W, G)):
        print("\n  §8·19·3 did not pass. Nothing was read. Fix it first.")
        return 1
    print()
    prior = prior_json(ROOT, partial_name("b10_legs", only))
    src, files = F.load_treasury()
    if not src:
        print("  no Treasury curve under data/raw/cmt.")
        return 1
    pos, tab = LO.curve_table_from(src, LO.RULE)

    print("§8·23: omega on the triangle windows, split into three legs.\n"
          "  **Read against no floor** (§8·23·5); B8 draws the same line.\n")
    acc = legs_new_acc()
    for v in vs:
        orig, _ = FR.read_orig(v)
        with zipfile.ZipFile(archive(v)) as zf:
            with zf.open(f"sample_perf_{v}.txt") as raw:
                seq, batch = None, []
                for line in io.TextIOWrapper(raw, encoding="utf-8",
                                             newline=""):
                    if not line.strip():
                        continue
                    f = line.split("|")
                    if f[0] != seq:
                        if seq is not None:
                            legs_absorb(acc, batch, orig.get(seq), pos, tab,
                                        CURVE_MAX_H, W.r_month,
                                        FR.contract_payment)
                        seq, batch = f[0], []
                    batch.append(floor_row(f))
                if seq is not None:
                    legs_absorb(acc, batch, orig.get(seq), pos, tab,
                                CURVE_MAX_H, W.r_month, FR.contract_payment)
        print(f"  {v}  done   loops {acc['loops']:,}"
              f"   measurable {acc['schemes']['sub']['ok']:,}", flush=True)
    pl = legs_payload(acc)
    print_vs_prior(prior, pl, partial_name("b10_legs", only))
    print_legs(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / partial_name("b10_legs", only)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "legs", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. omega on the loop "
             "windows and its three legs. Read against no floor: that is "
             "§8·24, and b8_loop_omega draws the same line in its own file.",
         "payment": "§12.2's substitution, split at t_M (§8·23·0); `orig` "
                    "carried beside it and wrong on leg 3 by construction",
         "caveats": ["the modification arm is the early-flagged minority "
                     "(§8·22·8)",
                     "bn == n; forgiven is 0 by absence; P is an estimate",
                     "no field 63 counterpart: 3.2%-11.2% narrower (§8·22·2)"],
         **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --signal. Registered before the code.
# B8-1's shape: MAD(signal) / MAD(floor), then the same with leg 1's closed
# form removed. **Not one new formula**: the residual is b8_omega's, the scale
# estimator is b8_0b_floor's, and both are imported.
# ---------------------------------------------------------------------------

#: §21.2's operative line, transcribed. **Readability, not significance**:
#: below it the loop sum sits inside one step of the instrument's resolution.
SIGNAL_READABLE = 1.0

#: §5's inherited number, printed beside under R01. **Not the operative one.**
SIGNAL_INHERITED = 3.0

#: `results/b8_1_signal.md`, transcribed 2026-08-20. Printed beside, never
#: subtracted (§7·9). (archive, MAD signal, MAD floor, ratio raw, ratio net,
#: net/raw).
B8_1_SIGNAL = (
    ("2002Q1", 1.4466e-01, 5.2162e-08, 2_773_329.7, 2_624_568.8, 0.9464),
    ("2006Q1", 2.2284e-01, 3.5436e-08, 6_288_484.9, 6_077_878.2, 0.9665),
    ("2007Q1", 2.2775e-01, 3.3663e-08, 6_765_766.9, 6_632_538.5, 0.9803),
    ("2012Q1", 7.9194e-02, 3.2822e-08, 2_412_840.2, 2_135_051.8, 0.8849),
    ("2017Q1", 1.0471e-01, 2.6950e-08, 3_885_165.5, 3_752_337.2, 0.9658),
    ("2019Q1", 1.3725e-01, 2.6803e-08, 5_120_587.2, 5_235_539.4, 1.0224),
)

SIGNAL_FLOORS = ("ambient", "resolution")


def signal_payload(legs_acc, omega_acc, mad_scale) -> dict:
    """§8·24's two statistics, on two floors, for both payment schemes.

    `mad_scale` is **`b8_0b_floor.mad_scale`, passed in**. Rewriting it here
    would put two copies of a scale estimator in the repository with no check
    between them, which is 失效模式 19; passing the function keeps the two
    sides of the ratio the same object (§18.7's own requirement).
    """
    def q(xs):
        return {"n": len(xs), "mad": (mad_scale(xs) if xs else None),
                "absmed": (_q([abs(x) for x in xs], (50,))[0] if xs else None)}

    floors = {}
    for f in SIGNAL_FLOORS:
        v = omega_acc["b8like"][f"gap_{f}"]
        floors[f] = q(v)

    out = {}
    for name in LEG_SCHEMES:
        sg = legs_acc["schemes"][name]["sig"]
        raw, net = sg["omega"], sg["omega_net"]
        cell = {"raw": q(raw), "net": q(net), "ratios": {}}
        for f in SIGNAL_FLOORS:
            fl = floors[f]["mad"]
            r_raw = (cell["raw"]["mad"] / fl) if (fl and cell["raw"]["mad"]
                                                  is not None) else None
            r_net = (cell["net"]["mad"] / fl) if (fl and cell["net"]["mad"]
                                                  is not None) else None
            cell["ratios"][f] = {
                "raw": r_raw, "net": r_net,
                "net_over_raw": (r_net / r_raw) if (r_raw and r_net) else None,
                "raw_above_1": (None if r_raw is None
                                else bool(r_raw > SIGNAL_READABLE)),
                "net_above_1": (None if r_net is None
                                else bool(r_net > SIGNAL_READABLE)),
                "raw_above_3": (None if r_raw is None
                                else bool(r_raw > SIGNAL_INHERITED)),
                "net_above_3": (None if r_net is None
                                else bool(r_net > SIGNAL_INHERITED))}
        #: §8·24·6. **The tolerance is derived at run time from this
        #: carrier's own resolution floor**, never copied from B8's `1e-7`:
        #: that number's source is Fannie's floor, and a tolerance imported
        #: across carriers is a tolerance reasoned from the wrong quantity.
        tol = (2.0 * floors["resolution"]["mad"]
               if floors["resolution"]["mad"] else None)
        ex = (sum(1 for d in sg["l1_exact_in"] if d <= tol)
              if tol is not None else None)
        cell["l1"] = {
            "tol": tol, "n": len(sg["l1_exact_in"]), "exact": ex,
            "share": (ex / len(sg["l1_exact_in"]))
            if (ex is not None and sg["l1_exact_in"]) else None,
            "q_gap": _q(sg["l1_exact_in"]) if sg["l1_exact_in"] else None,
            "q_n1": _q([x for x in sg["n1"]]) if sg["n1"] else None,
            "q_eff": (_q([x for x in sg["eff"] if x is not None])
                      if any(x is not None for x in sg["eff"]) else None),
            "l1c_missing": sum(1 for x in sg["l1c"] if x is None)}
        cell["by_arm"] = {}
        for arm, d in sorted(sg["by_arm"].items()):
            a = {"raw": q(d["omega"]), "net": q(d["omega_net"]), "ratios": {}}
            for f in SIGNAL_FLOORS:
                fl = floors[f]["mad"]
                a["ratios"][f] = {
                    "raw": (a["raw"]["mad"] / fl) if (fl and a["raw"]["mad"]
                                                      is not None) else None,
                    "net": (a["net"]["mad"] / fl) if (fl and a["net"]["mad"]
                                                      is not None) else None}
            cell["by_arm"][arm] = a
        out[name] = cell
    return {"floors": floors, "schemes": out,
            "readable_line": SIGNAL_READABLE,
            "inherited_line": SIGNAL_INHERITED,
            "fannie_beside": [list(r) for r in B8_1_SIGNAL]}


def _branch3(a, b, first, second, third):
    """Two booleans -> one of three branches, or None when either is unknown."""
    if a is None or b is None:
        return None
    if a and b:
        return first
    if not a and not b:
        return second
    return third


def print_signal(pl) -> None:
    main = pl["schemes"]["sub"]
    print("\n  A. the two floors (§8·24·3), both from `omega - closed` on the")
    print("     clean-cure arm, which is what §18.7 uses. **Not §8·21's**")
    print("     never-delinquent floor: that one is a payment-error floor on")
    print("     this carrier (§8·21·4), not a quantisation one.")
    print(f"     {'floor':<12}{'n':>10}{'MAD':>14}{'median |.|':>14}"
          f"   what it answers")
    for f in SIGNAL_FLOORS:
        d = pl["floors"][f]
        what = ("every clean-cure loop, path unfiltered"
                if f == "ambient" else
                "only the derived-path ones, where P is right")
        print(f"     {f:<12}{d['n']:>10,}"
              f"{('%.4e' % d['mad']) if d['mad'] is not None else 'n/a':>14}"
              f"{('%.4e' % d['absmed']) if d['absmed'] is not None else 'n/a':>14}"
              f"   {what}")

    print("\n  B. §8·24·4: the signal against each floor")
    print(f"     MAD(omega) = "
          f"{('%.4e' % main['raw']['mad']) if main['raw']['mad'] is not None else 'n/a'}"
          f"   on {main['raw']['n']:,} triangles")
    print(f"     {'floor':<12}{'ratio raw':>16}{'> 1':>6}{'> 3':>6}")
    for f in SIGNAL_FLOORS:
        r = main["ratios"][f]
        print(f"     {f:<12}"
              f"{('%.6g' % r['raw']) if r['raw'] is not None else 'n/a':>16}"
              f"{str(r['raw_above_1']):>6}{str(r['raw_above_3']):>6}")
    b1 = _branch3(main["ratios"]["ambient"]["raw_above_1"],
                  main["ratios"]["resolution"]["raw_above_1"],
                  "FIRST", "SECOND", "THIRD")
    if b1 is None:
        print("     NO REFERENT: a floor or the signal is empty.")
    elif b1 == "FIRST":
        print("     §8·24·4 -> FIRST BRANCH. Above the line on both floors.")
        print("     Same direction as Fannie's six archives.")
    elif b1 == "SECOND":
        print("     §8·24·4 -> SECOND BRANCH. **Below the line on both**: the")
        print("     loop sum sits inside the floor and is not readable on")
        print("     this carrier.")
    else:
        low = [f for f in SIGNAL_FLOORS
               if not main["ratios"][f]["raw_above_1"]]
        print("     §8·24·4 -> THIRD BRANCH, mixed (R01). The two floors")
        print(f"     disagree; `{low[0]}` is the one that puts it below.")
        print("     **That is evidence about selection, not about omega**:")
        print("     the two floors differ only in whether the path filter is")
        print("     on (§8·21·6's lesson, paid for once already).")
    print(f"     The line is {SIGNAL_READABLE:g} (§21.2): **readability, not")
    print("     significance** — below it the loop sum is inside one step of")
    print(f"     the instrument's resolution. {SIGNAL_INHERITED:g} is §5's")
    print("     inherited number, printed under R01 and **not operative**.")

    print("\n  C. §8·24·5: the same with leg 1's closed form removed")
    print("     Nothing before t_M knows a modification is coming, so leg 1")
    print("     on the modification arm is the clean-cure object and carries")
    print("     no news. **If the ratio collapses here, this station was")
    print("     measuring the construction** (B8's own words).")
    print(f"     MAD(omega - l1_closed) = "
          f"{('%.4e' % main['net']['mad']) if main['net']['mad'] is not None else 'n/a'}")
    print(f"     {'floor':<12}{'ratio net':>16}{'net/raw':>10}{'> 1':>6}"
          f"{'> 3':>6}")
    for f in SIGNAL_FLOORS:
        r = main["ratios"][f]
        print(f"     {f:<12}"
              f"{('%.6g' % r['net']) if r['net'] is not None else 'n/a':>16}"
              f"{('%.4f' % r['net_over_raw']) if r['net_over_raw'] is not None else 'n/a':>10}"
              f"{str(r['net_above_1']):>6}{str(r['net_above_3']):>6}")
    b2 = _branch3(main["ratios"]["ambient"]["net_above_1"],
                  main["ratios"]["resolution"]["net_above_1"],
                  "FIRST", "SECOND", "THIRD")
    if b2 is None:
        print("     NO REFERENT.")
    elif b2 == "FIRST":
        print("     §8·24·5 -> FIRST BRANCH. The ratio survives on both")
        print("     floors: **the signal is not the construction.**")
    elif b2 == "SECOND":
        print("     §8·24·5 -> SECOND BRANCH. **It collapses on both floors:")
        print("     this station was measuring the construction.** The omega")
        print("     reading is withdrawn to `outside leg 2 there is nothing`.")
    else:
        print("     §8·24·5 -> THIRD BRANCH, mixed (R01). The two floors")
        print("     disagree once the construction is removed. Set out on its")
        print("     own line.")
    print("     Fannie's net/raw runs 0.885 to 1.022 and stays above the line")
    print("     on all six.")

    print("\n  D. §8·24·6: how much of leg 1 IS the closed form")
    lc = main["l1"]
    print(f"     tolerance {('%.4e' % lc['tol']) if lc['tol'] is not None else 'n/a'}"
          f"  = 2 x MAD(resolution). **Derived at run time from this")
    print("     carrier's own floor**, never copied from B8's 1e-7: that")
    print("     number's source is Fannie's floor, and a tolerance carried")
    print("     across carriers is reasoned from the wrong quantity.")
    print(f"     loops with a computable l1_closed {lc['n']:,}"
          f"   without {lc['l1c_missing']:,}")
    if lc["exact"] is not None:
        print(f"     **exact** (|leg1 - l1_closed| <= tol) {lc['exact']:,}"
              f" = {lc['share']:.4f}")
    if lc["q_gap"]:
        print(f"     |leg1 - l1_closed|  p10 {lc['q_gap'][0]:.4e}"
              f"   p50 {lc['q_gap'][1]:.4e}   p90 {lc['q_gap'][2]:.4e}")
    if lc["q_n1"]:
        print(f"     n1   p10/p50/p90 {lc['q_n1'][0]:.0f} /"
              f" {lc['q_n1'][1]:.0f} / {lc['q_n1'][2]:.0f}")
    if lc["q_eff"]:
        print(f"     eff  p10/p50/p90 {lc['q_eff'][0]:.3f} /"
              f" {lc['q_eff'][1]:.3f} / {lc['q_eff'][2]:.3f}"
              f"   (months the data behaved like a flat delinquent run)")
    print("     eff and n1 are **delivered, not read**.")

    print("\n  E. by arm, scheme `sub`")
    print(f"     {'arm':<8}{'n':>9}{'MAD raw':>13}{'MAD net':>13}"
          f"{'ratio raw':>14}{'ratio net':>14}   (floor: resolution)")
    for arm, d in main["by_arm"].items():
        r = d["ratios"]["resolution"]
        print(f"     {arm:<8}{d['raw']['n']:>9,}"
              f"{('%.4e' % d['raw']['mad']) if d['raw']['mad'] is not None else 'n/a':>13}"
              f"{('%.4e' % d['net']['mad']) if d['net']['mad'] is not None else 'n/a':>13}"
              f"{('%.6g' % r['raw']) if r['raw'] is not None else 'n/a':>14}"
              f"{('%.6g' % r['net']) if r['net'] is not None else 'n/a':>14}")

    print("\n  F. the `orig` scheme, printed and not read (§8·24·2)")
    o = pl["schemes"]["orig"]
    for f in SIGNAL_FLOORS:
        r = o["ratios"][f]
        print(f"     {f:<12} raw "
              f"{('%.6g' % r['raw']) if r['raw'] is not None else 'n/a':>14}"
              f"   net "
              f"{('%.6g' % r['net']) if r['net'] is not None else 'n/a':>14}")
    print("     Both sides of every ratio above use **one** payment scheme.")
    print("     Mixing them is 失效模式 18 on the arguments (§11 item 11).")

    print("\n  G. Fannie beside it (results/b8_1_signal.md)")
    print(f"     {'archive':<9}{'MAD sig':>12}{'MAD floor':>12}"
          f"{'ratio raw':>14}{'ratio net':>14}{'net/raw':>9}")
    for a, ms, mf, rr, rn, nr in B8_1_SIGNAL:
        print(f"     {a:<9}{ms:>12.4e}{mf:>12.4e}{rr:>14,.1f}{rn:>14,.1f}"
              f"{nr:>9.4f}")
    print("     **Beside, not subtracted** (§7·9).")

    print("\n  H. What travels, and what this does NOT deliver")
    print("     §8·12 is **not** re-asked here; that is §8·25, and nothing")
    print("     above says §1.1 has an answer on this carrier.")
    print("     The modification arm is the early-flagged minority (§8·22·8)")
    print("     and is narrower than Fannie's by construction (§8·22·2).")


def cmd_signal(only) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    if not vs:
        print(f"  no archives under {RAW}")
        return 1
    sys.path.insert(0, str(ROOT / "experiments"))
    import b8_cmt_fetch as F                      # noqa: E402
    import b8_loop_omega as LO                    # noqa: E402
    import b8_omega as W                          # noqa: E402
    import b8_0a_gate as G                        # noqa: E402
    import b8_0b_floor as FL                      # noqa: E402
    import b10_c8_1d_freddie as FR                # noqa: E402

    if W.MAX_H != CURVE_MAX_H:
        print(f"  b8_omega.MAX_H is {W.MAX_H} and this file says "
              f"{CURVE_MAX_H}. Fix one; nothing is read until then.")
        return 1
    if not print_crosscheck(resid_crosscheck(W, G)):
        print("\n  §8·19·3 did not pass. Nothing was read. Fix it first.")
        return 1
    #: §18.7's estimator, **imported**. A second copy of a scale estimator
    #: with no check between the two is 失效模式 19, and the ratio's own
    #: requirement is that both sides be the same object.
    if abs(FL.mad_scale([1.0, 2.0, 3.0, 4.0]) - 1.4826) > 1e-12:
        print(f"  b8_0b_floor.mad_scale did not reproduce its own constant "
              f"on [1,2,3,4]; got {FL.mad_scale([1.0, 2.0, 3.0, 4.0])}.")
        return 1
    print()
    prior = prior_json(ROOT, partial_name("b10_signal", only))
    src, files = F.load_treasury()
    if not src:
        print("  no Treasury curve under data/raw/cmt.")
        return 1
    pos, tab = LO.curve_table_from(src, LO.RULE)

    print("§8·24: the triangle against the floor. **One scan, two**\n"
          "  **populations**: the triangles carry the signal and the\n"
          "  no-modification round trips carry the floor, and the two are\n"
          "  disjoint by construction. §8·23 and §8·20 are recomputed on the\n"
          "  same pass and compared field by field to their own artifacts.\n")
    lacc = legs_new_acc()
    oacc = omega_new_acc()
    for v in vs:
        orig, _ = FR.read_orig(v)
        with zipfile.ZipFile(archive(v)) as zf:
            with zf.open(f"sample_perf_{v}.txt") as raw:
                seq, batch = None, []
                for line in io.TextIOWrapper(raw, encoding="utf-8",
                                             newline=""):
                    if not line.strip():
                        continue
                    f = line.split("|")
                    if f[0] != seq:
                        if seq is not None:
                            legs_absorb(lacc, batch, orig.get(seq), pos, tab,
                                        CURVE_MAX_H, W.r_month,
                                        FR.contract_payment)
                            omega_absorb(oacc, batch, orig.get(seq), v, pos,
                                         tab, CURVE_MAX_H, W, G,
                                         FR.contract_payment)
                        seq, batch = f[0], []
                    batch.append(floor_row(f))
                if seq is not None:
                    legs_absorb(lacc, batch, orig.get(seq), pos, tab,
                                CURVE_MAX_H, W.r_month, FR.contract_payment)
                    omega_absorb(oacc, batch, orig.get(seq), v, pos, tab,
                                 CURVE_MAX_H, W, G, FR.contract_payment)
        print(f"  {v}  done   triangles {lacc['loops']:,}"
              f"   clean cures {oacc['b8like']['n']:,}", flush=True)

    print("\n  A00. §8·23 and §8·20 recomputed on this scan, each against its")
    print("       own artifact. Same finder, same driver, same payments.")
    print_vs_prior(prior_json(ROOT, partial_name("b10_legs", only)),
                   legs_payload(lacc), partial_name("b10_legs", only))
    print_vs_prior(prior_json(ROOT, partial_name("b10_omega", only)),
                   omega_payload(oacc), partial_name("b10_omega", only))

    pl = signal_payload(lacc, oacc, FL.mad_scale)
    print_vs_prior(prior, pl, partial_name("b10_signal", only))
    print_signal(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / partial_name("b10_signal", only)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "signal", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. B8-1's shape on the "
             "second carrier: MAD(signal)/MAD(floor), then the same with leg "
             "1's closed form removed. §8·12 is not re-asked here.",
         "estimator": "b8_0b_floor.mad_scale, imported",
         "floor_is": "|omega - closed| on the clean-cure arm (§18.7), NOT "
                     "§8·21's never-delinquent floor",
         "caveats": ["the modification arm is the early-flagged minority "
                     "(§8·22·8)",
                     "narrower than Fannie's by construction (§8·22·2)",
                     "both sides of every ratio use one payment scheme"],
         **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


#: The row tuple §8·16, §8·17 and §8·19 read, by index. Named so an eighth
#: field cannot silently shift a seventh: `rem` was appended when §8·17 needed
#: the horizon, `defer` when §8·19 needed §8·18's balance identity, and every
#: unpacking site reads `R_*` rather than counting commas.
R_PERIOD, R_DELINQ, R_MODFLAG, R_AGE, R_UPB, R_RATE, R_REM, R_DEFER = range(8)

#: Perf column 12, one-based; the deferred (zero-interest) balance. §8·18's
#: identity is `bal_ib = col 3 - col 12`, and §8·14·5 measured that this column
#: is **never blank and never negative**, with zero the majority value.
P_DEFER_BAL_IDX = 11


def floor_row(f):
    """One perf line -> the 8-tuple `R_*` indexes.

    Unreadable numerics come back as None rather than a sentinel, so a row that
    cannot be priced is loud at the point of use instead of quietly zero.
    **`R_DEFER` is no exception**: a line too short to carry column 12 reads
    None, not 0.0. §8·14·5's whole finding was that blank and zero are
    structurally opposite, and 失效模式 20 is what folding them costs.
    """
    def num(j, cast):
        try:
            return cast(f[j].strip())
        except (ValueError, IndexError):
            return None
    per = num(1, int)
    return (per if per is not None else -1,
            f[3].strip() if len(f) > 3 else "",
            f[7].strip() if len(f) > 7 else "",
            num(4, int), num(2, float), num(10, float), num(5, int),
            num(P_DEFER_BAL_IDX, float))


def cmd_triangles(only) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    if not vs:
        print(f"  no archives under {RAW}")
        return 1
    print(f"§24.6 step two. Rebuilding the triangle finder and checking it "
          f"against §3 and §4.\n{len(vs)} vintages. §26.0's three ambiguities "
          f"are all computed; §26.1 excludes 2026 from the gate.\n")

    recs, totals = [], defaultdict(Counter)
    for v in vs:
        r = scan_vintage(v)
        recs.append(r)
        pub = PUBLISHED_S3.get(v)
        got = {"loans": r["loans"], "perf_rows": r["perf_rows"],
               "ever_delinq": r["ever_delinq"]["digits"],
               "ever_mod": r["ever_mod"],
               "triangles": r["triangles"]["digits"],
               # §27.1: `digits` and `between` are the readings §3 used, and
               # that is a discovery from the 2007 run, not a choice: `digits`
               # reproduced ever_delinq exactly (13,521 against `any`'s 13,522)
               # and `between` reproduced the round trip exactly (10,562
               # against `whole_loan`'s 7,511). All readings still print below.
               "roundtrip": r["roundtrip"][("digits", "between")]}
        if pub is None:
            print(f"  {v}  loans {r['loans']:>6,}  rows {r['perf_rows']:>10,}  "
                  f"tri(digits) {r['triangles']['digits']:>6,}   "
                  f"**not in §3's table, excluded from the gate (§26.1)**")
            continue
        flags = "".join(
            " ok " if got[c] == pub[k] else f" {got[c]:,} vs {pub[k]:,} "
            for k, c in enumerate(S3_COLS))
        bad = any(got[c] != pub[k] for k, c in enumerate(S3_COLS))
        print(f"  {v}  {'MISMATCH' if bad else 'ok      '}  "
              f"loans {got['loans']:>6,} rows {got['perf_rows']:>10,} "
              f"del {got['ever_delinq']:>6,} mod {got['ever_mod']:>5,} "
              f"tri {got['triangles']:>5,} rt {got['roundtrip']:>6,}")
        if bad:
            print(f"        published: " + "  ".join(
                f"{c}={pub[k]:,}" for k, c in enumerate(S3_COLS)))
        for k, c in enumerate(S3_COLS):
            totals["got"][c] += got[c]
            totals["pub"][c] += pub[k]

    # §28.2's fourth branch: a total that agrees while the rows do not reads as
    # a reproduction. The per-vintage differences print beside the total so
    # cancellation cannot pass for equality.
    print(f"\n  --- §28.2: the shape of the difference, not just its total ---")
    diffs = {r["vintage"]: r["triangles"]["digits"]
             - PUBLISHED_S3[r["vintage"]][4]
             for r in recs if r["vintage"] in PUBLISHED_S3}
    nz = {v: d for v, d in diffs.items() if d}
    print(f"    total signed difference {sum(diffs.values()):+,}   "
          f"total absolute {sum(abs(d) for d in diffs.values()):,}   "
          f"vintages that differ {len(nz)}/{len(diffs)}")
    if nz:
        print("    per vintage: " + ", ".join(f"{v}:{d:+}"
                                              for v, d in sorted(nz.items())))
    rel = {v: abs(d) / max(1, PUBLISHED_S3[v][4]) for v, d in nz.items()}
    if rel:
        print(f"    relative, worst {max(rel.values()):.5f} at "
              f"{max(rel, key=rel.get)}; a difference proportional to size "
              f"reads as a specification difference, a scatter of +/-1 does not")

    print(f"\n  --- §26.0's readings, on the vintages §3 covers "
          f"({S3_SPAN[0]}..{S3_SPAN[1]}) ---")
    ingate = [r for r in recs if S3_SPAN[0] <= r["vintage"] <= S3_SPAN[1]]
    pubtri = sum(p[4] for v, p in PUBLISHED_S3.items())
    pubrt = sum(p[5] for v, p in PUBLISHED_S3.items())
    pubdel = sum(p[2] for v, p in PUBLISHED_S3.items())
    for d in ("digits", "any"):
        t = sum(r["triangles"][d] for r in ingate)
        dl = sum(r["ever_delinq"][d] for r in ingate)
        print(f"    delinquency = {d:<7}  triangles {t:>7,} "
              f"(§3 {pubtri:,}, {'MATCH' if t == pubtri else 'no'})   "
              f"ever_delinq {dl:>8,} "
              f"(§3 {pubdel:,}, {'MATCH' if dl == pubdel else 'no'})")
        for rr in ("whole_loan", "between"):
            x = sum(r["roundtrip"][(d, rr)] for r in ingate)
            print(f"      round trip = {rr:<11} {x:>8,} "
                  f"(§3 {pubrt:,}, {'MATCH' if x == pubrt else 'no'})")
    nlc = {d: sum(r["no_leading_current"][d] for r in ingate)
           for d in ("digits", "any")}
    print(f"    loans whose first row is already delinquent: {nlc}   "
          f"{'the fourth ambiguity never mattered' if not any(nlc.values()) else '**it matters**, see §27.3'}")

    # ---- §27.3's point prediction ---------------------------------------
    tri_req = sum(r["triangles"]["digits"] for r in ingate)
    tri_nol = sum(r["triangles_nolead"]["digits"] for r in ingate)
    want = sum(PUBLISHED_S3[r["vintage"]][4] for r in ingate
               if r["vintage"] in PUBLISHED_S3)
    print(f"\n  --- §27.3: the fourth reading, against a point prediction ---")
    print(f"    leading `current` required     {tri_req:>7,}")
    print(f"    leading `current` NOT required {tri_nol:>7,}")
    print(f"    §3 published                   {want:>7,}")
    if tri_nol == want:
        v = ("EXACT. §3 does not require the leading `current`. All four "
             "ambiguities are settled; go to the full sweep.")
    elif tri_nol > want:
        v = (f"OVERSHOOT by {tri_nol - want:,}. Relaxing it goes too far, so §3 "
             f"did not relax it, and the missing triangle comes from a fifth "
             f"disagreement. Do not proceed to step three.")
    else:
        v = (f"UNCHANGED at {tri_nol:,}. None of those loans completes the "
             f"chain, so the gap has nothing to do with the leading `current`. "
             f"Fifth disagreement. Do not proceed to step three.")
    print(f"    -> {v}")
    odd = Counter()
    for r in recs:
        odd.update(r["odd_modflag"])
    print(f"    modification-flag values outside {MODFLAG_MOD}: {dict(odd)}")

    print("\n  --- §4, per modification year and by window ---")
    year_match = {}
    for d in ("digits", "any"):
        for m in ("first_Y", "first_any"):
            tot = Counter()
            for r in ingate:
                tot.update(r["mod_year"][(d, m)])
            same = tot == Counter(PUBLISHED_S4_YEAR)
            diff = {y: (tot.get(y, 0), PUBLISHED_S4_YEAR.get(y, 0))
                    for y in sorted(set(tot) | set(PUBLISHED_S4_YEAR))
                    if tot.get(y, 0) != PUBLISHED_S4_YEAR.get(y, 0)}
            wins = {name: sum(n for y, n in tot.items() if lo <= y <= hi)
                    for name, lo, hi, _ in S4_WINDOWS}
            wok = all(wins[name] == want for name, _, _, want in S4_WINDOWS)
            noyear = sum(r["triangle_without_year"][(d, m)] for r in ingate)
            year_match[(d, m)] = {"exact": same, "windows_ok": wok,
                                  "windows": wins, "diff": diff,
                                  "triangles_with_no_year": noyear,
                                  "total_filed": sum(tot.values())}
            print(f"    {d:<7} / {m:<9}  year table "
                  f"{'MATCH' if same else 'no'}   windows "
                  f"{'MATCH' if wok else 'no'}   filed {sum(tot.values()):,}"
                  f"   unfiled {noyear:,}   {wins}")
            if diff and len(diff) <= 10:
                print(f"        differs at: " + ", ".join(
                    f"{y}: {a:,}/{b:,}" for y, (a, b) in diff.items()))
            elif diff:
                print(f"        differs at {len(diff)} years, worst "
                      + ", ".join(f"{y}: {a:,}/{b:,}" for y, (a, b) in
                                  sorted(diff.items(),
                                         key=lambda kv: -abs(kv[1][0] - kv[1][1]))[:6]))

    matched = [k for k, x in year_match.items() if x["exact"]]
    print(f"\n  §26.0's rule: {len(matched)} of the four (delinquency, "
          f"mod-year) readings reproduce §4's table exactly.")
    if len(matched) == 1:
        print(f"    -> §3/§4 used {matched[0]}. That is a discovery about the "
              f"vanished scan, not a choice made here.")
    elif len(matched) > 1:
        print(f"    -> more than one matches: {matched}. **The ambiguity does "
              f"not bear on this data**, which is itself a reading.")
    else:
        print("    -> none matches. §26.0 says do not pick: there is a fourth "
              "disagreement between this code and §3/§4 and it has to be found "
              "before step three.")

    mean_months = {d: (sum(r["months_of_triangle"][d] for r in ingate)
                       / max(1, sum(r["triangles"][d] for r in ingate)))
                   for d in ("digits", "any")}
    print(f"\n  `三角均月`, **definition guessed, not a gate** (§26.2): "
          f"months reported per triangle loan = "
          f"{ {d: round(x, 1) for d, x in mean_months.items()} }")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / partial_name("b10_cohort_width_triangles", only)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "cohort_width_triangles",
         "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B10 availability register §24.6 step two and "
             "§26. Reproduction check only; no omega, no cells, no B8 "
             "prediction.",
         "s3_span": list(S3_SPAN),
         "year_match": {f"{d}|{m}": x for (d, m), x in year_match.items()},
         "mean_months_definition_guessed": mean_months,
         "archives": [{k: (dict(v) if isinstance(v, Counter) else
                           {str(a): b for a, b in v.items()}
                           if isinstance(v, dict) else v)
                       for k, v in r.items()} for r in recs]},
        indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# §24.6 step three: the width curve.
# ---------------------------------------------------------------------------

#: §4's Flex window, by modification year. The only window step three uses.
FLEX_YEARS = (2017, 2019)

#: C9's class grids, **transcribed from `b8_c9_cells.py` rather than rebuilt**.
#: §24.3 borrows them wholesale, boundaries and all, and re-deriving something a
#: neighbouring file already has right is the mistake this station has made
#: three times. `FICO_LLPA` there is written as **ascending lower edges** with
#: `searchsorted(side="right")`, so level 0 is the lowest score; `fico_band` in
#: this file numbers the same partition the other way round. The selftest
#: asserts the two induce the same partition, so the relabelling can never
#: quietly become a different cut.
C9_FICO_LLPA9 = (640, 660, 680, 700, 720, 740, 760, 780)
C9_FICO_COARSE5 = (640, 680, 720, 760)

#: Widths. The dyadic chain is left-anchored so its bins nest exactly, which is
#: what makes §24.4's monotone invariant an identity rather than a hope. The
#: extra widths do not nest and are excluded from that assertion by design.
DYADIC_W = (1, 2, 4, 8, 16)
EXTRA_W = (3, 5, 6, 7)

#: §30.4 condition three. The unlocated residual between this station's triangle
#: finder and §3's, carried forward as a robustness requirement rather than
#: hidden: a verdict that changes when the thinnest cell moves by this much is
#: not a verdict.
RESIDUAL = 5

#: §24.4's two marks. Neither is a criterion line: `2` is the structural
#: minimum for a within-cell dispersion to exist at all, and `20` is **C9's
#: floor, borrowed and labelled as borrowed** (§24.7 rule 3 hands it back to B8
#: if the second branch lands).
MARK_STRUCTURAL, MARK_BORROWED_FROM_C9 = 2, 20


def c9_band(v: int, edges) -> int:
    """`b8_c9_cells._band`, ascending lower edges, `side='right'`."""
    n = 0
    for e in edges:
        if v >= e:
            n += 1
    return n


def dti_complement15(v: int) -> int:
    """C9's fifteen-level DTI grid: the integers 36..49 apart, the rest as one.

    `b8_c9_cells._dti_grids`: ``complement = where(36 <= x <= 49, x - 36, 14)``.
    §3.3's reading of it is that the level count is not what carries the
    structure, **which layers get merged is**, and this is the grid that keeps
    the fourteen bare integers and merges the five published buckets.
    """
    return v - 36 if 36 <= v <= 49 else 14


def grids_of(fico, dti, purpose, fthb) -> dict:
    """C9's five usable grids for one loan. `None` drops it from that grid only.

    §4 of C9 ruled that blanks and the file's own unknown codes both come out,
    each with a count, because neither is an agent class. The drop is **per
    grid**: a loan with no FICO still populates the `purpose` cells.
    """
    g = {}
    g["fico_llpa9"] = (None if fico is None
                       else c9_band(fico, C9_FICO_LLPA9))
    g["fico_llpa_coarse5"] = (None if fico is None
                              else c9_band(fico, C9_FICO_COARSE5))
    g["dti_complement15"] = None if dti is None else dti_complement15(dti)
    g["purpose"] = purpose
    g["fthb"] = fthb
    return g


C9_GRIDS = ("purpose", "fthb", "fico_llpa_coarse5", "dti_complement15",
            "fico_llpa9")


def parse_orig_classes(v: int) -> tuple:
    """`{loan_seq: (fico, dti, purpose, fthb)}` plus the exclusion counts.

    Field positions come from `ANCHORED`, which `--depth` earned by behaviour
    (§25). `9999` and `999` are the two fields' missing codes; `fthb`'s `9` is
    the file's own unknown, which C9 §4 rules out with a count rather than
    folding into a level.
    """
    out, drop = {}, Counter()
    for f in orig_rows(v):
        if len(f) < ORIG_FIELDS:
            continue
        s = f[O_FICO].strip()
        fico = int(s) if s.isdigit() and int(s) != 9999 else None
        if fico is None:
            drop["fico"] += 1
        s = f[O_DTI].strip()
        dti = int(s) if s.isdigit() and int(s) != 999 else None
        if dti is None:
            drop["dti"] += 1
        p = f[O_PURPOSE].strip()
        purpose = p if p in ("P", "C", "N") else None
        if purpose is None:
            drop["purpose"] += 1
        t = f[O_FTHB].strip()
        fthb = t if t in ("Y", "N") else None
        if fthb is None:
            drop["fthb"] += 1
        out[f[O_SEQ]] = (fico, dti, purpose, fthb)
    return out, drop


def flex_triangles(v: int) -> tuple:
    """Flex-window triangles of one vintage, with their class values.

    The population is §30.4's: `not_required` for the leading `current`,
    `digits` for delinquency, `first_any` for the modification month. Those four
    readings were settled in §29 and §30 against §3 and §4, not chosen here.
    """
    cls, drop = parse_orig_classes(v)
    rows_by_loan, out = [], []
    n_tri = 0
    with zipfile.ZipFile(archive(v)) as zf:
        with zf.open(f"sample_perf_{v}.txt") as raw:
            seq, batch = None, []

            def flush(sq, rows):
                nonlocal n_tri
                if not rows:
                    return
                c = classify_loan(rows)["digits"]
                if not c["triangle_nolead"] or c["first_any"] is None:
                    return
                n_tri += 1
                yr = c["first_any"] // 100
                if FLEX_YEARS[0] <= yr <= FLEX_YEARS[1]:
                    out.append((sq, yr, cls.get(sq, (None, None, None, None))))

            for line in io.TextIOWrapper(raw, encoding="utf-8", newline=""):
                if not line.strip():
                    continue
                f = line.split("|", 8)
                if f[0] != seq:
                    flush(seq, batch)
                    seq, batch = f[0], []
                batch.append((int(f[1]), f[3].strip(), f[7].strip()))
            flush(seq, batch)
    del rows_by_loan
    return out, drop, n_tri


def width_curve(items, grid: str, widths) -> list:
    """`M(w)` and `B(w)` for one grid, left-anchored bins over the cohort axis.

    `items` is `[(vintage, level), ...]` with the loans that grid keeps. The
    axis is the vintages that actually carry a Flex triangle (§24.2: read from
    the data, not chosen), and the bins are anchored at its left edge so the
    dyadic chain nests exactly.
    """
    if not items:
        return []
    lo = min(v for v, _ in items)
    rows = []
    for w in widths:
        cells = Counter((((v - lo) // w), lev) for v, lev in items)
        bins = {b for b, _ in cells}
        rows.append({"w": w, "bins": len(bins), "cells": len(cells),
                     "min_cell": min(cells.values()),
                     "mean_cell": round(sum(cells.values()) / len(cells), 2),
                     "loans": sum(cells.values())})
    return rows


def branch_of(m: int) -> str:
    """§24.5's partition of `M`. Three cells, and they are a partition."""
    if m <= 1:
        return "dead"
    if m < MARK_BORROWED_FROM_C9:
        return "thin"
    return "clears_c9_floor"



# ---------------------------------------------------------------------------
# --windows. Registered before the code.
#
# §31·4 asserts the fine grids die on geometry, not on sample size: "adding
# archives will not change it, because §24·2's geometry is independent of
# sample size". That was measured on Flex alone, 1,903 triangles. HAMP holds
# 10,703 in the same file, and it separates the two things: 5.6x the triangles
# (thicker) on a shorter cohort axis (worse). If the fine grids clear on HAMP,
# thickness was what mattered and §31·4 is falsified.
#
# Rule 19: `cmd_run` and `flex_triangles` are not touched, and this mode writes
# its own cache, so `--run` and b10_flex_triangles.json are unchanged by
# construction. The comparison still gets run.
# ---------------------------------------------------------------------------

#: The two grids §31 read as dead. §9·7·1's variable is whether either of them
#: reaches a robust non-dead reading on any window.
FINE_GRIDS = ("fico_llpa9", "dti_complement15")


def window_of(year: int) -> str:
    for name, lo, hi, _ in S4_WINDOWS:
        if lo <= year <= hi:
            return name
    return "outside"


def all_triangles(v: int) -> tuple:
    """Every triangle of one vintage with its modification year, no window filter.

    Same population as `flex_triangles` (§30·4: not_required / digits /
    first_any); the only difference is that nothing is dropped for falling
    outside Flex. Kept as a separate function so `flex_triangles` is untouched.
    """
    cls, drop = parse_orig_classes(v)
    out = []
    n_tri = 0
    with zipfile.ZipFile(archive(v)) as zf:
        with zf.open(f"sample_perf_{v}.txt") as raw:
            seq, batch = None, []

            def flush(sq, rows):
                nonlocal n_tri
                if not rows:
                    return
                c = classify_loan(rows)["digits"]
                if not c["triangle_nolead"] or c["first_any"] is None:
                    return
                n_tri += 1
                out.append((sq, c["first_any"] // 100,
                            cls.get(sq, (None, None, None, None))))

            for line in io.TextIOWrapper(raw, encoding="utf-8", newline=""):
                if not line.strip():
                    continue
                f = line.split("|", 8)
                if f[0] != seq:
                    flush(seq, batch)
                    seq, batch = f[0], []
                batch.append((int(f[1]), f[3].strip(), f[7].strip()))
            flush(seq, batch)
    return out, drop, n_tri


def cmd_windows(only, rescan: bool) -> int:
    cache = RESULTS / "b10_all_triangles.json"
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    print("§9·7: the width curve on all five windows, as a falsification route")
    print("for §31·4's claim that the fine grids die on geometry, not on size.")
    print("**§30·2's Flex membership caveat and §29·1's +5 residual travel with")
    print("every number below, on every window, not just on Flex.**\n")

    if cache.exists() and not rescan and not only:
        blob = json.loads(cache.read_text(encoding="utf-8"))
        loans = [tuple(x) for x in blob["loans"]]
        drops = Counter(blob["orig_exclusions"])
        print(f"  read {cache.relative_to(ROOT)} ({len(loans):,} triangles)."
              f" --rescan to rebuild.")
    else:
        loans, drops = [], Counter()
        for v in vs:
            got, drop, ntri = all_triangles(v)
            for seq, yr, cls in got:
                loans.append((v, yr, seq, *cls))
            drops.update(drop)
            print(f"  {v}  triangles {ntri:>6,}   kept {len(got):>6,}")
        if not only:
            RESULTS.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(
                {"stage": "B10", "step": "all_triangles",
                 "diagnostic_only": True,
                 "population": "not_required/digits/first_any (§30.4)",
                 "orig_exclusions": dict(drops),
                 "columns": ["vintage", "mod_year", "loan_seq", "fico", "dti",
                             "purpose", "fthb"],
                 "loans": loans}, indent=2, default=str) + "\n",
                encoding="utf-8", newline="\n")
            print(f"  wrote {cache.relative_to(ROOT)}")

    by_win = {}
    for row in loans:
        by_win.setdefault(window_of(row[1]), []).append(row)
    print(f"\n  triangles by window (§4 publishes 1130/10703/1903/2135/2004):")
    for name, _, _, want in S4_WINDOWS:
        got = len(by_win.get(name, []))
        print(f"     {name:<12}{got:>8,}   §4 {want:>7,}   diff {got - want:+,}")
    out_n = len(by_win.get("outside", []))
    print(f"     {'outside':<12}{out_n:>8,}   (no window claims these)")

    widths = tuple(sorted(set(DYADIC_W) | set(EXTRA_W)))
    rec = {"windows": {}}
    print(f"\n  §9·7·1's variable: does either fine grid reach a robust"
          f" non-dead reading?\n")
    verdict = {}
    for name, _, _, _ in S4_WINDOWS:
        rows_w = by_win.get(name, [])
        rec["windows"][name] = {"triangles": len(rows_w), "grids": {}}
        axis = sorted({r[0] for r in rows_w})
        print(f"  --- {name}   triangles {len(rows_w):,}   axis "
              f"{(str(axis[0]) + '..' + str(axis[-1])) if axis else 'empty'}"
              f"   {len(axis)} vintages")
        print(f"     {'grid':<20}{'w':>3}{'bins':>6}{'min':>6}{'-5':>6}"
              f"   reading")
        for gname in C9_GRIDS:
            items = [(r[0], grids_of(r[3], r[4], r[5], r[6])[gname])
                     for r in rows_w]
            items = [(v, lev) for v, lev in items if lev is not None]
            curve = width_curve(items, gname, widths)
            rec["windows"][name]["grids"][gname] = {"rows": curve,
                                                    "loans": len(items)}
            best = None
            for r in curve:
                if r["bins"] < 3:
                    continue
                b = branch_of(r["min_cell"])
                b2 = branch_of(max(0, r["min_cell"] - RESIDUAL))
                robust = (b == b2)
                if b != "dead" and robust and best is None:
                    best = r
                if gname in FINE_GRIDS and r["w"] in (4, 6, 8):
                    print(f"     {gname:<20}{r['w']:>3}{r['bins']:>6}"
                          f"{r['min_cell']:>6}{max(0, r['min_cell'] - RESIDUAL):>6}"
                          f"   {b}{'' if robust else '  NOT ROBUST'}")
            if gname in FINE_GRIDS:
                verdict[(name, gname)] = best
                tag = ("robust non-dead at w=%d" % best["w"]) if best else "no robust non-dead row"
                print(f"     {gname:<20}{'':>3}{'':>6}{'':>6}{'':>6}   => {tag}")
        print()

    hits = [k for k, v in verdict.items() if v is not None]
    print("  §9·7·1's three branches, on one variable:")
    if hits:
        print(f"     A fine grid reaches a robust non-dead reading on:"
              f" {', '.join(f'{w}/{g}' for w, g in hits)}")
        print("     -> the geometry claim is falsified. Flex's death was"
              " thinness, and §31·4\n        together with §24·5 branch one"
              " must be re-read. 'Too expensive' was right.")
    else:
        print("     Every fine grid is dead on every window, including HAMP at"
              " 5.6x Flex.")
        print("     -> the geometry claim stands, and it is now tested against a"
              " window that is\n        thicker by 5.6x. §24·5 branch one's"
              " 'cannot be bought, not too expensive' holds.")
    print("     Rows with fewer than 3 bins were skipped and are not read"
          " (§24·5).")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / partial_name("b10_window_width", only)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "window_width",
         "diagnostic_only": True,
         "diagnostic_reason":
             "Registered before the code. Counts and cell widths "
             "only; a falsification route for §31·4. C9's B8-4b domain is still "
             "Flex alone (§9·7·3).",
         "fine_grids": list(FINE_GRIDS),
         "by_window_counts": {n: len(by_win.get(n, [])) for n, _, _, _ in S4_WINDOWS},
         **rec}, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def cmd_run(only, rescan: bool) -> int:
    """§24.6 step three.

    **The cohort axis is the vintage, not the modification year.** B8-4b is
    `(class x issuance cohort)`; Freddie's archive *is* the origination year, so
    the vintage is the cohort. The modification year does one job only: it says
    whether a triangle is inside the Flex window.
    """
    cache = RESULTS / "b10_flex_triangles.json"
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    print("§24.6 step three: the width curve.")
    print(f"Population §30.4: not_required / digits / first_any, Flex window "
          f"{FLEX_YEARS[0]}..{FLEX_YEARS[1]}.")
    print("**Flex matches §4 by cancellation, not loan by loan: its membership "
          "differs by about\ntwo loans (§30.2), and the unlocated residual "
          "against §3 is +5 (§29.1). Both travel\nwith every number below.**\n")

    if cache.exists() and not rescan and not only:
        blob = json.loads(cache.read_text(encoding="utf-8"))
        loans = [tuple(x) for x in blob["loans"]]
        drops = Counter(blob["orig_exclusions"])
        tri_total = blob["triangles_all_windows"]
        print(f"  read {cache.relative_to(ROOT)} "
              f"({len(loans):,} Flex triangles). --rescan to rebuild.")
    else:
        loans, drops, tri_total = [], Counter(), 0
        for v in vs:
            got, drop, ntri = flex_triangles(v)
            for seq, yr, cls in got:
                loans.append((v, yr, seq, *cls))
            tri_total += ntri
            drops.update(drop)
            print(f"  {v}  triangles {ntri:>6,}   in Flex "
                  f"{sum(1 for x in got):>5,}")
        if not only:
            RESULTS.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(
                {"stage": "B10", "step": "flex_triangles",
                 "diagnostic_only": True,
                 "population": "not_required/digits/first_any (§30.4)",
                 "flex_years": list(FLEX_YEARS),
                 "triangles_all_windows": tri_total,
                 "orig_exclusions": dict(drops),
                 "columns": ["vintage", "mod_year", "loan_seq", "fico", "dti",
                             "purpose", "fthb"],
                 "loans": loans}, indent=2, default=str) + "\n",
                encoding="utf-8", newline="\n")
            print(f"  wrote {cache.relative_to(ROOT)}")

    print(f"\n  Flex triangles {len(loans):,}   (§4 publishes 1,903; the "
          f"difference is §30.2's)   all windows {tri_total:,}")
    print(f"  orig-side exclusions, per C9 §4 (blank and the file's own "
          f"unknown, each counted): {dict(drops)}")

    axis = sorted({x[0] for x in loans})
    print(f"  cohort axis, read from the data (§24.2): {axis[0]}..{axis[-1]}, "
          f"{len(axis)} vintages carry a Flex triangle; "
          f"{len(vs) - len(axis)} carry none")

    widths = tuple(sorted(set(DYADIC_W) | set(EXTRA_W)))
    rec = {"flex_triangles": len(loans), "axis": axis, "grids": {}}
    print(f"\n  {'grid':<20} {'w':>3} {'bins':>5} {'cells':>6} {'min':>5} "
          f"{'mean':>7} {'loans':>6}  reading")
    for gi, gname in enumerate(C9_GRIDS):
        items = []
        for v, yr, seq, fico, dti, purpose, fthb in loans:
            lev = grids_of(fico, dti, purpose, fthb)[gname]
            if lev is not None:
                items.append((v, lev))
        rows = width_curve(items, gname, widths)
        rec["grids"][gname] = {"rows": rows, "loans": len(items)}
        for r in rows:
            if r["bins"] < 3:
                read = "not read: under 3 bins is not an axis (§24.5)"
            else:
                b, b2 = branch_of(r["min_cell"]), \
                    branch_of(max(0, r["min_cell"] - RESIDUAL))
                read = (f"{b}" if b == b2 else
                        f"{b} -> **NOT ROBUST**: {b2} at -{RESIDUAL} (§30.4·3)")
            r["reading"] = read
            print(f"  {gname if r is rows[0] else '':<20} {r['w']:>3} "
                  f"{r['bins']:>5} {r['cells']:>6} {r['min_cell']:>5} "
                  f"{r['mean_cell']:>7} {r['loans']:>6}  {read}")
        # §24.4's invariant, on the nesting chain only
        chain = [r for r in rows if r["w"] in DYADIC_W]
        chain.sort(key=lambda r: r["w"])
        viol = [(a["w"], b["w"], a["min_cell"], b["min_cell"])
                for a, b in zip(chain, chain[1:])
                if b["min_cell"] < a["min_cell"]]
        rec["grids"][gname]["dyadic_violations"] = viol
        print(f"  {'':<20} monotone on the dyadic chain: "
              f"{'PASS' if not viol else f'FAIL {viol}'}")
        if gi < len(C9_GRIDS) - 1:
            print()

    print("\n  §24.5, and the readings were written before these numbers:")
    print(f"    dead            min cell <= 1        the direction dies on the "
          f"continuous axis; 17x and 41x both saved, and the reason is that "
          f"they buy nothing")
    print(f"    thin            2 <= min < {MARK_BORROWED_FROM_C9}       a width "
          f"exists but the cells are thinner than B8's own floor; the question "
          f"becomes whether C9's {MARK_BORROWED_FROM_C9} should carry over, "
          f"**which is B8's ruling, handed back** (§24.7 rule 3)")
    print(f"    clears_c9_floor min >= {MARK_BORROWED_FROM_C9}          a width "
          f"exists and clears the borrowed floor; report the width and the bin "
          f"count. **This is not a statement that B8-4b can run** (§23.2 (b))")
    print(f"    NOT ROBUST      the branch moves at -{RESIDUAL}   §30.4·3: a "
          f"verdict that turns on the unlocated residual is not a verdict")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / partial_name("b10_cohort_width", only)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "cohort_width", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B10 availability register §24, entry "
             "conditions re-registered in §30.4. Counts and cell widths only; "
             "no omega, no B8 prediction.",
         "population_caveat":
             "Flex membership matches §4 by cancellation, not loan by loan "
             "(§30.2); residual against §3 is +5 (§29.1). Both must travel with "
             "any citation.",
         "marks": {"structural": MARK_STRUCTURAL,
                   "borrowed_from_c9": MARK_BORROWED_FROM_C9},
         "residual_for_robustness": RESIDUAL,
         "dyadic_widths": list(DYADIC_W), "extra_widths": list(EXTRA_W),
         "orig_exclusions": dict(drops), **rec},
        indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def cmd_depth(only) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    if not vs:
        print(f"  no archives under {RAW}")
        return 1
    print(f"§24.6 step one. Origination side only, {len(vs)} vintages "
          f"({vs[0]}..{vs[-1]}). No triangles, no cells, no omega.\n")

    cols, widths = profile(vs)
    print(f"  field count seen: {dict(widths)}   (expected {ORIG_FIELDS})")
    print("\n  --- enumeration, appearance only, picks nothing (discipline 12) ---")
    print(f"  {'col':>3} {'blank%':>7} {'num%':>6} {'int%':>6} "
          f"{'lo':>10} {'hi':>10}  top values")
    for c in cols:
        n = c["rows"] or 1
        tops = ", ".join(f"{v}:{k}" for v, k in c["top"])
        mark = f"  <= {EARNED[c['i']]}" if c["i"] in EARNED else ""
        print(f"  {c['i']:>3} {100*c['blank']/n:>6.1f}% {100*c['numeric']/n:>5.1f}%"
              f" {100*c['int']/n:>5.1f}% {str(c['lo']):>10} {str(c['hi']):>10}"
              f"  {tops[:60]}{'...' if c['over_cap'] else ''}{mark}")

    # ---- candidate sets, by appearance, printed -------------------------
    def usable(c):
        return (c["i"] not in EARNED
                and c["blank"] / (c["rows"] or 1) <= MAX_BLANK_SHARE)

    def num_frac(c):
        return c["numeric"] / (c["rows"] or 1)

    dropped_blank = [c["i"] for c in cols if c["i"] not in EARNED
                     and c["blank"] / (c["rows"] or 1) > MAX_BLANK_SHARE]
    # **No range filter.** See the constants block: the first version's ranges
    # excluded both fields via their own missing codes. Numeric-and-not-earned
    # is the whole enumeration; the anchors pick.
    fico_c = [c["i"] for c in cols if usable(c) and num_frac(c) > 0.5]
    dti_c = [c["i"] for c in cols if usable(c) and num_frac(c) > 0.5
             and c["int"] / (c["rows"] or 1) > 0.5]
    lev = {c["i"]: c["n_distinct"] for c in cols}
    fthb_c = [c["i"] for c in cols if usable(c) and not c["over_cap"]
              and 1 < lev[c["i"]] <= FTHB_MAX_LEVELS]
    purp_c = [c["i"] for c in cols if usable(c) and not c["over_cap"]
              and PURPOSE_LEVELS[0] <= lev[c["i"]] <= PURPOSE_LEVELS[1]]
    print(f"\n  candidates by appearance:  fico {fico_c}   dti {dti_c}"
          f"   fthb {fthb_c}   purpose {purp_c}")
    print(f"  dropped for being blank on more than {MAX_BLANK_SHARE:.0%} of "
          f"rows: {dropped_blank}")
    if not (fico_c and dti_c and fthb_c and purp_c):
        print("  **a candidate set is empty.** The appearance filter is wrong or\n"
              "  the field is absent. Behaviour cannot pick from nothing; stop\n"
              "  here rather than widening the filter until something appears.")

    # ---- one pass over the data, collecting exactly what the anchors need
    per_vintage = {v: defaultdict(list) for v in vs}
    hist = {i: Counter() for i in dti_c}
    pair_counts = defaultdict(Counter)
    totals = {i: Counter() for i in set(fthb_c) | set(purp_c)}
    totals["rows"] = 0
    lvl_by_vintage = {v: Counter() for v in vs}
    rate_by_vintage = {}
    rates_tmp = defaultdict(list)

    for v in vs:
        for f in orig_rows(v):
            if len(f) < ORIG_FIELDS:
                continue
            try:
                rate = float(f[O_RATE])
            except ValueError:
                rate = None
            if rate is not None:
                rates_tmp[v].append(rate)
            totals["rows"] += 1
            for i in fico_c:
                s = f[i].strip()
                try:
                    per_vintage[v][i].append((float(s), rate))
                except ValueError:
                    pass
            for i in dti_c:
                s = f[i].strip()
                if s.isdigit():
                    hist[i][int(s)] += 1
            for i in set(fthb_c) | set(purp_c):
                totals[i][f[i].strip()] += 1
            for a in fthb_c:
                for b in purp_c:
                    if a != b:
                        pair_counts[(a, b)][(f[a].strip(), f[b].strip())] += 1
            for i in purp_c:
                lvl_by_vintage[v][(i, f[i].strip())] += 1
    for v, r in rates_tmp.items():
        if r:
            rate_by_vintage[v] = statistics.median(r)

    rec = {"vintages": vs, "field_count": dict(widths),
           "candidates": {"fico": fico_c, "dti": dti_c, "fthb": fthb_c,
                          "purpose": purp_c}}

    # ---- anchor 1: FICO prices the loan --------------------------------
    print("\n  --- anchor 1: FICO prices the loan (within vintage) ---")
    fa = anchor_fico(per_vintage, fico_c)
    rec["anchor_fico"] = fa
    order = sorted(fa, key=lambda i: -fa[i]["score"])
    order = [i for i in order if fa[i]["vintages"] > 0]
    for i in order[:5]:
        d = fa[i]
        print(f"    col {i:>3}  rate monotone across the bands in "
              f"{d['score']:>3}/{d['vintages']:<3} vintages that populate "
              f">= {MIN_BANDS_POPULATED} bands")
    skipped = [i for i in fa if fa[i]["vintages"] == 0]
    print(f"    columns that never populate {MIN_BANDS_POPULATED} bands, so the "
          f"ordering has nothing to order: {skipped}")
    if order:
        win = order[0]
        runner = fa[order[1]]["score"] if len(order) > 1 else 0
        print(f"    winner col {win}, margin {fa[win]['score'] - runner} vintages")
        for d in fa[win]["detail"]:
            print(f"      {d['vintage']}  bands {d['bands']}")
            print(f"            median rate {d['median_rate']}  "
                  f"{'monotone' if d['monotone'] else 'NOT monotone'}")
        rec["fico_col"] = win
        rec["fico_margin"] = fa[win]["score"] - runner

    # ---- anchor 2: the underwriting cap is a cliff ----------------------
    print("\n  --- anchor 2: DTI, the underwriting cap as a cliff ---")
    da = anchor_dti(hist, dti_c)
    rec["anchor_dti"] = da
    for i in sorted(da, key=lambda i: -da[i]["cliff_size"])[:5]:
        d = da[i]
        caps = "  ".join(f"drop@{c} {n:,}" for c, n in
                         d["drop_at_each_cap"].items())
        print(f"    col {i:>3}  largest one-step drop at {d['cliff_at']} "
              f"(size {d['cliff_size']:,}, {d['cliff_frac']:.3%})   {caps}   "
              f"{'PASS' if d['passes'] else 'not a GSE cap'}")
    ok = [i for i in da if da[i]["passes"]]
    if len(ok) == 1:
        rec["dti_col"] = ok[0]
        w = da[ok[0]]["window"]
        print(f"    winner col {ok[0]}. Histogram 38..55:")
        print("      " + "  ".join(f"{v}:{w[v]:,}" for v in sorted(w)))
    else:
        print(f"    **{len(ok)} columns pass.** Not identified; do not pick one.")

    # ---- anchor 3: fthb implies purchase -------------------------------
    print("\n  --- anchor 3: first-time buyer implies purchase (joint) ---")
    ia = anchor_implication({k: dict(v) for k, v in pair_counts.items()},
                            {**{i: dict(c) for i, c in totals.items()
                                if i != "rows"}, "rows": totals["rows"]},
                            fthb_c, purp_c)
    rec["anchor_implication"] = ia
    for r in ia["ranked"]:
        print(f"    fthb col {r['fthb_col']:>3} = {r['fthb_val']!r:<5} "
              f"=> purpose col {r['purpose_col']:>3} = {r['purpose_val']!r:<5}"
              f"   lift {r['lift']:>6.3f}   impl {r['implication']:.5f}"
              f"   counterexamples {r['counterexamples']:>6,}   n = {r['n']:,}")
    if ia["best"]:
        b, second = ia["best"], (ia["ranked"][1] if len(ia["ranked"]) > 1 else None)
        print(f"    winner: fthb col {b['fthb_col']}, purpose col "
              f"{b['purpose_col']}, lift margin "
              f"{b['lift'] - (second['lift'] if second else 0):.4f}, "
              f"{b['counterexamples']:,} counterexamples")
        rec["fthb_col"], rec["purpose_col"] = b["fthb_col"], b["purpose_col"]
        rec["fthb_purchase_codes"] = [b["fthb_val"], b["purpose_val"]]

    # ---- anchor 4: refinancing is rate-driven ---------------------------
    print("\n  --- anchor 4: refi share moves against the coupon level ---")
    pcol = rec.get("purpose_col")
    if pcol is not None:
        share = {}
        for v in vs:
            tot = sum(n for (i, _), n in lvl_by_vintage[v].items() if i == pcol)
            if tot:
                share[v] = {lv: n / tot for (i, lv), n in
                            lvl_by_vintage[v].items() if i == pcol}
        pa = anchor_purpose_rate(share, rate_by_vintage)
        rec["anchor_purpose_rate"] = pa
        if not pa["levels"]:
            # **`not measurable`, not `disagree`.** The covariance needs a
            # handful of vintages to exist at all, and the first version let an
            # empty level table fall through to the agreement test, which then
            # printed DISAGREE on a run of two vintages. A check that returns a
            # verdict when it could not run is the same defect B8 fixed in its
            # own results file when a `0.000e+00` was indistinguishable from a
            # measured zero. Say which one it is.
            print(f"    not measurable: {pa['vintages']} vintages, the "
                  f"covariance needs at least 4. **No verdict.**")
            rec["anchors_3_and_4_agree"] = None
        else:
            for lv, d in sorted(pa["levels"].items(),
                                key=lambda kv: -kv[1]["cov_with_rate"]):
                print(f"    level {lv!r:<5} mean share {d['mean_share']:.4f}   "
                      f"cov with coupon {d['cov_with_rate']:+.6f}  {d['sign']}")
            pos = [lv for lv, d in pa["levels"].items() if d["cov_with_rate"] > 0]
            code = rec.get("fthb_purchase_codes", [None, None])[1]
            agree = code in pos
            print(f"    anchor 3 named {code!r} the purchase level; anchor 4's "
                  f"positive-covariance levels are {pos}  ->  "
                  f"{'AGREE' if agree else 'DISAGREE, do not pick'}")
            rec["anchors_3_and_4_agree"] = bool(agree)

    print("\n  --- against the pinned positions (§24.1's hole) ---")
    found = {"fico": rec.get("fico_col"), "dti": rec.get("dti_col"),
             "fthb": rec.get("fthb_col"), "purpose": rec.get("purpose_col")}
    bad = {k: (v, ANCHORED[k]) for k, v in found.items() if v != ANCHORED[k]}
    for k, v in found.items():
        print(f"    {k:<8} anchor picked {str(v):>5}   pinned {ANCHORED[k]:>3}   "
              f"{'ok' if v == ANCHORED[k] else '**MISMATCH**'}")
    rec["pinned_mismatch"] = {k: list(t) for k, t in bad.items()}
    if bad:
        print("    **The anchors and the pinned constants disagree.** Do not\n"
              "    edit the constants to match. One of the two is wrong and the\n"
              "    run that pinned them is in git; find out which.")
    fa_ok = rec.get("fico_margin", 0) > 0
    print("\n  §24.6 step one passes only when all four anchors fired **and**\n"
          "  anchors 3 and 4 agree. A field with no margin is a coincidence\n"
          "  wearing an identification; widening a filter until something wins\n"
          "  is the thing C0b exists to stop.")
    passed = (not bad and fa_ok and rec.get("dti_col") is not None
              and rec.get("anchors_3_and_4_agree") is True)
    rec["step_one_passed"] = bool(passed)
    print(f"  step one: {'PASS' if passed else 'NOT PASSED'}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / partial_name("b10_cohort_width_depth", only)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "cohort_width_depth", "diagnostic_only": True,
         "diagnostic_reason":
             "Registered in the B10 availability register §24. Field "
             "identification only; no omega, no triangles, no B8 prediction "
             "(§24.7).",
         **rec}, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# selftest. Constructed cases, answers known before the code runs.
# ---------------------------------------------------------------------------

def _selftest_windows(fails: list) -> None:
    """§9·7's own path. A miss here is a no-op otherwise (MEASUREMENT.md 16)."""
    print("\n  §9·7: window assignment and the fine-grid verdict path")
    edges = [(2008, "pre_crisis"), (2009, "hamp"), (2016, "hamp"),
             (2017, "flex"), (2019, "flex"), (2020, "covid"),
             (2022, "covid"), (2023, "post2023"), (2099, "post2023")]
    bad = [(y, window_of(y), w) for y, w in edges if window_of(y) != w]
    print(f"     window_of on the nine boundary years: "
          f"{'all correct' if not bad else bad}")
    if bad:
        fails.append(f"window_of misassigns {bad}")
    # the five windows must partition the years they claim, with no overlap
    span = [window_of(y) for y in range(1990, 2040)]
    if "outside" in span:
        fails.append("the five windows leave a gap in the year axis")
    print(f"     1990..2039 all claimed by some window: "
          f"{'outside' not in span}")
    if set(FINE_GRIDS) - set(C9_GRIDS):
        fails.append("FINE_GRIDS names a grid C9_GRIDS does not have")
    print(f"     FINE_GRIDS are both in C9_GRIDS: "
          f"{not (set(FINE_GRIDS) - set(C9_GRIDS))}")
    # branch_of must still be a partition, since §9·7 leans on it unchanged
    got = {branch_of(m) for m in (0, 1, 2, 19, 20, 1000)}
    print(f"     branch_of still returns exactly three labels: {sorted(got)}")
    if got != {"dead", "thin", "clears_c9_floor"}:
        fails.append(f"branch_of returned {got}")


# ---------------------------------------------------------------------------
# --pgrid. Registered before the code.
# The two items §8·20·8 left open in §12, answered on **one scan** because both
# want the same population and both quantities exist at the same point inside
# `omega_absorb`. **Not one new object**: `P_orig`, `P_sub`, `u0` and the path
# verdict are all already computed there; this only files them jointly.
# ---------------------------------------------------------------------------

#: §8·26·1. **`1e-6` is not a line this station drew.** It is the published
#: definition of `p_reldiff_tiny` in `b10_omega.json`, transcribed. Changing it
#: here would make the 2x2's row margin a different number from the 0.1083 the
#: results file already carries, which is the whole thing §12 asked about.
PGRID_TINY = 1e-6

#: Half of Freddie's $1,000 origination grid. §8·20·8 measured the grid on
#: 100% of rows on two archives, 50,000 rows each. **This is a hard bound, not
#: an empirical line**: a payment derived from a balance rounded to the nearest
#: $1,000 cannot be off by more than the half-step in relative terms, because
#: `contract_payment` is homogeneous of degree one in the balance.
PGRID_HALF_STEP = 500.0

#: The four cells, `c`/`x` for the payments agreeing or not, `q`/`n` for the
#: path qualifying or not. Fixed here so the table cannot silently lose a cell.
PGRID_CELLS = ("cq", "cn", "xq", "xn")


def pgrid_new_acc() -> dict:
    return {"n": 0, "no_pair": 0, "no_u0": 0,
            "cell": {k: 0 for k in PGRID_CELLS},
            "rel": [], "ratio": [],
            #: §8·26·2's separation test, kept as running extremes so it needs
            #: no second pass and no sample cap to be exact.
            "over": 0, "over_rel_min": None, "under_rel_max": None,
            "over_ratio_max": None, "capped": False,
            #: §8·27. `h = age + rem - term` at the anchor row, and what the
            #: exceedance looks like once the horizon is made internally
            #: consistent with `P_orig`'s own schedule.
            "h": {}, "h_bad": 0, "h_over": {}, "h_under": {},
            "h_cell": {k: {} for k in PGRID_CELLS},
            "over_h": 0, "no_ph": 0, "term_le_age": 0, "n_h": 0,
            "ratio_h": [], "rescued": 0, "newly_over": 0}


def pgrid_over(P_orig, P_sub, u0):
    """§8·26·2's over-the-grid-bound test. `(rel, bound, over)` or `(None,)*3`.

    **Extracted the moment §8·32 needed the same test at a second call site.**
    §8·31 had just finished proving that the fine print of a predicate's
    definition can decide an entire 2x2, so copying `ratio > 1.0` into the
    other file point was not an option (§11 item 11).

    The bound is a hard one: Freddie's origination UPB is on a $1,000 grid on
    every row checked, and `contract_payment` is homogeneous of degree one in
    the balance, so rounding it to the nearest thousand cannot move the
    payment by more than the half-step in relative terms.
    """
    if P_orig is None or P_sub is None or not P_orig > 0:
        return None, None, None
    if u0 is None or not u0 > 0:
        return None, None, None
    rel = abs(P_sub - P_orig) / P_orig
    bound = PGRID_HALF_STEP / u0
    return rel, bound, rel > bound


def ideal_pattern(n_months: int) -> str:
    """§8·32·1. The sign pattern an exactly-ideal clean cure must produce.

    **Not a new formula: this is §8·31·1's derivation stated for any window.**
    On the ideal path the balance sits flat at `B0` through the delinquency
    while the schedule keeps falling, so every delinquent month reads `r > 0`;
    at the cure the balance drops to `f^(k+1)(B0)` against a `b_hat` of
    `f(B0)`, so that month reads `r < 0`. Hence `L-1` pluses and one minus.

    Window 2 gives `+-`, which is what the archives already printed as 64.66%
    of that window (§8·31·2), so the generalisation has one measured anchor.
    """
    return "+" * max(0, n_months - 1) + "-"


def pgrid_file(pg, P_orig, P_sub, derived, u0, t0=None, term=None,
               contract_payment=None) -> None:
    """One `b8like` loop, filed jointly. §8·26·1 and §8·26·2 in one place.

    **Both readings come off the same row**, which is the point of the station:
    §12 registered them as two items and they share a population, a payment
    pair and a path verdict.
    """
    pg["n"] += 1
    if P_orig is None or P_sub is None or not P_orig > 0:
        pg["no_pair"] += 1
        return
    rel = abs(P_sub - P_orig) / P_orig
    consistent = rel < PGRID_TINY
    key = ("c" if consistent else "x") + ("q" if derived else "n")
    pg["cell"][key] += 1
    if len(pg["rel"]) < OMEGA_SAMPLE_CAP:
        pg["rel"].append(rel)
    else:
        pg["capped"] = True
    #: §8·26·3 item 2. A loop whose origination balance will not read cannot be
    #: asked about the grid at all. **Counted apart, never folded into "not
    #: over"** — that would turn "we could not ask" into "we asked and the
    #: answer was no" (§11 item 6).
    if u0 is None or not u0 > 0:
        pg["no_u0"] += 1
        return
    #: **One body, two call sites** (§8·32·3). `rel` was computed above for
    #: the 2x2's row margin; this call is what decides `over`, and the assert
    #: is there so the two can never drift into disagreeing.
    _rel, bound, over = pgrid_over(P_orig, P_sub, u0)
    assert _rel == rel, "pgrid_over disagrees with the row margin's rel"
    ratio = rel / bound
    if len(pg["ratio"]) < OMEGA_SAMPLE_CAP:
        pg["ratio"].append(ratio)
    if over:
        pg["over"] += 1
        pg["over_rel_min"] = (rel if pg["over_rel_min"] is None
                              else min(pg["over_rel_min"], rel))
        pg["over_ratio_max"] = (ratio if pg["over_ratio_max"] is None
                                else max(pg["over_ratio_max"], ratio))
    else:
        pg["under_rel_max"] = (rel if pg["under_rel_max"] is None
                               else max(pg["under_rel_max"], rel))
    pgrid_horizon(pg, t0, term, contract_payment, P_orig, bound, over, key)


def pgrid_horizon(pg, t0, term, contract_payment, P_orig, bound, over,
                  key) -> None:
    """§8·27. `h = age + rem - term`, and the exceedance on a fixed horizon.

    **`h` is a pure field quantity**: three published integers, no interest
    arithmetic anywhere in it. What it can and cannot settle was fixed before the run — in particular a **constant** `h` does not by itself clear
    the horizon, because the relative gap between the two payments varies with
    where the loan sits on its schedule even when the offset does not.

    So the reading is the counterfactual: recompute the substitution on
    `term - age`, the horizon that is internally consistent with `P_orig`'s own
    amortisation, and count the exceedances again.
    """
    if t0 is None or term is None or contract_payment is None:
        pg["h_bad"] += 1
        return
    age, rem = t0[R_AGE], t0[R_REM]
    if age is None or rem is None or not term > 0:
        pg["h_bad"] += 1
        return
    h = age + rem - term
    pg["n_h"] += 1
    pg["h"][h] = pg["h"].get(h, 0) + 1
    (pg["h_over"] if over else pg["h_under"])[h] = \
        (pg["h_over"] if over else pg["h_under"]).get(h, 0) + 1
    pg["h_cell"][key][h] = pg["h_cell"][key].get(h, 0) + 1
    #: §8·27·3 item 2. A loan already past its original term has no horizon to
    #: put a payment on. **A reading, not a defect**, and counted apart from
    #: "the payment would not compute" (§11 item 6).
    n_h = term - age
    if n_h <= 0:
        pg["term_le_age"] += 1
        return
    P_h = substitution_payment(t0, contract_payment, n_override=n_h)
    if P_h is None:
        pg["no_ph"] += 1
        return
    rel_h = abs(P_h - P_orig) / P_orig
    ratio_h = rel_h / bound
    if len(pg["ratio_h"]) < OMEGA_SAMPLE_CAP:
        pg["ratio_h"].append(ratio_h)
    if ratio_h > 1.0:
        pg["over_h"] += 1
        if not over:
            pg["newly_over"] += 1
    elif over:
        pg["rescued"] += 1


def overlap_read(n, n_x, n_y, a, dir_x_in_y, dir_y_in_x, dir_same) -> dict:
    """§8·26·1's reading of a 2x2, as one body. Used by §8·26 and by §8·28.

    **Extracted the moment a second station wanted it**, not before. §8·28·3
    registered itself as "§8·26·1's criteria with the two edges swapped", and
    a second inline copy is how "the same criteria" quietly becomes two.

    Three branches, all structural and all without a threshold: one side sits
    entirely inside the other, the corner cell is empty, or neither. The lift
    is a **deliverable**, and its two anchors are computed from the margins —
    `1` under independence, `1 / max(p_x, p_y)` under containment — so the
    question "which is it nearer to" contains no hand-picked number.
    """
    lift = (a * n / (n_x * n_y)) if (n and n_x and n_y) else None
    p_x = (n_x / n) if n else None
    p_y = (n_y / n) if n else None
    lift_same = (1.0 / max(p_x, p_y)) if (p_x and p_y) else None
    verdict, which = "mixed", None
    if n:
        if a and (a == n_x or a == n_y):
            verdict = "contained"
            which = dir_x_in_y if a == n_x else dir_y_in_x
            if a == n_x and a == n_y:
                which = dir_same
        elif a == 0:
            verdict = "disjoint"
    near = None
    if lift and lift > 0 and lift_same:
        #: **The two anchors can coincide, and that is a reading of its own.**
        #: When one margin saturates at 1.0 — every loop qualifies, say —
        #: `1 / max(p_x, p_y)` is 1, which is also the independence anchor. The
        #: lift then cannot tell the two apart and there is nothing to be
        #: nearer to. Returning `None` here would be indistinguishable from
        #: "there was no lift at all", which is two things in one bucket
        #: (§11 item 6), so it is named.
        if lift_same <= 1.0:
            near = "anchors coincide"
        else:
            #: **The comparison is in log space and it is written without a
            #: logarithm.** §8·19·3's 甲2 counts every `log` call in this file
            #: and refuses the run if there is one, because the one thing this
            #: file must never do is write a residual formula of its own — and
            #: that gate cannot tell a residual from a ratio comparison, nor
            #: should it have to. The boundary between the two anchors is
            #: their geometric mean `sqrt(lift_same)`, so
            #: `lift > sqrt(lift_same)` is `lift * lift > lift_same`. Same
            #: boundary, one multiplication, no transcendental.
            near = ("same" if lift * lift > lift_same
                    else ("independent" if lift * lift < lift_same
                          else "equidistant"))
    #: **Which of the three branches the margins even allow.** §8·28 landed
    #: `mixed` with `p_x + p_y = 1.179`, and at those margins inclusion and
    #: exclusion force `a >= n_x + n_y - n = 20,601`: **the disjoint branch
    #: could not have fired whatever the data did.** A branch that cannot fire
    #: is §11 item 13's defect wearing a criterion's clothes, and the reason it
    #: got past registration is that margins are not knowable before the run.
    #: They are knowable **at read time**, so they are computed and printed
    #: here rather than left for someone to notice.
    #:
    #: `overlap_read` does not refuse on this. The branch is still whatever it
    #: is; what changes is that the printed reading says how many of the three
    #: were reachable, so nobody quotes a `mixed` as though `disjoint` had been
    #: a live alternative.
    a_floor = max(0, (n_x + n_y - n)) if n else None
    a_ceiling = min(n_x, n_y) if n else None
    return {"a": a, "p_x": p_x, "p_y": p_y, "lift": lift,
            "lift_if_independent": 1.0, "lift_if_contained": lift_same,
            "lift_nearer": near, "overlap_verdict": verdict,
            "contained_direction": which,
            "a_floor": a_floor, "a_ceiling": a_ceiling,
            "disjoint_reachable": (a_floor == 0) if n else None,
            "contained_reachable": (a_ceiling > 0) if n else None,
            "branches_reachable": (
                (1 if (a_ceiling or 0) > 0 else 0)
                + (1 if a_floor == 0 else 0) + 1) if n else None}


def print_reachable(pl) -> None:
    """How many of `overlap_read`'s three branches the margins allowed.

    **Printed with every 2x2 this file reads**, because a branch the margins
    exclude is a branch that cannot fire, and a verdict of `mixed` reads very
    differently depending on whether the alternatives were live.
    """
    if pl.get("branches_reachable") is None:
        return
    print(f"     branches the margins allowed: {pl['branches_reachable']} of 3"
          f"   (a had to land in [{pl['a_floor']:,}, {pl['a_ceiling']:,}])")
    if not pl["disjoint_reachable"]:
        print(f"     **the disjoint branch could not fire**: the two margins"
              f" sum above 1, so")
        print(f"     inclusion and exclusion force a >= {pl['a_floor']:,}"
              f" whatever the data does.")
    if not pl["contained_reachable"]:
        print("     **the contained branch could not fire**: one side is"
              " empty.")


def pgrid_payload(pg) -> dict:
    c = pg["cell"]
    n = sum(c.values())
    n_c, n_q = c["cq"] + c["cn"], c["cq"] + c["xq"]
    a = c["cq"]
    #: §8·26·1's two anchors, **derived from the margins, not typed**. Under
    #: independence the lift is 1; when one side sits entirely inside the
    #: other the lift is `1 / max(p_c, p_q)`. Which anchor the observed lift is
    #: nearer to is then a comparison with no hand-picked number in it.
    r = overlap_read(n, n_c, n_q, a, "consistent inside qualified",
                     "qualified inside consistent",
                     "the two sets are identical")
    lift, p_c, p_q = r["lift"], r["p_x"], r["p_y"]
    lift_same, near = r["lift_if_contained"], r["lift_nearer"]
    verdict, which = r["overlap_verdict"], r["contained_direction"]
    #: §8·26·2's separation test, structural: do the two sides' `rel` ranges
    #: touch. `over` is defined by `rel` against a bound that moves with `u0`,
    #: so nothing forces them apart and a clean split would mean something.
    sep = None
    if pg["over"] and pg["over_rel_min"] is not None \
            and pg["under_rel_max"] is not None:
        sep = pg["over_rel_min"] > pg["under_rel_max"]
    if pg["over"] == 0:
        tail = "grid_explains_all"
    elif sep is True:
        tail = "two_populations"
    else:
        tail = "mixed"
    return {"n_b8like": pg["n"], "no_pair": pg["no_pair"],
            "no_u0": pg["no_u0"], "capped": pg["capped"],
            "cell": dict(c), "n_paired": n,
            "n_consistent": n_c, "n_qualified": n_q, "a": a,
            "p_consistent": p_c, "p_qualified": p_q,
            "lift": lift, "lift_if_independent": 1.0,
            "lift_if_contained": lift_same, "lift_nearer": near,
            "overlap_verdict": verdict, "contained_direction": which,
            "n_over": pg["over"],
            "over_rel_min": pg["over_rel_min"],
            "under_rel_max": pg["under_rel_max"],
            "over_ratio_max": pg["over_ratio_max"],
            "separated": sep, "tail_verdict": tail,
            **pgrid_h_payload(pg),
            "q_rel": _q(pg["rel"], (10, 50, 90, 99)),
            "q_ratio": _q(pg["ratio"], (10, 50, 90, 99)),
            "rel_n": len(pg["rel"]), "ratio_n": len(pg["ratio"])}


def pgrid_h_payload(pg) -> dict:
    """§8·27's half of the payload. Separate so §8·26's keys stay where they are.

    **The branch is read on the loops where BOTH horizons computed**, which is
    `len(ratio_h)`. A loop that drops out on `term <= age` was neither rescued
    nor left stranded; folding it into either would answer a question it was
    never asked (§11 item 6).
    """
    hs = pg["h"]
    tot = sum(hs.values())
    disjoint = None
    if pg["h_over"] and pg["h_under"]:
        disjoint = not (set(pg["h_over"]) & set(pg["h_under"]))
    #: Exceedances at the **original** horizon, restricted to that same set.
    over_base = pg["over_h"] + pg["rescued"] - pg["newly_over"]
    if over_base <= 0:
        #: Nothing was over the bound to begin with here, so there is nothing
        #: for the horizon to have caused. **Not the first branch**: that one
        #: says the correction removed the exceedance, and a correction cannot
        #: remove what was not there.
        verdict = "no_reading"
    elif pg["over_h"] == 0:
        verdict = "horizon_is_all"
    elif pg["rescued"] == 0 and pg["newly_over"] == 0:
        verdict = "horizon_is_none"
    else:
        verdict = "mixed"
    return {
        "h_n": pg["n_h"], "h_bad": pg["h_bad"],
        "h_distinct": len(hs), "h_zero": hs.get(0, 0),
        "h_zero_share": (hs.get(0, 0) / tot) if tot else None,
        "h_hist": {str(k): v for k, v in sorted(hs.items())},
        "h_over_hist": {str(k): v for k, v in sorted(pg["h_over"].items())},
        "h_under_hist": {str(k): v for k, v in sorted(pg["h_under"].items())},
        "h_cell_hist": {c: {str(k): v for k, v in sorted(d.items())}
                        for c, d in pg["h_cell"].items()},
        "h_sets_disjoint": disjoint,
        "term_le_age": pg["term_le_age"], "no_ph": pg["no_ph"],
        "n_both_horizons": len(pg["ratio_h"]),
        "over_base_in_both": over_base,
        "n_over_h": pg["over_h"], "rescued": pg["rescued"],
        "newly_over": pg["newly_over"],
        "rescued_share": (pg["rescued"] / over_base) if over_base > 0 else None,
        "q_ratio_h": _q(pg["ratio_h"], (10, 50, 90, 99)),
        "horizon_verdict": verdict,
    }


def print_pgrid(pl) -> None:
    print("\n  A. the population, and the two denominators §12 asked about")
    print(f"     b8like loops reaching the file point: {pl['n_b8like']:,}")
    print(f"     of those, no payment pair: {pl['no_pair']:,}"
          f"    origination balance unreadable: {pl['no_u0']:,}")
    print(f"     the 2x2's denominator is {pl['n_paired']:,}."
          + ("  **capped**" if pl["capped"] else ""))
    print("     (§8·20's published 0.1083 is `p_reldiff` over **every priced**")
    print("      trip with both payments, and 0.1082 is `rate_derived` over")
    print("      **b8like**. Two different denominators, which is one reason")
    print("      two marginals could not settle this. Here both margins are")
    print("      taken on one population, stated rather than assumed away.)")

    c = pl["cell"]
    print("\n  B. §8·26·1's 2x2")
    print(f"     {'':<26}{'path qualifies':>16}{'does not':>12}{'row':>12}")
    print(f"     {'|dP|/P < 1e-6':<26}{c['cq']:>16,}{c['cn']:>12,}"
          f"{pl['n_consistent']:>12,}")
    print(f"     {'otherwise':<26}{c['xq']:>16,}{c['xn']:>12,}"
          f"{c['xq'] + c['xn']:>12,}")
    print(f"     {'column':<26}{pl['n_qualified']:>16,}"
          f"{c['cn'] + c['xn']:>12,}{pl['n_paired']:>12,}")
    if pl["p_consistent"] is not None:
        print(f"     margins: consistent {pl['p_consistent']:.4f}"
              f"   qualified {pl['p_qualified']:.4f}")

    print()
    v = pl["overlap_verdict"]
    if v == "contained":
        print("     §8·26·1 -> FIRST BRANCH. One side sits entirely inside the")
        print(f"     other: {pl['contained_direction']}. The two 0.108 are one")
        print("     set, and §12's question is answered by containment rather")
        print("     than by a rate that happens to agree to four places.")
    elif v == "disjoint":
        print("     §8·26·1 -> SECOND BRANCH. The cell is empty: no loop is")
        print("     both consistent and qualified. **Two separate mechanisms**")
        print("     each push the rate to a tenth, and they never coincide.")
    else:
        print("     §8·26·1 -> THIRD BRANCH, mixed (R01). Neither containment")
        print("     nor disjointness. **That is a reading, not a failure**:")
        print("     it says the two 0.108 are neither the same set nor")
        print("     independent of each other, which is exactly why two")
        print("     marginals could not settle it (fixed before the run).")
    if pl["lift"] is not None:
        print(f"     lift {pl['lift']:.4f}   anchors: independent 1.0000,"
              f" contained {pl['lift_if_contained']:.4f}"
              f"   nearer: {pl['lift_nearer']}")
        print("     **Both anchors are computed from the margins**, so which")
        print("     one it is nearer to contains no hand-picked number.")
    print_reachable(pl)

    print("\n  C. §8·26·2: |dP|/P against the grid's hard bound 500/u0")
    q, r = pl["q_ratio"], pl["q_rel"]
    print(f"     |dP|/P        p10 {r[0]:.3e}  p50 {r[1]:.3e}"
          f"  p90 {r[2]:.3e}  p99 {r[3]:.3e}")
    print(f"     over bound    p10 {q[0]:.4f}  p50 {q[1]:.4f}"
          f"  p90 {q[2]:.4f}  p99 {q[3]:.4f}   (ratio to 500/u0)")
    print(f"     loops over the bound: {pl['n_over']:,} of {pl['ratio_n']:,}"
          + (f"   worst {pl['over_ratio_max']:.4f}x"
             if pl["over_ratio_max"] else ""))
    if pl["over_rel_min"] is not None:
        print(f"     smallest |dP|/P among the over set  {pl['over_rel_min']:.6e}")
    if pl["under_rel_max"] is not None:
        print(f"     largest  |dP|/P among the under set {pl['under_rel_max']:.6e}")
    print()
    t = pl["tail_verdict"]
    if t == "grid_explains_all":
        print("     §8·26·2 -> FIRST BRANCH. Nothing exceeds the bound, so the")
        print("     grid explains every one of these payment differences **by")
        print("     construction**. `P_sub`'s tail is the grid.")
    elif t == "two_populations":
        print("     §8·26·2 -> SECOND BRANCH. The over set and the under set")
        print("     do not overlap in |dP|/P at all, so they are two kinds of")
        print("     object rather than one tail. **Those loans are not on")
        print("     schedule.** The join to §12 item 9 is the next station,")
        print("     not this one.")
    else:
        print("     §8·26·2 -> THIRD BRANCH, mixed (R01). Loops do exceed the")
        print("     bound, and their |dP|/P range overlaps the under set's, so")
        print("     the exceedances are the far end of one distribution rather")
        print("     than a separate population.")

    print("\n  D. §8·27: is the exceedance the horizon or the balance")
    print(f"     h = age + rem - term at the anchor row, on {pl['h_n']:,} loops"
          f"   ({pl['h_bad']:,} could not be asked)")
    print(f"     distinct values of h: {pl['h_distinct']}"
          + (f"   h == 0 on {pl['h_zero']:,}"
             f" = {pl['h_zero_share']:.4f}" if pl["h_zero_share"] is not None
             else ""))
    _hh = list(pl["h_hist"].items())
    print("     h histogram (C0b, every value): "
          + ", ".join(f"{k}x{v:,}" for k, v in _hh[:14])
          + (" ..." if len(_hh) > 14 else ""))
    print(f"     h on the over set:  "
          + ", ".join(f"{k}x{v:,}"
                      for k, v in list(pl["h_over_hist"].items())[:8]))
    print(f"     h on the under set: "
          + ", ".join(f"{k}x{v:,}"
                      for k, v in list(pl["h_under_hist"].items())[:8]))
    if pl["h_sets_disjoint"] is None:
        print("     the two h sets: **the question cannot be asked** — one of")
        print("     the two sides is empty, and the empty set is vacuously")
        print("     disjoint from everything, which would read as the")
        print("     strongest possible evidence for the horizon.")
    else:
        print(f"     the two h sets are disjoint: {pl['h_sets_disjoint']}")
    print("     (§8·27·2 item 2: disjoint would mean h alone decides the")
    print("      exceedance, which is the strongest shape a horizon cause has)")
    _c78 = pl["h_cell_hist"].get("xq", {})
    print("     h on §8·26·1's `path qualifies, payments disagree` cell: "
          + (", ".join(f"{k}x{v:,}" for k, v in list(_c78.items())[:8])
             or "empty"))
    print("     (that cell is where P_orig is already proved right by the path")
    print("      test, so what h does there is fixed before the run)")

    print(f"\n     recomputed on term - age: both horizons ran on "
          f"{pl['n_both_horizons']:,} loops"
          f"   (term <= age on {pl['term_le_age']:,},"
          f" no payment on {pl['no_ph']:,})")
    _qh = pl["q_ratio_h"]
    print(f"     over bound, fixed horizon   p10 {_qh[0]:.4f}  p50 {_qh[1]:.4f}"
          f"  p90 {_qh[2]:.4f}  p99 {_qh[3]:.4f}")
    print(f"     over at the original horizon {pl['over_base_in_both']:,}"
          f"  ->  at the fixed one {pl['n_over_h']:,}"
          f"   (rescued {pl['rescued']:,}, newly over {pl['newly_over']:,})")
    print()
    _hv = pl["horizon_verdict"]
    if _hv == "no_reading":
        print("     §8·27·1 -> NO READING. Nothing exceeded the bound on the")
        print("     loops where both horizons ran, so there was nothing for")
        print("     the correction to remove. **Not the first branch**: a")
        print("     correction cannot remove what was not there.")
    elif _hv == "horizon_is_all":
        print("     §8·27·1 -> FIRST BRANCH. Nothing exceeds the bound once")
        print("     the horizon is made consistent with P_orig's own schedule.")
        print("     **The horizon is the whole cause.** §8·26·2's 36% is ours,")
        print("     and `P_sub` needs the correction before it can be used.")
    elif _hv == "horizon_is_none":
        print("     §8·27·1 -> SECOND BRANCH. Not one loop changed side. **The")
        print("     horizon is not the cause at all**, so the exceedance is in")
        print("     the balance: the reported balance is not the scheduled one.")
        print("     Which of (a) prepayment and (c) bookkeeping it is, this")
        print("     station does not say (fixed before the run). §8·26·3 is")
        print("     now worth running.")
    else:
        print("     §8·27·1 -> THIRD BRANCH, mixed (R01). The correction moves")
        print("     some loops and not others, so the horizon is one cause")
        print("     among others and its share is the number above.")
    if pl["rescued_share"] is not None:
        print(f"     share of the original exceedance the horizon explains: "
              f"{pl['rescued_share']:.4f}")

    print("\n  E. §8·26·3's caveats, printed with the reading")
    print("     1. `derived` is judged under `P_orig`, and §8·20·8 already")
    print("        ruled that its qualifying subsample carries a selection:")
    print("        it is chosen by the borrower's origination balance landing")
    print("        on a round thousand, which is a property of the borrower.")
    print("        **What is read here is overlap, not level.**")
    print(f"     2. {pl['no_u0']:,} loops could not be asked about the grid at")
    print("        all; they are counted apart, never folded into `not over`.")
    print(f"     3. sample cap {'IN EFFECT' if pl['capped'] else 'not reached'}"
          f" ({OMEGA_SAMPLE_CAP:,}).")


def cmd_pgrid(only) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    if not vs:
        print(f"  no archives under {RAW}")
        return 1
    sys.path.insert(0, str(ROOT / "experiments"))
    import b8_cmt_fetch as F                       # noqa: E402
    import b8_loop_omega as LO                     # noqa: E402
    import b8_omega as W                           # noqa: E402
    import b8_0a_gate as G                         # noqa: E402
    import b10_c8_1d_freddie as FR                 # noqa: E402

    if W.MAX_H != CURVE_MAX_H:
        print(f"  b8_omega.MAX_H is {W.MAX_H} and this file says "
              f"{CURVE_MAX_H}. Fix one; nothing is read until then.")
        return 1
    if not print_crosscheck(resid_crosscheck(W, G)):
        print("\n  §8·19·3 did not pass. Nothing was read. Fix it first.")
        return 1
    print()
    prior = prior_json(ROOT, partial_name("b10_pgrid", only))
    src, files = F.load_treasury()
    if not src:
        print("  no Treasury curve under data/raw/cmt.")
        return 1
    pos, tab = LO.curve_table_from(src, LO.RULE)

    print("§8·26: the two items §8·20·8 left open in §12, on one scan.\n"
          "  Same population, same payment pair, same path verdict — they\n"
          "  were two items only because they were noticed on two days.\n")
    acc = omega_new_acc()
    for v in vs:
        orig, _ = FR.read_orig(v)
        with zipfile.ZipFile(archive(v)) as zf:
            with zf.open(f"sample_perf_{v}.txt") as raw:
                seq, batch = None, []
                for line in io.TextIOWrapper(raw, encoding="utf-8",
                                             newline=""):
                    if not line.strip():
                        continue
                    f = line.split("|")
                    if f[0] != seq:
                        if seq is not None:
                            omega_absorb(acc, batch, orig.get(seq), v, pos,
                                         tab, CURVE_MAX_H, W, G,
                                         FR.contract_payment)
                        seq, batch = f[0], []
                    batch.append(floor_row(f))
                if seq is not None:
                    omega_absorb(acc, batch, orig.get(seq), v, pos, tab,
                                 CURVE_MAX_H, W, G, FR.contract_payment)
        print(f"  {v}  done   b8like {acc['b8like']['n']:,}"
              f"   filed {acc['pgrid']['n']:,}", flush=True)
    pl = pgrid_payload(acc["pgrid"])
    print_vs_prior(prior, pl, partial_name("b10_pgrid", only))
    print_pgrid(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / partial_name("b10_pgrid", only)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "pgrid",
         "registered": "before the code",
         "population": "the b8like clean-cure round trips of §8·20, filed "
                       "jointly on (payments agree) x (path qualifies)",
         "tiny": PGRID_TINY, "half_step": PGRID_HALF_STEP,
         "caveats": ["`derived` is judged under P_orig, whose qualifying "
                     "subsample carries §8·20·8's selection",
                     "loops with no readable origination balance are counted "
                     "apart, never folded into `not over`",
                     "what is read is overlap and exceedance, not level"],
         **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --o18join. Registered before the code.
# §8·26·2's over-bound loops against §12 item 9's O18 months, joined on the
# **loan**. Both predicates are computed inside one loan's row block, so no
# loan number is ever stored: the unit of the join is the unit of the scan.
# ---------------------------------------------------------------------------

#: §8·28·3's four cells. `A` is "carries at least one over-bound loop", `B` is
#: "carries at least one O18 residue month with the counter saying paid".
OJ_CELLS = ("AB", "Ab", "aB", "ab")

#: §8·28·5 item 1. A loan can carry both kinds of loop, and folding that into
#: `A` alone would hide it.
OJ_SPLIT = ("all_over", "some_over", "none_over", "no_loop")


def o18_months(rows, codes, O) -> tuple:
    """§8·28·1's predicate B, per loan. `(residue_le0, residue_frozen, pairs)`.

    **Transcribed from `b10_o18_null.py`'s scan loop, condition by condition**,
    with its own constants imported rather than retyped: `O.AGE_SPLIT`,
    `O.P_ASSIST`, `O.ASSIST_CODES`, `O.parse_delinq`, `O.next_period`,
    `O.delta_bucket`, `O.population_of`. This station has already paid once for
    treating a stand-in's constants as the real module's, and a predicate
    copied by eye is the same mistake with more steps.

    `codes[i]` is the assistance code of `rows[i]`, read off the raw line in
    the command loop so `floor_row` keeps its shape (§8·25·2's precedent).
    """
    le0 = frozen = pairs = 0
    for i in range(1, len(rows)):
        p0, cur = rows[i - 1], rows[i]
        per0, per = p0[R_PERIOD], cur[R_PERIOD]
        u0, upb = p0[R_UPB], cur[R_UPB]
        a0, age = p0[R_AGE], cur[R_AGE]
        if u0 is None or upb is None or a0 is None or age is None:
            continue
        if per != O.next_period(per0) or not (u0 > 0 and upb > 0):
            continue
        pairs += 1
        if u0 != upb:
            continue
        frozen += 1
        pop = O.population_of(a0 >= O.AGE_SPLIT and age >= O.AGE_SPLIT,
                              codes[i] in O.ASSIST_CODES)
        if pop != "residue":
            continue
        d0 = O.parse_delinq(p0[R_DELINQ])
        d1 = O.parse_delinq(cur[R_DELINQ])
        #: §41.1: `RA` and blanks are counted apart and are **not** a delta of
        #: zero. Folding them in here would put the carrier's own missing
        #: values on the "borrower paid" side of the join.
        if d0 is None or d1 is None:
            continue
        if O.delta_bucket(d1 - d0) == "le0":
            le0 += 1
    return le0, frozen, pairs


def o18join_new_acc() -> dict:
    return {"loans": 0, "cell": {k: 0 for k in OJ_CELLS},
            "split": {k: 0 for k in OJ_SPLIT},
            "loans_with_loop": 0, "loans_with_B_no_loop": 0,
            #: §8·28·5 item 3. The month counts, kept only so they can be set
            #: beside `b10_o18_null.json`'s. **Never reported as the reading.**
            "months_le0": 0, "months_frozen": 0, "months_pairs": 0,
            "loops": 0, "loops_over": 0, "loops_scored": 0}


def o18join_absorb(acc, one, rows, codes, orig, pos, tab, max_h, W, G,
                   contract_payment, O) -> None:
    """One loan. Predicate A from §8·26's own file point, predicate B here.

    **`A` is not a second implementation of "over the bound".** It is the same
    `omega_absorb` call `--pgrid` makes, into the same `pgrid` subtree, read as
    a **delta across this loan**. Writing the test again here is exactly how
    two stations end up citing one predicate and measuring two.

    The delta is taken rather than a fresh accumulator per loan because
    `omega_new_acc` allocates some fifty containers and there are 1.36 million
    loans. `pgrid`'s `ratio` list is capped at `OMEGA_SAMPLE_CAP`; §8·26
    measured 115,081 entries against a cap of a million, so the cap cannot bite
    here — **and if it ever did, the delta would silently read zero**, which is
    why `capped` is asserted below rather than assumed.
    """
    acc["loans"] += 1
    pg = one["pgrid"]
    over0, scored0, n0 = pg["over"], len(pg["ratio"]), pg["n"]
    omega_absorb(one, rows, orig, None, pos, tab, max_h, W, G,
                 contract_payment)
    over = pg["over"] - over0
    scored = len(pg["ratio"]) - scored0
    acc["loops"] += pg["n"] - n0
    acc["loops_scored"] += scored
    acc["loops_over"] += over
    le0, frozen, pairs = o18_months(rows, codes, O)
    acc["months_le0"] += le0
    acc["months_frozen"] += frozen
    acc["months_pairs"] += pairs
    B = le0 > 0
    if scored == 0:
        acc["split"]["no_loop"] += 1
        if B:
            acc["loans_with_B_no_loop"] += 1
        return
    acc["loans_with_loop"] += 1
    acc["split"]["all_over" if over == scored else
                ("none_over" if over == 0 else "some_over")] += 1
    A = over > 0
    acc["cell"][("A" if A else "a") + ("B" if B else "b")] += 1


def o18join_payload(acc) -> dict:
    """§8·28·3, and it is `pgrid_payload`'s overlap block with two new edges.

    The verdict, the lift and the two margin-derived anchors are computed by
    `overlap_read`, which `pgrid_payload` calls too — one body, two stations,
    so the two 2x2s cannot drift into being read by two rules.
    """
    c = acc["cell"]
    n = sum(c.values())
    n_A, n_B = c["AB"] + c["Ab"], c["AB"] + c["aB"]
    r = overlap_read(n, n_A, n_B, c["AB"],
                     "A inside B", "B inside A", "A and B are the same set")
    return {"loans": acc["loans"], "loans_with_loop": acc["loans_with_loop"],
            "loans_with_B_no_loop": acc["loans_with_B_no_loop"],
            "cell": dict(c), "n_joined": n, "n_A": n_A, "n_B": n_B,
            "split": dict(acc["split"]),
            "loops": acc["loops"], "loops_scored": acc["loops_scored"],
            "loops_over": acc["loops_over"],
            "months_le0": acc["months_le0"],
            "months_frozen": acc["months_frozen"],
            "months_pairs": acc["months_pairs"], **r}


def print_o18join(pl) -> None:
    print("\n  A. the join's population (§8·28·2)")
    print(f"     loans scanned {pl['loans']:,}"
          f"   carrying at least one scored loop {pl['loans_with_loop']:,}")
    print(f"     loans with an O18 month but no scored loop: "
          f"{pl['loans_with_B_no_loop']:,}")
    print("     (only a loan with a loop can have A, so the 2x2's denominator")
    print("      is the loans that have one. The line above is what that")
    print("      choice leaves outside, printed rather than left in my head.)")
    print(f"     loops {pl['loops']:,}   scored {pl['loops_scored']:,}"
          f"   over the bound {pl['loops_over']:,}")

    print("\n  B. §8·28·5 item 3: the O18 months against their own artifact")
    print(f"     consecutive priced pairs {pl['months_pairs']:,}"
          f"   frozen {pl['months_frozen']:,}"
          f"   residue with the counter saying paid {pl['months_le0']:,}")
    print("     **Set these beside `results/b10_o18_null.json` before reading")
    print("     anything below.** Same predicate, same archives: if they do")
    print("     not agree the predicate was transcribed wrong, and that is a")
    print("     hard stop, not a footnote (fixed before the run).")

    c = pl["cell"]
    print("\n  C. §8·28·3's 2x2, on loans")
    print(f"     {'':<34}{'has an O18 month':>18}{'none':>10}{'row':>12}")
    print(f"     {'has an over-bound loop':<34}{c['AB']:>18,}{c['Ab']:>10,}"
          f"{pl['n_A']:>12,}")
    print(f"     {'none':<34}{c['aB']:>18,}{c['ab']:>10,}"
          f"{c['aB'] + c['ab']:>12,}")
    print(f"     {'column':<34}{pl['n_B']:>18,}"
          f"{c['Ab'] + c['ab']:>10,}{pl['n_joined']:>12,}")
    if pl["p_x"] is not None:
        print(f"     margins: over-bound {pl['p_x']:.4f}"
              f"   O18 {pl['p_y']:.4f}")
    s = pl["split"]
    print(f"     §8·28·5 item 1, the three-way split of loans with loops: "
          f"all over {s['all_over']:,}, some {s['some_over']:,}, "
          f"none {s['none_over']:,}")

    print()
    v = pl["overlap_verdict"]
    if v == "contained":
        print("     §8·28·3 -> FIRST BRANCH. One side sits entirely inside the")
        print(f"     other: {pl['contained_direction']}.")
        print("     Written before the run: the same loans")
        print("     both fail to amortise when the counter says they paid AND")
        print("     sit off their own schedule. **Two deviations in opposite")
        print("     directions on one set of borrowers reads as reporting")
        print("     behaviour rather than borrower behaviour** — evidence for")
        print("     (c), against (a).")
    elif v == "disjoint":
        print("     §8·28·3 -> SECOND BRANCH. The corner cell is empty: no")
        print("     loan has both. Fixed before the run: O18 is balance-too-high and")
        print("     the over-bound set, if it is prepayment, is balance-too-")
        print("     low. **Disjoint is what (a) and (c) each owning a")
        print("     different set of borrowers looks like.**")
    else:
        print("     §8·28·3 -> THIRD BRANCH, mixed (R01). Both kinds of loan")
        print("     exist and the proportions are the reading. **Not to be")
        print("     told as either of the other two**.")
    if pl["lift"] is not None:
        print(f"     lift {pl['lift']:.4f}   anchors: independent 1.0000,"
              f" contained {pl['lift_if_contained']:.4f}"
              f"   nearer: {pl['lift_nearer']}")
        print(f"     (denominator {pl['n_joined']:,}, per §8·28·2)")
    print_reachable(pl)

    print("\n  D. what this does NOT settle (fixed before the run, §8·28·6)")
    print("     **This station does not choose between (a) borrowers paying")
    print("     ahead and (c) the servicer's bookkeeping.** All three branches")
    print("     speak to whose territory is larger, none of them to what the")
    print("     thing is. §8·27 killed (b); (a) against (c) is not here.")
    print("     Months and loans are not interchangeable either: one loan")
    print("     contributes many months, and this station reports loans only")
    print("     (§8·28·5 item 2).")


def cmd_o18join(only) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    if not vs:
        print(f"  no archives under {RAW}")
        return 1
    sys.path.insert(0, str(ROOT / "experiments"))
    import b8_cmt_fetch as F                       # noqa: E402
    import b8_loop_omega as LO                     # noqa: E402
    import b8_omega as W                           # noqa: E402
    import b8_0a_gate as G                         # noqa: E402
    import b10_c8_1d_freddie as FR                 # noqa: E402
    import b10_o18_null as O                       # noqa: E402

    if W.MAX_H != CURVE_MAX_H:
        print(f"  b8_omega.MAX_H is {W.MAX_H} and this file says "
              f"{CURVE_MAX_H}. Fix one; nothing is read until then.")
        return 1
    if not print_crosscheck(resid_crosscheck(W, G)):
        print("\n  §8·19·3 did not pass. Nothing was read. Fix it first.")
        return 1
    print()
    name = partial_name("b10_o18join", only)
    prior = prior_json(ROOT, name)
    src, files = F.load_treasury()
    if not src:
        print("  no Treasury curve under data/raw/cmt.")
        return 1
    pos, tab = LO.curve_table_from(src, LO.RULE)

    print("§8·28: §8·26·2's over-bound loops against §12 item 9's O18 months,\n"
          "  joined on the loan. Both predicates in one pass, and O18's own\n"
          f"  constants are imported: AGE_SPLIT {O.AGE_SPLIT}, assistance "
          f"column {O.P_ASSIST + 1} (one-based), codes {O.ASSIST_CODES}.\n")
    acc = o18join_new_acc()
    one = omega_new_acc()
    for v in vs:
        orig, _ = FR.read_orig(v)
        with zipfile.ZipFile(archive(v)) as zf:
            with zf.open(f"sample_perf_{v}.txt") as raw:
                seq, batch, codes = None, [], []
                for line in io.TextIOWrapper(raw, encoding="utf-8",
                                             newline=""):
                    if not line.strip():
                        continue
                    f = line.rstrip("\r\n").split("|")
                    if f[0] != seq:
                        if seq is not None:
                            o18join_absorb(acc, one, batch, codes,
                                           orig.get(seq), pos, tab,
                                           CURVE_MAX_H, W, G,
                                           FR.contract_payment, O)
                        seq, batch, codes = f[0], [], []
                    batch.append(floor_row(f))
                    #: §8·25·2's precedent: a field `floor_row` does not carry,
                    #: read off the raw line so 規矩 19's surface stays put.
                    codes.append(f[O.P_ASSIST].strip()
                                 if len(f) > O.P_ASSIST else "")
                if seq is not None:
                    o18join_absorb(acc, one, batch, codes, orig.get(seq),
                                   pos, tab, CURVE_MAX_H, W, G,
                                   FR.contract_payment, O)
        print(f"  {v}  done   loans {acc['loans']:,}"
              f"   with a loop {acc['loans_with_loop']:,}"
              f"   O18 months {acc['months_le0']:,}", flush=True)

    #: The delta trick in `o18join_absorb` reads zero once the sample cap
    #: bites, so the cap is checked rather than trusted (§11 item 13's first
    #: kind: a counter that has stopped counting).
    if one["pgrid"]["capped"]:
        print("\n  the pgrid sample cap was reached, so the per-loan deltas")
        print("  stopped counting partway. Nothing is read. Raise the cap.")
        return 1
    pl = o18join_payload(acc)
    print_vs_prior(prior, pl, name)
    print_o18join(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / name
    out.write_text(json.dumps(
        {"stage": "B10", "step": "o18join",
         "registered": "before the code",
         "predicate_A": "at least one loop with |dP|/P > 500/u0 "
                        "(§8·26·2, the same pgrid_file call)",
         "predicate_B": "at least one O18 residue month with the delinquency "
                        "counter not rising and the balance frozen "
                        "(b10_o18_null.py's conditions, its constants "
                        "imported)",
         "denominator": "loans carrying at least one scored loop (§8·28·2)",
         "caveats": ["months and loans are different units and this file "
                     "reports loans (§8·28·5 item 2)",
                     "A is `at least one`; the three-way split is beside it",
                     "this station does not choose between prepayment and "
                     "bookkeeping (§8·28·4)"],
         **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
# --gridvar. Registered before the code.
# §8·12 re-asked on the second carrier: does the grid decide the reading of
# omega here too. **Not one new object.** The windows are §8·22's, omega is
# §8·23's `sub` scheme, the grids are `b10_support.GRIDS`, and the reduction,
# the cycle test, the R^2 and its permutation null are all imported from
# `b10_holonomy_ladder`. What is written here is the wiring and the census.
# ---------------------------------------------------------------------------

def state_delinq(s: str, SUP, tally=None) -> str:
    """Freddie's delinquency field as a label. **Anything unnameable is `UNK`.**

    §8·25·3. §8·22 counted 125,824 rows on this carrier whose status is neither
    `00` nor a two-digit non-zero code, and §8·15 had just finished paying for
    the other carrier's version of exactly this: `delinq == 99` fell through
    `anchor_states`' value range, kept `None`, and `g1(None)` returned `"90+"`.
    A row nobody could name was read as a deep delinquency for as long as that
    lasted.

    So this returns a label that has its own vertex in `g1`/`g2`/`g3` rather
    than a value some grid will fold. `RA` is already Freddie's own unavailable
    code and already has its own node, so it passes through under its own name
    and is **counted apart from `UNK`** (§11 item 6): "the field says
    unavailable" and "this file cannot name the value" are two things.

    `tally` receives the **raw** value, every value, so the alphabet is
    enumerated rather than picked (C0b). It counts label reads over loop
    windows, so a row inside two windows is read twice; that is what the paths
    are built from and therefore what is worth counting.
    """
    if tally is not None:
        tally[s] += 1
    if len(s) == 2 and s.isdigit():
        return s
    if s == SUP.RA:
        return SUP.RA
    return SUP.UNK


#: §8·25·2's four cells plus the fifth thing that is not a cell. Column 12
#: unreadable is **not** column 12 zero (§8·14·5, 失效模式 20), so it stands
#: outside the table instead of being counted on the "not positive" side.
GV_DEFER_CELLS = ("col12+_f25+", "col12+_f25-", "col12-_f25+", "col12-_f25-")


def defer_xtab_key(c12, f25):
    """`None` when column 12 will not read, else one of `GV_DEFER_CELLS`.

    Extracted from the command loop so it can be exercised on a fixture. A key
    built inline in a scan is a key nothing ever checks, and this one carries
    the whole of §8·25·2's table.
    """
    if c12 is None:
        return None
    return (("col12+" if c12 > 0 else "col12-")
            + ("_f25+" if f25 in ("P", "C") else "_f25-"))

#: Perf field 25, one-based: Freddie's deferral indicator, `P` or `C`.
#: `b10_support.raw_state` judges deferral by this and §8·22 / §8·23 judge it
#: by column 12 being positive. §8·25·2 keeps column 12 as the working
#: definition and measures the disagreement rather than assuming it away.
P_DEFERRAL_IDX = 24


def gridvar_new_acc() -> dict:
    return {"loans": 0, "loops": 0, "measurable": 0, "drop": {},
            "t_M_row_reads_current": 0, "alphabet": Counter(),
            "not_cycle": {}, "by_vintage": {},
            #: §8·25·2, filled by the command loop from the raw split line so
            #: `floor_row` is not touched and 規矩 19's surface stays put.
            "defer_xtab": {k: 0 for k in GV_DEFER_CELLS},
            "defer_col12_unreadable": 0, "defer_rows": 0}


def gridvar_absorb(acc, rows, orig, vintage, pos, tab, max_h, r_month,
                   contract_payment, SUP, grids, reduce_fn, cycle_fn) -> None:
    """One loan. §8·22's windows, §8·23's omega, and one reduced path per grid.

    The path recipe is `b10_holonomy_ladder.loop_paths`, transcribed rather
    than called because that function reads a Fannie `Core` and this side has
    8-tuples. **Both of its corrections come with it, and they are the reason
    it is transcribed line for line instead of rewritten:**

    One, the walk is **closed by hand**. `t_M == t_B` on most loops, so the
    last row of the window is the modification and the path stops at `modified`
    without returning. Leg 3 exists as an edge and occupies no month. Demanding
    a row to prove the return read zero cycles on the whole modification arm
    when the other side first tried it.

    Two, the interior reads the **delinquency field only**. A modification flag
    that persists after its event is a stale mark, not a vertex; the window
    carries exactly one event and it sits at `t_M`, which is B8's index and
    B8's arm.
    """
    acc["loans"] += 1
    found, _c = find_loops_rows(rows, ("Y", "P"))
    for rec in found:
        if not rec["closed"] or not all(rec["ok"].values()):
            continue
        acc["loops"] += 1
        pays = loop_payments(rows, rec, orig, contract_payment)
        status, m = loop_omega(rows, rec, pays["sub"], pos, tab, max_h,
                               r_month)
        if status != "ok":
            acc["drop"][status] = acc["drop"].get(status, 0) + 1
            continue
        acc["measurable"] += 1
        arm = rec["arm"]
        start_raw, seq, at_M = gridvar_states(rows, rec, SUP,
                                              acc["alphabet"])
        if at_M == "00":
            acc["t_M_row_reads_current"] += 1
        om = m["omega"]
        bv = acc["by_vintage"].setdefault(vintage, {})
        for gname, gf in grids:
            red = gridvar_reduce(start_raw, seq, gf, reduce_fn)
            nc = acc["not_cycle"].setdefault(gname, {"mod": 0, "defer": 0})
            if not cycle_fn(red):
                nc[arm] += 1
                continue
            cell = bv.setdefault(gname, {}).setdefault(
                arm, {"keys": [], "om": []})
            cell["keys"].append(red)
            cell["om"].append(om)


def gridvar_states(rows, rec, SUP, tally=None):
    """`(start_raw, seq, at_M)` for one loop. **No grid, no reduction.**

    `at_M` is what the delinquency field read at `t_M` **before** the arm's
    label went in, which is the one thing here worth counting: §8·22·9 measured
    that Freddie writes the modification flag **after** the cure, so an onset
    row reading `00` is this carrier's shape and not a defect.
    `seq[j] != "modified"` would instead be true on every loop at every grid,
    and a count that cannot come out any other way measures nothing
    (§11 item 13).
    """
    t_A, t_M, t_B = rec["t_A"], rec["t_M"], rec["t_B"]
    start_raw = state_delinq(rows[t_A][R_DELINQ], SUP, tally)
    seq = [state_delinq(rows[i][R_DELINQ], SUP, tally)
           for i in range(t_A + 1, t_B + 1)]
    j = t_M - (t_A + 1)
    if not 0 <= j < len(seq):
        #: **An assertion and not a counter, and the difference is §11 item
        #: 13.** `find_loops_rows` sets `t_A = last_cur[t_M]` and
        #: `t_B = first_cur[t_M]`, so `t_A < t_M <= t_B` holds by its own
        #: construction — and that function is in **this** file, three hundred
        #: lines up, not across a file boundary. A tally on something the same
        #: file makes impossible is a counter that cannot fire, which is the
        #: fourth one this station has caught. `b10_holonomy_ladder` counts
        #: this instead of raising and is right to: there `t_M` arrives from
        #: `b8_loops`, another file, and the two could drift apart.
        raise RuntimeError(
            f"t_M {t_M} is outside its own window ({t_A}, {t_B}]. "
            "find_loops_rows guarantees t_A < t_M <= t_B; if that changed, "
            "the path recipe changed with it and nothing here is readable.")
    at_M = seq[j]
    seq[j] = SUP.MODIFIED if rec["arm"] == "mod" else SUP.DEFERRED
    return start_raw, seq, at_M


def gridvar_reduce(start_raw, seq, gf, reduce_fn):
    """One grid: coarsen, close the walk by hand, reduce.

    **The closing step is the correction `b10_holonomy_ladder.loop_paths` had
    to make, and it travels with the recipe.** `t_M == t_B` on most loops, so
    the last row of the window *is* the event and the path stops there without
    returning; leg 3 exists as an edge and occupies zero months. Requiring a
    row to prove the return read zero cycles on a whole arm when the other side
    first tried it.
    """
    start = gf(start_raw)
    mapped = [start] + [gf(s) for s in seq]
    mapped = [x for x in mapped if x != "__drop__"]
    mapped.append(start)              # leg 3, which may occupy no month
    return reduce_fn(mapped)


def gridvar_cell(keys, om, r2_of, r2_null, np, seed) -> dict:
    """One (grid, arm): observed R^2, its permutation null, `E`, and `pct`.

    `b10_holonomy_ladder.variance_of`'s body, with the same two refusals: fewer
    than two points has no variance to explain, and a cell whose omega is
    constant has **no referent** rather than a zero.
    """
    n = len(om)
    empty = {"n": n, "classes": 0, "r2": None, "null_p50": None,
             "null_p95": None, "pct": None, "E": None, "min_class": None,
             "top_path": None}
    if n < 2:
        return empty
    cnt = Counter(keys)
    extra = {"min_class": int(min(cnt.values())),
             "top_path": " -> ".join(cnt.most_common(1)[0][0])}
    uniq = {k: j for j, k in enumerate(dict.fromkeys(keys))}
    codes = np.array([uniq[k] for k in keys], dtype=np.int64)
    omv = np.asarray(om, dtype=float)
    obs = r2_of(codes, omv)
    if not np.isfinite(obs):
        return {**empty, "classes": len(uniq), **extra}
    rng = np.random.default_rng(seed)
    null = np.array(r2_null(codes, omv, rng), dtype=float)
    p50 = float(np.median(null))
    return {"n": n, "classes": len(uniq), "r2": float(obs), "null_p50": p50,
            "null_p95": float(np.percentile(null, 95)),
            "pct": float((null < obs).mean()), "E": float(obs - p50), **extra}


def gridvar_payload(acc, ladder, r2_of, r2_null, perm_seed, n_perm, np,
                    zlib) -> dict:
    """Pooled first (§8·25·4's reading), then the same table per vintage.

    **The pool is built from the per-vintage cells, not accumulated twice.**
    One copy of every `(path, omega)` pair exists and both tables are read off
    it; a second accumulator is how two tables that cite the same population
    end up describing two.

    **`ladder` comes in rather than out of the data.** Iterating whatever grids
    happen to have a cycle makes a table that silently loses a row when a grid
    comes back empty, and a row that vanishes reads as a row that was never
    asked for. Every rung prints, empty or not.
    """
    grids, pooled = {}, {}
    for v, per_g in acc["by_vintage"].items():
        for gname, per_arm in per_g.items():
            for arm, cell in per_arm.items():
                p = pooled.setdefault(gname, {}).setdefault(
                    arm, {"keys": [], "om": []})
                p["keys"].extend(cell["keys"])
                p["om"].extend(cell["om"])
    for gname in ladder:
        per_arm, out = pooled.get(gname, {}), {}
        for arm in ("mod", "defer"):
            c = per_arm.get(arm, {"keys": [], "om": []})
            seed = perm_seed + zlib.crc32(
                f"freddie|{gname}|{arm}".encode("utf-8")) % 10_000
            out[arm] = gridvar_cell(c["keys"], c["om"], r2_of, r2_null, np,
                                    seed)
        grids[gname] = out

    by_v = {}
    for v in sorted(acc["by_vintage"]):
        per_g, rec = acc["by_vintage"][v], {}
        for gname in ladder:
            out = {}
            for arm in ("mod", "defer"):
                c = per_g.get(gname, {}).get(arm, {"keys": [], "om": []})
                seed = perm_seed + zlib.crc32(
                    f"{v}|{gname}|{arm}".encode("utf-8")) % 10_000
                out[arm] = gridvar_cell(c["keys"], c["om"], r2_of, r2_null,
                                        np, seed)
            rec[gname] = out
        by_v[str(v)] = rec

    alph = acc["alphabet"]
    named = {k: n for k, n in alph.items() if len(k) == 2 and k.isdigit()}
    ra = {k: n for k, n in alph.items() if k == "RA"}
    unk = {k: n for k, n in alph.items() if k not in named and k not in ra}
    xt = acc["defer_xtab"]
    tot_x = sum(xt.values())
    return {
        "loans": acc["loans"], "loops": acc["loops"],
        "measurable": acc["measurable"], "drop": dict(acc["drop"]),
        "drop_total": sum(acc["drop"].values()),
        "t_M_row_reads_current": acc["t_M_row_reads_current"],
        "n_perm": n_perm, "perm_seed": perm_seed, "ladder": list(ladder),
        "not_cycle": {g: dict(acc["not_cycle"].get(
            g, {"mod": 0, "defer": 0})) for g in ladder},
        "grids": grids, "by_vintage": by_v,
        "alphabet": {
            "reads": int(sum(alph.values())),
            "distinct": len(alph),
            "named_reads": int(sum(named.values())),
            "ra_reads": int(sum(ra.values())),
            "unk_reads": int(sum(unk.values())),
            "unk_values": dict(Counter(unk).most_common()),
            "named_values": dict(sorted(named.items())),
        },
        "defer_xtab": dict(xt),
        "defer_rows": acc["defer_rows"],
        "defer_col12_unreadable": acc["defer_col12_unreadable"],
        "defer_agree": ((xt["col12+_f25+"] + xt["col12-_f25-"]) / tot_x
                        if tot_x else None),
        "defer_col12_only": xt["col12+_f25-"],
        "defer_f25_only": xt["col12-_f25+"],
    }


def print_gridvar(pl) -> None:
    ladder = pl["ladder"]

    print("\n  A. the population, and what it cost to get here")
    print(f"     loans {pl['loans']:,}   loops (six conditions passed) "
          f"{pl['loops']:,}   measurable {pl['measurable']:,}")
    if pl["drop"]:
        for k, n in sorted(pl["drop"].items(), key=lambda kv: -kv[1]):
            print(f"       dropped  {k:<44}{n:>9,}")
    print(f"     t_M reads current in the delinquency field: "
          f"{pl['t_M_row_reads_current']:,} of {pl['measurable']:,}"
          "   (§8·22·9's shape: the flag is written after the cure)")
    print("     t_M outside its own window is an **assertion, not a count**:")
    print("     find_loops_rows is in this file and guarantees t_A < t_M <= t_B,")
    print("     so a tally on it could never fire (§11 item 13).")
    for g in ladder:
        d = pl["not_cycle"][g]
        print(f"     {g:<4} reduced to a non-cycle:  mod {d['mod']:,}"
              f"   defer {d['defer']:,}")
    print("     (a closed walk that reduces to one node is not a cycle;")
    print("      b1_theorem.md §5 draws that line and this file imports it)")

    a = pl["alphabet"]
    print("\n  B. §8·25·3: the delinquency alphabet on the loop windows")
    print(f"     label reads {a['reads']:,}   distinct values {a['distinct']}")
    print(f"     named (two digits) {a['named_reads']:,}"
          f"   RA {a['ra_reads']:,}   UNK {a['unk_reads']:,}")
    print(f"     named values: "
          f"{', '.join(f'{k}x{v:,}' for k, v in a['named_values'].items())}")
    #: §8·25·7, registered before the run. `results/b10_support_depth.json`
    #: enumerates this carrier's whole raw-state alphabet as 104 values:
    #: `00`-`99` with no hole, plus `RA`, `XX`, and the two event labels. So
    #: `99` occurs here too, and this file lets `g1` fold it into `90+` exactly
    #: as it folds `90`-`98`. **That is a choice and it is printed, not
    #: assumed.** §8·15's ruling was made on Fannie's evidence — 251 of 279
    #: runs beginning right after `98`, and zero rows before month 99 of the
    #: loan's own reporting — and a ruling about one carrier's field is not
    #: transportable to another carrier's field. Freddie's alphabet has no
    #: hole, which is what a count looks like.
    n99 = a["named_values"].get("99", 0)
    print(f"     §8·25·7: `99` reads on these windows: {n99:,}"
          f"   ({n99 / a['reads']:.6f} of all reads)" if a["reads"]
          else f"     §8·25·7: `99` reads on these windows: {n99:,}")
    print("     It is folded into 90+ by g1 and delinquent by g2, like 90-98.")
    print("     **No branch hangs on it**: if the count is")
    print("     small the question is closed here, and if it is large enough")
    print("     to move a reading that is the next station's object.")
    if a["unk_values"]:
        print("     UNK values, enumerated (C0b), commonest first. The whole")
        print("     carrier's alphabet is 104 values and only `XX` is outside")
        print("     `00`-`99` and `RA`, so anything else here is news:")
        for k, n in a["unk_values"].items():
            print(f"       {k!r:<14}{n:>12,}")
    else:
        print("     nothing landed in UNK on these windows. The node exists")
        print("     anyway: §8·25·3 put it there before it could bite, and an")
        print("     empty node is the cheap outcome, not a wasted one.")

    print("\n  C. §8·25·2: the two deferral definitions against each other")
    xt = pl["defer_xtab"]
    print(f"     perf rows read {pl['defer_rows']:,}"
          f"    column 12 unreadable on {pl['defer_col12_unreadable']:,}"
          f" (outside the table, not a zero)")
    print(f"     {'':<18}{'field 25 in P,C':>18}{'field 25 otherwise':>20}")
    print(f"     {'column 12 > 0':<18}{xt['col12+_f25+']:>18,}"
          f"{xt['col12+_f25-']:>20,}")
    print(f"     {'column 12 <= 0':<18}{xt['col12-_f25+']:>18,}"
          f"{xt['col12-_f25-']:>20,}")
    if pl["defer_agree"] is not None:
        print(f"     agreement {pl['defer_agree']:.6f}"
              f"    column 12 alone {pl['defer_col12_only']:,}"
              f"    field 25 alone {pl['defer_f25_only']:,}")
    print("     **This is a deliverable, not a criterion**.")
    print("     The reading below uses column 12, because §8·23's omega was")
    print("     computed on it: finding the loop by one definition and")
    print("     labelling its states by another is 失效模式 18 on the")
    print("     arguments, which is §11 item 11's second shape.")

    print(f"\n  D. R^2 against a label-permutation null, {pl['n_perm']} draws, "
          f"seed {pl['perm_seed']}, pooled over vintages")
    print(f"     {'grid':<6}{'arm':<7}{'n':>9}{'cls':>6}{'min':>6}{'R2':>9}"
          f"{'null p50':>10}{'null p95':>10}{'pct':>8}{'E':>9}")
    for g in ladder:
        for arm in ("mod", "defer"):
            d = pl["grids"][g][arm]
            if d["r2"] is None:
                print(f"     {g:<6}{arm:<7}{d['n']:>9,}{'-':>6}{'-':>6}"
                      f"{'no referent':>46}")
                continue
            print(f"     {g:<6}{arm:<7}{d['n']:>9,}{d['classes']:>6}"
                  f"{d['min_class']:>6}{d['r2']:>9.4f}{d['null_p50']:>10.4f}"
                  f"{d['null_p95']:>10.4f}{d['pct']:>8.3f}{d['E']:>+9.4f}")
    for g in ladder:
        for arm in ("mod", "defer"):
            tp = pl["grids"][g][arm]["top_path"]
            if tp:
                print(f"     commonest {g}/{arm}: {tp}")

    outside = [(g, arm) for g in ladder for arm in ("mod", "defer")
               if pl["grids"][g][arm]["pct"] is not None
               and pl["grids"][g][arm]["pct"] >= 0.95]
    print(f"\n     cells at or above the null's 95th percentile: "
          f"{len(outside)} of {2 * len(ladder)}"
          + (("  -> " + ", ".join(f"{g}/{a}" for g, a in outside))
             if outside else ""))
    print("     **Carried with the reading, never as a branch.** §8·25·4")
    print("     registered one variable and three branches on the sign of")
    print("     E(g0m) - E(g2); adding a gate here after the fact is exactly")
    print("     the re-coding R01 forbids. If nothing is outside the null the")
    print("     sign is a sign of noise, and that sentence goes beside the")
    print("     branch rather than replacing it.")

    print("\n  E. §8·25·4's variable: the sign of E(g0m) - E(g2), one per arm")
    print(f"     {'arm':<7}{'E(g2)':>10}{'E(g1)':>10}{'E(g0m)':>10}"
          f"{'g0m-g2':>11}{'sign':>8}")
    signs = {}
    for arm in ("mod", "defer"):
        e = {g: pl["grids"][g][arm]["E"] for g in ladder}
        if any(e.get(g) is None for g in ("g2", "g0m")):
            signs[arm] = None
            print(f"     {arm:<7}" + "".join(
                f"{('-' if e.get(g) is None else f'{e[g]:+.4f}'):>10}"
                for g in ("g2", "g1", "g0m")) + f"{'-':>11}{'none':>8}")
            continue
        d = e["g0m"] - e["g2"]
        signs[arm] = d > 0
        print(f"     {arm:<7}" + "".join(
            f"{('-' if e.get(g) is None else f'{e[g]:+.4f}'):>10}"
            for g in ("g2", "g1", "g0m"))
            + f"{d:>+11.4f}{('up' if d > 0 else 'not up'):>8}")
    print("     g1 is the middle rung. §8·12·3's rule, kept here: it sharpens")
    print("     whichever branch lands and is **never a branch of its own**.")

    both_up = signs["mod"] is True and signs["defer"] is True
    both_not = signs["mod"] is False and signs["defer"] is False
    print()
    if signs["mod"] is None or signs["defer"] is None:
        print("     §8·25·4 -> NO READING. An arm has no referent, so the")
        print("     variable does not exist on it. This is not the third")
        print("     branch: mixed means two signs that disagree, and a")
        print("     missing sign is a missing sign (§11 item 6).")
    elif both_up:
        print("     §8·25·4 -> FIRST BRANCH. Both arms rise, same direction as")
        print("     Fannie. **The cut decides the reading on both carriers**,")
        print("     so every holonomy reading has to carry its grid with it.")
        print("     §8·25·6 item 2, written before the run: this is §1.1's")
        print("     worry landing in two places, **not** §1.1 being closed.")
    elif both_not:
        print("     §8·25·4 -> SECOND BRANCH. Neither arm rises. On this")
        print("     carrier the cut does not decide the reading, and that")
        print("     **differs from Fannie**, which is its own item and gets")
        print("     its own line in the results.")
    else:
        up = "mod" if signs["mod"] else "defer"
        print(f"     §8·25·4 -> THIRD BRANCH, mixed (R01). Only the {up} arm")
        print("     rises. Named, and not folded into either of the other two.")

    print("\n  F. the same table per vintage. **Delivered, not read**")
    print(". §8·22·5 measured the vintage trend to be a")
    print("     composition effect, half the loops coming out of 2020-2021,")
    print("     so a per-vintage sign is a sign of the mix.")
    print(f"     {'vintage':<9}{'arm':<7}{'n(g2)':>8}{'E(g2)':>10}"
          f"{'E(g0m)':>10}{'g0m-g2':>11}{'thinnest cell':>15}")
    thin = None
    for v, rec in sorted(pl["by_vintage"].items()):
        for arm in ("mod", "defer"):
            d2 = rec.get("g2", {}).get(arm)
            d0 = rec.get("g0m", {}).get(arm)
            if d2 is None or d0 is None:
                continue
            mc = d2.get("min_class")
            if d2["n"] and (thin is None or d2["n"] < thin[2]):
                thin = (v, arm, d2["n"])
            if d2["E"] is None or d0["E"] is None:
                print(f"     {v:<9}{arm:<7}{d2['n']:>8,}"
                      f"{'no referent':>31}{'':>11}"
                      f"{(mc if mc is not None else '-'):>15}")
                continue
            print(f"     {v:<9}{arm:<7}{d2['n']:>8,}{d2['E']:>+10.4f}"
                  f"{d0['E']:>+10.4f}{d0['E'] - d2['E']:>+11.4f}"
                  f"{(mc if mc is not None else '-'):>15}")
    if thin is not None:
        print(f"     §3·4's thinnest cell, named: {thin[0]} / {thin[1]} "
              f"with {thin[2]:,} loops on g2.")

    print("\n  G. §8·25·5's four, printed with the reading and not under it")
    print("     1. the modification arm is the early-flagged minority")
    print("        (§8·22·8), and narrower than Fannie's by construction")
    print("        (§8·22·2: field 63 alone contributes 3.2% to 11.2% there).")
    print("     2. bn == n; forgiven is zero by absence; P is an estimate and")
    print("        not a published value.")
    print(f"     3. unnameable states have their own node: {a['unk_reads']:,}"
          f" UNK reads and {a['ra_reads']:,} RA reads on these windows.")
    print("     4. the two arms' omega differ by 5.8x in level (§8·24·4).")
    print("        **What is read above is a sign, not a level.**")


def cmd_gridvar(only) -> int:
    vs = [v for v in vintages_on_disk() if not only or str(v) in only]
    if not vs:
        print(f"  no archives under {RAW}")
        return 1
    sys.path.insert(0, str(ROOT / "experiments"))
    import zlib                                    # noqa: E402
    import numpy as np                             # noqa: E402
    import b8_cmt_fetch as F                       # noqa: E402
    import b8_loop_omega as LO                     # noqa: E402
    import b8_omega as W                           # noqa: E402
    import b8_0a_gate as G                         # noqa: E402
    import b10_c8_1d_freddie as FR                 # noqa: E402
    import b10_support as SUP                      # noqa: E402
    import b10_holonomy_ladder as HL               # noqa: E402

    if W.MAX_H != CURVE_MAX_H:
        print(f"  b8_omega.MAX_H is {W.MAX_H} and this file says "
              f"{CURVE_MAX_H}. Fix one; nothing is read until then.")
        return 1
    if not print_crosscheck(resid_crosscheck(W, G)):
        print("\n  §8·19·3 did not pass. Nothing was read. Fix it first.")
        return 1
    print()
    prior = prior_json(ROOT, partial_name("b10_gridvar", only))
    src, files = F.load_treasury()
    if not src:
        print("  no Treasury curve under data/raw/cmt.")
        return 1
    pos, tab = LO.curve_table_from(src, LO.RULE)

    #: The ladder is `b10_holonomy_ladder.VAR_LADDER` and the grids are
    #: `b10_support.GRIDS`. Neither is this file's to shorten, so a rung that
    #: is not there is a refusal and not a quieter table.
    gd = dict(SUP.GRIDS)
    missing = [g for g in HL.VAR_LADDER if g not in gd]
    if missing:
        print(f"  b10_support.GRIDS carries no {missing}, and the ladder is "
              f"b10_holonomy_ladder.VAR_LADDER = {HL.VAR_LADDER}. "
              f"Nothing was read.")
        return 1
    grids = [(g, gd[g]) for g in HL.VAR_LADDER]
    print("§8·25: §8·12 re-asked on Freddie. The grid ladder "
          f"{' -> '.join(HL.VAR_LADDER)} against omega on §8·22's windows.\n"
          "  Grids, reduction, cycle test, R^2 and its null are all imported\n"
          ". This file writes the wiring and the census.\n")
    acc = gridvar_new_acc()
    for v in vs:
        orig, _ = FR.read_orig(v)
        with zipfile.ZipFile(archive(v)) as zf:
            with zf.open(f"sample_perf_{v}.txt") as raw:
                seq, batch = None, []
                for line in io.TextIOWrapper(raw, encoding="utf-8",
                                             newline=""):
                    if not line.strip():
                        continue
                    f = line.split("|")
                    #: §8·25·2, straight off the raw line. `floor_row` is not
                    #: touched, so nothing that reads it changes shape.
                    acc["defer_rows"] += 1
                    try:
                        c12 = float(f[P_DEFER_BAL_IDX].strip())
                    except (ValueError, IndexError):
                        c12 = None
                    f25 = (f[P_DEFERRAL_IDX].strip()
                           if len(f) > P_DEFERRAL_IDX else "")
                    key = defer_xtab_key(c12, f25)
                    if key is None:
                        acc["defer_col12_unreadable"] += 1
                    else:
                        acc["defer_xtab"][key] += 1
                    if f[0] != seq:
                        if seq is not None:
                            gridvar_absorb(acc, batch, orig.get(seq), v, pos,
                                           tab, CURVE_MAX_H, W.r_month,
                                           FR.contract_payment, SUP, grids,
                                           HL.reduce_closed_walk, HL.is_cycle)
                        seq, batch = f[0], []
                    batch.append(floor_row(f))
                if seq is not None:
                    gridvar_absorb(acc, batch, orig.get(seq), v, pos, tab,
                                   CURVE_MAX_H, W.r_month,
                                   FR.contract_payment, SUP, grids,
                                   HL.reduce_closed_walk, HL.is_cycle)
        print(f"  {v}  done   loops {acc['loops']:,}"
              f"   measurable {acc['measurable']:,}", flush=True)
    pl = gridvar_payload(acc, HL.VAR_LADDER, HL.r2_of, HL.r2_null,
                         HL.PERM_SEED, HL.N_PERM, np, zlib)
    print_vs_prior(prior, pl, partial_name("b10_gridvar", only))
    print_gridvar(pl)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / partial_name("b10_gridvar", only)
    out.write_text(json.dumps(
        {"stage": "B10", "step": "gridvar",
         "registered": "before the code",
         "objects": {
             "windows": "§8·22 find_loops_rows, mod_set (Y, P)",
             "omega": "§8·23 loop_omega, scheme sub",
             "grids": "b10_support.GRIDS, imported",
             "reduction": "b10_holonomy_ladder.reduce_closed_walk / is_cycle",
             "statistic": "b10_holonomy_ladder.r2_of / r2_null, its PERM_SEED",
         },
         "deferral_definition":
             "column 12 positive, because §8·23's omega was computed on it. "
             "Field 25 in (P, C) is cross-tabulated against it and delivered, "
             "never used as a criterion.",
         "caveats": ["the modification arm is the early-flagged minority "
                     "(§8·22·8) and narrower than Fannie's (§8·22·2)",
                     "bn == n; forgiven is 0 by absence; P is an estimate",
                     "unnameable states get their own node UNK (§8·25·3)",
                     "the two arms differ 5.8x in |omega| level (§8·24·4); "
                     "what is read is a sign, not a level"],
         **pl}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\n  wrote {out.relative_to(ROOT)}")
    return 0


def cmd_selftest() -> int:
    print("b10_cohort_width selftest. Constructed cases, answers first.\n")
    fails = []

    def chk(name, got, want):
        ok = got == want
        print(f"  {name:<52} {str(got):<24} {'ok' if ok else f'FAIL want {want}'}")
        if not ok:
            fails.append(name)

    print("  fico_band, C9 §2.1's lower-bound convention:")
    for s, w in ((800, 0), (780, 0), (779, 1), (760, 1), (759, 2), (640, 7),
                 (639, 8), (300, 8)):
        chk(f"    fico_band({s})", fico_band(s), w)
    print("  the boundary that bit the Fannie side once: a score exactly on a\n"
          "  cut belongs to the HIGHER band, because FICO is published with\n"
          "  lower bounds while LTV is published with upper bounds (C9 §2.1).")

    print("\n  anchor_fico, on constructed vintages:")
    # nine bands, 200 loans each, rate falling as the score rises
    spread = [(790, 5.0), (770, 5.1), (750, 5.2), (730, 5.3), (710, 5.4),
              (690, 5.5), (670, 5.6), (650, 5.7), (600, 6.0)]
    pv = {y: {7: [(s, r + 0.5 * k) for s, r in spread] * 200}
          for k, y in enumerate((2001, 2002))}
    chk("    a banded, monotonically priced field scores on both",
        anchor_fico(pv, [7])[7]["score"], 2)
    scrambled = [(790, 6.0), (770, 5.1), (750, 5.2), (730, 5.3), (710, 5.4),
                 (690, 5.5), (670, 5.6), (650, 5.7), (600, 5.0)]
    pv2 = {2001: {7: [(s, r) for s, r in scrambled] * 200}}
    chk("    the right bands but the wrong ordering scores zero",
        anchor_fico(pv2, [7])[7]["score"], 0)
    pv3 = {2001: {7: [(1, 6.0), (2, 5.0), (3, 5.5), (4, 5.2)] * 500}}
    r3 = anchor_fico(pv3, [7])[7]
    chk("    a column living in one band is never even read",
        (r3["vintages"], r3["score"]), (0, 0))
    print("    (the third case is the number of borrowers: values 1..4 all land\n"
          "     in the bottom band, so there is nothing to order. That is what\n"
          "     removes it, not a range filter and not its name)")

    print("\n  anchor_dti, cliff detection:")
    h = {i: 1000 for i in range(20, 46)}
    h.update({i: 20 for i in range(46, 61)})
    d = anchor_dti({0: h}, [0])[0]
    chk("    cliff found at the cap", d["cliff_at"], 45)
    chk("    and it passes", d["passes"], True)
    flat = {i: 500 for i in range(20, 61)}
    chk("    a flat histogram does not land on a cap",
        anchor_dti({0: flat}, [0])[0]["passes"], False)

    print("\n  anchor_implication, and BOTH of its vacuity guards:")
    pc = {(3, 4): {("Y", "P"): 100, ("N", "P"): 400, ("N", "C"): 500}}
    tot = {3: {"Y": 100, "N": 900}, 4: {"P": 500, "C": 500}, "rows": 1000}
    r = anchor_implication(pc, tot, [3], [4])
    chk("    Y => P at 1.0", r["best"]["implication"], 1.0)
    chk("    and its lift is 1/0.5", r["best"]["lift"], 2.0)
    pc2 = {(3, 4): {("Z", "P"): 3}}
    tot2 = {3: {"Z": 3, "N": 9997}, 4: {"P": 500}, "rows": 10000}
    chk("    a 0.03% antecedent is refused despite scoring 1.0",
        anchor_implication(pc2, tot2, [3], [4])["best"], None)
    # the hole the first run walked into: a consequent that holds for everyone
    pc3 = {(3, 4): {("N", "X"): 900, ("Y", "X"): 100},
           (3, 5): {("Y", "P"): 100, ("N", "P"): 400, ("N", "C"): 500}}
    tot3 = {3: {"Y": 100, "N": 900}, 4: {"X": 1000},
            5: {"P": 500, "C": 500}, "rows": 1000}
    r3 = anchor_implication(pc3, tot3, [3], [4, 5])
    chk("    a universal consequent loses to a real one",
        (r3["best"]["purpose_col"], r3["best"]["lift"]), (5, 2.0))
    chk("    counterexamples are counted, not rated",
        r3["best"]["counterexamples"], 0)
    # counterexamples are an integer count, and the ranking prefers zero of
    # them over a higher lift. Both halves are checked on one fixture.
    pc4 = {(3, 4): {("Y", "P"): 97, ("Y", "C"): 3},
           (3, 5): {("Y", "Q"): 100, ("N", "Q"): 900}}
    tot4 = {3: {"Y": 100, "N": 900}, 4: {"P": 97, "C": 3},
            5: {"Q": 1000}, "rows": 1000}
    r4 = anchor_implication(pc4, tot4, [3], [4, 5])
    near = [d for d in r4["ranked"] if d["purpose_val"] == "P"][0]
    chk("    three violating rows print as 3, not as 0.03",
        near["counterexamples"], 3)
    chk("    and a lift of 10 does not beat a clean implication",
        r4["best"]["counterexamples"], 0)
    print("    (the second guard is the one the registration missed: a\n"
          "     consequent holding for everyone is as vacuous as an antecedent\n"
          "     holding for no one, and the first run returned exactly that)")

    print("\n  anchor_purpose_rate, sign of the covariance:")
    share = {v: {"P": 0.5 + 0.05 * k, "C": 0.5 - 0.05 * k}
             for k, v in enumerate((1999, 2000, 2001, 2002))}
    rate = {1999: 6.0, 2000: 6.5, 2001: 7.0, 2002: 7.5}
    pr = anchor_purpose_rate(share, rate)
    chk("    the level rising with the coupon reads +", pr["levels"]["P"]["sign"], "+")
    chk("    the level falling with it reads -", pr["levels"]["C"]["sign"], "-")

    print("\n  the two published tables, checked against each other before "
          "either is used as a gate:")
    t3 = sum(p[4] for p in PUBLISHED_S3.values())
    t4 = sum(PUBLISHED_S4_YEAR.values())
    chk("    §3's triangle column sums to §4's year table", t3, t4)
    chk("    and both read 17,875", t3, 17875)
    wsum = sum(w for _, _, _, w in S4_WINDOWS)
    chk("    §4's four windows plus the remainder sum to the same", wsum, t4)
    for name, lo, hi, want in S4_WINDOWS:
        got = sum(n for y, n in PUBLISHED_S4_YEAR.items() if lo <= y <= hi)
        chk(f"    window {name} adds up", got, want)
    print("    (a transcription slip in either table would show here rather\n"
          "     than as a mismatch blamed on the new code)")

    print("\n  classify_loan, hand-built loans, §26.0's readings:")
    def L(*t):
        return [(200001 + i, s, m) for i, (s, m) in enumerate(t)]

    c = classify_loan(L(("00", ""), ("01", ""), ("02", ""), ("00", "Y")))
    chk("    cure on the modification row is still a triangle",
        c["digits"]["triangle"], True)
    c = classify_loan(L(("00", ""), ("01", ""), ("00", "")))
    chk("    a cure with no modification is not a triangle",
        c["digits"]["triangle"], False)
    chk("    and it is a whole-loan round trip", c["digits"]["whole_loan"], True)
    c = classify_loan(L(("00", ""), ("01", "Y"), ("00", ""), ("02", ""),
                        ("00", "")))
    chk("    a later clean cure is not a whole-loan round trip",
        c["digits"]["whole_loan"], False)
    chk("    but it is a between round trip", c["digits"]["between"], True)
    c = classify_loan(L(("00", ""), ("RA", ""), ("00", "Y")))
    chk("    RA is delinquent under `any`", c["any"]["ever_delinq"], True)
    chk("    and is not under `digits`", c["digits"]["ever_delinq"], False)

    # §8·16·3's window, added to the one finder rather than written twice.
    print("\n  classify_loan's round-trip window (§8·16·3):")
    c = classify_loan(L(("00", ""), ("01", ""), ("00", "")))
    chk("    last current .. cure", c["digits"]["between_window"],
        {"prev_current": 0, "delinq_start": 1, "cure": 2})
    c = classify_loan(L(("00", ""), ("01", "Y"), ("00", ""), ("02", ""),
                        ("00", "")))
    chk("    the SECOND trip, not the modified first",
        c["digits"]["between_window"],
        {"prev_current": 2, "delinq_start": 3, "cure": 4})
    c = classify_loan(L(("00", ""), ("00", ""), ("01", ""), ("02", ""),
                        ("03", ""), ("00", "")))
    chk("    a three-month run spans the whole run",
        c["digits"]["between_window"],
        {"prev_current": 1, "delinq_start": 2, "cure": 5})
    c = classify_loan(L(("01", ""), ("00", "")))
    chk("    a loan that opens delinquent records None, not a guess",
        c["digits"]["between_window"],
        {"prev_current": None, "delinq_start": 0, "cure": 1})
    c = classify_loan(L(("00", ""), ("01", ""), ("02", "")))
    chk("    no cure, no window", c["digits"]["between_window"], None)

    # --floor, §8·16. Constructed loans whose answers are known first.
    print("\n  --floor, §8·16's construction half:")

    def FR(*t):
        """Rows in `floor_row`'s own shape, `R_*`-indexed.

        **Eight fields.** The fixture built six until §8·17 appended `rem`, and
        seven until §8·19 appended the deferred balance. A fixture whose shape
        has drifted from the reader's is a test of something that no longer
        exists, and that lesson has now been paid for twice.

        The deferred balance is optional **in the fixture**, never in the row:
        omitting it writes 0.0, which §8·14·5 measured to be the majority
        value. A caller that wants to test the blank case passes None
        explicitly.
        """
        return [(200001 + i, s, m, age, upb, rate, 360 - i,
                 (d[0] if d else 0.0))
                for i, (s, m, age, upb, rate, *d) in enumerate(t)]

    #: A trip that sits wholly above the boundary and prices.
    acc = floor_new_acc()
    floor_absorb(acc, FR(("00", "", 20, 100_000.0, 6.0),
                         ("01", "", 21, 99_900.0, 6.0),
                         ("00", "", 22, 99_800.0, 6.0)))
    chk("    a trip above the boundary is priced",
        (acc["roundtrips"], acc["age_ge_min"], acc["touches_below"],
         len(acc["bounds"])), (1, 1, 0, 1))
    chk("    k is the span, not the run length", dict(acc["k_hist"]), {2: 1})
    chk("    and the bound is the derivation, not a constant",
        round(acc["bounds"][0] / floor_bound(2, 6.0, 99_800.0), 12), 1.0)

    #: The same trip one age lower touches the $1,000 grid and is set aside.
    acc = floor_new_acc()
    floor_absorb(acc, FR(("00", "", 7, 100_000.0, 6.0),
                         ("01", "", 8, 99_900.0, 6.0),
                         ("00", "", 9, 99_800.0, 6.0)))
    chk("    a trip touching age 7 is counted, not priced",
        (acc["roundtrips"], acc["age_ge_min"], acc["touches_below"],
         len(acc["bounds"])), (1, 0, 1, 0))

    #: A rate that moves inside the loop has no single `i`.
    acc = floor_new_acc()
    floor_absorb(acc, FR(("00", "", 20, 100_000.0, 6.0),
                         ("01", "", 21, 99_900.0, 6.5),
                         ("00", "", 22, 99_800.0, 6.5)))
    chk("    a loop whose rate moved is set apart, never averaged",
        (acc["age_ge_min"], acc["rate_varies"], len(acc["bounds"])), (1, 1, 0))

    #: A loan that opens delinquent has no current -> delinquent leg.
    acc = floor_new_acc()
    floor_absorb(acc, FR(("01", "", 20, 99_900.0, 6.0),
                         ("00", "", 21, 99_800.0, 6.0)))
    chk("    opening delinquent is counted on its own line",
        (acc["roundtrips"], acc["no_prev_current"], acc["age_ge_min"]),
        (1, 1, 0))

    #: An unreadable field must be loud, not zero.
    acc = floor_new_acc()
    floor_absorb(acc, FR(("00", "", 20, 100_000.0, 6.0),
                         ("01", "", 21, None, 6.0),
                         ("00", "", 22, 99_800.0, 6.0)))
    chk("    an unreadable balance is counted, not treated as zero",
        (acc["roundtrips"], acc["unreadable"], acc["age_ge_min"]), (1, 1, 0))

    #: A modified loan is not a no-modification round trip at all.
    acc = floor_new_acc()
    floor_absorb(acc, FR(("00", "", 20, 100_000.0, 6.0),
                         ("01", "Y", 21, 99_900.0, 6.0),
                         ("00", "", 22, 99_800.0, 6.0)))
    chk("    a modified trip is not a round trip here",
        (acc["roundtrips"], acc["age_ge_min"]), (0, 0))

    #: The four buckets have to partition the round trips, or the coverage line
    #: is decoration (§11's 'kept + dropped = total').
    acc = floor_new_acc()
    for L6 in (FR(("00", "", 20, 100_000.0, 6.0), ("01", "", 21, 99_900.0, 6.0),
                  ("00", "", 22, 99_800.0, 6.0)),
               FR(("00", "", 7, 100_000.0, 6.0), ("01", "", 8, 99_900.0, 6.0),
                  ("00", "", 9, 99_800.0, 6.0)),
               FR(("01", "", 20, 99_900.0, 6.0), ("00", "", 21, 99_800.0, 6.0)),
               FR(("00", "", 20, 100_000.0, 6.0), ("01", "", 21, None, 6.0),
                  ("00", "", 22, 99_800.0, 6.0))):
        floor_absorb(acc, L6)
    chk("    the four buckets partition the round trips",
        (acc["age_ge_min"] + acc["touches_below"] + acc["no_prev_current"]
         + acc["unreadable"]), acc["roundtrips"])

    #: floor_row must not turn a bad number into a good one.
    SHORT = "F1|200001|junk|00|3|350|| |||6.0"
    GOOD = "F1|200001|99000.00|00|9|350|| |||6.0|1500.00"
    chk("    floor_row reports an unreadable balance as None",
        floor_row(SHORT.split("|"))[R_UPB], None)
    chk("    and reads a good row",
        floor_row(GOOD.split("|"))[3:], (9, 99000.0, 6.0, 350, 1500.00))
    chk("    the row tuple is eight wide, rem then defer",
        (len(floor_row(GOOD.split("|"))), R_REM, R_DEFER), (8, 6, 7))
    #: 失效模式 20's own shape, as a test: a line with no column 12 at all is
    #: **not** a line whose deferred balance is zero.
    chk("    a line too short to carry column 12 reads None, not 0.0",
        floor_row(SHORT.split("|"))[R_DEFER], None)
    chk("    a blank column 12 reads None too",
        floor_row((GOOD.rsplit("|", 1)[0] + "|").split("|"))[R_DEFER], None)
    chk("    and a zero there reads 0.0, which is a number",
        floor_row((GOOD.rsplit("|", 1)[0] + "|0.00").split("|"))[R_DEFER], 0.0)

    pl = floor_payload(acc)
    print_floor(pl, gated=False)
    blob = json.dumps({"stage": "B10", "step": "floor", **pl},
                      indent=2, sort_keys=True)
    print(f"\n     printer and json.dumps both exercised, {len(blob):,} bytes")

    for tag, n, want in (("first", 25, "FIRST BRANCH"),
                         ("second", 3, "SECOND BRANCH"),
                         ("third", 0, "THIRD BRANCH")):
        p2 = dict(pl); p2["age_ge_min"] = n
        buf, keep = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            print_floor(p2, gated=False)
        finally:
            sys.stdout = keep
        chk(f"    print_floor reads the {tag} branch", want in buf.getvalue(),
            True)
    p3 = dict(pl); p3["roundtrips"] = 1
    buf, keep = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        print_floor(p3, gated=True)
    finally:
        sys.stdout = keep
    txt = buf.getvalue()
    chk("    a gate mismatch stops before anything is quotable",
        ("MISMATCH" in txt) and ("FIRST BRANCH" not in txt), True)

    # --curve, §8·17. A constructed table, so no Treasury CSV is needed.
    print("\n  --curve, §8·17's coverage question:")
    #: **The units check that would have caught the first version.** The table
    #: is keyed by month index, not by a period; feeding a YYYYMM straight in
    #: missed every row of a 603,609-row scan.
    chk("    month_index_of matches b8_core's epoch", month_index_of(199001), 0)
    chk("    and Freddie's first vintage", month_index_of(199901), 108)
    chk("    and today", month_index_of(202608), 439)
    chk("    a period before the epoch is refused, not wrapped",
        month_index_of(198912), -1)
    chk("    month 13 is refused", month_index_of(200013), -1)
    chk("    yyyymm_of inverts it",
        [yyyymm_of(month_index_of(p)) for p in (199901, 200507, 202608)],
        [199901, 200507, 202608])

    NAN = float("nan")
    #: Two months of curve, **keyed the way the real table is**: by index.
    #: 200002 is index 121, 200003 is 122.
    tpos = {month_index_of(200002): 0, month_index_of(200003): 1}
    ttab = [[NAN] * 6, [NAN] * 6]
    for h, y in ((1, 1.0), (2, 1.2), (3, 1.4)):
        ttab[0][h] = y
    for h, y in ((1, 1.1), (2, 1.3)):
        ttab[1][h] = y

    chk("    a month with no curve is named, not silently zero",
        curve_cell(199901, 2, tpos, ttab, 5)[0], "no_curve_that_month")
    chk("    a period before the epoch is a month miss, not a crash",
        curve_cell(198901, 2, tpos, ttab, 5)[0], "no_curve_that_month")
    chk("    a horizon past the table is its own label",
        curve_cell(200002, 9, tpos, ttab, 5)[0], "horizon_out_of_table")
    chk("    horizon 0 is out too, not a lookup at index 0",
        curve_cell(200002, 0, tpos, ttab, 5)[0], "horizon_out_of_table")
    chk("    a NaN inside the table is its own label",
        curve_cell(200003, 3, tpos, ttab, 5)[0], "curve_nan")
    chk("    and a good cell returns the value",
        curve_cell(200002, 2, tpos, ttab, 5), ("usable", 1.2))
    chk("    the four labels are b8_omega.disc_of_row's own",
        sorted({curve_cell(199901, 2, tpos, ttab, 5)[0],
                curve_cell(200002, 9, tpos, ttab, 5)[0],
                curve_cell(200003, 3, tpos, ttab, 5)[0],
                curve_cell(200002, 2, tpos, ttab, 5)[0]}),
        ["curve_nan", "horizon_out_of_table", "no_curve_that_month", "usable"])

    def CR(*t):
        """Rows with an explicit rem, for the curve lookup.

        Eighth field as in `FR`: §8·19 reads it, §8·17 does not, and a fixture
        narrower than the reader tests nothing.
        """
        return [(per, s, m, age, upb, rate, rem, (d[0] if d else 0.0))
                for per, s, m, age, upb, rate, rem, *d in t]

    #: A trip every one of whose rows reads: usable.
    acc = curve_new_acc()
    curve_absorb(acc, CR((200002, "00", "", 20, 100_000.0, 6.0, 1),
                         (200003, "01", "", 21, 99_900.0, 6.0, 2),
                         (200002, "00", "", 22, 99_800.0, 6.0, 3)),
                 tpos, ttab, 5)
    chk("    a wholly covered trip is usable",
        (acc["priced_trips"], acc["usable_trips"], dict(acc["trip_status"])),
        (1, 1, {"usable": 1}))

    #: One bad row takes the whole trip, and the FIRST failure names it.
    acc = curve_new_acc()
    curve_absorb(acc, CR((200002, "00", "", 20, 100_000.0, 6.0, 1),
                         (199901, "01", "", 21, 99_900.0, 6.0, 2),
                         (200003, "00", "", 22, 99_800.0, 6.0, 3)),
                 tpos, ttab, 5)
    chk("    one uncovered row takes the trip with it",
        (acc["usable_trips"], dict(acc["trip_status"])),
        (0, {"no_curve_that_month": 1}))
    chk("    and the later NaN row did not relabel it",
        dict(acc["row_status"]),
        {"usable": 1, "no_curve_that_month": 1, "curve_nan": 1})

    #: A trip §8·16 does not price never reaches the curve at all.
    acc = curve_new_acc()
    curve_absorb(acc, CR((200002, "00", "", 3, 100_000.0, 6.0, 1),
                         (200003, "01", "", 4, 99_900.0, 6.0, 2),
                         (200002, "00", "", 5, 99_800.0, 6.0, 3)),
                 tpos, ttab, 5)
    chk("    a trip below the grid boundary is not priced here either",
        (acc["roundtrips"], acc["priced_trips"], acc["rows"]), (1, 0, 0))

    #: An unreadable horizon is its own label, not a lookup at None.
    acc = curve_new_acc()
    curve_absorb(acc, CR((200002, "00", "", 20, 100_000.0, 6.0, 1),
                         (200003, "01", "", 21, 99_900.0, 6.0, None),
                         (200002, "00", "", 22, 99_800.0, 6.0, 3)),
                 tpos, ttab, 5)
    chk("    an unreadable horizon does not crash the lookup",
        dict(acc["trip_status"]), {"horizon_unreadable": 1})

    cens = {"files": ["a.csv"], "n_files": 1, "months": 2,
            "first_month": 200002, "last_month": 200003, "missing": [199901],
            "h_min": 2, "h_med": 2, "h_max": 3}
    acc = curve_new_acc()
    for L7 in (CR((200002, "00", "", 20, 100_000.0, 6.0, 1),
                  (200003, "01", "", 21, 99_900.0, 6.0, 2),
                  (200002, "00", "", 22, 99_800.0, 6.0, 3)),
               CR((200002, "00", "", 20, 100_000.0, 6.0, 1),
                  (199901, "01", "", 21, 99_900.0, 6.0, 2),
                  (200003, "00", "", 22, 99_800.0, 6.0, 1))):
        curve_absorb(acc, L7, tpos, ttab, 5)
    pl_c = curve_payload(acc, cens)
    chk("    the trip labels add up to the priced trips",
        sum(pl_c["trip_status"].values()), pl_c["priced_trips"])
    chk("    the thinnest cell is named, not just counted",
        pl_c["thinnest_cell"] is not None and pl_c["cells"] > 0, True)
    print_curve(pl_c)
    blob_c = json.dumps({"stage": "B10", "step": "curve", **pl_c},
                        indent=2, sort_keys=True)
    print(f"\n     printer and json.dumps both exercised, {len(blob_c):,} bytes")

    #: §8·17·2's branches, on the sharpened reading. The third case is the one
    #: the first version got wrong: **no horizon misses at all**, which used to
    #: pass a `<= 3` test and read as concentration.
    cens2 = dict(cens); cens2["missing"] = [200101, 200102]
    for tag, mut, want in (
            ("first", {"row_status": {"usable": 9}, "rows": 9,
                       "bad_periods": []}, "FIRST BRANCH"),
            #: The regression the 2026-08-20 disambiguation exists for: the
            #: curve reached every row it was asked about, and the only misses
            #: are rows whose own horizon would not parse.
            ("first, with unreadable horizons beside it",
             {"row_status": {"usable": 9, "horizon_unreadable": 3},
              "rows": 12, "bad_periods": []}, "FIRST BRANCH"),
            ("second, every miss is a month the curve lacks",
             {"row_status": {"usable": 5, "x": 4}, "rows": 9,
              "census": cens2, "bad_periods": [200101, 200102],
              "bad_horizon_distinct": 0}, "SECOND BRANCH"),
            ("third, a miss in a month the curve HAS",
             {"row_status": {"usable": 5, "x": 4}, "rows": 9,
              "census": cens2, "bad_periods": [200101, 200507],
              "bad_horizon_distinct": 0}, "THIRD BRANCH"),
            ("third, the whole scan misses and no horizon does",
             {"row_status": {"no_curve_that_month": 9}, "rows": 9,
              "census": cens2,
              "bad_periods": [200000 + m for m in range(101, 113)],
              "bad_horizon_distinct": 0}, "THIRD BRANCH")):
        p4 = dict(pl_c); p4.update(mut)
        buf, keep = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            print_curve(p4)
        finally:
            sys.stdout = keep
        txt4 = buf.getvalue()
        other = "SECOND BRANCH" if want == "THIRD BRANCH" else "THIRD BRANCH"
        chk(f"    print_curve reads the {tag} branch",
            (want in txt4) and (other not in txt4), True)
    # --resid, §8·19. The gates, on constructed loans. **The residual itself
    # is not checked here**: `resid_absorb` takes `r_month` as an argument
    # precisely so the gate order can be tested without B8's modules on the
    # path, and §8·19·3's cross-check tests the arithmetic against B8's own
    # closed form. Two jobs, two places, neither pretending to be the other.
    print("\n  --resid, §8·19's driver gates:")

    def RR(*t):
        """Rows in `floor_row`'s shape. (period, delinq, mod, age, upb, rate,
        rem, defer)."""
        return [tuple(r) for r in t]

    #: One trip that prices, on the curve table built above. rem falls 3,2,1 so
    #: every pair clears gate 4's `n_prev > 1`, and both lookups land on a cell
    #: `ttab` actually holds.
    CLEAN = RR((200002, "00", "", 20, 100_000.0, 6.0, 3, 0.0),
               (200003, "01", "", 21, 99_900.0, 6.0, 2, 0.0),
               (200002, "00", "", 22, 99_800.0, 6.0, 1, 0.0))
    PAY = lambda u, i, n: 100.0                       # noqa: E731
    NOPAY = lambda u, i, n: float("nan")              # noqa: E731
    RM = lambda *a, **k: 0.5                          # noqa: E731
    RMNAN = lambda *a, **k: float("nan")              # noqa: E731
    ORIG = (100_000.0, 6.0, 360)

    def run(rows, orig=ORIG, pay=PAY, rm=RM):
        acc = resid_new_acc()
        resid_absorb(acc, rows, orig, 2001, tpos, ttab, 5, rm, pay)
        return acc

    def gates(acc):
        return [acc["gates"][g] for g in RESID_GATES]

    acc = run(CLEAN)
    chk("    a clean trip walks every row and admits all but the first",
        (acc["trips"], acc["priced_trips"], acc["pairs"], acc["ok"]),
        (1, 1, 3, 2))
    chk("    and only the first-row gate fired", gates(acc),
        [1, 0, 0, 0, 0, 0, 0])
    chk("    the residual reached by_vintage",
        (acc["by_vintage"][2001]["n"], acc["by_vintage"][2001]["r"]),
        (2, [0.5, 0.5]))

    #: **Gate 2 must be able to fire.** A loan with no orig row still walks its
    #: rows; returning early would leave this counter dead, which is the defect
    #: --horizon and --balid each paid for once.
    acc = run(CLEAN, orig=None)
    chk("    a loan with no orig row fires gate 2 on every row after the first",
        (gates(acc)[1], acc["ok"], acc["no_orig"], acc["rows_no_payment"]),
        (2, 0, 1, 2))
    acc = run(CLEAN, pay=NOPAY)
    chk("    so does a payment that will not compute",
        (gates(acc)[1], acc["no_payment"], acc["no_orig"],
         acc["rows_no_payment"]), (2, 1, 0, 2))

    #: §8·18's identity refuses, never reads a blank as zero (失效模式 20).
    BLANK = RR(CLEAN[0], CLEAN[1][:7] + (None,), CLEAN[2])
    acc = run(BLANK)
    chk("    an unreadable column 12 is refused on both its pairs",
        (gates(acc)[2], acc["ok"]), (2, 0))
    NEG = RR(CLEAN[0], CLEAN[1][:7] + (200_000.0,), CLEAN[2])
    acc = run(NEG)
    chk("    a deferred balance above the UPB is refused, not signed",
        (gates(acc)[2], acc["ok"]), (2, 0))

    #: Gate 4's thresholds are `row_residuals`' own: `rem > 0` here, `rem > 1`
    #: on the previous row.
    SHORTREM = RR(CLEAN[0][:6] + (1, 0.0), CLEAN[1][:6] + (3, 0.0),
                  CLEAN[2][:6] + (2, 0.0))
    acc = run(SHORTREM)
    chk("    a previous row with rem 1 is dropped at gate 4",
        (gates(acc)[3], acc["ok"]), (1, 1))
    BADPER = RR(CLEAN[0], CLEAN[1][:0] + (-1,) + CLEAN[1][1:], CLEAN[2])
    acc = run(BADPER)
    chk("    an unreadable period is dropped at gate 4, not at the curve",
        (gates(acc)[3], gates(acc)[5]), (1, 0))

    #: **Gate 5 cannot fire on this carrier, and that is proved rather than
    #: observed.** `bn == n` (§8·14·6·8), so gate 4's `n_prev > 1` already
    #: implies gate 5's `bn_prev > 1` over the whole reachable domain.
    unreachable = all(
        not (z > 0 and not (float(n) > 1))
        for n in range(2, 600) for z in (0.0, 0.01, 5_000.0, 1e9))
    chk("    gate 5 is unreachable once gate 4 has passed, for every rem>1",
        unreachable, True)
    DEFER = RR(CLEAN[0][:7] + (5_000.0,), CLEAN[1][:7] + (5_000.0,),
               CLEAN[2][:7] + (5_000.0,))
    acc = run(DEFER)
    chk("    a trip carrying a balloon still admits, gate 5 silent",
        (gates(acc)[4], acc["ok"]), (0, 2))

    #: Gate 6: a month the table does not hold.
    OFFCURVE = RR((199901,) + CLEAN[0][1:], (199902,) + CLEAN[1][1:],
                  (199903,) + CLEAN[2][1:])
    acc = run(OFFCURVE)
    chk("    a month with no curve is dropped at gate 6",
        (gates(acc)[5], acc["ok"]), (2, 0))

    #: Gate 7: the counterfactual balance would be non-positive.
    acc = run(CLEAN, pay=lambda u, i, n: 1e9)
    chk("    a payment that would clear the loan is dropped at gate 7",
        (gates(acc)[6], acc["ok"]), (2, 0))

    #: The defect counter is **not** a gate, and it is reachable.
    acc = run(CLEAN, rm=RMNAN)
    chk("    a non-finite r is a defect, counted apart from every gate",
        (acc["defect"], acc["ok"], sum(gates(acc))), (2, 0, 1))

    #: The partition, on every fixture above at once. `kept + dropped = total`
    #: is the line §11 says a coverage table is decoration without.
    acc = resid_new_acc()
    for rows, o, pay, rm in ((CLEAN, ORIG, PAY, RM), (CLEAN, None, PAY, RM),
                             (CLEAN, ORIG, NOPAY, RM), (BLANK, ORIG, PAY, RM),
                             (NEG, ORIG, PAY, RM), (SHORTREM, ORIG, PAY, RM),
                             (BADPER, ORIG, PAY, RM), (DEFER, ORIG, PAY, RM),
                             (OFFCURVE, ORIG, PAY, RM), (CLEAN, ORIG, PAY,
                                                         RMNAN)):
        resid_absorb(acc, rows, o, 2001, tpos, ttab, 5, rm, pay)
    pl_r = resid_payload(acc)
    chk("    gates + admitted + defect = rows walked",
        pl_r["gates_total"] + pl_r["ok"] + pl_r["defect"], pl_r["pairs"])
    chk("    and gate 2 equals the rows on loans with no usable payment",
        pl_r["gates"][RESID_GATES[1]], pl_r["rows_no_payment"])
    chk("    a trip that does not price never reaches a gate at all",
        (pl_r["trips"], pl_r["priced_trips"]), (10, 10))
    acc2 = resid_new_acc()
    resid_absorb(acc2, RR((200002, "00", "", 3, 100_000.0, 6.0, 3, 0.0),
                          (200003, "01", "", 4, 99_900.0, 6.0, 2, 0.0),
                          (200002, "00", "", 5, 99_800.0, 6.0, 1, 0.0)),
                 ORIG, 2001, tpos, ttab, 5, RM, PAY)
    chk("    a trip below §8·16's age floor is a trip, and nothing more",
        (acc2["trips"], acc2["priced_trips"], acc2["pairs"]), (1, 0, 0))

    print_resid(pl_r)
    blob_r = json.dumps({"stage": "B10", "step": "resid", **pl_r},
                        indent=2, sort_keys=True)
    print(f"\n     printer and json.dumps both exercised, {len(blob_r):,} bytes")
    buf, keep = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        p5 = dict(pl_r); p5["rows_no_payment"] = pl_r["rows_no_payment"] + 1
        print_resid(p5)
    finally:
        sys.stdout = keep
    chk("    a gate-2 count that does not reconcile says so on the page",
        "DO NOT MATCH" in buf.getvalue(), True)

    # §8·19·8's sub-causes. Registered before the code before this was
    # written. **The refactor must not move a single gate**, so the first
    # thing tested is that the six-way split is the same predicate as the
    # single `or` it replaced.
    print("\n  §8·19·8, the six-way splits:")
    VALS = (None, -1, 0, 1, 2, 400)
    RATES = (None, 6.0)
    PERS = (-1, 200002)
    same, checked = True, 0
    for n_now in VALS:
        for n_prev in VALS:
            for i_now in RATES:
                for i_prev in RATES:
                    for per in PERS:
                        orig = (n_now is None or n_prev is None
                                or i_now is None or i_prev is None
                                or n_now <= 0 or n_prev <= 1 or per < 0)
                        s4v = (n_now is None, n_prev is None,
                               i_now is None or i_prev is None, per < 0,
                               n_now is not None and n_now <= 0,
                               n_prev is not None and n_prev <= 1)
                        checked += 1
                        if any(s4v) != orig:
                            same = False
    chk(f"    gate 4's six-way split is the same predicate as its `or` "
        f"({checked} cases)", same, True)

    #: Each reachable sub-cause fires on a fixture built for it, and the six
    #: sum to the gate. A split whose members never fire is a split in name.
    def sub4run(rows):
        acc = resid_new_acc()
        resid_absorb(acc, rows, ORIG, 2001, tpos, ttab, 5, RM, PAY)
        return acc

    a = sub4run(RR(CLEAN[0][:6] + (None, 0.0), CLEAN[1], CLEAN[2]))
    chk("    an unreadable rem on the previous row names itself",
        (a["sub4"][RESID_SUB4[1]], a["sub4"][RESID_SUB4[0]]), (1, 0))
    a = sub4run(RR(CLEAN[0], CLEAN[1][:6] + (None, 0.0), CLEAN[2]))
    chk("    and on this row, itself",
        (a["sub4"][RESID_SUB4[0]], a["sub4"][RESID_SUB4[1]]), (1, 1))
    a = sub4run(BADPER)
    chk("    an unreadable period names itself",
        a["sub4"][RESID_SUB4[3]], 1)
    a = sub4run(RR(CLEAN[0], CLEAN[1][:6] + (0, 0.0), CLEAN[2]))
    chk("    rem 0 on this row names itself, and rem 0 as `prev` next",
        (a["sub4"][RESID_SUB4[4]], a["sub4"][RESID_SUB4[5]]), (1, 1))
    a = sub4run(SHORTREM)
    chk("    rem 1 on the previous row names itself",
        a["sub4"][RESID_SUB4[5]], 1)
    a = sub4run(BLANK)
    chk("    an unreadable column 12 names itself on both pairs",
        (a["sub3"][RESID_SUB3[2]], a["sub3"][RESID_SUB3[3]]), (1, 1))
    a = sub4run(NEG)
    chk("    a negative bal_ib names itself on both pairs",
        (a["sub3"][RESID_SUB3[4]], a["sub3"][RESID_SUB3[5]]), (1, 1))

    #: **The three that cannot fire.** Proved through `floor_window`, not
    #: observed as zeros: a trip carrying an unreadable UPB or rate never
    #: becomes `priced`, so `resid_absorb` returns before the pair walk.
    for tag, bad in (("UPB", RR(CLEAN[0], CLEAN[1][:4] + (None,)
                                + CLEAN[1][5:], CLEAN[2])),
                     ("rate", RR(CLEAN[0], CLEAN[1][:5] + (None,)
                                 + CLEAN[1][6:], CLEAN[2]))):
        chk(f"    floor_window refuses a trip with an unreadable {tag}",
            floor_window(bad)[0], "unreadable")
        a = sub4run(bad)
        chk(f"    so no {tag} sub-cause can fire, and no gate at all",
            (a["priced_trips"], a["pairs"], sum(a["sub3"].values()),
             sum(a["sub4"].values())), (0, 0, 0, 0))

    #: §8·19·8 variable two's census.
    ALLBAD = RR(CLEAN[0][:6] + (None, 0.0), CLEAN[1][:6] + (None, 0.0),
                CLEAN[2][:6] + (None, 0.0))
    a = sub4run(ALLBAD)
    chk("    a trip whose every rem is unreadable is counted whole",
        (a["trips_all_rem_bad"], a["rows_all_rem_bad"],
         a["pairs_in_all_rem_bad"], a["rows_rem_bad"]), (1, 3, 2, 3))
    chk("    and its pairs are exactly rows minus one",
        a["pairs_in_all_rem_bad"], a["rows_all_rem_bad"] - 1)
    a = sub4run(RR(CLEAN[0], CLEAN[1][:6] + (None, 0.0), CLEAN[2]))
    chk("    a trip with one bad rem is not a wholly bad trip",
        (a["trips_all_rem_bad"], a["rows_rem_bad"]), (0, 1))

    #: The two branch readings, all six cases driven through the printer.
    base_r = dict(pl_r)
    for tag, mut, want, var in (
            ("variable one, first",
             {"gates": {**pl_r["gates"], RESID_GATES[3]: 5},
              "sub4": {**{k: 0 for k in RESID_SUB4},
                       RESID_SUB4[0]: 2, RESID_SUB4[1]: 3},
              "sub4_total": 5}, "variable one: FIRST BRANCH", 1),
            ("variable one, second",
             {"gates": {**pl_r["gates"], RESID_GATES[3]: 5},
              "sub4": {**{k: 0 for k in RESID_SUB4},
                       RESID_SUB4[0]: 2, RESID_SUB4[5]: 3},
              "sub4_total": 5}, "variable one: SECOND BRANCH", 1),
            ("variable one, third",
             {"gates": {**pl_r["gates"], RESID_GATES[3]: 5},
              "sub4": {**{k: 0 for k in RESID_SUB4}, RESID_SUB4[0]: 2},
              "sub4_total": 2}, "variable one: THIRD BRANCH", 1),
            ("variable two, first",
             {"gates": {**pl_r["gates"], RESID_GATES[3]: 53},
              "sub4": {**{k: 0 for k in RESID_SUB4}, RESID_SUB4[0]: 53},
              "sub4_total": 53, "pairs_in_all_rem_bad": 53,
              "rows_all_rem_bad": 57, "trips_all_rem_bad": 4},
             "variable two: FIRST BRANCH", 2),
            ("variable two, second",
             {"gates": {**pl_r["gates"], RESID_GATES[3]: 60},
              "sub4": {**{k: 0 for k in RESID_SUB4},
                       RESID_SUB4[0]: 53, RESID_SUB4[5]: 7},
              "sub4_total": 60, "pairs_in_all_rem_bad": 53,
              "rows_all_rem_bad": 57, "trips_all_rem_bad": 4},
             "variable two: SECOND BRANCH", 2),
            ("variable two, third",
             {"gates": {**pl_r["gates"], RESID_GATES[3]: 40},
              "sub4": {**{k: 0 for k in RESID_SUB4}, RESID_SUB4[0]: 40},
              "sub4_total": 40, "pairs_in_all_rem_bad": 53,
              "rows_all_rem_bad": 57, "trips_all_rem_bad": 4},
             "variable two: THIRD BRANCH", 2)):
        p6 = dict(base_r); p6.update(mut)
        buf, keep = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            print_resid(p6)
        finally:
            sys.stdout = keep
        chk(f"    print_resid reads {tag}", want in buf.getvalue(), True)

    #: A producer that is not on disk must be said so, never skipped.
    buf, keep = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        print_resid(pl_r, prod=[("results/nope.json", False, []),
                                ("results/b10_floor.json", True,
                                 [("priced", pl_r["priced_trips"],
                                   "priced_trips")])])
    finally:
        sys.stdout = keep
    txt6 = buf.getvalue()
    chk("    a missing producer is reported, and a matching one matches",
        ("not on disk" in txt6) and ("MATCH" in txt6), True)
    chk("    resid_producers on a directory with neither file says so",
        [(a2, b2) for a2, b2, _ in resid_producers(Path("/nonexistent"))],
        [("results/b10_floor.json", False),
         ("results/b10_curve.json", False)])

    #: 規矩 19, driven both ways.
    buf, keep = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        same = print_vs_prior({**pl_r, "stage": "B10"}, dict(pl_r), "x.json")
        moved = print_vs_prior({**pl_r, "ok": pl_r["ok"] + 1}, dict(pl_r),
                               "x.json")
        gone = print_vs_prior({**pl_r, "zzz": 1}, dict(pl_r), "x.json")
        none = print_vs_prior(None, dict(pl_r), "x.json")
    finally:
        sys.stdout = keep
    txt7 = buf.getvalue()
    chk("    規矩 19 passes when every previous field reproduces",
        (same, none), (True, True))
    chk("    a moved field is caught and named",
        (moved, "**MOVED** ok" in txt7), (False, True))
    chk("    a vanished field is caught too, not only a moved one",
        (gone, "**GONE** zzz" in txt7), (False, True))
    chk("    and the run-describing fields are excluded by name, not by luck",
        RESID_NOT_COMPARED, ("diagnostic_reason", "stage", "step"))

    #: **The nested case, which is the whole reason this walks leaves.**
    #: `b10_noise.json` keeps this station's reading under one key, so a
    #: flat comparison names the root and dumps fifty kilobytes beside it.
    _n_old = {"coh": {"rows": {"2": {"n": 10, "q": [1, 2]}, "3": {"n": 4}}},
              "stage": "B10"}
    _n_new = {"coh": {"rows": {"2": {"n": 10, "q": [1, 3], "new": 1},
                               "3": {}}}, "stage": "B10"}
    _buf19, _keep19 = io.StringIO(), sys.stdout
    sys.stdout = _buf19
    try:
        _nested = print_vs_prior(_n_old, _n_new, "x.json")
    finally:
        sys.stdout = _keep19
    _t19 = _buf19.getvalue()
    _added_named = any(ln.strip().startswith("added")
                       and ln.strip().endswith("coh.rows.2.new")
                       for ln in _t19.splitlines())
    chk("    a leaf deep inside one key is named by its path, not its root",
        (_nested, "**MOVED** coh.rows.2.q" in _t19,
         "**GONE** coh.rows.3.n" in _t19, _added_named),
        (False, True, True, True))
    chk("    and the root itself is never what gets reported",
        ("**MOVED** coh:" in _t19) or ("**MOVED** coh " in _t19), False)
    chk("    an emptied subtree is a leaf, so it is news and not silence",
        flat_leaves({"a": {"b": {}}, "c": 1}), {"a.b": {}, "c": 1})
    _buf19b, _keep19b = io.StringIO(), sys.stdout
    sys.stdout = _buf19b
    try:
        print_vs_prior({"a": 1}, {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5},
                       "x.json", cap=2)
    finally:
        sys.stdout = _keep19b
    chk("    and the cap says how many lines it did not print",
        "and 2 more under added" in _buf19b.getvalue(), True)
    print("     (a silent cap reads as full coverage — B8's own words about")
    print("      `capped_at`. And a MOVED line that dumps a whole subtree is")
    print("      §11 item 3 from the other side: there the check could not")
    print("      fail, here it could not be read, and both print something")
    print("      that looks like diligence.)")

    # --omega, §8·20. Registered before the code.
    # The arithmetic is checked by §8·19·3 against B8's closed form; what is
    # checked here is the population, the four screens and the k convention.
    print("\n  --omega, §8·20's loop sum:")

    #: §8·20·6, the whole point. B8's k is the missed-month count; §8·16's is
    #: the span. **One lower, always**, and both are printed so the difference
    #: cannot be argued about.
    chk("    b8_k is the missed-month count, not the span",
        [b8_k(["r"] * n) for n in (3, 4, 5, 8)], [1, 2, 3, 6])
    chk("    and it is exactly one below §8·16's k_hist key",
        all(b8_k(["r"] * n) + 1 == n - 1 for n in range(3, 40)), True)

    #: `is_del_digits` was lifted out of `classify_loan`'s closure. **The
    #: equality is proved against `classify_loan` itself**, over an alphabet
    #: that includes every two-digit value and the odd tokens §10·6 has seen.
    ALPHA = ["%02d" % i for i in range(100)] + [
        "", " ", "  ", "0", "1", "000", "R", "RA", "XX", "9A", "A9", "0a",
        "01 ", " 01", "100", "-1"]
    agree = True
    for tok in ALPHA:
        c2 = classify_loan([(200001, "00", ""), (200002, tok, ""),
                            (200003, "00", "")])
        if c2["digits"]["between"] != is_del_digits(tok):
            agree = False
    chk(f"    is_del_digits agrees with classify_loan on {len(ALPHA)} tokens",
        agree, True)

    #: A curve of three consecutive months, so a clean loop has no gap.
    opos = {month_index_of(m): j for j, m in enumerate((200002, 200003,
                                                        200004))}
    otab = [[NAN] * 6 for _ in range(3)]
    for row in range(3):
        for h in (1, 2, 3):
            otab[row][h] = 1.0 + 0.1 * h

    OCLEAN = RR((200002, "00", "", 20, 100_000.0, 6.0, 3, 0.0),
                (200003, "01", "", 21, 100_000.0, 6.0, 2, 0.0),
                (200004, "00", "", 22, 99_000.0, 6.0, 1, 0.0))

    class _SW:
        """A stub residual. The real one is exercised by §8·19·3."""
        @staticmethod
        def r_month(*a, **k):
            return 0.001

        @staticmethod
        def loop_residual_ideal(B0, note, P, k):
            return 0.001 * (k + 1)

        @staticmethod
        def carry_forward(b, note, P):
            return b * (1.0 + note / 1200.0) - P

    class _SG:
        IDEAL_TOL_LOOSE = 0.05

        @staticmethod
        def ideal_tol(note, k):
            return 0.01

    def orun(rows, W=_SW, G=_SG, orig=ORIG, pay=PAY):
        acc = omega_new_acc()
        omega_absorb(acc, rows, orig, 2001, opos, otab, 5, W, G, pay)
        return acc

    a = orun(OCLEAN)
    chk("    a clean loop is measured, on both populations",
        (a["priced_trips"], a["as16"]["n"], a["b8like"]["n"]), (1, 1, 1))
    chk("    its k is B8's, and the stub's closed form matches the stream",
        (list(a["as16"]["k"]), a["as16"]["ratio"][0]), ([1], 0.0))
    chk("    and no screen fired",
        (a["screened_out"], sum(a["screen_any"].values())), (0, 0))

    #: One fixture per screen, each named after the B8 line it mirrors.
    ODEFER = RR(OCLEAN[0], OCLEAN[1][:7] + (5_000.0,), OCLEAN[2])
    OBLANK = RR(OCLEAN[0], OCLEAN[1][:7] + (None,), OCLEAN[2])
    OGAP = RR(OCLEAN[0], (200004,) + OCLEAN[1][1:],
              (200002,) + OCLEAN[2][1:])
    for tag, rows, idx in (("a positive column 12", ODEFER, 0),
                           ("a period gap", OGAP, 2)):
        a = orun(rows)
        chk(f"    {tag} keeps the loop in as16 and out of b8like",
            (a["as16"]["n"], a["b8like"]["n"], a["screened_out"],
             a["screen_first"][OMEGA_SCREENS[idx]]), (1, 0, 1, 1))
    #: A blank column 12 stops at gate 3 before the screen is reached, which
    #: is the right order: an unreadable balance is not a screened loop.
    a = orun(OBLANK)
    chk("    a blank column 12 is unmeasurable, and never reaches the screens",
        (a["not_measurable"], a["as16"]["n"], a["screened_out"],
         sum(a["screen_any"].values())), (1, 0, 0, 0))
    #: The `p_ndq` screen needs a window with a current month inside it, which
    #: `between_window` will not produce, so it is driven on `omega_flags`
    #: directly. **A screen that cannot be reached through the finder is still
    #: written and still tested** (§11 item 3's converse).
    chk("    omega_flags names a non-delinquent month inside the window",
        omega_flags(RR(OCLEAN[0], (200003, "00", "", 21, 100_000.0, 6.0, 2,
                                   0.0), OCLEAN[1], OCLEAN[2])), 
        (False, False, True, True))
    chk("    and a clean window trips none of the four",
        omega_flags(OCLEAN), (False, False, False, False))

    #: Two screens at once: once in the first-match column, twice in the
    #: independent one. **This is the §8·19·8 lesson made into a test.**
    OTWO = RR(OCLEAN[0], (200004, "01", "", 21, 100_000.0, 6.0, 2, 5_000.0),
              (200002,) + OCLEAN[2][1:])
    a = orun(OTWO)
    chk("    a loop tripping two screens counts once first-match, twice free",
        (a["screened_out"], sum(a["screen_first"].values()),
         sum(a["screen_any"].values())), (1, 1, 2))

    #: Unmeasurable, and which gate stopped it.
    a = orun(RR(OCLEAN[0], OCLEAN[1][:6] + (None, 0.0), OCLEAN[2]))
    chk("    a month with no computable r drops the whole loop, gate named",
        (a["not_measurable"], a["as16"]["n"],
         a["nm_by_gate"].get(RESID_GATES[3])), (1, 0, 1))
    a = orun(OCLEAN, orig=None)
    chk("    a loop with no usable payment is counted apart",
        (a["no_P"], a["as16"]["n"]), (1, 0))

    class _SWNAN(_SW):
        @staticmethod
        def loop_residual_ideal(B0, note, P, k):
            return float("nan")
    a = orun(OCLEAN, W=_SWNAN)
    chk("    f(B0) <= 0 is counted apart, never swallowed",
        (a["closed_no_log"], a["as16"]["n"]), (1, 0))

    #: The population line has to add up, or section A is decoration.
    acc = omega_new_acc()
    for rows, o, W2 in ((OCLEAN, ORIG, _SW), (ODEFER, ORIG, _SW),
                        (OGAP, ORIG, _SW), (OBLANK, ORIG, _SW),
                        (OCLEAN, None, _SW), (OCLEAN, ORIG, _SWNAN),
                        (OTWO, ORIG, _SW)):
        omega_absorb(acc, rows, o, 2001, opos, otab, 5, W2, _SG, PAY)
    oacc_for_noise = acc
    pl_o = omega_payload(acc)
    chk("    the population line adds up",
        (pl_o["no_P"] + pl_o["span_too_short"] + pl_o["not_measurable"]
         + pl_o["closed_no_log"] + pl_o["as16"]["n"]), pl_o["priced_trips"])
    chk("    and first-match sums to the screened-out count",
        sum(pl_o["screen_first"].values()), pl_o["screened_out"])

    #: §8·20·6 item 2, as a test rather than as a claim: §8·16's bound is the
    #: same function at a higher k, so the ratio is above one, always.
    chk("    §8·16's bound is strictly the more conservative of the two",
        all(floor_bound(n - 1, nt, bb) > floor_bound(b8_k(["r"] * n), nt, bb)
            for n in (3, 4, 8, 20) for nt in (3.0, 6.5, 11.25)
            for bb in (1_000.0, 145_972.35)), True)
    chk("    and the measured ratio is above one on the fixtures too",
        min(pl_o["q_b16_ratio"]) > 1.0, True)

    print_omega(pl_o)
    blob_o = json.dumps({"stage": "B10", "step": "omega", **pl_o},
                        indent=2, sort_keys=True)
    print(f"\n     printer and json.dumps both exercised, {len(blob_o):,} bytes")

    for tag, mut, want in (
            ("first", {"ratio_max_derived": 0.4, "ideal_derived": 9}, "FIRST"),
            ("second", {"ratio_max_derived": 1.7, "ideal_derived": 9,
                        "over_one_derived": 2}, "SECOND"),
            ("third", {"ratio_max_derived": None, "ideal_derived": 0},
             "THIRD")):
        p8 = dict(pl_o); p8["b8like"] = {**pl_o["b8like"], **mut}
        buf, keep = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            print_omega(p8)
        finally:
            sys.stdout = keep
        t8 = buf.getvalue()
        others = {"FIRST", "SECOND", "THIRD"} - {want}
        chk(f"    print_omega reads the {tag} branch for §8·20·3",
            (f"§8·20·3 -> {want} BRANCH" in t8)
            and not any(f"§8·20·3 -> {o} BRANCH" in t8 for o in others), True)

    #: §8·20·8's two payments. Registered before the code before this was
    #: written, together with a falsifiable prediction.
    print("\n  §8·20·8, the two payments:")
    _seen = []

    def SPY(u, i, n):
        _seen.append((u, i, n))
        return 100.0

    chk("    substitution_payment reads the loop's FIRST row",
        (substitution_payment(OCLEAN[0], SPY), _seen[-1][0], _seen[-1][2]),
        (100.0, 100_000.0, 3))
    chk("    and it uses the interest-bearing balance, not the raw UPB",
        (substitution_payment(OCLEAN[0][:7] + (2_500.0,), SPY),
         _seen[-1][0]), (100.0, 97_500.0))
    chk("    and the rate as a monthly decimal, as contract_payment wants",
        round(_seen[-1][1] * 1200.0, 6), 6.0)
    for tag, row in (("no rem", OCLEAN[0][:6] + (None, 0.0)),
                     ("rem 0", OCLEAN[0][:6] + (0, 0.0)),
                     ("no UPB", OCLEAN[0][:4] + (None,) + OCLEAN[0][5:]),
                     ("no column 12", OCLEAN[0][:7] + (None,)),
                     ("column 12 above the UPB",
                      OCLEAN[0][:7] + (200_000.0,))):
        chk(f"    a row with {tag} yields no substitution payment",
            substitution_payment(row, SPY), None)
    chk("    a payment that will not compute is None, not a silent zero",
        substitution_payment(OCLEAN[0], lambda u, i, n: float("nan")), None)

    a = orun(OCLEAN)
    chk("    both payments file the same loop into their own trees",
        (a["as16"]["n"], a["p_sub"]["as16"]["n"], a["p_sub"]["b8like"]["n"]),
        (1, 1, 1))
    chk("    and their relative difference is recorded",
        (len(a["p_reldiff"]), a["p_sub_unusable"]), (1, 0))
    a = orun(RR(OCLEAN[0][:6] + (0, 0.0), OCLEAN[1], OCLEAN[2]))
    chk("    a first row with rem 0 leaves P_sub unusable and says so",
        (a["p_sub_unusable"], a["p_sub"]["no_P"], a["p_sub"]["as16"]["n"]),
        (1, 1, 0))
    chk("    while P_orig still measures its own loop",
        a["as16"]["n"] + a["not_measurable"], 1)

    #: H2's three branches, driven through the printer. Fannie's band is
    #: [0.5354, 0.6619] and the third branch's threshold is a tenth of the
    #: P_orig rate, both as registered.
    for tag, ro, rsub, want in (("first", 0.1082, 0.6000, "FIRST"),
                                ("second", 0.1082, 0.3000, "SECOND"),
                                ("third", 0.1082, 0.1100, "THIRD"),
                                ("third by default", 0.1082, None, "THIRD")):
        p9 = dict(pl_o)
        p9["b8like"] = {**pl_o["b8like"], "rate_derived": ro}
        p9["p_sub"] = {**pl_o["p_sub"],
                       "b8like": {**pl_o["p_sub"]["b8like"],
                                  "rate_derived": rsub}}
        buf, keep = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            print_omega(p9)
        finally:
            sys.stdout = keep
        t9 = buf.getvalue()
        others = {"FIRST", "SECOND", "THIRD"} - {want}
        chk(f"    print_omega reads the {tag} branch for §8·20·8",
            (f"§8·20·8 -> {want} BRANCH" in t9)
            and not any(f"§8·20·8 -> {o} BRANCH" in t9 for o in others), True)
    chk("    the third branch's threshold is a tenth, not a constant",
        (0.1082 + 0.10 * 0.1082 > 0.1100, 0.1082 + 0.10 * 0.1082 < 0.1200),
        (True, True))

    # --noise, §8·21. Registered before the code.
    print("\n  --noise, §8·21's floor:")

    #: §8·21·4's encoding, written down before it is used. The §8·20·6 bill is
    #: two days old.
    #: A loop with `k = L - 1` spans `k + 2 = L + 1` rows and its residual
    #: runs over `k + 1 = L` months; the floor's window spans `L + 1` rows and
    #: its sum runs over `L`. **Same number of terms, which is the match.**
    chk("    the floor's L matches the loop's k + 1",
        [L - 1 for L in NOISE_LENS],
        [b8_k(["r"] * (L + 1)) for L in NOISE_LENS])
    chk("    and the two windows carry the same number of terms",
        [L for L in NOISE_LENS],
        [b8_k(["r"] * (L + 1)) + 1 for L in NOISE_LENS])
    chk("    and NOISE_LENS is b8_0a_gate's own FLOOR_LENS", NOISE_LENS,
        (2, 3, 4, 7))

    def NR(n, per0=200001, age0=8, upb0=100_000.0, rate=6.0, rem0=300,
           dq="00", mod="", defer=0.0):
        return [(per0 + j, dq, mod, age0 + j, upb0 - 100.0 * j, rate,
                 rem0 - j, defer) for j in range(n)]

    NCLEAN = NR(10)
    chk("    a never-delinquent loan trips none of the three screens",
        noise_screens(NCLEAN), (False, False, False))
    for tag, rows, want in (
            ("a delinquent row", NR(3)[:1] + NR(1, per0=200002, dq="01")
             + NR(1, per0=200003), (True, False, False)),
            ("a modification flag", NR(3)[:1] + NR(1, per0=200002, mod="Y")
             + NR(1, per0=200003), (False, True, False)),
            ("a positive column 12", NR(3)[:1]
             + NR(1, per0=200002, defer=5_000.0) + NR(1, per0=200003),
             (False, False, True))):
        chk(f"    {tag} is named on its own line", noise_screens(rows), want)

    chk("    the anchor is the first usable row",
        noise_anchor(NCLEAN, None), 0)
    chk("    and with the age floor it is the first at or past it",
        noise_anchor(NR(10, age0=2), FLOOR_MIN_AGE), 6)
    chk("    a loan that never reaches the age floor has no cent anchor",
        noise_anchor(NR(4, age0=0), FLOOR_MIN_AGE), None)
    chk("    an unreadable UPB is skipped by the anchor, not accepted",
        noise_anchor([NCLEAN[0][:4] + (None,) + NCLEAN[0][5:]] + NCLEAN[1:],
                     None), 1)

    class _NW:
        @staticmethod
        def carry_forward(b, note, P):
            return b * (1.0 + note / 1200.0) - P

        @staticmethod
        def r_month(*a, **k):
            return 0.001

    chk("    a clean window sums L terms",
        noise_window(NCLEAN, 0, 4, 500.0, _NW), (None, 0.004))
    chk("    a window running past the loan is named",
        noise_window(NCLEAN, 7, 4, 500.0, _NW)[0], NOISE_SKIPS[0])
    GAPPED = NCLEAN[:3] + [(200099,) + t[1:] for t in NCLEAN[3:]]
    chk("    a period gap is named", noise_window(GAPPED, 0, 4, 500.0, _NW)[0],
        NOISE_SKIPS[1])
    BADROW = NCLEAN[:2] + [NCLEAN[2][:4] + (None,) + NCLEAN[2][5:]] \
        + NCLEAN[3:]
    chk("    an unusable row inside the window is named",
        noise_window(BADROW, 0, 4, 500.0, _NW)[0], NOISE_SKIPS[2])
    chk("    a non-positive rate at the anchor is named",
        noise_window([NCLEAN[0][:5] + (0.0,) + NCLEAN[0][6:]] + NCLEAN[1:],
                     0, 4, 500.0, _NW)[0], NOISE_SKIPS[3])
    chk("    no payment is named, not treated as zero",
        noise_window(NCLEAN, 0, 4, None, _NW)[0], NOISE_SKIPS[4])
    sk, exv = noise_window(NCLEAN, 0, 4, 1e9, _NW)
    chk("    a payment that drives b_hat non-positive is named",
        sk, NOISE_SKIPS[5])
    chk("    and it carries the values, not a bare flag",
        sorted(exv), ["P", "b_hat", "bal_now", "bal_prev", "note", "t"])

    acc = noise_new_acc()
    noise_absorb(acc, NCLEAN, (100_000.0, 6.0, 360), 2001, _NW,
                 lambda u, i, n: 500.0)
    chk("    a clean loan fills all four (anchor, payment) cells",
        [acc["cells"][(a2, p2)][2]["kept"] for a2 in ("cent", "grid")
         for p2 in ("orig", "sub")], [1, 1, 1, 1])
    chk("    and the screens leave it alone",
        (acc["clean_loans"], sum(acc["screen_any"].values())), (1, 0))
    acc = noise_new_acc()
    for _ in range(NOISE_CAP + 3):
        noise_absorb(acc, NCLEAN, (100_000.0, 6.0, 360), 2001, _NW,
                     lambda u, i, n: 500.0)
    c0 = acc["cells"][("cent", "orig")][2]
    chk("    the per-vintage cap binds and says so",
        (c0["kept"], c0["capped"]), (NOISE_CAP, True))
    noise_absorb(acc, NCLEAN, (100_000.0, 6.0, 360), 2002, _NW,
                 lambda u, i, n: 500.0)
    chk("    and a new vintage gets its own budget, not the leftovers",
        acc["cells"][("cent", "orig")][2]["kept"], NOISE_CAP + 1)

    #: The AUC and its null. `_ranks` first, because a wrong rank table makes
    #: every number downstream plausible and wrong.
    chk("    _ranks averages ties", _ranks([10, 20, 20, 30]),
        [1.0, 2.5, 2.5, 4.0])
    chk("    and handles a flat vector", _ranks([5, 5, 5]), [2.0, 2.0, 2.0])
    chk("    an empty side has no AUC, it does not win",
        (noise_auc([], [1.0, 2.0]), noise_auc([1.0], [])), (None, None))
    r1 = noise_auc([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], n_perm=199)
    chk("    two identical samples give AUC 0.5, inside the null",
        (round(r1["auc"], 6), r1["outside"]), (0.5, False))
    r2 = noise_auc([float(x) for x in range(200, 400)],
                   [float(x) for x in range(200)], n_perm=199)
    chk("    a wholly separated pair gives AUC 1 and sits outside the null",
        (round(r2["auc"], 6), r2["outside"], r2["auc"] > r2["null_p95"]),
        (1.0, True, True))
    r3 = noise_auc([float(x) for x in range(200)],
                   [float(x) for x in range(200, 400)], n_perm=199)
    chk("    the reverse gives 0 and is also outside, on the other side",
        (round(r3["auc"], 6), r3["outside"], r3["auc"] < r3["null_p05"]),
        (0.0, True, True))
    chk("    the null is reproducible from its printed seed",
        noise_auc([1.0, 5.0, 9.0], [2.0, 3.0, 4.0], n_perm=99)["null_p95"],
        noise_auc([1.0, 5.0, 9.0], [2.0, 3.0, 4.0], n_perm=99)["null_p95"])

    pl_n = noise_payload(acc, oacc_for_noise)
    print_noise(pl_n)
    blob_n = json.dumps({"stage": "B10", "step": "noise", **pl_n},
                        indent=2, sort_keys=True)
    print(f"\n     printer and json.dumps both exercised, {len(blob_n):,} bytes")

    for tag, om, fl, want in (
            ("first", [10.0] * 40, [1.0] * 40, "FIRST"),
            ("second", [float(x % 7) for x in range(40)],
             [float(x % 7) for x in range(40)], "SECOND"),
            ("third", [1.0] * 40, [10.0] * 40, "THIRD")):
        pn = dict(pl_n)
        pn["auc"] = {str(L): (noise_auc(om, fl, n_perm=99) if L == 2 else None)
                     for L in NOISE_LENS}
        pn["auc_sizes"] = {str(L): {"omega": len(om), "floor": len(fl),
                                    "k": L - 1} for L in NOISE_LENS}
        #: §8·21·9's own pair, driven the other way round on the same
        #: fixtures, so both sections are exercised on every branch.
        pn["auc_all"] = {str(L): (noise_auc(fl, om, n_perm=99) if L == 2
                                  else None) for L in NOISE_LENS}
        pn["auc_all_sizes"] = {
            str(L): {"omega": len(fl), "floor": len(om), "k": L - 1,
                     "omega_absmed": _q([abs(x) for x in fl], (50,))[0],
                     "floor_absmed": _q([abs(x) for x in om], (50,))[0]}
            for L in NOISE_LENS}
        buf, keep = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            print_noise(pn)
        finally:
            sys.stdout = keep
        tn = buf.getvalue()
        others = {"FIRST", "SECOND", "THIRD"} - {want}
        chk(f"    print_noise reads the {tag} branch for §8·21·5",
            (f"§8·21·5 {want}: " in tn)
            and not any(f"§8·21·5 {o}: " in tn for o in others), True)
    chk("    a length with no referent says so rather than reading a branch",
        "NO REFERENT" in tn, True)
    #: §8·21·9's section is driven with the two sides swapped, so its branch
    #: must be the mirror of §8·21·5's on the same fixture.
    chk("    and §8·21·9's section reads the mirrored branch on the same data",
        "§8·21·9 FIRST: " in tn, True)

    # --loops, §8·22. Registered before the code.
    # **No omega is computed anywhere in this section**, here or in the runner.
    print("\n  --loops, §8·22's windows:")

    def LR(*t):
        """(delinq, modflag, defer) -> a row in `floor_row`'s shape."""
        return [(200001 + j, dq, mf, 20 + j, 100_000.0 - 100.0 * j, 6.0,
                 300 - j, df) for j, (dq, mf, df) in enumerate(t)]

    #: **A leading current row, on purpose.** `find_loops` drops a loop whose
    #: departure is the loan's own first row (`ok_not_first`), so a fixture
    #: without a lead tests the condition instead of the loop. That is how the
    #: first version of this block was written, and every "all six pass" check
    #: read False for a reason that had nothing to do with what it was testing.
    LEAD = ("00", "", 0.0)
    TRI = LR(LEAD, ("00", "", 0.0), ("01", "", 0.0), ("02", "Y", 0.0),
             ("00", "", 0.0))
    lp, c = find_loops_rows(TRI, ("Y", "P"))
    chk("    a canonical triangle gives one loop at the right rows",
        (len(lp), lp[0]["t_A"], lp[0]["t_M"], lp[0]["t_B"], lp[0]["arm"]),
        (1, 1, 3, 4, "mod"))
    chk("    and every one of its six conditions passes",
        all(lp[0]["ok"].values()), True)
    chk("    the census counts the onset once, on the right side",
        (c["onsets_raw"], c["onsets_mod"], c["onsets_defer"]), (1, 1, 0))

    DEF = LR(LEAD, ("00", "", 0.0), ("01", "", 0.0), ("02", "", 5_000.0),
             ("00", "", 5_000.0))
    lp, c = find_loops_rows(DEF, ("Y", "P"))
    chk("    a deferral onset is the other arm, at column 12",
        (len(lp), lp[0]["arm"], c["onsets_defer"], c["onsets_mod"]),
        (1, "defer", 1, 0))

    BOTH = LR(LEAD, ("00", "", 0.0), ("01", "Y", 0.0), ("02", "", 5_000.0),
              ("00", "", 5_000.0))
    lp, _c = find_loops_rows(BOTH, ("Y", "P"))
    chk("    two arms in one window fail two_arms and nothing else",
        (lp[0]["ok"]["two_arms"],
         sum(1 for g, v in lp[0]["ok"].items() if not v)), (False, 1))
    chk("    and the arm label goes to the modification, as B8 does",
        lp[0]["arm"], "mod")

    #: §17.3: the flag turns on and the row already reads `00`, so leg 3 is
    #: empty **by construction**. Counted, never pooled.
    EMPTY3 = LR(LEAD, ("00", "", 0.0), ("01", "", 0.0), ("00", "Y", 0.0))
    lp, _c = find_loops_rows(EMPTY3, ("Y", "P"))
    chk("    t_M == t_B is found and flagged, not silently ordinary",
        (lp[0]["t_M"], lp[0]["t_B"], lp[0]["empty_leg3"]), (3, 3, True))
    chk("    and it still passes every condition, so it is a real loop",
        all(lp[0]["ok"].values()), True)

    NOCUR = LR(("01", "", 0.0), ("02", "Y", 0.0), ("00", "", 0.0))
    lp, c = find_loops_rows(NOCUR, ("Y", "P"))
    chk("    an onset with no current row before it is counted, not a loop",
        (len(lp), c["drop_no_current_before"], c["candidate_loops"]),
        (0, 1, 0))

    NEVER = LR(LEAD, ("00", "", 0.0), ("01", "", 0.0), ("02", "Y", 0.0),
               ("03", "", 0.0))
    lp, _c = find_loops_rows(NEVER, ("Y", "P"))
    chk("    a loop that never cures is not closed, and carries no verdicts",
        (lp[0]["closed"], "ok" in lp[0]), (False, False))

    LEFT = LR(("00", "Y", 0.0), ("01", "Y", 0.0), ("02", "Y", 0.0),
              ("00", "Y", 0.0))
    _lp, c = find_loops_rows(LEFT, ("Y", "P"))
    chk("    a state present on the first row is left truncation, not an "
        "onset", (c["left_truncated_mod"], c["onsets_mod"]), (1, 0))

    #: §8·22·3: `P` is a modification value on this carrier and not on Fannie.
    PONLY = LR(("00", "", 0.0), ("01", "", 0.0), ("02", "P", 0.0),
               ("00", "", 0.0))
    chk("    a `P` flag is an onset under YP and not under Y",
        (len(find_loops_rows(PONLY, ("Y", "P"))[0]),
         len(find_loops_rows(PONLY, ("Y",))[0])), (1, 0))

    #: Each remaining condition, one fixture apiece.
    GAP = TRI[:2] + [(200099,) + TRI[2][1:]] + TRI[3:]
    chk("    a period gap in the window is caught",
        find_loops_rows(GAP, ("Y", "P"))[0][0]["ok"]["gap_in_window"], False)
    NODEL = LR(LEAD, ("00", "", 0.0), ("00", "Y", 0.0), ("00", "", 0.0))
    ld = find_loops_rows(NODEL, ("Y", "P"))[0]
    chk("    a window with no delinquent month is caught",
        ld[0]["ok"]["no_delinquency"], False)
    FIRST = LR(("00", "", 0.0), ("01", "", 0.0), ("02", "Y", 0.0),
               ("00", "", 0.0))
    chk("    departure on the loan's first row is caught",
        find_loops_rows(FIRST, ("Y", "P"))[0][0]["ok"][
            "departure_is_first_row"], False)
    BADREM = TRI[:1] + [TRI[1][:6] + (None, 0.0)] + TRI[2:]
    chk("    an unreadable rem at a vertex is caught",
        find_loops_rows(BADREM, ("Y", "P"))[0][0]["ok"]["vertex_rem_blank"],
        False)
    BADUPB = TRI[:1] + [TRI[1][:4] + (0.0,) + TRI[1][5:]] + TRI[2:]
    chk("    a zero UPB at a vertex is caught",
        find_loops_rows(BADUPB, ("Y", "P"))[0][0]["ok"]["vertex_upb_zero"],
        False)

    #: marginal and alone must differ exactly where conditions overlap.
    accl = loops_new_acc()
    for L8 in (TRI, DEF, BOTH, EMPTY3, NOCUR, NEVER, GAP, NODEL, BADREM,
               BADUPB):
        loops_absorb(accl, L8, 2001)
    pl_l = loops_payload(accl)
    m = pl_l["cuts"]["YP"]
    chk("    not closed + dropped + loops = candidates",
        m["not_closed"] + m["marginal_total"] + m["loops"],
        m["candidate_loops"])
    chk("    right censored + terminated = not closed",
        m["right_censored"] + m["terminated"], m["not_closed"])
    chk("    and a condition's alone is at least its marginal",
        all(m["alone"][g] >= m["marginal"][g] for g in LOOPS_TESTS), True)
    #: **The wider value set does NOT always give more onsets, and the first
    #: version of this block asserted that it did.** The assertion passed on a
    #: fixture with no alternation and read false on the archives: 18,354
    #: under `YP` against 21,397 under `Y`. An onset is a **rising edge**, so
    #: a flag that alternates `P, Y, P, Y` is continuously on under `YP` and
    #: switches four times under `Y`. A fixture that cannot produce the
    #: sequence cannot test the claim.
    ALT = LR(LEAD, ("00", "", 0.0), ("01", "P", 0.0), ("02", "Y", 0.0),
             ("03", "P", 0.0), ("00", "Y", 0.0))
    chk("    an alternating flag gives FEWER onsets under the wider set",
        (find_loops_rows(ALT, ("Y", "P"))[1]["onsets_mod"],
         find_loops_rows(ALT, ("Y",))[1]["onsets_mod"]), (1, 2))
    chk("    while a single flag gives more under the wider set",
        (find_loops_rows(PONLY, ("Y", "P"))[1]["onsets_mod"],
         find_loops_rows(PONLY, ("Y",))[1]["onsets_mod"]), (1, 0))
    chk("    so neither cut dominates, and both are printed",
        sorted(pl_l["cuts"]), ["Y", "YP"])

    #: The ruler, before it is used on anything.
    chk("    rank_corr on a perfectly monotone pair reads +1, outside",
        (round(rank_corr([1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6],
                         n_perm=199)["rho"], 6),
         rank_corr([1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6],
                   n_perm=199)["outside"]), (1.0, True))
    chk("    reversed reads -1, also outside",
        (round(rank_corr([1, 2, 3, 4, 5, 6], [6, 5, 4, 3, 2, 1],
                         n_perm=199)["rho"], 6),
         rank_corr([1, 2, 3, 4, 5, 6], [6, 5, 4, 3, 2, 1],
                   n_perm=199)["outside"]), (-1.0, True))
    chk("    a constant side has no rank order, and says so",
        rank_corr([1, 2, 3, 4], [7, 7, 7, 7], n_perm=99), None)
    chk("    fewer than three points is not a reading",
        rank_corr([1, 2], [1, 2], n_perm=99), None)
    chk("    and the null is reproducible from its printed seed",
        rank_corr([1, 2, 3, 4, 5], [2, 1, 4, 3, 5], n_perm=99)["null_p95"],
        rank_corr([1, 2, 3, 4, 5], [2, 1, 4, 3, 5], n_perm=99)["null_p95"])

    #: §8·22·8's census, registered before it was written. It reads only on
    #: candidates `no_delinquency` refuses, and it must tell "no delinquent
    #: month" apart from "the states will not read" (§11 item 6).
    ld2 = find_loops_rows(NODEL, ("Y", "P"))[0][0]
    chk("    a refused window carries its own state census",
        (ld2["gap_M"], ld2["win_cur"], ld2["win_unk"], ld2["empty_leg3"]),
        (1, 1, 0, True))
    UNK = LR(LEAD, ("00", "", 0.0), ("RA", "", 0.0), ("00", "Y", 0.0))
    lu = find_loops_rows(UNK, ("Y", "P"))[0][0]
    chk("    an unreadable state is counted apart from a current one",
        (lu["ok"]["no_delinquency"], lu["win_cur"], lu["win_unk"]),
        (False, 1, 1))
    accn = loops_new_acc()
    for L9 in (NODEL, NODEL, UNK):
        loops_absorb(accn, L9, 2001)
    nd2 = loops_payload(accn)["cuts"]["YP"]["no_delinq_census"]
    chk("    the census counts the refusals, not the loops",
        (nd2["n"], nd2["gapM_eq1_and_empty_leg3"],
         nd2["windows_with_unknown_row"], nd2["rows_unknown"]), (3, 2, 1, 1))
    chk("    and its top t_M - t_A is a value, not a count",
        (nd2["top_gapM"], nd2["gapM_hist"]["1"]), (1, 2))
    chk("    §8·22·8's census does not move a single gate",
        (loops_payload(accn)["cuts"]["YP"]["loops"],
         loops_payload(accn)["cuts"]["YP"]["marginal"]["no_delinquency"]),
        (0, 3))

    for tag, mut, want in (
            ("first", {"n": 100, "top_gapM": 1,
                       "gapM_eq1_and_empty_leg3": 90,
                       "windows_with_unknown_row": 0, "rows_unknown": 0,
                       "share_both": 0.90}, "FIRST"),
            ("second", {"n": 100, "top_gapM": 1,
                        "gapM_eq1_and_empty_leg3": 90,
                        "windows_with_unknown_row": 7, "rows_unknown": 9,
                        "share_both": 0.90}, "SECOND"),
            ("third", {"n": 100, "top_gapM": 5,
                       "gapM_eq1_and_empty_leg3": 3,
                       "windows_with_unknown_row": 0, "rows_unknown": 0,
                       "share_both": 0.03}, "THIRD")):
        pq = dict(pl_l)
        pq["cuts"] = dict(pl_l["cuts"])
        pq["cuts"]["YP"] = {**m,
                            "no_delinq_census": {**m["no_delinq_census"],
                                                 **mut}}
        buf, keep = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            print_loops(pq)
        finally:
            sys.stdout = keep
        tq = buf.getvalue()
        others = {"FIRST", "SECOND", "THIRD"} - {want}
        chk(f"    print_loops reads the {tag} branch for §8·22·8",
            (f"§8·22·8 -> {want} BRANCH" in tq)
            and not any(f"§8·22·8 -> {o} BRANCH" in tq for o in others), True)

    #: §8·22·9's buckets and its census. Registered before it was written.
    chk("    the prior-delinquency buckets are fixed and cover the cases",
        [prior_del_bucket(g) for g in (None, "unreadable", 0, -3, 1, 2, 3, 4,
                                       6, 7, 12, 13, 400)],
        ["never", "unreadable", "<=0", "<=0", "1", "2", "3", "4-6", "4-6",
         "7-12", "7-12", "13+", "13+"])
    chk("    and every one of them is a declared bucket",
        all(prior_del_bucket(g) in PRIOR_DEL_BUCKETS
            for g in [None, "unreadable"] + list(range(-40, 200))), True)
    #: **`<=0` is its own bucket.** The first version tested `gap < 0` against
    #: an integer sentinel, so a genuinely out-of-order pair of periods was
    #: relabelled unparseable. Two different things, one bucket (§11 item 6).
    chk("    an out-of-order gap is not the same thing as an unreadable one",
        (prior_del_bucket(-3), prior_del_bucket("unreadable")),
        ("<=0", "unreadable"))

    #: **Months, not rows.** A hole in the periods must not read as two months,
    #: which is what counting rows would do.
    PRIOR = [(200001, "01", "", 20, 100_000.0, 6.0, 300, 0.0),
             (200002, "00", "", 21, 99_900.0, 6.0, 299, 0.0),
             (200003, "00", "Y", 22, 99_800.0, 6.0, 298, 0.0)]
    lpz = find_loops_rows(PRIOR, ("Y", "P"))[0][0]
    chk("    prior_del_gap counts from t_A back to the last delinquent row",
        (lpz["t_A"], lpz["t_M"], lpz["prior_del_gap"]), (1, 2, 1))
    HOLE = PRIOR[:1] + [(200301,) + PRIOR[1][1:], (200302,) + PRIOR[2][1:]]
    chk("    and it counts MONTHS, so a hole is not one row",
        find_loops_rows(HOLE, ("Y", "P"))[0][0]["prior_del_gap"], 36)
    BADPER2 = [(-1,) + PRIOR[0][1:]] + PRIOR[1:]
    chk("    an unreadable period says unreadable, not a number",
        prior_del_bucket(
            find_loops_rows(BADPER2, ("Y", "P"))[0][0]["prior_del_gap"]),
        "unreadable")
    NOPRIOR = LR(LEAD, ("00", "", 0.0), ("00", "Y", 0.0), ("00", "", 0.0))
    chk("    a candidate with no delinquency before t_A reads `never`",
        prior_del_bucket(
            find_loops_rows(NOPRIOR, ("Y", "P"))[0][0]["prior_del_gap"]),
        "never")

    #: One that SURVIVES and has a prior delinquency, for the background table.
    KEPT = [(200001, "01", "", 20, 100_000.0, 6.0, 300, 0.0),
            (200002, "00", "", 21, 99_900.0, 6.0, 299, 0.0),
            (200003, "01", "", 22, 99_800.0, 6.0, 298, 0.0),
            (200004, "02", "Y", 23, 99_700.0, 6.0, 297, 0.0),
            (200005, "00", "", 24, 99_600.0, 6.0, 296, 0.0)]
    lk = find_loops_rows(KEPT, ("Y", "P"))[0][0]
    chk("    a surviving loop also carries its prior-delinquency gap",
        (all(lk["ok"].values()), lk["t_A"], lk["prior_del_gap"]), (True, 1, 1))

    accp = loops_new_acc()
    for LA in (PRIOR, NOPRIOR, NOPRIOR, KEPT):
        loops_absorb(accp, LA, 2001)
    mp = loops_payload(accp)["cuts"]["YP"]
    chk("    the refused set's buckets are split by arm and counted",
        (mp["no_delinq_census"]["prior_del"]["mod"]["never"],
         mp["no_delinq_census"]["prior_del"]["mod"]["1"],
         mp["no_delinq_census"]["prior_del_mode"]["mod"]), (2, 1, "never"))
    chk("    and the kept loops get their own background table",
        mp["kept_prior_del"]["mod"]["1"], 1)
    chk("    §8·22·9's census does not move a single gate",
        (mp["loops"], mp["marginal"]["no_delinquency"]), (1, 3))

    for tag, mode, want in (("first", "1", "FIRST"),
                            ("first at 3", "3", "FIRST"),
                            ("second", "never", "SECOND"),
                            ("third", "7-12", "THIRD"),
                            ("third on unreadable", "unreadable", "THIRD"),
                            ("third on out-of-order", "<=0", "THIRD")):
        pr = dict(pl_l)
        pr["cuts"] = dict(pl_l["cuts"])
        pr["cuts"]["YP"] = {
            **m, "no_delinq_census": {
                **m["no_delinq_census"],
                "prior_del": {"mod": {b: (99 if b == mode else 1)
                                      for b in PRIOR_DEL_BUCKETS},
                              "defer": {b: 0 for b in PRIOR_DEL_BUCKETS}},
                "prior_del_mode": {"mod": mode, "defer": None}}}
        buf, keep = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            print_loops(pr)
        finally:
            sys.stdout = keep
        tr = buf.getvalue()
        others = {"FIRST", "SECOND", "THIRD"} - {want}
        chk(f"    print_loops reads the {tag} branch for §8·22·9",
            (f"§8·22·9 -> {want} BRANCH" in tr)
            and not any(f"§8·22·9 -> {o} BRANCH" in tr for o in others), True)

    print_loops(pl_l)
    blob_l = json.dumps({"stage": "B10", "step": "loops", **pl_l},
                        indent=2, sort_keys=True)
    print(f"\n     printer and json.dumps both exercised, {len(blob_l):,} bytes")

    for tag, xs2, ys2, want in (
            ("first", [1, 2, 3, 4, 5, 6], [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
             "FIRST"),
            ("third", [1, 2, 3, 4, 5, 6], [0.6, 0.5, 0.4, 0.3, 0.2, 0.1],
             "THIRD"),
            ("second", [1, 2, 3, 4, 5, 6], [0.3, 0.1, 0.5, 0.2, 0.6, 0.4],
             "SECOND")):
        pm = dict(pl_l)
        pm["cuts"] = dict(pl_l["cuts"])
        pm["cuts"]["YP"] = {**m,
                            "rho_vintage_defer_share": rank_corr(xs2, ys2,
                                                                 n_perm=199)}
        buf, keep = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            print_loops(pm)
        finally:
            sys.stdout = keep
        tl = buf.getvalue()
        others = {"FIRST", "SECOND", "THIRD"} - {want}
        chk(f"    print_loops reads the {tag} branch",
            (f"§8·22·6 -> {want} BRANCH" in tl)
            and not any(f"§8·22·6 -> {o} BRANCH" in tl for o in others), True)
    pm = dict(pl_l)
    pm["cuts"] = dict(pl_l["cuts"])
    pm["cuts"]["YP"] = {**m, "rho_vintage_defer_share": None}
    buf, keep = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        print_loops(pm)
    finally:
        sys.stdout = keep
    chk("    and with no referent it says so instead of reading a branch",
        ("NO REFERENT" in buf.getvalue())
        and ("§8·22·6 ->" not in buf.getvalue()), True)

    # --legs, §8·23. Registered before the code.
    print("\n  --legs, §8·23's three legs:")

    #: A curve wide enough that `curve_cell` never refuses, so the leg
    #: arithmetic is what is under test and not the lookup.
    lpos = {month_index_of(200001 + j): j for j in range(10)}
    ltab = [[1.0 + 0.0001 * h for h in range(401)] for _ in range(10)]

    def POW2():
        """A stub residual returning 1, 2, 4, 8 ... so any subset sum names
        its members uniquely. A stub that returns a constant cannot tell leg 1
        from leg 3."""
        st = {"k": 0}

        def f(*a, **kw):
            st["k"] += 1
            return float(2 ** (st["k"] - 1))
        return f

    #: **Six rows, so leg 3 spans two months.** A five-row fixture gives
    #: `t_B = t_M + 1`, which leaves no row strictly inside leg 3, and then a
    #: gate placed "after t_M" can only land on a vertex — where §8·22's own
    #: conditions catch it first and this section never sees it. That is how
    #: the first version of this block was written.
    THREE = [(200001, "01", "", 20, 100_000.0, 6.0, 300, 0.0),
             (200002, "00", "", 21, 99_900.0, 6.0, 299, 0.0),
             (200003, "01", "", 22, 99_800.0, 6.0, 298, 0.0),
             (200004, "02", "Y", 23, 99_700.0, 6.0, 297, 0.0),
             (200005, "03", "", 24, 99_600.0, 6.0, 296, 0.0),
             (200006, "00", "", 25, 99_500.0, 6.0, 295, 0.0)]
    r3 = find_loops_rows(THREE, ("Y", "P"))[0][0]
    chk("    the three-leg fixture is a real loop at the right rows",
        (all(r3["ok"].values()), r3["t_A"], r3["t_M"], r3["t_B"]),
        (True, 1, 3, 5))
    st3, m3 = loop_omega(THREE, r3, (500.0, 500.0), lpos, ltab, 400, POW2())
    chk("    each leg picks up exactly its own months",
        (st3, m3["leg1"], m3["leg2"], m3["leg3"], m3["omega"]),
        ("ok", 1.0, 2.0, 12.0, 15.0))
    chk("    and the month counts partition the window",
        (m3["n1"], m3["n2"], m3["n3"], m3["n_win"]), (1, 1, 2, 4))

    #: §8·23·1 item 2, the check that is **not** vacuous.
    E3 = [(200001, "01", "", 20, 100_000.0, 6.0, 300, 0.0),
          (200002, "00", "", 21, 99_900.0, 6.0, 299, 0.0),
          (200003, "01", "", 22, 99_800.0, 6.0, 298, 0.0),
          (200004, "00", "Y", 23, 99_700.0, 6.0, 297, 0.0)]
    re3 = find_loops_rows(E3, ("Y", "P"))[0][0]
    chk("    an empty-leg-3 loop is a loop, with t_M == t_B",
        (all(re3["ok"].values()), re3["t_M"], re3["t_B"], re3["empty_leg3"]),
        (True, 3, 3, True))
    _st, me3 = loop_omega(E3, re3, (500.0, 500.0), lpos, ltab, 400, POW2())
    chk("    and its leg 3 is EXACTLY zero, not merely small",
        (me3["n3"], me3["leg3"], me3["leg3"] == 0.0), (0, 0.0, True))
    chk("    while legs 1 and 2 still pick up their own months",
        (me3["leg1"], me3["leg2"], me3["omega"]), (1.0, 2.0, 3.0))

    #: A gate before t_M and a gate after it must land on different counters:
    #: §17.10 requires the split because the two arms have different
    #: contract-period structure.
    #: **Inside the window, never on a vertex.** `t_A` and `t_B` are checked
    #: by §8·22's own `vertex_rem_blank`, so a gate placed there is caught one
    #: section earlier and this one never sees the loop at all.
    BEFORE = THREE[:2] + [THREE[2][:6] + (None, 0.0)] + THREE[3:]
    AFTER = THREE[:4] + [THREE[4][:6] + (None, 0.0)] + THREE[5:]
    for tag, rows, want in (("before t_M", BEFORE, True),
                            ("after t_M", AFTER, False)):
        rr = find_loops_rows(rows, ("Y", "P"))[0][0]
        stt, mm = loop_omega(rows, rr, (500.0, 500.0), lpos, ltab, 400,
                             POW2())
        chk(f"    a gate {tag} is counted on its own side",
            (stt != "ok", mm["before"]), (True, want))
    chk("    a window with no payment on one side is named, not zeroed",
        loop_omega(THREE, r3, (None, 500.0), lpos, ltab, 400, POW2())[0],
        "no payment for the window")

    #: §8·23·0: `orig` cannot move at t_M, `sub` can.
    pay = loop_payments(THREE, r3, (100_000.0, 6.0, 360),
                        lambda u, i, n: u / max(n, 1))
    chk("    `orig` gives one value on both sides of t_M, by construction",
        pay["orig"][0] == pay["orig"][1], True)
    chk("    `sub` anchors before at t_A and after at t_B",
        (round(pay["sub"][0], 6), round(pay["sub"][1], 6)),
        (round(99_900.0 / 299, 6), round(99_500.0 / 295, 6)))
    chk("    and both anchors are current rows, which §12.2 requires",
        (THREE[r3["t_A"]][R_DELINQ], THREE[r3["t_B"]][R_DELINQ]),
        ("00", "00"))

    accg = legs_new_acc()
    for LB in (THREE, E3, BEFORE, AFTER):
        legs_absorb(accg, LB, (100_000.0, 6.0, 360), lpos, ltab, 400,
                    POW2(), lambda u, i, n: u / max(n, 1))
    pl_g = legs_payload(accg)
    sg = pl_g["schemes"]["sub"]
    chk("    measurable + dropped = loops, per scheme",
        (sg["ok"] + sg["drop_total"], sg["n"]), (4, 4))
    chk("    and the two drops landed on opposite sides of t_M",
        (sg["miss_before"], sg["miss_after"]), (1, 1))
    chk("    the empty-leg-3 count and the all-three count partition the ok",
        sg["n3_zero"] + sg["all3"], sg["ok"])
    chk("    and no empty leg 3 came back non-zero",
        (sg["empty3_nonzero"], sg["identity_bad"]), (0, 0))

    print_legs(pl_g)
    blob_g = json.dumps({"stage": "B10", "step": "legs", **pl_g},
                        indent=2, sort_keys=True)
    print(f"\n     printer and json.dumps both exercised, {len(blob_g):,} bytes")

    for tag, mut, want in (
            ("first", {"ok": 90, "drop": {"x": 5}}, "FIRST"),
            ("second", {"ok": 5, "drop": {"curve does not reach": 90}},
             "SECOND"),
            ("third", {"ok": 5, "drop": {RESID_DEFECT: 90}}, "THIRD")):
        pg = dict(pl_g)
        pg["schemes"] = dict(pl_g["schemes"])
        pg["schemes"]["sub"] = {**sg, **mut}
        buf, keep = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            print_legs(pg)
        finally:
            sys.stdout = keep
        tg = buf.getvalue()
        others = {"FIRST", "SECOND", "THIRD"} - {want}
        chk(f"    print_legs reads the {tag} branch for §8·23·2",
            (f"§8·23·2 -> {want} BRANCH" in tg)
            and not any(f"§8·23·2 -> {o} BRANCH" in tg for o in others), True)
    for tag, dom, want in (("leg2", "leg2", "FIRST"), ("leg1", "leg1",
                                                       "SECOND"),
                           ("leg3", "leg3", "THIRD")):
        pg = dict(pl_g)
        pg["schemes"] = dict(pl_g["schemes"])
        pg["schemes"]["sub"] = {**sg, "dominant_leg": dom, "all3": 10}
        buf, keep = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            print_legs(pg)
        finally:
            sys.stdout = keep
        tg = buf.getvalue()
        others = {"FIRST", "SECOND", "THIRD"} - {want}
        chk(f"    print_legs reads {tag} dominant for §8·23·3",
            (f"§8·23·3 -> {want} BRANCH" in tg)
            and not any(f"§8·23·3 -> {o} BRANCH" in tg for o in others), True)

    # --signal, §8·24. Registered before the code.
    print("\n  --signal, §8·24's two statistics:")

    chk("    _branch3 maps two booleans onto three branches, exhaustively",
        [_branch3(a2, b2, "F", "S", "T")
         for a2 in (True, False) for b2 in (True, False)],
        ["F", "T", "T", "S"])
    chk("    and an unknown side gives no branch at all, rather than a guess",
        (_branch3(None, True, "F", "S", "T"),
         _branch3(True, None, "F", "S", "T")), (None, None))

    #: **Both floors must be populated or the test tests one of them.** The
    #: omega fixtures above never clear the derived path tolerance, so their
    #: `resolution` floor is empty and `mad` reads None — which is correct
    #: behaviour and a useless fixture. A gate whose tolerance admits
    #: everything fills both.
    class _SGALL(_SG):
        @staticmethod
        def ideal_tol(note, k):
            return 1e9

    oacc_sig = omega_new_acc()
    for L10 in (OCLEAN, DEFER, OTWO):
        omega_absorb(oacc_sig, L10, ORIG, 2001, opos, otab, 5, _SW, _SGALL,
                     PAY)
    chk("    the signal fixture fills BOTH floors, not just one",
        [len(oacc_sig["b8like"][f"gap_{f}"]) > 0 for f in SIGNAL_FLOORS],
        [True, True])

    #: **The scale estimator is passed in, never written here.** A stub that
    #: returns a fixed number proves the payload uses what it is given: if
    #: `mad_scale` were reimplemented inside, this would read the real MAD.
    pl_s = signal_payload(accg, oacc_sig, lambda xs: 2.0 if xs else None)
    chk("    signal_payload uses the estimator it is handed",
        pl_s["schemes"]["sub"]["raw"]["mad"], 2.0)
    chk("    and both floors go through the same one",
        [pl_s["floors"][f]["mad"] for f in SIGNAL_FLOORS], [2.0, 2.0])
    chk("    the operative line is 1 and the inherited 3 is carried beside it",
        (pl_s["readable_line"], pl_s["inherited_line"]), (1.0, 3.0))
    chk("    the l1 tolerance is 2 x the resolution floor, computed not typed",
        pl_s["schemes"]["sub"]["l1"]["tol"], 4.0)

    print_signal(pl_s)
    blob_s = json.dumps({"stage": "B10", "step": "signal", **pl_s},
                        indent=2, sort_keys=True)
    print(f"\n     printer and json.dumps both exercised, {len(blob_s):,} bytes")

    def _sig_mut(amb, res, key):
        q = dict(pl_s)
        q["schemes"] = dict(pl_s["schemes"])
        sc = pl_s["schemes"]["sub"]
        q["schemes"]["sub"] = {
            **sc,
            "ratios": {"ambient": {**sc["ratios"]["ambient"],
                                   f"{key}_above_1": amb, "raw": 9.0,
                                   "net": 9.0, "net_over_raw": 1.0,
                                   "raw_above_3": True, "net_above_3": True},
                       "resolution": {**sc["ratios"]["resolution"],
                                      f"{key}_above_1": res, "raw": 9.0,
                                      "net": 9.0, "net_over_raw": 1.0,
                                      "raw_above_3": True,
                                      "net_above_3": True}}}
        other = "net" if key == "raw" else "raw"
        for f in SIGNAL_FLOORS:
            q["schemes"]["sub"]["ratios"][f][f"{other}_above_1"] = True
        return q

    for sec, key in (("§8·24·4", "raw"), ("§8·24·5", "net")):
        for tag, amb, res, want in (("first", True, True, "FIRST"),
                                    ("second", False, False, "SECOND"),
                                    ("third", True, False, "THIRD")):
            buf, keep = io.StringIO(), sys.stdout
            sys.stdout = buf
            try:
                print_signal(_sig_mut(amb, res, key))
            finally:
                sys.stdout = keep
            ts = buf.getvalue()
            others = {"FIRST", "SECOND", "THIRD"} - {want}
            chk(f"    print_signal reads the {tag} branch for {sec}",
                (f"{sec} -> {want} BRANCH" in ts)
                and not any(f"{sec} -> {o} BRANCH" in ts for o in others),
                True)

    print("\n  partial_name, so a subset run cannot wear the full run's name:")
    _FULL = ["1999", "2000", "2001"]
    chk("    a full run keeps the plain name",
        partial_name("b10_x", _FULL, full=_FULL), "b10_x.json")
    chk("    and so does an empty selection, which means `all`",
        (partial_name("b10_x", None, full=_FULL),
         partial_name("b10_x", [], full=_FULL)),
        ("b10_x.json", "b10_x.json"))
    chk("    a subset run gets its own name, B12's own scheme",
        partial_name("b10_x", ["2000"], full=_FULL), "b10_x.2000.json")
    chk("    and the suffix is order-free, so two spellings are one file",
        partial_name("b10_x", ["2001", "1999"], full=_FULL)
        == partial_name("b10_x", ["1999", "2001"], full=_FULL), True)
    chk("    an int selection and a str selection are the same file",
        partial_name("b10_x", [2000], full=_FULL),
        partial_name("b10_x", ["2000"], full=_FULL))
    chk("    naming a vintage that is not on disk still says it is partial",
        partial_name("b10_x", ["2099"], full=_FULL), "b10_x.2099.json")

    #: **規矩 19 for this change, run rather than asserted.** Fourteen write
    #: sites moved from a literal to a call, and the claim is that a full run
    #: writes exactly where it wrote before. Every basename is checked, so a
    #: typo in any one of them is caught here rather than by an artifact
    #: appearing under a name nobody looks at.
    _BASES = ("b10_resid", "b10_curve", "b10_floor", "b10_omega", "b10_noise",
              "b10_loops", "b10_legs", "b10_signal", "b10_pgrid",
              "b10_gridvar", "b10_cohort_width", "b10_cohort_width_depth",
              "b10_cohort_width_triangles", "b10_window_width")
    chk(f"    all {len(_BASES)} artifacts keep their exact name on a full run",
        [partial_name(b, None, full=_FULL) for b in _BASES],
        [f"{b}.json" for b in _BASES])
    _src = Path(__file__).read_text(encoding="utf-8")
    chk("    and no write site is still holding a literal name",
        [b for b in _BASES if f'RESULTS / "{b}.json"' in _src], [])
    print("     (the two triangle caches keep their literal names on purpose:")
    print("      both already guard their WRITE with `if not only`, which the")
    print("      fourteen artifacts did not. That asymmetry is what this is.)")

    #: §8·19·3's 甲2, called **unconditionally**, because it can be.
    #:
    #: The whole of §8·19·3 lives in `resid_crosscheck`, which takes `b8_omega`
    #: and `b8_0a_gate`; where those do not import, the selftest prints a skip
    #: and the gate is invisible. **But 甲2 depends on nothing except this
    #: file** — it counts the logarithms called here, and refuses the run if
    #: any is not the single `log10`, because writing a residual formula in
    #: this file is the one thing it must never do.
    #:
    #: §8·26 tripped it with four `math.log` calls used to compare a lift
    #: against two anchors, and the trip happened at the pre-flight of a
    #: 27-archive run rather than in the selftest. **A gate that only runs when
    #: an optional import succeeds is a gate that some environments cannot
    #: see.** So the part of it that can always run, now always runs. This is
    #: a second **call**, not a second copy: `_logs_in_this_file` has one body.
    chk("    §8·19·3 甲2 without b8: the only logarithm here is log10, once",
        _logs_in_this_file(), {"log10": 1})
    print("    (the lift comparison §8·26 wanted logs for is written as")
    print("     `lift * lift > lift_same`, which is the same geometric-mean")
    print("     boundary with one multiplication and no transcendental.)")

    #: §8·19·3, run here when B8's modules are importable and **printed as a
    #: skip when they are not**. `cmd_resid` runs the same call as a hard
    #: pre-flight, so no archive is ever read without it.
    sys.path.insert(0, str(ROOT / "experiments"))
    try:
        import b8_omega as _W                        # noqa: E402
        import b8_0a_gate as _G                      # noqa: E402
        _why = None
    except Exception as _e:                          # pragma: no cover
        _W = _G = None
        _why = f"{type(_e).__name__}: {_e}"
    print()
    if _W is None:
        print(f"    §8·19·3 SKIPPED here: b8_omega would not import ({_why}).")
        print("    cmd_resid runs it as a hard pre-flight and refuses to read")
        print("    an archive without it. A skip is printed, never silent.")
    else:
        _xc = resid_crosscheck(_W, _G)
        print_crosscheck(_xc)
        chk("    §8·19·3's eight lines all pass",
            all(g for _n, g, _d in _xc), True)

        #: §8·20 end to end, on B8's real functions rather than the stubs
        #: above: one exact clean cure through `omega_absorb`, and the ratio it
        #: produces must sit well inside the bound. **The stubs test the
        #: bookkeeping; this tests that the bookkeeping is wrapped around real
        #: arithmetic.**
        _B0, _NOTE, _TERM = 180_000.00, 6.5, 360
        _P = float(_W.level_payment(_B0, _NOTE, _TERM))
        _b = _B0
        for _ in range(2):                       # k = 1, so k + 1 = 2 steps
            _b = float(_W.carry_forward(_b, _NOTE, _P))
        _rows = [(200002, "00", "", 20, round(_B0, 2), _NOTE, 3, 0.0),
                 (200003, "01", "", 21, round(_B0, 2), _NOTE, 2, 0.0),
                 (200004, "00", "", 22, round(_b, 2), _NOTE, 1, 0.0)]
        _acc = omega_new_acc()
        omega_absorb(_acc, _rows, (_B0, _NOTE, _TERM), 2001, opos, otab, 5,
                     _W, _G,
                     lambda u, i, n: float(_W.level_payment(u, i * 1200.0, n)))
        _pl = omega_payload(_acc)
        print(f"    §8·20 end to end: k {list(_acc['as16']['k'])}"
              f"   omega {_acc['as16']['stream'][0]:+.6e}"
              f"   closed {_acc['as16']['closed'][0]:+.6e}"
              f"   ratio {_acc['as16']['ratio'][0]:.4f}"
              f"   path dev {_acc['as16']['pathdev'][0]:.4f}")
        chk("    one exact clean cure is measured, k is B8's",
            (_acc["as16"]["n"], list(_acc["as16"]["k"])), (1, [1]))
        chk("    its path is ideal under BOTH tolerances",
            (_acc["as16"]["ideal_loose"], _acc["as16"]["ideal_derived"]),
            (1, 1))
        chk("    and the streamed sum sits inside the bound",
            _acc["as16"]["ratio"][0] < 1.0, True)
        chk("    the loop sum is the closed form to the bound, not to zero",
            abs(_acc["as16"]["closed"][0]) > 1e-6, True)
        #: A payment one per cent wrong must move the endpoint off the ideal
        #: path. B8-0a's own selftest reads that as $30.55; the number here is
        #: this fixture's, and what matters is that the path test **fires**.
        _acc2 = omega_new_acc()
        omega_absorb(_acc2, _rows, (_B0, _NOTE, _TERM), 2001, opos, otab, 5,
                     _W, _G,
                     lambda u, i, n: 1.01 * float(
                         _W.level_payment(u, i * 1200.0, n)))
        chk("    a payment one per cent wrong fails the derived path test",
            (_acc2["as16"]["n"], _acc2["as16"]["ideal_derived"]), (1, 0))
        print(f"    a one per cent payment error moves the endpoint by "
              f"${_acc2['as16']['pathdev'][0]:,.2f}")

        #: §8·21·8. **The cancellation is proved, not asserted in a comment.**
        #: With `zib = 0`, `note_prev = note` and `n_prev = n_now`, `V`'s
        #: factor is the same on both sides, so `r_month` returns
        #: `log bal - log b_hat` and the answer cannot depend on the discount
        #: rate or on the horizon. If it did, this file would be writing a
        #: residual formula through the back door.
        _vals = []
        for _d in (0.01, 1.0, 4.0, 9.75):
            for _n in (12.0, 240.0, 599.0):
                _vals.append(float(_W.r_month(
                    99_000.00, 100_000.00, 6.0, 500.0, _n, _d,
                    zib_now=0.0, zib_prev=0.0, balloon_n=_n,
                    note_prev=6.0, n_prev=_n, balloon_n_prev=_n)))
        chk(f"    r_month is invariant to disc and n once V cancels "
            f"({len(_vals)} pairs)",
            max(_vals) - min(_vals) < 1e-12, True)
        chk("    and the value is not zero, so the test is not vacuous",
            abs(_vals[0]) > 1e-3, True)
        print(f"    §8·21·8: r_month over 4 discount rates x 3 horizons ->"
              f" {_vals[0]:+.12f}, spread {max(_vals) - min(_vals):.3e}")

        #: A never-delinquent loan on the exact contract path is what the
        #: floor is drawn from. Its sum must be at rounding, not at signal.
        _P2 = float(_W.level_payment(240_000.00, 5.75, 360))
        _path, _bb = [240_000.00], 240_000.00
        for _ in range(8):
            _bb = float(_W.carry_forward(_bb, 5.75, _P2))
            _path.append(_bb)
        _exact = [(200001 + jj, "00", "", 8 + jj, _path[jj], 5.75,
                   360 - jj, 0.0) for jj in range(9)]
        _cents = [t[:4] + (round(t[4], 2),) + t[5:] for t in _exact]
        for _tag, _rows, _lim in (("exact", _exact, 1e-13),
                                  ("cent-rounded", _cents, 1e-6)):
            _sk, _val = noise_window(_rows, 0, 7, _P2, _W)
            print(f"    §8·21 floor fixture, {_tag}: sum {_val:+.4e}")
            chk(f"    a never-delinquent {_tag} path sums under {_lim:.0e}",
                (_sk, abs(_val) < _lim), (None, True))

        #: §8·20·8's whole claim, as a decisive fixture. The loan's **true**
        #: original balance is $200,437.19; the file reports it rounded to the
        #: $1,000 grid as $200,000, which is what every Freddie archive
        #: checked does on every row. The perf balances are the true
        #: amortisation, to the cent, at age 100.
        _U_TRUE, _U_GRID = 200_437.19, 200_000.00
        _PT = float(_W.level_payment(_U_TRUE, _NOTE, _TERM))
        _bal = _U_TRUE
        for _ in range(100):
            _bal = float(_W.carry_forward(_bal, _NOTE, _PT))
        _b2 = _bal
        for _ in range(2):
            _b2 = float(_W.carry_forward(_b2, _NOTE, _PT))
        _grows = [(200002, "00", "", 100, round(_bal, 2), _NOTE, 260, 0.0),
                  (200003, "01", "", 101, round(_bal, 2), _NOTE, 259, 0.0),
                  (200004, "00", "", 102, round(_b2, 2), _NOTE, 258, 0.0)]
        _bpos = {month_index_of(m): jj for jj, m in
                 enumerate((200002, 200003, 200004))}
        _btab = [[1.0 + 0.0001 * h for h in range(300)] for _ in range(3)]
        _acc3 = omega_new_acc()
        omega_absorb(_acc3, _grows, (_U_GRID, _NOTE, _TERM), 2001, _bpos,
                     _btab, 299, _W, _G,
                     lambda u, i, n: float(_W.level_payment(u, i * 1200.0, n)))
        print(f"    §8·20·8 fixture: true u0 ${_U_TRUE:,.2f} reported as "
              f"${_U_GRID:,.2f} on the $1,000 grid")
        print(f"      |P_sub - P_orig| / P_orig  "
              f"{_acc3['p_reldiff'][0]:.4e}"
              f"   (u0's own relative error "
              f"{abs(_U_TRUE - _U_GRID) / _U_GRID:.4e})")
        print(f"      path dev under P_orig ${_acc3['as16']['pathdev'][0]:,.2f}"
              f"   under P_sub "
              f"${_acc3['p_sub']['as16']['pathdev'][0]:,.2f}")
        chk("    a gridded u0 fails the derived path test under P_orig",
            (_acc3["as16"]["n"], _acc3["as16"]["ideal_derived"]), (1, 0))
        chk("    and passes it under §12.2's substitution",
            (_acc3["p_sub"]["as16"]["n"],
             _acc3["p_sub"]["as16"]["ideal_derived"]), (1, 1))
        chk("    the payment error tracks u0's own, as ΔP/P = Δu0/u0",
            abs(_acc3["p_reldiff"][0]
                - abs(_U_TRUE - _U_GRID) / _U_GRID) < 1e-5, True)
        chk("    and P_sub's loop still sits inside the bound",
            _acc3["p_sub"]["as16"]["ratio"][0] < 1.0, True)

        #: §8·23·1 item 3, **the check that is not vacuous**. A triangle whose
        #: "modification" changes nothing — the flag is set and the rate, the
        #: term and the balance path all carry on unchanged — must give back
        #: exactly the clean-cure closed form. A wrong `_prev` wiring or a
        #: mis-anchored payment fails it, and §8·19·3 丙 already measured that
        #: the `_prev` arguments are worth 0.2496 at a real modification.
        #: **The rems must sit on one schedule with the balances**, or the
        #: two anchors disagree before any modification does — which is
        #: exactly what §8·23·0·1 is about. `t_A` carries `f(B0)` at 249
        #: months, the delinquent month freezes that balance while `rem`
        #: falls, and the cure lands on `f^3(B0)` at 247. Both anchors are
        #: then on the same level payment.
        _B3, _N3, _R3 = 240_000.00, 5.75, 250
        _P3 = float(_W.level_payment(_B3, _N3, _R3))
        _s1 = float(_W.carry_forward(_B3, _N3, _P3))
        _s3 = _s1
        for _ in range(2):
            _s3 = float(_W.carry_forward(_s3, _N3, _P3))
        _null = [(200001, "00", "", 30, round(_B3, 2), _N3, 250, 0.0),
                 (200002, "00", "", 31, round(_s1, 2), _N3, 249, 0.0),
                 (200003, "01", "Y", 32, round(_s1, 2), _N3, 248, 0.0),
                 (200004, "00", "", 33, round(_s3, 2), _N3, 247, 0.0)]
        _r3 = find_loops_rows(_null, ("Y", "P"))[0][0]
        _pay = loop_payments(_null, _r3, (_B3, _N3, 360),
                             lambda u, i, n: float(
                                 _W.level_payment(u, i * 1200.0, n)))
        _st, _m = loop_omega(_null, _r3, _pay["sub"], _bpos, _btab, 299,
                             _W.r_month)
        _closed = float(_W.loop_residual_ideal(round(_s1, 2), _N3,
                                               _pay["sub"][0], 1))
        _bnd = floor_bound(1, _N3, min(round(_s1, 2), round(_s3, 2)))
        print(f"    §8·23·1 item 3: null modification, omega "
              f"{_m['omega'] if _st == 'ok' else _st}"
              f"   closed {_closed:+.6e}"
              + (f"   gap {abs(_m['omega'] - _closed):.3e} against bound "
                 f"{_bnd:.3e}" if _st == "ok" else ""))
        chk("    a null-modification triangle is measurable at all",
            (_st, _r3["t_A"], _r3["t_M"], _r3["t_B"]), ("ok", 1, 2, 3))
        #: **The tolerance is derived, not typed.** The two anchors read
        #: balances rounded to the cent, and a half-cent error in a balance
        #: moves the level payment by the same relative amount, so the two
        #: payments cannot agree to floating point even with no
        #: re-contracting. `2h / balance` is that bound; writing `1e-9` here
        #: instead failed a correct fixture, which is B8-0a's own first-run
        #: shape (a tolerance reasoned from the wrong quantity).
        _ptol = 2.0 * FLOOR_HALF_CENT / min(round(_s1, 2), round(_s3, 2))
        _pgap = abs(_pay["sub"][1] - _pay["sub"][0]) / _pay["sub"][0]
        print(f"    the two payments differ by {_pgap:.3e}, cent-rounding "
              f"alone allows {_ptol:.3e}")
        chk("    its two payments agree to cent-rounding, nothing re-contracted",
            _pgap <= _ptol, True)
        chk("    and its omega is the clean-cure closed form, inside the bound",
            abs(_m["omega"] - _closed) <= _bnd, True)
        chk("    leg 2 is the modification month and it is not zero here",
            abs(_m["leg2"]) > 0.0, True)

        #: §8·24·5's object. On a **flat** delinquent run leg 1 is exactly
        #: `n1` copies of one month, which is what `l1_closed` computes, so
        #: the two must agree to floating point. If they do not, the closed
        #: form is not the same object as the leg and removing it would be
        #: subtracting something else.
        _wpos = {month_index_of(200001 + j): j for j in range(8)}
        _wtab = [[1.0 + 0.0001 * h for h in range(300)] for _ in range(8)]
        _flat = [(200001, "00", "", 30, round(_B3, 2), _N3, 250, 0.0),
                 (200002, "00", "", 31, round(_s1, 2), _N3, 249, 0.0),
                 (200003, "01", "", 32, round(_s1, 2), _N3, 248, 0.0),
                 (200004, "01", "", 33, round(_s1, 2), _N3, 247, 0.0),
                 (200005, "02", "Y", 34, round(_s1, 2), _N3, 246, 0.0),
                 (200006, "00", "", 35, round(_s3, 2), _N3, 245, 0.0)]
        _rf = find_loops_rows(_flat, ("Y", "P"))[0][0]
        _pf = loop_payments(_flat, _rf, (_B3, _N3, 360),
                            lambda u, i, n: float(
                                _W.level_payment(u, i * 1200.0, n)))
        _sf, _mf = loop_omega(_flat, _rf, _pf["sub"], _wpos, _wtab, 299,
                              _W.r_month)
        print(f"    §8·24·5 fixture: n1 {_mf['n1']}   leg1 {_mf['leg1']:+.8e}"
              f"   l1_closed {_mf['l1_closed']:+.8e}"
              f"   eff {_mf['eff']:.6f}")
        chk("    the flat-run fixture has a leg 1 with months in it",
            (_sf, _rf["t_A"], _rf["t_M"], _rf["t_B"], _mf["n1"]),
            ("ok", 1, 4, 5, 2))
        chk("    leg 1 on a flat run IS n1 copies of the closed form",
            abs(_mf["leg1"] - _mf["l1_closed"]) < 1e-12, True)
        chk("    so eff reads n1 exactly, meaning every month was flat",
            abs(_mf["eff"] - _mf["n1"]) < 1e-9, True)
        chk("    and omega_net is omega with that construction removed",
            abs(_mf["omega_net"] - (_mf["omega"] - _mf["l1_closed"])) < 1e-15,
            True)
        #: A run that is **not** flat must move `eff` off `n1`, or the
        #: diagnostic says nothing.
        _bumpy = _flat[:3] + [(_flat[3][:4] + (round(_s1 - 500.0, 2),)
                               + _flat[3][5:])] + _flat[4:]
        _sb, _mb = loop_omega(_bumpy, find_loops_rows(_bumpy, ("Y", "P"))[0][0],
                              _pf["sub"], _wpos, _wtab, 299, _W.r_month)
        print(f"    a balance that moves mid-delinquency: eff {_mb['eff']:.6f}"
              f" against n1 {_mb['n1']}")
        chk("    a balance that moves during the delinquency moves eff off n1",
            abs(_mb["eff"] - _mb["n1"]) > 0.01, True)

    c = classify_loan(L(("00", ""), ("01", ""), ("02", "P"), ("00", "")))
    chk("    a `P`-only loan has no first_Y", c["digits"]["first_Y"], None)
    chk("    but it has a first_any", c["digits"]["first_any"], 200003)
    # §29.3 layer two: the triangle's modification, not the loan's first
    c = classify_loan(L(("00", ""), ("00", "Y"), ("01", ""), ("02", "Y"),
                        ("00", "")))
    chk("    a pre-delinquency modification does not date the triangle",
        c["digits"]["first_Y"], 200004)
    c = classify_loan(L(("00", ""), ("01", "Y"), ("00", "")))
    chk("    a modification on the first delinquent row still dates it",
        c["digits"]["first_Y"], 200002)
    chk("    and that loan is a triangle", c["digits"]["triangle"], True)
    c = classify_loan(L(("01", ""), ("02", ""), ("00", "Y")))
    chk("    a loan that opens delinquent closes no triangle",
        c["digits"]["triangle"], False)
    chk("    and is counted, so the fourth ambiguity is measurable",
        c["digits"]["no_leading_current"], True)
    chk("    §27.3's reading counts it", c["digits"]["triangle_nolead"], True)
    c = classify_loan(L(("00", ""), ("01", ""), ("02", "Y"), ("00", "")))
    chk("    the two readings agree on an ordinary triangle",
        (c["digits"]["triangle"], c["digits"]["triangle_nolead"]), (True, True))
    c = classify_loan(L(("01", ""), ("02", ""), ("03", "")))
    chk("    neither reading fires without a modification",
        (c["digits"]["triangle"], c["digits"]["triangle_nolead"]),
        (False, False))
    c = classify_loan(L(("00", ""), ("00", "Y"), ("01", ""), ("00", "")))
    chk("    a modification BEFORE the delinquency is not the chain",
        c["digits"]["triangle"], False)

    print("\n  the two FICO implementations induce the same partition:")
    same = all((fico_band(a) == fico_band(b))
               == (c9_band(a, C9_FICO_LLPA9) == c9_band(b, C9_FICO_LLPA9))
               for a in range(300, 851, 7) for b in range(300, 851, 13))
    chk("    same cut, opposite labels", same, True)
    chk("    C9's own fixture reproduces",
        [c9_band(x, C9_FICO_LLPA9) for x in
         (600, 639, 640, 659, 660, 700, 759, 760, 779, 780, 850)],
        [0, 0, 1, 1, 2, 4, 6, 7, 7, 8, 8])
    chk("    and the coarse five",
        [c9_band(x, C9_FICO_COARSE5) for x in (600, 640, 680, 720, 760)],
        [0, 1, 2, 3, 4])
    chk("    C9's dti_complement15 fixture",
        [dti_complement15(x) for x in (19, 20, 29, 30, 35, 36, 37, 49, 50, 60,
                                       61)],
        [14, 14, 14, 14, 14, 0, 1, 13, 14, 14, 14])
    print("    (all four are `b8_c9_cells.py`'s own selftest vectors, run\n"
          "     against this file's transcription of the same boundaries)")

    print("\n  width_curve, on a constructed cohort axis:")
    it = [(y, lev) for y in range(2000, 2008) for lev in range(3)
          for _ in range(4)]
    rows = {r["w"]: r for r in width_curve(it, "x", (1, 2, 4, 8))}
    chk("    w=1 gives one bin per year", rows[1]["bins"], 8)
    chk("    and a min cell of 4", rows[1]["min_cell"], 4)
    chk("    w=2 halves the bins", rows[2]["bins"], 4)
    chk("    and doubles the min cell", rows[2]["min_cell"], 8)
    chk("    w=8 collapses to one bin", rows[8]["bins"], 1)
    mono = all(rows[b]["min_cell"] >= rows[a]["min_cell"]
               for a, b in ((1, 2), (2, 4), (4, 8)))
    chk("    monotone along the dyadic chain", mono, True)

    print("\n  branch_of, §24.5's partition:")
    for m, w in ((0, "dead"), (1, "dead"), (2, "thin"), (19, "thin"),
                 (20, "clears_c9_floor"), (100, "clears_c9_floor")):
        chk(f"    M = {m}", branch_of(m), w)
    chk("    and §30.4·3 bites where it should: 22 -> 17 crosses",
        branch_of(22) == branch_of(22 - RESIDUAL), False)
    chk("    while 30 -> 25 does not", branch_of(30) == branch_of(30 - RESIDUAL),
        True)


    # §8·29, folded into --noise. Registered before the code before this.
    print("\n  §8·29's three factors, on constructed residual streams:")

    def _coh(streams, ders=None, obs=None):
        """streams: list of per-loop `rs`. **Calls `coh_file`, does not copy it.**

        The first version of this helper reimplemented the accumulation so it
        could build fixtures, which is a fixture testing its own copy of the
        code. `coh_file` was extracted for exactly this line.
        """
        acc = {}
        for i2, rs in enumerate(streams):
            coh_file(acc, len(rs) - 1, rs, sum(rs),
                     True if ders is None else ders[i2],
                     None if obs is None else obs[i2])
        return acc

    _sizes = {str(L): {"floor_absmed": 1.0} for L in NOISE_LENS}
    #: All residuals the same sign: C is exactly 1 whatever the window.
    _aligned = {L: [[1.0] * L] * 5 for L in NOISE_LENS}
    _pl_a = coh_payload(_coh([rs for L in NOISE_LENS for rs in _aligned[L]]),
                        _sizes)
    chk("    residuals that all share a sign read C = 1 at every window",
        [_pl_a["rows"][str(L)]["C_p50"] for L in NOISE_LENS],
        [1.0] * len(NOISE_LENS))
    chk("    and every window then reads `aligned` against its own anchors",
        [_pl_a["rows"][str(L)]["C_nearer"] for L in NOISE_LENS],
        ["aligned"] * len(NOISE_LENS))
    chk("    the independence anchor is L**-0.5, computed not typed",
        [round(_pl_a["rows"][str(L)]["C_if_independent"], 10)
         for L in NOISE_LENS],
        [round(float(L) ** -0.5, 10) for L in NOISE_LENS])
    chk("    and the boundary is their geometric mean, L**-0.25",
        [round(_pl_a["rows"][str(L)]["C_boundary"], 10) for L in NOISE_LENS],
        [round(float(L) ** -0.25, 10) for L in NOISE_LENS])

    #: A perfectly cancelling stream: C = 0, and it must not read `aligned`.
    _alt = {L: [[1.0 if i % 2 == 0 else -1.0 for i in range(L)]] * 5
            for L in NOISE_LENS}
    _pl_x = coh_payload(_coh([rs for L in NOISE_LENS for rs in _alt[L]]),
                        _sizes)
    chk("    alternating signs read low C and `independent`",
        [_pl_x["rows"][str(L)]["C_nearer"] for L in NOISE_LENS],
        ["independent"] * len(NOISE_LENS))
    chk("    an even window cancels exactly and an odd one leaves 1/L",
        [round(_pl_x["rows"][str(L)]["C_p50"], 10) for L in (2, 4)],
        [0.0, 0.0])

    #: §8·29·3's three branches. `L*mean|r|` rises by construction whenever
    #: `mean|r|` is flat, since L is the window; so the first branch needs C
    #: flat and the second needs C climbing.
    chk("    C flat with L*mean|r| rising reads FIRST BRANCH",
        (_pl_a["verdict"], _pl_a["C_rises"], _pl_a["C_constant"],
         _pl_a["L_meanabs_rises"]),
        ("arithmetic_only", False, True, True))
    #: **Constant and non-monotone are two shapes, not one.** The first
    #: version had a single `C_flat` reading `not rises and not falls`, and
    #: the archives handed it 0.3319, 0.3288, 0.2155, 0.3128 — non-monotone —
    #: which it labelled `flat`. §11 item 6.
    _pl_w = coh_payload(_coh(
        [[1.0] * 2] * 5 + [[1.0, -0.9, 1.0]] * 5
        + [[1.0] * 4] * 5 + [[1.0] * 7] * 5), _sizes)
    chk("    a wobbling C is non-monotone, and is NOT called constant",
        (_pl_w["C_constant"], _pl_w["C_non_monotone"], _pl_w["C_rises"]),
        (False, True, False))
    chk("    while a truly constant C is called constant and not wobbling",
        (_pl_a["C_constant"], _pl_a["C_non_monotone"]), (True, False))
    #: §8·29·1's guard. The branch says which factor is monotone; the two
    #: growth numbers say whether that accounts for the size.
    chk("    the factor-median prediction and the observed growth both print",
        (round(_pl_a["growth_predicted_by_factor_medians"], 6),
         round(_pl_a["growth_observed_absomega"], 6)), (3.5, 3.5))
    print("     (on the aligned fixture the two agree exactly, because there")
    print("      C is 1 and mean|r| is 1 on every loop, so the medians DO")
    print("      multiply. On the archives they disagree by eight-fold, which")
    print("      is why the guard exists.)")
    chk("    and flat still reads non-decreasing, which is why it fooled it",
        _pl_a["C_nondecreasing"], True)
    print("     (this is the one that would have shipped a wrong branch:")
    print("      `all(b >= a)` is true of a constant series, so C sitting at")
    print("      exactly 1 read as `coherence rises`. §11 item 4 — a tie does")
    print("      not get put on one side.)")

    _climb = []
    for L in NOISE_LENS:
        n_pos = L if L <= 3 else L
        _climb += [[1.0] * L] * 5 if L > 2 else \
            [[1.0, -0.9]] * 5
    _pl_c = coh_payload(_coh(_climb), _sizes)
    chk("    C climbing from a low first window reads SECOND BRANCH",
        _pl_c["verdict"], "coherence_rises")
    chk("    a single window gives NO READING, not a branch",
        coh_payload(_coh([[1.0, 1.0]]), _sizes)["verdict"], "no_reading")

    _buf, _keep = io.StringIO(), sys.stdout
    sys.stdout = _buf
    try:
        print_coh({"coh": _pl_a})
        print_coh({"coh": _pl_c})
    finally:
        sys.stdout = _keep
    _tc = _buf.getvalue()
    chk("    print_coh reads both branches, each tagged with its section",
        ("§8·29·3 -> FIRST BRANCH" in _tc)
        and ("§8·29·3 -> SECOND BRANCH" in _tc), True)
    chk("    and it never re-judges §8·21",
        "§8·21's readings are not re-judged here" in _tc, True)

    #: 規矩 19 for §8·29: the accumulator grew, and `b10_omega.json` must not.
    _oa29 = omega_new_acc()
    _b429 = json.dumps(omega_payload(_oa29), sort_keys=True)
    _oa29["b8like"]["coh"][1] = {"C": [0.5], "meanabs": [1.0],
                                 "absom": [1.0], "same_sign": [0.5],
                                 "n_months": 2}
    chk("    filling §8·29's subtree leaves omega_payload byte for byte",
        json.dumps(omega_payload(_oa29), sort_keys=True) == _b429, True)

    #: §8·30, registered before the code.
    print("\n  §8·30's shape objects:")

    def _mk(L, n, scale):
        """n loops at window L whose |omega| spreads over a decade."""
        out = []
        for i in range(n):
            m = scale * (1.0 + 9.0 * i / max(1, n - 1))
            out.append([m] + [0.0] * (L - 1))
        return out

    #: A **uniform** shift: every quantile of |omega| grows by the same factor,
    #: because the long window's stream is the short one's times four.
    _uni = coh_payload(_coh(_mk(2, 200, 1.0) + _mk(7, 200, 4.0)), _sizes)
    chk("    a uniform shift reads FIRST BRANCH and is NAMED uniform",
        _uni["shift_verdict"], "uniform_shift")
    #: **A branch defined by two negations must not be named by an
    #: affirmation** (§11 item 14). The first version called every
    #: non-monotone sequence `whole_distribution_shifts`, and the archives
    #: handed it 10.30 / 20.86 / 6.08 / 3.22 — peaked at the median, a 6.49x
    #: spread. Same shape as `C_flat` one station earlier.
    _peak = coh_payload(_coh(
        _mk(2, 200, 1.0)
        + [[1.0 * (1.0 + 9.0 * i / 199) ** 0.5 * (4.0 if 40 < i < 160 else 1.0)]
           + [0.0] * 6 for i in range(200)]), _sizes)
    chk("    a growth factor peaking at an interior quantile is NAMED peaked",
        _peak["shift_verdict"], "peaked_in_the_middle")
    _buf, _keep = io.StringIO(), sys.stdout
    sys.stdout = _buf
    try:
        print_coh_shape(_peak)
    finally:
        sys.stdout = _keep
    _tp30 = _buf.getvalue()
    chk("    peaked still prints the FIRST BRANCH, and says it is not uniform",
        ("§8·30·0 -> FIRST BRANCH" in _tp30)
        and ("PEAKS in the" in _tp30)
        and ("whole" not in _tp30.split("PEAKS")[0].split("FIRST BRANCH")[1]),
        True)
    chk("    and the spread of the growth factors prints beside it",
        "max/min =" in _tp30, True)
    chk("    and its growth factor is the same 4x at every quantile",
        [round(x, 6) for x in _uni["growth_by_quantile"]], [4.0] * 4)
    print("     (this is the case the criteria said must land in the first")
    print("      branch. Four identical ratios are not monotone, and that is")
    print("      the whole reason `no systematic drift` was chosen over a")
    print("      tolerance on `much the same`.)")

    #: A **tail**: the long window multiplies the top of the distribution more
    #: than the bottom, so the growth factor climbs with the quantile.
    _tail = coh_payload(_coh(
        _mk(2, 200, 1.0)
        + [[1.0 * (1.0 + 9.0 * i / 199) ** 2] + [0.0] * 6
           for i in range(200)]), _sizes)
    chk("    a distribution stretched at the top reads SECOND BRANCH",
        _tail["shift_verdict"], "tail_carries_it")
    _bot = coh_payload(_coh(
        [[1.0 * (1.0 + 9.0 * i / 199) ** 2] + [0.0] for i in range(200)]
        + _mk(7, 200, 1.0)), _sizes)
    chk("    and one stretched at the bottom reads THIRD BRANCH",
        _bot["shift_verdict"], "bottom_carries_it")

    #: §8·30·1 item 3: a COUNT under the anchor, not a median compared to it.
    _half = [[1.0, 1.0]] * 100 + [[1.0, -0.99]] * 100
    _pl_h = coh_payload(_coh(_half), _sizes)
    _r2 = _pl_h["rows"]["2"]
    chk("    C under the anchor is counted loop by loop",
        (_r2["C_below_independent"], _r2["n"]), (100, 200))
    chk("    and the count is against L**-0.5, computed not typed",
        round(_r2["C_below_independent_share"], 6), 0.5)
    print("     (§8·29·2 read every window's MEDIAN C under the anchor. A")
    print("      median under a line and most loops under it are two claims,")
    print("      and this one is the second.)")

    chk("    the quantile ranks print, so a thin window says how thin",
        (_r2["p90_rank"], _r2["p99_rank"]), (179, 197))
    #: **The tie problem, in the binning.** C here is exactly two values, so
    #: both tertile cuts land on real data and `<=` on each side sends the TOP
    #: mode into the middle bin, leaving the top bin empty. The first version
    #: of this check expected `[100, 0, 100]` and was simply wrong about the
    #: code — but the code is right and the ORDINAL is what lies, so the bin's
    #: range prints and the label was dropped.
    chk("    a two-valued C fills bins 0 and 1 and leaves bin 2 empty",
        ([b["n"] for b in _r2["joint"]], len(_r2["joint"])),
        ([100, 100, 0], 3))
    chk("    and each bin carries its own C range, so no label can lie",
        [(round(b["C_lo"], 4), round(b["C_hi"], 4))
         for b in _r2["joint"] if b["n"]],
        [(0.005, 0.005), (1.0, 1.0)])
    print("     (the empty bin is printed as empty rather than dropped, and")
    print("      the middle bin holding the TOP mode is why the low/mid/high")
    print("      label came out and the range went in.)")

    for _tag, _pl, _want in (("first", _uni, "FIRST"),
                             ("second", _tail, "SECOND"),
                             ("third", _bot, "THIRD")):
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_coh_shape(_pl)
        finally:
            sys.stdout = _keep
        _ts = _buf.getvalue()
        _o = {"FIRST", "SECOND", "THIRD"} - {_want}
        chk(f"    print_coh_shape reads the {_tag} branch for §8·30·0",
            (f"§8·30·0 -> {_want} BRANCH" in _ts)
            and not any(f"§8·30·0 -> {o} BRANCH" in _ts for o in _o), True)
    _buf, _keep = io.StringIO(), sys.stdout
    sys.stdout = _buf
    try:
        print_coh_shape(_uni)
    finally:
        sys.stdout = _keep
    chk("    and the first branch carries §8·30·3 item 3's refusal with it",
        "the same picture" in _buf.getvalue(), True)

    #: §8·31, registered before the code.
    print("\n  §8·31's sign alphabet and its 2x2:")

    def _cohd(rows):
        """rows: (rs, derived) or (rs, derived, over_bound).

        **Calls `coh_file`.** The first version copied the accumulation out of
        `omega_file` so it could build fixtures, and then §8·32 had to add a
        field in two places. One body now.
        """
        acc = {}
        for r in rows:
            rs, der = r[0], r[1]
            ob = r[2] if len(r) > 2 else None
            coh_file(acc, len(rs) - 1, rs, sum(rs), der, ob)
        return acc

    _rows31 = ([([1.0, 1.0], True)] * 10 + [([-1.0, -2.0], True)] * 5
               + [([1.0, -1.0], False)] * 20 + [([2.0, -1.0], False)] * 5)
    _pl31 = coh_payload(_cohd(_rows31), _sizes)["rows"]["2"]
    chk("    all four sign patterns are enumerated, none summarised away",
        sorted(_pl31["sign_patterns"]), ["++", "+-", "--"])
    chk("    and their counts partition the window",
        sum(v["n"] for v in _pl31["sign_patterns"].values()),
        _pl31["sign_n"])
    chk("    same-sign counts both all-positive and all-negative",
        (_pl31["n_same_sign"], _pl31["same_sign_share"]), (15, 0.375))
    chk("    C is exactly 1 on the same-sign loops and exactly 0 on |a|==|b|",
        (_pl31["C_exact_values"].get("1"),
         _pl31["C_exact_values"].get("0"),
         _pl31["C_exact_values"].get("mid")), (15, 20, 5))
    print("     (§8·31·3 item 2: on two months C's alphabet is small enough")
    print("      to count, so `exactly 1` is a structural fact and not a")
    print("      quantile artefact.)")

    _o31 = _pl31["sign_overlap"]
    #: Both margins are 15 here, so this is the **identical** case, not a
    #: one-way containment. The first draft asserted the directional string
    #: and the fixture could not produce it — the directional case needs the
    #: two margins to differ, which is what `_rows31d` below is for.
    chk("    the 2x2 is read by overlap_read, the same body §8·26 and §8·28 use",
        (_o31["a"], _o31["overlap_verdict"], _o31["contained_direction"]),
        (15, "contained", "the two sets are identical"))
    _rows31d = _rows31 + [([1.0, -1.0], True)] * 5
    _o31d = coh_payload(_cohd(_rows31d), _sizes)["rows"]["2"]["sign_overlap"]
    chk("    with the margins apart it names the direction instead",
        (_o31d["a"], _o31d["overlap_verdict"], _o31d["contained_direction"]),
        (15, "contained", "same-sign inside path-qualifying"))
    chk("    and the reachability count comes with it (§11 item 20)",
        (_o31["branches_reachable"], _o31["disjoint_reachable"]), (3, True))

    #: The pattern-level qualify rate has to be per pattern, not pooled: that
    #: is the whole point of enumerating the alphabet.
    chk("    each pattern carries its own qualify rate",
        [(k, _pl31["sign_patterns"][k]["qualify_rate"])
         for k in ("++", "--", "+-")], [("++", 1.0), ("--", 1.0), ("+-", 0.0)])

    _buf, _keep = io.StringIO(), sys.stdout
    sys.stdout = _buf
    try:
        print_coh_signs(coh_payload(_cohd(_rows31), _sizes))
    finally:
        sys.stdout = _keep
    _ts31 = _buf.getvalue()
    chk("    print_coh_signs reads the first branch and tags it",
        ("§8·31·2 -> FIRST BRANCH" in _ts31)
        and not any(f"§8·31·2 -> {o} BRANCH" in _ts31
                    for o in ("SECOND", "THIRD")), True)
    chk("    and it carries §8·31·4's refusal to rule on what the mode IS",
        "a motive, not a conclusion" in _ts31, True)

    _rows31b = ([([1.0, 1.0], False)] * 10 + [([1.0, -1.0], True)] * 10)
    _o31b = coh_payload(_cohd(_rows31b),
                        _sizes)["rows"]["2"]["sign_overlap"]
    chk("    an empty corner reads the second branch",
        (_o31b["a"], _o31b["overlap_verdict"]), (0, "disjoint"))
    _rows31c = ([([1.0, 1.0], True)] * 6 + [([1.0, 1.0], False)] * 4
                + [([1.0, -1.0], True)] * 4 + [([1.0, -1.0], False)] * 6)
    chk("    and anything else is mixed",
        coh_payload(_cohd(_rows31c),
                    _sizes)["rows"]["2"]["sign_overlap"]["overlap_verdict"],
        "mixed")

    #: 規矩 19 for §8·31: the accumulator grew again.
    _oa31 = omega_new_acc()
    _b431 = json.dumps(omega_payload(_oa31), sort_keys=True)
    _oa31["b8like"]["coh"][1] = _cohd([([1.0, 1.0], True)])[1]
    chk("    filling §8·31's subtree leaves omega_payload byte for byte",
        json.dumps(omega_payload(_oa31), sort_keys=True) == _b431, True)

    #: §8·32, registered before the code, with the
    #: §11 item 15 check written out in §8·32·0 first.
    print("\n  §8·32's ideal pattern and its 2x2:")

    chk("    ideal_pattern is §8·31·1's derivation, stated for any window",
        [ideal_pattern(L) for L in (2, 3, 4, 7)],
        ["+-", "++-", "+++-", "++++++-"])
    chk("    and window 2 agrees with the alphabet already measured",
        ideal_pattern(2), "+-")

    #: **The same relative gap flips with `u0`**, which is the whole point of
    #: the bound being `500/u0` rather than a number. The first draft of this
    #: check used one `u0` for both sides and asserted a `True` the arithmetic
    #: could not produce.
    chk("    pgrid_over is one body, and the same gap flips with u0",
        (pgrid_over(1000.0, 1000.5, 2_000_000.0)[2],
         pgrid_over(1000.0, 1000.5, 200_000.0)[2],
         pgrid_over(1000.0, None, 200_000.0)[2],
         pgrid_over(1000.0, 1000.5, None)[2]),
        (True, False, None, None))
    print("     (gap 5e-4 either way. Bound is 500/u0: 2.5e-4 on a two-million")
    print("      loan, so over; 2.5e-3 on a two-hundred-thousand loan, so")
    print("      under. The two Nones are `could not ask`, not `no`.)")

    _p32 = ([([1.0, -1.0], True, False)] * 40
            + [([1.0, -1.0], False, True)] * 10
            + [([1.0, 1.0], False, True)] * 30
            + [([1.0, 1.0], False, False)] * 20)
    _r32 = coh_payload(_cohd(_p32), _sizes)["rows"]["2"]
    chk("    on-pattern is counted against the whole window",
        (_r32["ideal_pat"], _r32["ideal_pat_share"]), (50, 0.5))
    chk("    and derived-off-pattern is 0, which §8·31·1 says it must be",
        (_r32["ideal_and_derived"], _r32["derived_off_pattern"]), (40, 0))
    print("     (that zero is a **structural cross-check**, not a reading:")
    print("      §8·31·1 derives that an ideal path forces this pattern. A")
    print("      non-zero would mean the derivation is wrong.)")

    _o32 = _r32["pat_overlap"]
    chk("    the 2x2's four cells partition the loops that could be asked",
        (_r32["pat_n"], sum(_r32["pat_cell"].values())), (100, 100))
    chk("    off-pattern x over-bound reads through overlap_read",
        (_o32["a"], _r32["n_off_pattern"], _r32["n_over_bound"],
         _o32["overlap_verdict"]), (30, 50, 40, "mixed"))
    chk("    and the reachability count comes with it",
        (_o32["branches_reachable"], _o32["a_floor"], _o32["a_ceiling"]),
        (3, 0, 40))

    _p32u = _p32 + [([1.0, -1.0], True)] * 7
    _r32u = coh_payload(_cohd(_p32u), _sizes)["rows"]["2"]
    chk("    a loan with no readable u0 is counted apart, not as `not over`",
        (_r32u["ob_unknown"], _r32u["pat_n"]), (7, 100))
    print("     (§11 item 6: `could not ask` is its own counter. Folding it")
    print("      into `not over` would answer a question never put.)")

    _p32c = ([([1.0, 1.0], False, True)] * 30
             + [([1.0, -1.0], False, True)] * 10
             + [([1.0, -1.0], False, False)] * 20)
    chk("    one side wholly inside the other reads FIRST BRANCH",
        coh_payload(_cohd(_p32c), _sizes)["rows"]["2"]["pat_overlap"]
        ["contained_direction"], "off-pattern inside over-bound")
    _p32d = ([([1.0, 1.0], False, False)] * 30
             + [([1.0, -1.0], False, True)] * 30)
    chk("    an empty corner reads SECOND BRANCH",
        coh_payload(_cohd(_p32d), _sizes)["rows"]["2"]["pat_overlap"]
        ["overlap_verdict"], "disjoint")

    for _tag, _rows, _want in (("first", _p32c, "FIRST"),
                               ("second", _p32d, "SECOND"),
                               ("third", _p32, "THIRD")):
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_pat_overlap(coh_payload(_cohd(_rows), _sizes))
        finally:
            sys.stdout = _keep
        _t32 = _buf.getvalue()
        _o = {"FIRST", "SECOND", "THIRD"} - {_want}
        chk(f"    print_pat_overlap reads the {_tag} branch for §8·32·2",
            (f"§8·32·2 -> {_want} BRANCH" in _t32)
            and not any(f"§8·32·2 -> {o} BRANCH" in _t32 for o in _o), True)
    _buf, _keep = io.StringIO(), sys.stdout
    sys.stdout = _buf
    try:
        print_pat_overlap(coh_payload(_cohd(_p32), _sizes))
    finally:
        sys.stdout = _keep
    chk("    and it carries §8·32·4 item 3's warning about a large lift",
        "is not `the same set`" in _buf.getvalue(), True)

    #: §8·33, registered before the code.
    print("\n  §8·33's compound prediction:")

    def _w3(a, b, c, n):
        """n loops at window 3 with the given signs; `-` on the cure."""
        return [([1.0 if a else -1.0, 1.0 if b else -1.0,
                  1.0 if c else -1.0], True)] * n

    #: **Independent by construction**: p = 0.8 on each of two delinquent
    #: months, and the joint is exactly the product, so observed == predicted.
    _ind3 = (_w3(1, 1, 0, 64) + _w3(1, 0, 0, 16)
             + _w3(0, 1, 0, 16) + _w3(0, 0, 0, 4))
    _r3 = coh_payload(_cohd(_ind3), _sizes)["rows"]["3"]
    chk("    p and q are counts over the same loops, not fits",
        (round(_r3["p_month"], 6), round(_r3["q_cure"], 6)), (0.8, 1.0))
    chk("    and an independent fixture reads observed == predicted exactly",
        (round(_r3["ideal_pat_share"], 6), round(_r3["predicted"], 6),
         round(_r3["obs_over_pred"], 6)), (0.64, 0.64, 1.0))
    chk("    the npos histogram says one bad month from two",
        _r3["npos_hist"], {"0": 4, "1": 32, "2": 64})

    #: Clustered: same `p`, but the misses pile onto the same loops.
    _clu3 = _w3(1, 1, 0, 80) + _w3(0, 0, 0, 20)
    _c3 = coh_payload(_cohd(_clu3), _sizes)["rows"]["3"]
    chk("    clustering keeps p and lifts the observed share above predicted",
        (round(_c3["p_month"], 6), round(_c3["ideal_pat_share"], 6),
         round(_c3["predicted"], 6)), (0.8, 0.8, 0.64))
    #: Anti-clustered: same `p`, misses spread one per loop.
    _ant3 = _w3(1, 1, 0, 60) + _w3(1, 0, 0, 40)
    _a3 = coh_payload(_cohd(_ant3), _sizes)["rows"]["3"]
    chk("    and spreading them keeps p and drops it below",
        (round(_a3["p_month"], 6), round(_a3["ideal_pat_share"], 6)),
        (0.8, 0.6))
    print("     (all three fixtures have p = 0.8 and q = 1. **Only the")
    print("      clustering differs**, which is what the branch is about.)")

    def _w4(pos, n):
        """n loops at window 4 with `pos` of the 3 delinquent months positive."""
        rs = [1.0] * pos + [-1.0] * (3 - pos) + [-1.0]
        return [(rs, True)] * n

    _clu = _clu3 + _w4(3, 80) + _w4(0, 20)
    _ant = _ant3 + _w4(3, 40) + _w4(2, 60)
    _ind = _ind3 + (_w4(3, 512) + _w4(2, 384) + _w4(1, 96) + _w4(0, 8))
    chk("    two voting windows above 1 read FIRST BRANCH",
        coh_payload(_cohd(_clu), _sizes)["compound_verdict"], "clustered")
    chk("    two below 1 read SECOND BRANCH",
        coh_payload(_cohd(_ant), _sizes)["compound_verdict"], "anti_clustered")
    #: **The tie.** `obs == pred` satisfies `>= 1` and `<= 1` both, and the
    #: first version tested `>= 1` first, so independence — the null this
    #: station measures against — would have printed as clustering. §11 item 4.
    _pi = coh_payload(_cohd(_ind), _sizes)
    #: **The tie has to be tested in integers.** Written on the float ratio it
    #: was unreachable: `0.8**3` is not `0.512` in binary, so this very
    #: fixture read `0.99999999999999989` and fell to `anti_clustered` — a
    #: patch for §11 item 4 that manufactured a §11 item 3. The vote runs on
    #: `cmp_exact`, which cross-multiplies to integers.
    chk("    exact equality at every window is NAMED, and tested in integers",
        (_pi["compound_verdict"],
         [_pi["rows"][str(L)]["cmp_exact"] for L in (3, 4)]),
        ("independent", [0, 0]))
    chk("    while NEITHER float ratio is exactly 1, which is why it is exact",
        [_pi["rows"][str(L)]["obs_over_pred"] == 1.0 for L in (3, 4)],
        [False, False])
    print(f"     (integers say equal at both windows; the floats read "
          f"{_pi['rows']['3']['obs_over_pred']:.17f} and "
          f"{_pi['rows']['4']['obs_over_pred']:.17f}.")
    print("      0.8**2 and 0.8**3 are not 0.64 and 0.512 in binary.)")
    chk("    a mix of directions is mixed",
        coh_payload(_cohd(_clu3 + _w4(3, 40) + _w4(2, 60)),
                    _sizes)["compound_verdict"], "mixed")

    #: **Window 2 is not a special case, and the fixture that said it was
    #: could only ever say so.** The claim was that `p*q` is the observed
    #: share identically when there is one delinquent month. It is not:
    #: `p*q` multiplies two marginals and the observed share is the joint.
    #: The old fixture set every cure month negative, so `q = 1` and
    #: `p*q = p = observed` held trivially — **a fixture with only one
    #: possible answer**. The archives read 1.0239 there, not 1.0000.
    _p2 = coh_payload(_cohd([([1.0, -1.0], True)] * 50
                            + [([1.0, 1.0], True)] * 10
                            + [([-1.0, -1.0], True)] * 40), _sizes)
    _r2c = _p2["rows"]["2"]
    chk("    with q below 1, window 2's p*q is NOT the observed share",
        (round(_r2c["p_month"], 6), round(_r2c["q_cure"], 6),
         round(_r2c["ideal_pat_share"], 6), round(_r2c["predicted"], 6)),
        (0.6, 0.9, 0.5, 0.54))
    chk("    so it is a real test there and it votes",
        (_r2c["cmp_exact"], round(_r2c["obs_over_pred"], 6)),
        (-1, round(0.5 / 0.54, 6)))
    chk("    and the degenerate q = 1 fixture is what hid it",
        round(coh_payload(_cohd([([1.0, -1.0], True)] * 60
                                + [([-1.0, -1.0], True)] * 40),
                          _sizes)["rows"]["2"]["obs_over_pred"], 6), 1.0)
    print("     (that last line is the old fixture. Its q is 1, so p*q = p =")
    print("      observed whatever the data does — it could only confirm.")
    print("      §11 item 3 in a fixture's clothes.)")

    for _tag, _rows, _want in (("first", _clu, "FIRST"),
                               ("second", _ant, "SECOND"),
                               ("third", _clu3 + _w4(3, 40) + _w4(2, 60),
                                "THIRD")):
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_compound(coh_payload(_cohd(_rows), _sizes))
        finally:
            sys.stdout = _keep
        _t33 = _buf.getvalue()
        _o = {"FIRST", "SECOND", "THIRD"} - {_want}
        chk(f"    print_compound reads the {_tag} branch for §8·33·2",
            (f"§8·33·2 -> {_want} BRANCH" in _t33)
            and not any(f"§8·33·2 -> {o} BRANCH" in _t33 for o in _o), True)
    _buf, _keep = io.StringIO(), sys.stdout
    sys.stdout = _buf
    try:
        print_compound(_pi)
    finally:
        sys.stdout = _keep
    _t33i = _buf.getvalue()
    chk("    and the tie prints NO BRANCH, not one of the three",
        ("§8·33·2 -> NO BRANCH" in _t33i)
        and not any(f"§8·33·2 -> {o} BRANCH" in _t33i
                    for o in ("FIRST", "SECOND", "THIRD")), True)

    #: 規矩 19 once more: the accumulator grew, `b10_omega.json` must not.
    _oa33 = omega_new_acc()
    _b433 = json.dumps(omega_payload(_oa33), sort_keys=True)
    _oa33["b8like"]["coh"][2] = _cohd(_clu3)[2]
    chk("    filling §8·33's subtree leaves omega_payload byte for byte",
        json.dumps(omega_payload(_oa33), sort_keys=True) == _b433, True)

    #: §8·34, registered before the code.
    print("\n  §8·34's class census:")

    def _prow(per, dq, upb=100_000.0):
        return (per, dq, "", 20, upb, 6.0, 300, 0.0)

    #: `tail_outcome` picks the rows after the cure **by period**, and the
    #: exposure is months to the FIRST re-delinquency, not every month after.
    _sp = [_prow(200001, "00"), _prow(200002, "01"), _prow(200003, "00")]
    _tl = [_prow(200004, "00"), _prow(200005, "01"), _prow(200006, "02"),
           _prow(200007, "00")]
    chk("    months after the cure are picked by period, not by index",
        tail_outcome(_sp + _tl, _sp)[0], 4)
    chk("    exposure stops at the FIRST re-delinquency",
        tail_outcome(_sp + _tl, _sp)[1], 2)
    chk("    and with no re-delinquency it is every remaining month",
        tail_outcome(_sp + [_prow(200004, "00"), _prow(200005, "00")], _sp)[:3],
        (2, 2, False))
    print("     (counting all remaining months for a loan that re-defaults in")
    print("      month 2 would hand it exposure it never had at risk. That is")
    print("      why §8·34·2 is a hazard and not a share.)")
    chk("    RA and a zero balance are their own flags, not re-delinquency",
        tail_outcome(_sp + [_prow(200004, "RA"), _prow(200005, "00", 0.0)],
                     _sp)[2:], (False, True, True))
    chk("    an empty span asks nothing rather than guessing",
        tail_outcome(_sp, None), (0, 0, False, False, False))

    def _clsrow(fico, dti, fthb, purpose, months, exposure, redel):
        return {"prof": {"fico": fico, "dti": dti, "fthb": fthb,
                         "purpose": purpose},
                "months": months, "exposure": exposure, "redel": redel,
                "ra": False, "zero": False}

    _d = cls_new()
    for _ in range(3):
        cls_file(_d, _clsrow("780", "30", "Y", "P", 24, 24, False))
    cls_file(_d, _clsrow("640", "45", "N", "C", 12, 6, True))
    cls_file(_d, _clsrow("", "999", "9", "9", 10, 10, False))
    chk("    FICO goes through fico_band and unreadable is counted apart",
        (_d["fico"], _d["fico_bad"]), ({0: 3, 7: 1}, 1))
    chk("    a blank DTI is unreadable, and 999 is NOT silently a band",
        (_d["dti"], _d["dti_bad"]), ([30, 30, 30, 45, 999], 0))
    print("     (Freddie writes 999 for a missing DTI and this file does NOT")
    print("      know that — it parses as an integer. It lands in the")
    print("      quantiles as 999 and the reading has to say so. Guessing a")
    print("      sentinel this file never registered would be worse.)")
    chk("    the hazard's two counts are kept apart from the share's",
        (_d["redel"], _d["exposure"], _d["n"]), (1, 24 * 3 + 6 + 10, 5))

    def _pl34(pp, pm):
        """pp / pm: (n, redel, exposure) for `++` and `+-`."""
        cls = {}
        for k, (n, rd, ex) in (("++", pp), ("+-", pm)):
            d = cls_new()
            for i in range(n):
                per = ex // n
                cls_file(d, _clsrow("700", "35", "N", "P", per, per,
                                    i < rd))
            d["redel"], d["exposure"] = rd, ex
            cls[k] = d
        return cls_payload(cls)

    chk("    a higher hazard on ++ reads FIRST BRANCH",
        _pl34((100, 30, 1000), (100, 20, 1000))["hazard_verdict"],
        "plus_plus_riskier")
    chk("    a lower one reads SECOND BRANCH",
        _pl34((100, 10, 1000), (100, 20, 1000))["hazard_verdict"],
        "plus_plus_safer")
    #: **The tie again**, and again in integers: 20/1000 against 40/2000 is
    #: the same hazard and floats would not say so reliably.
    _tie = _pl34((100, 20, 1000), (100, 40, 2000))
    chk("    and equal hazards on unequal exposure read THIRD BRANCH exactly",
        (_tie["hazard_verdict"], _tie["hazard_cmp"]), ("identical", 0))
    print("     (20/1000 and 40/2000 are the same hazard. Cross-multiplied")
    print("      that is 20*2000 == 40*1000, exact. §11 item 4.)")
    chk("    and with no exposure there is no reading rather than a zero",
        _pl34((100, 0, 0), (100, 20, 1000))["hazard_verdict"], None)

    for _tag, _args, _want in (
            ("first", ((100, 30, 1000), (100, 20, 1000)), "FIRST"),
            ("second", ((100, 10, 1000), (100, 20, 1000)), "SECOND"),
            ("third", ((100, 20, 1000), (100, 40, 2000)), "THIRD")):
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_classes({"rows": {str(NOISE_LENS[0]): _pl34(*_args)}})
        finally:
            sys.stdout = _keep
        _t34 = _buf.getvalue()
        _o = {"FIRST", "SECOND", "THIRD"} - {_want}
        chk(f"    print_classes reads the {_tag} branch for §8·34·2",
            (f"§8·34·2 -> {_want} BRANCH" in _t34)
            and not any(f"§8·34·2 -> {o} BRANCH" in _t34 for o in _o), True)
    _buf, _keep = io.StringIO(), sys.stdout
    sys.stdout = _buf
    try:
        print_classes({"rows": {str(NOISE_LENS[0]):
                                _pl34((100, 30, 1000), (100, 20, 1000))}})
    finally:
        sys.stdout = _keep
    chk("    and every branch carries §8·34·4's refusal to say what ++ IS",
        "does not say what `++` IS" in _buf.getvalue(), True)

    #: 規矩 19: the census is accumulator-only and rides on `--noise` alone.
    _oa34 = omega_new_acc()
    _b434 = json.dumps(omega_payload(_oa34), sort_keys=True)
    _c34 = {}
    coh_file(_c34, 1, [1.0, 1.0], 2.0, False, None,
             cls=_clsrow("700", "35", "N", "P", 5, 5, True))
    _oa34["b8like"]["coh"] = _c34
    chk("    filling §8·34's subtree leaves omega_payload byte for byte",
        json.dumps(omega_payload(_oa34), sort_keys=True) == _b434, True)
    chk("    and coh_file without a profile files no class at all",
        "cls" in _cohd([([1.0, 1.0], True)])[1], False)
    print("     (`--omega`, `--pgrid` and `--o18join` pass no profile, so they")
    print("      carry none of this.)")

    #: §8·35, registered before the code.
    print("\n  §8·35's crisis windows:")

    chk("    the windows are declared by name, and calm is everything else",
        [crisis_of(y) for y in (2007, 2008, 2011, 2012, 2019, 2020,
                                2021, 2022, None)],
        ["calm", "gfc", "gfc", "calm", "calm", "cares", "cares", "calm",
         None])
    print("     (2008-2011 and 2020-2021 are public dates, not shapes picked")
    print("      out of the series. 纪律 11 lets a pre-declared reading of a")
    print("      printed object in; it does not let a fitted line in.)")

    def _cy(pp_years, pm_years):
        """Build a class census straight from `{year: n}` counts."""
        cls = {}
        for k, ys in (("++", pp_years), ("+-", pm_years)):
            d = cls_new()
            for y, n in ys.items():
                for _ in range(n):
                    cls_file(d, {"prof": {}, "months": 1, "exposure": 1,
                                 "redel": False, "ra": False, "zero": False,
                                 "cure_year": y})
            cls[k] = d
        return cls_payload(cls)

    _hi = _cy({2009: 30, 2015: 10}, {2009: 70, 2015: 90})
    chk("    a higher ++ share inside the windows reads FIRST BRANCH",
        (_hi["crisis_verdict"], _hi["crisis"]["crisis_pp"],
         _hi["crisis"]["crisis_total"], _hi["crisis"]["calm_total"]),
        ("crisis_higher", 30, 100, 100))
    _lo = _cy({2009: 10, 2015: 30}, {2009: 90, 2015: 70})
    chk("    a lower one reads SECOND BRANCH",
        _lo["crisis_verdict"], "crisis_lower")
    #: **The tie is the institutional branch**, so it has to be reachable and
    #: it has to be exact: 20/100 against 40/200 is the same share.
    _eq = _cy({2009: 20, 2015: 40}, {2009: 80, 2015: 160})
    chk("    equal shares on unequal totals read THIRD BRANCH exactly",
        (_eq["crisis_verdict"], _eq["crisis_cmp"]), ("institutional", 0))
    print("     (20/100 and 40/200 are the same share; cross-multiplied that")
    print("      is 20*200 == 40*100. The third branch IS the tie, and this")
    print("      station's whole point is that it can fire. §11 item 4.)")

    #: Both windows must pool, and both must also print apart.
    _two = _cy({2009: 10, 2021: 20, 2015: 5}, {2009: 10, 2021: 20, 2015: 45})
    chk("    the two windows pool for the reading and split for the table",
        (_two["crisis"]["crisis_pp"], _two["crisis"]["crisis_total"],
         sorted(_two["crisis"]["windows"])),
        (30, 60, ["calm", "cares", "gfc"]))
    chk("    and every cure year prints, none filtered",
        sorted(_two["crisis"]["years"], key=int), ["2009", "2015", "2021"])
    chk("    each year carries which window it fell in",
        [_two["crisis"]["years"][y]["window"]
         for y in ("2009", "2015", "2021")], ["gfc", "calm", "cares"])
    chk("    with only one side present there is no reading, not a zero",
        _cy({2009: 5}, {})["crisis_verdict"], None)

    for _tag, _pl, _want in (("first", _hi, "FIRST"), ("second", _lo, "SECOND"),
                             ("third", _eq, "THIRD")):
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_crisis({"rows": {str(NOISE_LENS[0]): _pl}})
        finally:
            sys.stdout = _keep
        _t35 = _buf.getvalue()
        _o = {"FIRST", "SECOND", "THIRD"} - {_want}
        chk(f"    print_crisis reads the {_tag} branch for §8·35·2",
            (f"§8·35·2 -> {_want} BRANCH" in _t35)
            and not any(f"§8·35·2 -> {o} BRANCH" in _t35 for o in _o), True)
    _buf, _keep = io.StringIO(), sys.stdout
    sys.stdout = _buf
    try:
        print_crisis({"rows": {str(NOISE_LENS[0]): _eq}})
    finally:
        sys.stdout = _keep
    _t35e = _buf.getvalue()
    chk("    the third branch says what `institutional` means for the reader",
        "biased" in _t35e and "not only in the crisis years" in _t35e, True)
    chk("    and every branch inherits §8·34·4's refusal",
        "What `++` IS remains unsaid" in _t35e, True)

    #: 規矩 19 again: the year census rides on `--noise` and nothing else.
    _oa35 = omega_new_acc()
    _b435 = json.dumps(omega_payload(_oa35), sort_keys=True)
    _c35 = {}
    coh_file(_c35, 1, [1.0, 1.0], 2.0, False, None,
             cls={"prof": {}, "months": 1, "exposure": 1, "redel": False,
                  "ra": False, "zero": False, "cure_year": 2009})
    _oa35["b8like"]["coh"] = _c35
    chk("    filling §8·35's subtree leaves omega_payload byte for byte",
        json.dumps(omega_payload(_oa35), sort_keys=True) == _b435, True)

    #: §8·36, registered before the code.
    #: That sentence is the whole of §11 item 16: the previous pass shipped a
    #: printer citing a registration number for which no registration existed.
    print("\n  §8·36's frozen delinquent month:")

    def _ibrow(u, z):
        row = [None] * 8
        row[R_UPB], row[R_DEFER] = u, z
        return tuple(row)

    chk("    bal_ib is col 3 - col 12, and an unreadable side asks nothing",
        (_ib_of(_ibrow(1000.0, 40.0)), _ib_of(_ibrow(1000.0, 0.0)),
         _ib_of(_ibrow(None, 40.0)), _ib_of(_ibrow(1000.0, None))),
        (960.0, 1000.0, None, None))
    print("     (a deferred balance of 0.00 is a NUMBER and a blank one is")
    print("      not. That is §8·14·5's entire finding, and failure mode 20")
    print("      is what folding the two together costs.)")

    chk("    frozen is exact, and exact on the INTEREST-BEARING balance",
        (frozen_pair(_ibrow(200000.0, 0.0), _ibrow(200000.0, 0.0)),
         frozen_pair(_ibrow(200000.0, 0.0), _ibrow(199999.99, 0.0)),
         frozen_pair(_ibrow(200500.0, 500.0), _ibrow(201000.0, 1000.0)),
         frozen_pair(_ibrow(None, 0.0), _ibrow(200000.0, 0.0)),
         frozen_pair(_ibrow(200000.0, 0.0), _ibrow(200000.0, None))),
        (True, False, True, None, None))
    print("     (the third case moves col 3 by $500 and col 12 with it, so")
    print("      the interest-bearing balance did not move. A check written")
    print("      on col 3 alone reads that as unfrozen.)")
    print("     (a cent apart is not frozen. §8·16 already holds the whole")
    print("      window at age >= 8, where §5·2 measured this carrier to")
    print("      report to the cent, so there is no tolerance to set.)")

    #: The frozen-month theorem, in the arithmetic it actually lives in.
    #: `r_month` reads `bal(t1)` against `b_hat = carry_forward(bal(t0), note,
    #: P)`, and `carry_forward` is `b*(1+i) - P`. On a frozen month `bal(t1)
    #: == bal(t0)`, so the gap is `P - bal(t0)*i` — positive for **any** loan
    #: whose payment covers its own interest, which every amortising contract
    #: payment does by construction.
    _thm_ok = True
    for _b0 in (50000.0, 200000.0, 750000.0):
        for _rate in (2.5, 5.0, 9.5):
            _i = _rate / 1200.0
            for _term in (180, 360):
                _P = _b0 * _i / (1.0 - (1.0 + _i) ** (-_term))
                if not (_b0 - (_b0 * (1.0 + _i) - _P)) > 0.0:
                    _thm_ok = False
    chk("    §8·36·1's theorem holds across the rate x term x balance grid",
        _thm_ok, True)
    chk("    and it rests on the payment, so it has a reachable converse",
        (200000.0 - (200000.0 * 1.004 - 500.0)) > 0.0, False)
    print("     (a payment smaller than the month's interest breaks it, so")
    print("      the theorem is a statement about amortising contracts and")
    print("      not a tautology. §11 item 3: a check that cannot fail is")
    print("      not a check.)")

    def _fzcls(spec, months=None, unread=0):
        """`{year: (loops, frozen, r1_neg)}` -> one filed class census.

        Files real rows through `cls_file`, so the fixture calls what the
        scan calls — the same reason `coh_file` was extracted, and the same
        account `b10_support_fannie`'s SENTINEL made this station pay once.
        """
        d = cls_new()
        for y, (n, fz, r1) in sorted(spec.items()):
            for j in range(n):
                cls_file(d, {"prof": {}, "months": 1, "exposure": 1,
                             "redel": False, "ra": False, "zero": False,
                             "cure_year": y,
                             "cure_period": (months or {}).get(y, y * 100 + 6),
                             "frozen": j < fz, "r1_negative": j >= n - r1})
        for _ in range(unread):
            cls_file(d, {"prof": {}, "months": 1, "exposure": 1,
                         "redel": False, "ra": False, "zero": False,
                         "cure_year": 2020, "cure_period": 202006,
                         "frozen": None, "r1_negative": False})
        return d

    _v36 = {}
    for _tag, _spec in (
            ("convention_changed", {2018: (10, 7, 3), 2020: (5, 5, 0),
                                    2021: (4, 4, 0)}),
            ("frozen_not_total", {2018: (10, 10, 0), 2020: (5, 3, 0)}),
            ("frozen_always_total", {2018: (10, 10, 0), 2020: (5, 5, 0)}),
            ("no_reading", {2018: (10, 7, 3)})):
        _v36[_tag] = frozen_read({"+-": _fzcls(_spec)})
    chk("    each of §8·36·3's four branches fires on its own fixture",
        [_v36[t]["frozen_verdict"] for t in
         ("convention_changed", "frozen_not_total", "frozen_always_total",
          "no_reading")],
        ["convention_changed", "frozen_not_total", "frozen_always_total",
         "no_reading"])
    chk("    and the branch is picked by the two booleans, nothing else",
        (_v36["convention_changed"]["frozen"]["post_all_frozen"],
         _v36["convention_changed"]["frozen"]["pre_all_frozen"],
         _v36["frozen_always_total"]["frozen"]["pre_all_frozen"]),
        (True, False, True))

    _big = cls_new()
    _big["froz_year"][2018] = [10, 10, 0]
    _big["froz_year"][2020] = [10 ** 17, 10 ** 17 - 1, 0]
    chk("    'every loop frozen' is a COUNT; a float cannot express it",
        ((10 ** 17 - 1) / 10 ** 17 == 1.0,
         frozen_read({"+-": _big})["frozen_verdict"]),
        (True, "frozen_not_total"))
    print("     (that share IS exactly 1.0 in binary floating point while the")
    print("      counts differ by one. The tie is the branch here, so it has")
    print("      to be judged in arithmetic that can express one — §11 item")
    print("      4, the same account §8·33 and §8·34 paid.)")

    _thm = cls_new()
    _thm["froz_year"][2018] = [10, 10, 0]
    _thm["froz_year"][2020] = [10, 8, 3]
    chk("    the theorem cross-check fires when r1<0 outruns unfrozen",
        frozen_read({"+-": _thm})["frozen"]["theorem_violations"], [2020])
    chk("    and it is silent on every fixture that respects the theorem",
        [_v36[t]["frozen"]["theorem_violations"] for t in sorted(_v36)],
        [[], [], [], []])
    print("     (frozen makes carry_forward drop the balance, so r1 > 0")
    print("      follows, and it is a THEOREM, so that column is")
    print("      a structural check and never a finding: §11 item 15, which")
    print("      §8·31 paid a full scan to learn.)")

    _pa, _pb = cls_new(), cls_new()
    _pa["froz_year"][2020] = [3, 3, 0]
    _pb["froz_year"][2020] = [4, 4, 0]
    _pb["froz_year"][2018] = [6, 2, 4]
    _rp = frozen_read({"++": _pa, "+-": _pb})
    chk("    the years pool ACROSS the sign classes, not inside one",
        (_rp["frozen"]["years"]["2020"]["loops"],
         _rp["frozen"]["years"]["2018"]["loops"], _rp["frozen_verdict"]),
        (7, 6, "convention_changed"))
    print("     (a loop's sign class is downstream of the very thing being")
    print("      measured: `--` and `-+` CANNOT exist once the delinquent")
    print("      month is frozen, so a frozen share taken inside a class")
    print("      would condition on the outcome.)")

    _mo = cls_new()
    _mo["froz_year"].update({2018: [5, 5, 0], 2019: [10, 7, 0],
                             2020: [7, 7, 0]})
    for _p, _n, _f in ((201812, 5, 5), (201903, 4, 1), (201911, 6, 6),
                       (202001, 7, 7)):
        _mo["froz_month"][_p] = [_n, _f, 0]
    _rmo = frozen_read({"+-": _mo})
    chk("    the 2019 month table keeps 2019 and drops both neighbours",
        sorted(_rmo["frozen"]["months_2019"]), ["201903", "201911"])

    _ur = frozen_read({"+-": _fzcls({2018: (10, 7, 3), 2020: (5, 5, 0)},
                                    unread=4)})
    chk("    an unreadable balance is counted apart, not as 'not frozen'",
        (_ur["frozen"]["unreadable"],
         _ur["frozen"]["years"]["2020"]["loops"],
         _ur["frozen"]["years"]["2020"]["all_frozen"],
         _ur["frozen_verdict"]),
        (4, 5, True, "convention_changed"))
    _abs36 = cls_new()
    cls_file(_abs36, {"prof": {}, "months": 1, "exposure": 1, "redel": False,
                      "ra": False, "zero": False, "cure_year": 2020,
                      "cure_period": 202006})
    chk("    a loop the question was never PUT to lands in neither box",
        (_abs36["froz_unread"], _abs36["froz_year"], _abs36["by_year"]),
        (0, {}, {2020: 1}))
    print("     (three states kept apart: the key ABSENT means the loop is")
    print("      not a window-2 span so the question does not apply; None")
    print("      means it was put and could not be answered; a bool means it")
    print("      was. §11 item 6.)")

    for _tag, _want in (("convention_changed", "FIRST BRANCH"),
                        ("frozen_not_total", "SECOND BRANCH"),
                        ("frozen_always_total", "THIRD BRANCH"),
                        ("no_reading", "NO READING")):
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_frozen({"rows": {str(NOISE_LENS[0]): _v36[_tag]}})
        finally:
            sys.stdout = _keep
        _t36 = _buf.getvalue()
        _o = {"FIRST BRANCH", "SECOND BRANCH", "THIRD BRANCH",
              "NO READING"} - {_want}
        chk("    print_frozen reads the %s branch for §8·36·3" % _tag,
            ("§8·36·3 -> " + _want in _t36)
            and not any("§8·36·3 -> " + o in _t36 for o in _o), True)

    _buf, _keep = io.StringIO(), sys.stdout
    sys.stdout = _buf
    try:
        print_frozen({"rows": {str(NOISE_LENS[0]): _rmo}})
    finally:
        sys.stdout = _keep
    _t36m = _buf.getvalue()
    chk("    the printer names §3·4's thinnest 2019 month",
        "thinnest 2019 month: 201903" in _t36m, True)
    chk("    and prints the theorem column and the unanswerable count",
        ("theorem violations" in _t36m)
        and ("could not be answered on" in _t36m), True)
    chk("    and refuses to say whose convention this is",
        "this station does not say" in _t36m, True)

    #: 規矩 19: the frozen census rides on `--noise` and nothing else.
    _oa36 = omega_new_acc()
    _b436 = json.dumps(omega_payload(_oa36), sort_keys=True)
    _c36 = {}
    coh_file(_c36, 1, [1.0, 1.0], 2.0, False, None,
             cls={"prof": {}, "months": 1, "exposure": 1, "redel": False,
                  "ra": False, "zero": False, "cure_year": 2020,
                  "cure_period": 202006, "frozen": True})
    _oa36["b8like"]["coh"] = _c36
    chk("    filling §8·36's subtree leaves omega_payload byte for byte",
        json.dumps(omega_payload(_oa36), sort_keys=True) == _b436, True)
    _c36n = {}
    coh_file(_c36n, 1, [-1.0, 1.0], 0.0, False, None,
             cls={"prof": {}, "months": 1, "exposure": 1, "redel": False,
                  "ra": False, "zero": False, "cure_year": 2018,
                  "cure_period": 201806, "frozen": False})
    chk("    r1_negative is set where `rs` lives, not carried in from above",
        (_c36[1]["cls"]["++"]["froz_year"][2020],
         _c36n[1]["cls"]["-+"]["froz_year"][2018]),
        ([1, 1, 0], [1, 0, 1]))
    print("     (Fixed before the run: the delinquent month's sign lives in")
    print("      `coh_file` with `rs`. Deriving it a second time elsewhere is")
    print("      failure mode 19 — two copies of one definition with no check")
    print("      between them.)")

    #: §8·37 and §8·38, both registered before the code was written
    #: (§11 item 16, which §8·36 paid for one round ago).
    print("\n  §8·37's r2 margin, conditioned on frozen:")

    def _r2cls(spec):
        """`{year: {class: (loops, frozen)}}` -> the raw class accumulator."""
        out = {}
        for y, per in sorted(spec.items()):
            for k, (n, fz) in sorted(per.items()):
                d = out.setdefault(k, cls_new())
                d["froz_year"][y] = [n, fz, 0]
        return out

    _r2 = {}
    for _tag, _spec in (
            ("r2_moved_too", {2018: {"++": (100, 60), "+-": (100, 40)},
                              2020: {"++": (100, 10), "+-": (100, 90)}}),
            ("r2_moved_up", {2018: {"++": (100, 10), "+-": (100, 90)},
                             2020: {"++": (100, 60), "+-": (100, 40)}}),
            ("composition_only", {2018: {"++": (100, 20), "+-": (100, 80)},
                                  2020: {"++": (200, 40), "+-": (200, 160)}})):
        _r2[_tag] = r2_read(_r2cls(_spec))
    chk("    §8·37·2's three branches each fire on their own fixture",
        [_r2[t]["r2_verdict"] for t in
         ("r2_moved_too", "r2_moved_up", "composition_only")],
        ["r2_moved_too", "r2_moved_up", "composition_only"])
    chk("    and the tie is exact on unequal denominators",
        (_r2["composition_only"]["r2_cmp"],
         _r2["composition_only"]["r2"]["pre"]["share"],
         _r2["composition_only"]["r2"]["post"]["share"]),
        (0, 0.2, 0.2))
    print("     (20/100 against 40/200 is the same share, cross-multiplied")
    print("      20*200 == 40*100. **The third branch IS the tie**, and it is")
    print("      the branch that says the whole collapse was composition, so")
    print("      it has to be able to fire. §11 item 4.)")

    #: The straddling year belongs to neither segment: §8·36·3 put the break
    #: inside it, so folding it either way would put two regimes in one bucket.
    _st = r2_read(_r2cls({2018: {"++": (10, 5), "+-": (10, 5)},
                          2019: {"++": (10, 7), "+-": (10, 3)},
                          2020: {"++": (10, 1), "+-": (10, 9)}}))
    chk("    the straddling year 2019 is in neither segment, and prints alone",
        (_st["r2"]["pre"]["total"], _st["r2"]["post"]["total"],
         _st["r2"]["straddle_year"]["year"],
         _st["r2"]["straddle_year"]["total"]),
        (10, 10, 2019, 10))
    chk("    and the segment edges are 2018 and 2020, taken from the break",
        (FROZEN_BREAK_YEAR - 2, FROZEN_BREAK_YEAR), (2018, 2020))

    _thm37 = _r2cls({2018: {"++": (10, 5), "+-": (10, 5)},
                     2020: {"++": (10, 1), "+-": (10, 9)}})
    _thm37["-+"] = cls_new()
    _thm37["-+"]["froz_year"][2020] = [4, 3, 0]
    chk("    a frozen loop filed under `-+` is caught: it contradicts §8·36·1",
        r2_read(_thm37)["r2"]["theorem_frozen_in_neg_classes"],
        {"-+": 3, "--": 0})
    chk("    and the clean fixtures read zero on both negative classes",
        _r2["r2_moved_too"]["r2"]["theorem_frozen_in_neg_classes"],
        {"-+": 0, "--": 0})
    chk("    one class missing is no reading, not a zero",
        r2_read({"++": cls_new()})["r2_verdict"], None)

    _uf = _r2["r2_moved_too"]["r2"]["years"]["2018"]
    chk("    `++ | unfrozen` is carried beside it and never judged",
        (_uf["unfrozen_pp"], _uf["unfrozen_total"],
         round(_uf["unfrozen_pp_share"], 4)), (40, 100, 0.4))

    for _tag, _want in (("r2_moved_too", "FIRST BRANCH"),
                        ("r2_moved_up", "SECOND BRANCH"),
                        ("composition_only", "THIRD BRANCH")):
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_r2({"rows": {str(NOISE_LENS[0]): _r2[_tag]}})
        finally:
            sys.stdout = _keep
        _t37 = _buf.getvalue()
        _o = {"FIRST BRANCH", "SECOND BRANCH", "THIRD BRANCH"} - {_want}
        chk("    print_r2 reads the %s branch for §8·37·2" % _tag,
            ("§8·37·2 -> " + _want in _t37)
            and not any("§8·37·2 -> " + o in _t37 for o in _o), True)
    chk("    and the printer states the theorem check beside the table",
        "theorem holds" in _t37, True)

    #: §8·37·2's处置 (回去查). The dump must fire on a loop that trips the
    #: gate and stay quiet on one that does not.
    def _sprow(per, upb, defer, rate=6.0, age=20, rem=340):
        row = [None] * 8
        row[R_PERIOD], row[R_UPB], row[R_DEFER] = per, upb, defer
        row[R_RATE], row[R_AGE], row[R_REM] = rate, age, rem
        return tuple(row)

    def _dxcls(frozen, span, P, vintage=2007):
        return {"prof": {}, "months": 1, "exposure": 1, "redel": False,
                "ra": False, "zero": False, "cure_year": 2008,
                "cure_period": 200802, "frozen": frozen,
                "dx": (span, P, vintage)}

    _span37 = [_sprow(200712, 200000.0, 0.0), _sprow(200801, 200000.0, 0.0),
               _sprow(200802, 199000.0, 0.0)]
    _cbrk = {}
    coh_file(_cbrk, 1, [-1.0, -1.0], -2.0, False, None,
             cls=_dxcls(True, _span37, 500.0))
    chk("    a frozen loop on the negative side is captured, not passed over",
        (_cbrk[1]["thm_n"], len(_cbrk[1]["thm_break"])), (1, 1))
    _bk = _cbrk[1]["thm_break"][0]
    chk("    and the dump carries the theorem's own premise as a column",
        (_bk["class"], _bk["ib_a"], _bk["ib_1"], _bk["P"],
         round(_bk["interest"], 2), _bk["P_exceeds_interest"]),
        ("--", 200000.0, 200000.0, 500.0, 1000.0, False))
    chk("    and a payment that does cover the interest reads True",
        thm_break_row(_dxcls(True, _span37, 2000.0),
                      [-1.0, -1.0], "--")["P_exceeds_interest"], True)
    print("     (200,000 at 6.00% owes 1,000.00 of interest that month, so a")
    print("      payment of 500 cannot push carry_forward's balance down and")
    print("      §8·36·1's step does not run. **That column is the theorem's")
    print("      unstated premise**, printed rather than ruled on.)")
    _cok = {}
    coh_file(_cok, 1, [1.0, -1.0], 0.0, False, None,
             cls=_dxcls(True, _span37, 2000.0))
    coh_file(_cok, 1, [-1.0, -1.0], -2.0, False, None,
             cls=_dxcls(False, _span37, 2000.0))
    chk("    and it stays quiet on `+-`, and on an unfrozen negative loop",
        (_cok[1].get("thm_n", 0), _cok[1].get("thm_break", [])), (0, []))
    _ccap = {}
    for _ in range(THM_BREAK_CAP + 5):
        coh_file(_ccap, 1, [-1.0, -1.0], -2.0, False, None,
                 cls=_dxcls(True, _span37, 500.0))
    chk("    the cap holds the sample while the count keeps counting",
        (_ccap[1]["thm_n"], len(_ccap[1]["thm_break"])),
        (THM_BREAK_CAP + 5, THM_BREAK_CAP))
    chk("    and coh_payload carries count, cap and sample together",
        sorted(k for k in coh_payload(_ccap, {})["rows"]["2"]
               if k.startswith("theorem_break")),
        ["theorem_break", "theorem_break_cap", "theorem_break_n"])
    _buf, _keep = io.StringIO(), sys.stdout
    sys.stdout = _buf
    try:
        print_thm_break({"theorem_break_n": THM_BREAK_CAP + 5,
                         "theorem_break": _ccap[1]["thm_break"],
                         "theorem_break_cap": THM_BREAK_CAP})
        print_thm_break({"theorem_break_n": 0, "theorem_break": [],
                         "theorem_break_cap": THM_BREAK_CAP})
    finally:
        sys.stdout = _keep
    _tb = _buf.getvalue()
    chk("    the printer names how many it did not print",
        "5 not printed" in _tb, True)
    chk("    and an empty dump is not read as `the theorem holds everywhere`",
        "**The gate did not fire on this population**" in _tb, True)

    #: The vintage x cure-month cut. **No branch, no verdict**, by design, so
    #: what the selftest checks is that the table is right
    #: and that the cross-check can actually fail.
    print("\n  the vintage x cure-month cut:")

    def _vincls(vin, per, frozen):
        return {"prof": {}, "months": 1, "exposure": 1, "redel": False,
                "ra": False, "zero": False, "cure_year": per // 100,
                "cure_period": per, "vintage": vin, "frozen": frozen}

    _cv = {}
    for _v, _p, _f, _rs in ((2005, 201904, True, [1.0, 1.0]),
                            (2005, 201904, True, [1.0, -1.0]),
                            (2005, 201905, True, [1.0, -1.0]),
                            (2005, 201905, False, [1.0, 1.0]),
                            (2012, 201904, True, [1.0, 1.0]),
                            (2012, 202101, True, [1.0, 1.0])):
        coh_file(_cv, 1, _rs, sum(_rs), False, None,
                 cls=_vincls(_v, _p, _f))
    chk("    all-time totals are per vintage: loops / frozen / ++frozen",
        _cv[1]["vin_all"], {"2005": [4, 3, 1], "2012": [2, 2, 2]})
    chk("    and the month cells are keyed vintage|period, window applied",
        sorted(_cv[1]["vin_month"]),
        ["2005|201904", "2005|201905", "2012|201904"])
    print("     (202101 is outside the display window so it has no month")
    print("      cell, **and it is still in that vintage's all-time row** —")
    print("      a window on a table, not a filter on a population.)")
    chk("    an unfrozen loop counts in loops but not in frozen",
        _cv[1]["vin_month"]["2005|201905"], [2, 1, 0])
    _cn = {}
    coh_file(_cn, 1, [1.0, 1.0], 2.0, False, None,
             cls={"prof": {}, "months": 1, "exposure": 1, "redel": False,
                  "ra": False, "zero": False, "cure_year": 2020,
                  "cure_period": 202006})
    chk("    a loop with no frozen answer is not cut at all",
        (_cn[1].get("vin_all", {}), _cn[1].get("vin_month", {})), ({}, {}))

    _va, _bv, _mo = vin_split({"vin_all": _cv[1]["vin_all"],
                               "vin_month": _cv[1]["vin_month"]})
    chk("    vin_split reshapes to vintage -> period -> counts",
        (sorted(_bv), _mo, _bv["2005"][201904]),
        (["2005", "2012"], [201904, 201905], [2, 2, 1]))

    _pl = {"vin_all": _cv[1]["vin_all"], "vin_month": _cv[1]["vin_month"],
           "vin_window": [VIN_MONTH_LO, VIN_MONTH_HI]}
    #: 3 frozen in 201904 (two from 2005, one from 2012), of which 2 are
    #: `++`. **The denominator is frozen loops, not loops** — writing 4 here
    #: is what the first draft did, and the check caught it.
    _good = {"r2": {"months_2019": {
        "201904": {"frozen_pp": 2, "frozen_total": 3},
        "201905": {"frozen_pp": 0, "frozen_total": 1}}}}
    _bad = {"r2": {"months_2019": {
        "201904": {"frozen_pp": 2, "frozen_total": 3},
        "201905": {"frozen_pp": 9, "frozen_total": 1}}}}
    _out = []
    for _prod in (_good, _bad, {}):
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_vin({"rows": {str(NOISE_LENS[0]): _pl}}, _prod)
        finally:
            sys.stdout = _keep
        _out.append(_buf.getvalue())
    chk("    the cross-check against the prior artifact reads MATCH",
        ("MATCH" in _out[0]) and ("DO NOT MATCH" not in _out[0]), True)
    chk("    and it CAN fail, which is what makes it a check",
        "**DO NOT MATCH**" in _out[1], True)
    chk("    and a missing prior is said, not passed over",
        "no previous file" in _out[2], True)
    print("     (失效模式 18: pointing at a producer is necessary and not")
    print("      sufficient — the two sides have to be the same population,")
    print("      and §8·37's own 2019 table is the side with a producer.)")
    chk("    the thinnest vintage by frozen loops is named",
        "thinnest vintage by frozen loops: 2012" in _out[0], True)
    chk("    and every printed section says it carries no verdict",
        "No branch and no verdict here" in _out[0], True)

    print("\n  §8·38's servicing-assistance code:")

    def _arow(per):
        row = [None] * 8
        row[R_PERIOD] = per
        return tuple(row)

    chk("    assist_of keeps a listed code, a blank and a missing row apart",
        assist_of([_arow(202001), _arow(202002), _arow(202003)],
                  {202001: "F", 202002: ""}),
        ("F", "", None))
    chk("    an unreadable period is `row not found`, never a blank",
        (assist_of([_arow(-1)], {202001: "F"}),
         assist_of([_arow(202001)], None)), ((None,), (None,)))
    print("     ((blank) says the servicer reported no assistance;")
    print("      (row not found) says this file could not be asked. Folding")
    print("      them together is 失效模式 20, which §8·14·5 was entirely")
    print("      about. §11 item 6.)")

    def _asgrow(year, codes, ok=("F", "R", "T")):
        return {"prof": {}, "months": 1, "exposure": 1, "redel": False,
                "ra": False, "zero": False, "cure_year": year,
                "cure_period": year * 100 + 6,
                "assist": tuple(codes), "assist_codes": tuple(ok)}

    _da = cls_new()
    cls_file(_da, _asgrow(2020, ("", "F", "")))
    cls_file(_da, _asgrow(2020, ("", "", "")))
    cls_file(_da, _asgrow(2021, (None, "R", "T")))
    chk("    the census counts asked / assisted / unknown-row apart",
        (_da["asg_n"], _da["asg_any"], _da["asg_unk"]), (3, 2, 1))
    chk("    every raw value is enumerated, C0b, nothing lumped",
        _da["asg_code"],
        {"(blank)": 5, "(row not found)": 1, "F": 1, "R": 1, "T": 1})
    chk("    and which span row carried the code is kept, three named rows",
        (_da["asg_pos"], ASSIST_POS),
        ({"cure": 1, "delinq": 2}, ("anchor", "delinq", "cure")))
    chk("    the year table keeps loops and assisted apart",
        _da["asg_year"], {2020: [2, 1], 2021: [1, 1]})
    _dn = cls_new()
    cls_file(_dn, {"prof": {}, "months": 1, "exposure": 1, "redel": False,
                   "ra": False, "zero": False, "cure_year": 2020,
                   "cure_period": 202006})
    chk("    with no code map the question is not put, and nothing is filed",
        (_dn["asg_n"], _dn["asg_code"], _dn["asg_year"]), (0, {}, {}))
    chk("    and omega_absorb's map defaults to absent, so other modes"
        " carry none",
        omega_absorb.__defaults__[-2:], (None, ()))

    def _asg(pp, pm):
        cls = {}
        for k, (n, hit) in (("++", pp), ("+-", pm)):
            d = cls_new()
            for j in range(n):
                cls_file(d, _asgrow(2020, ("", "F", "") if j < hit
                                    else ("", "", "")))
            cls[k] = d
        return assist_read(cls)

    chk("    §8·38·2's four branches each fire on their own fixture",
        [_asg(*x)["assist_verdict"] for x in
         (((100, 30), (100, 10)), ((100, 10), (100, 30)),
          ((100, 20), (200, 40)), ((100, 0), (100, 0)))],
        ["pp_more_assisted", "pp_less_assisted", "code_does_not_separate",
         "no_assisted_loops"])
    chk("    and the tie is exact on unequal denominators",
        _asg((100, 20), (200, 40))["assist_cmp"], 0)
    chk("    a population never asked reads not_asked, which is not a zero",
        assist_read({"++": cls_new(), "+-": cls_new()})["assist_verdict"],
        "not_asked")
    print("     (`no_assisted_loops` had to stay a live branch: the b8like")
    print("      population was never screened on this column, so whether it")
    print("      holds a single assisted loop is unmeasured. A branch that")
    print("      cannot fire is §11 item 13; this one can, and might.)")

    for _tag, _args, _want in (
            ("first", ((100, 30), (100, 10)), "FIRST BRANCH"),
            ("second", ((100, 10), (100, 30)), "SECOND BRANCH"),
            ("third", ((100, 20), (200, 40)), "THIRD BRANCH"),
            ("fourth", ((100, 0), (100, 0)), "FOURTH BRANCH")):
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_assist({"rows": {str(NOISE_LENS[0]): _asg(*_args)}})
        finally:
            sys.stdout = _keep
        _t38 = _buf.getvalue()
        _o = {"FIRST BRANCH", "SECOND BRANCH", "THIRD BRANCH",
              "FOURTH BRANCH"} - {_want}
        chk("    print_assist reads the %s branch for §8·38·2" % _tag,
            ("§8·38·2 -> " + _want in _t38)
            and not any("§8·38·2 -> " + o in _t38 for o in _o), True)
    chk("    and every branch refuses to join the code to §8·34's hazard",
        "needs its own registration" in _t38, True)

    #: 規矩 19: both sections ride on `--noise` and touch nothing else.
    _oa38 = omega_new_acc()
    _b438 = json.dumps(omega_payload(_oa38), sort_keys=True)
    _c38 = {}
    coh_file(_c38, 1, [1.0, 1.0], 2.0, False, None,
             cls=_asgrow(2020, ("", "F", "")))
    _oa38["b8like"]["coh"] = _c38
    chk("    filling §8·37 and §8·38's subtrees leaves omega_payload alone",
        json.dumps(omega_payload(_oa38), sort_keys=True) == _b438, True)


    # --o18join, §8·28. Registered before the code.
    print("\n  --o18join, §8·28's loan-level join:")

    chk("    overlap_read is one body: §8·26 and §8·28 read the same 2x2",
        (overlap_read(20, 10, 10, 10, "x", "y", "same")["overlap_verdict"],
         overlap_read(20, 10, 10, 0, "x", "y", "same")["overlap_verdict"],
         overlap_read(20, 10, 10, 5, "x", "y", "same")["overlap_verdict"]),
        ("contained", "disjoint", "mixed"))
    #: **The defect §8·28 found in its own criteria, now a printed object.**
    #: At margins summing above 1, inclusion and exclusion put a floor under
    #: the corner cell and the disjoint branch cannot fire; §8·28 landed
    #: `mixed` under exactly that condition. Registration cannot check this
    #: (margins are not known before the run) but the read can.
    _rt = overlap_read(100, 40, 90, 35, "x", "y", "same")
    chk("    margins summing above 1 put a floor under the corner cell",
        (_rt["a_floor"], _rt["disjoint_reachable"],
         _rt["branches_reachable"]), (30, False, 2))
    _rl = overlap_read(100, 10, 20, 5, "x", "y", "same")
    chk("    and margins summing below 1 leave all three live",
        (_rl["a_floor"], _rl["disjoint_reachable"],
         _rl["branches_reachable"]), (0, True, 3))
    chk("    an empty side takes the contained branch out instead",
        overlap_read(100, 0, 20, 0, "x", "y", "same")["contained_reachable"],
        False)
    chk("    the ceiling is min of the two margins, which containment needs",
        (_rt["a_ceiling"], _rl["a_ceiling"]), (40, 10))
    print("     (§8·28 landed `mixed` with the disjoint branch arithmetically")
    print("      excluded and I did not notice until the numbers came back.")
    print("      A branch that cannot fire is §11 item 13 in a criterion's")
    print("      clothes, so the count of live branches now prints beside")
    print("      every 2x2 this file reads.)")

    chk("    and it names the direction from the edge that saturates",
        (overlap_read(20, 5, 10, 5, "x_in_y", "y_in_x", "same")
         ["contained_direction"],
         overlap_read(20, 10, 5, 5, "x_in_y", "y_in_x", "same")
         ["contained_direction"],
         overlap_read(20, 5, 5, 5, "x_in_y", "y_in_x", "same")
         ["contained_direction"]),
        ("x_in_y", "y_in_x", "same"))

    class _O18:
        """A stand-in for `b10_o18_null`, and it stands in for the CONSTANTS
        too, which is the part that matters: the real run imports the module
        and this fixture must not diverge from it silently."""
        AGE_SPLIT = 8
        P_ASSIST = 29
        ASSIST_CODES = ("F", "R", "T")

        @staticmethod
        def parse_delinq(s):
            s = s.strip()
            return int(s) if len(s) == 2 and s.isdigit() else None

        @staticmethod
        def next_period(p):
            y, m = divmod(p, 100)
            return y * 100 + m + 1 if m < 12 else (y + 1) * 100 + 1

        @staticmethod
        def delta_bucket(d):
            return "ge+2" if d >= 2 else ("+1" if d == 1 else "le0")

        @staticmethod
        def population_of(age_ok, coded):
            if not age_ok:
                return "grid_age_lt8"
            return "coded_age_ge8" if coded else "residue"

    def _orow(per, dq, age, upb):
        return (per, dq, "", age, upb, 6.0, 300, 0.0)

    #: The O18 month: two consecutive periods, both ages >= 8, no assistance
    #: code, both delinquency values two digits, the balance identical and the
    #: counter not rising.
    _o_hit = [_orow(200001, "01", 20, 100_000.0),
              _orow(200002, "01", 21, 100_000.0)]
    chk("    the O18 month fires on the shape b10_o18_null describes",
        o18_months(_o_hit, ["", ""], _O18), (1, 1, 1))
    chk("    a moving balance is not frozen and not an O18 month",
        o18_months([_orow(200001, "01", 20, 100_000.0),
                    _orow(200002, "01", 21, 99_000.0)], ["", ""], _O18),
        (0, 0, 1))
    chk("    a rising counter is +1, not le0",
        o18_months([_orow(200001, "01", 20, 100_000.0),
                    _orow(200002, "02", 21, 100_000.0)], ["", ""], _O18),
        (0, 1, 1))
    chk("    an assistance code takes the month out of the residue",
        [o18_months(_o_hit, ["", c], _O18)[0] for c in _O18.ASSIST_CODES],
        [0, 0, 0])
    chk("    and a code outside the three does not",
        o18_months(_o_hit, ["", "Z"], _O18)[0], 1)
    chk("    age below the split is the grid population, not the residue",
        o18_months([_orow(200001, "01", 6, 100_000.0),
                    _orow(200002, "01", 7, 100_000.0)], ["", ""], _O18),
        (0, 1, 1))
    chk("    a gap in the periods is not a pair at all",
        o18_months([_orow(200001, "01", 20, 100_000.0),
                    _orow(200003, "01", 22, 100_000.0)], ["", ""], _O18),
        (0, 0, 0))
    chk("    and December to January is a pair, which off-by-one gets wrong",
        o18_months([_orow(200012, "01", 20, 100_000.0),
                    _orow(200101, "01", 21, 100_000.0)], ["", ""], _O18),
        (1, 1, 1))
    #: §41.1. `RA` and blanks are counted apart on the other side and must not
    #: arrive here as a delta of zero — that would put the carrier's own
    #: missing values on the "the borrower paid" side of the join.
    chk("    RA and blank are not a delta of zero",
        [o18_months([_orow(200001, x, 20, 100_000.0),
                     _orow(200002, "01", 21, 100_000.0)], ["", ""], _O18)[0]
         for x in ("RA", "", "  ", "XX")], [0, 0, 0, 0])
    print("     (nine shapes, and the last four are §41.1's: an unnameable")
    print("      status is not a payment. That is the same discipline §8·25·3")
    print("      put a node in for on the other carrier.)")

    def _oj(cells, split=None, extra=None):
        acc = o18join_new_acc()
        for k, n in cells.items():
            acc["cell"][k] = n
        acc["loans_with_loop"] = sum(cells.values())
        acc["loans"] = acc["loans_with_loop"] + (extra or 0)
        for k, n in (split or {}).items():
            acc["split"][k] = n
        return o18join_payload(acc)

    chk("    the 2x2's four cells partition the joined loans",
        _oj({"AB": 3, "Ab": 4, "aB": 5, "ab": 6})["n_joined"], 18)
    chk("    A inside B reads FIRST BRANCH and names the direction",
        (_oj({"AB": 5, "Ab": 0, "aB": 5, "ab": 5})["overlap_verdict"],
         _oj({"AB": 5, "Ab": 0, "aB": 5, "ab": 5})["contained_direction"]),
        ("contained", "A inside B"))
    chk("    B inside A reads it the other way",
        _oj({"AB": 5, "Ab": 5, "aB": 0, "ab": 5})["contained_direction"],
        "B inside A")
    chk("    an empty corner reads SECOND BRANCH",
        _oj({"AB": 0, "Ab": 5, "aB": 5, "ab": 5})["overlap_verdict"],
        "disjoint")
    chk("    and anything else is mixed",
        _oj({"AB": 3, "Ab": 4, "aB": 5, "ab": 6})["overlap_verdict"], "mixed")

    for _tag, _pl, _want in (
            ("first", _oj({"AB": 5, "Ab": 0, "aB": 5, "ab": 5}), "FIRST"),
            ("second", _oj({"AB": 0, "Ab": 5, "aB": 5, "ab": 5}), "SECOND"),
            ("third", _oj({"AB": 3, "Ab": 4, "aB": 5, "ab": 6}), "THIRD")):
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_o18join(_pl)
        finally:
            sys.stdout = _keep
        _tj = _buf.getvalue()
        _o = {"FIRST", "SECOND", "THIRD"} - {_want}
        chk(f"    print_o18join reads the {_tag} branch for §8·28·3",
            (f"§8·28·3 -> {_want} BRANCH" in _tj)
            and not any(f"§8·28·3 -> {o} BRANCH" in _tj for o in _o), True)
    _buf, _keep = io.StringIO(), sys.stdout
    sys.stdout = _buf
    try:
        print_o18join(_oj({"AB": 5, "Ab": 0, "aB": 5, "ab": 5}))
    finally:
        sys.stdout = _keep
    _tj = _buf.getvalue()
    #: **Match on phrases that live on ONE printed line.** The first version
    #: looked for "reporting behaviour rather than borrower", which the
    #: printer hand-wraps across two `print` calls, so the substring never
    #: existed in the output and the check read False on correct text. A test
    #: on hand-wrapped prose has to be written against the wrapping.
    chk("    each branch carries §8·28·4's pre-written meaning with it",
        ("behaviour rather than borrower behaviour" in _tj)
        and ("does not choose between (a) borrowers paying" in _tj), True)
    _ojblob = json.dumps({"stage": "B10", "step": "o18join",
                          **_oj({"AB": 3, "Ab": 4, "aB": 5, "ab": 6})},
                         indent=2, sort_keys=True)
    print(f"     printer and json.dumps both exercised, {len(_ojblob):,} bytes")

    #: 設計件 §8·28·1's own instruction, enforced: the constants come from
    #: `b10_o18_null` and this fixture must agree with it. Where the module
    #: will not import, the skip is printed rather than passed over.
    try:
        import b10_o18_null as _REALO                # noqa: E402
    except Exception as _e:                          # pragma: no cover
        _REALO = None
        print(f"    §8·28·1's constant check SKIPPED: b10_o18_null would not "
              f"import ({type(_e).__name__}).")
    if _REALO is not None:
        chk("    the fixture's O18 constants match the real module's",
            (_REALO.AGE_SPLIT, _REALO.P_ASSIST, tuple(_REALO.ASSIST_CODES)),
            (_O18.AGE_SPLIT, _O18.P_ASSIST, _O18.ASSIST_CODES))
        chk("    and so do its four helpers, over an exhaustive little domain",
            ([_REALO.parse_delinq(x) for x in ("01", "RA", "", "99", "1")],
             [_REALO.next_period(p) for p in (200001, 200012, 199912)],
             [_REALO.delta_bucket(d) for d in (-3, -1, 0, 1, 2, 9)],
             [_REALO.population_of(a, c)
              for a in (True, False) for c in (True, False)]),
            ([_O18.parse_delinq(x) for x in ("01", "RA", "", "99", "1")],
             [_O18.next_period(p) for p in (200001, 200012, 199912)],
             [_O18.delta_bucket(d) for d in (-3, -1, 0, 1, 2, 9)],
             [_O18.population_of(a, c)
              for a in (True, False) for c in (True, False)]))
        print("     (the stand-in is checked against the real module rather")
        print("      than trusted. This station has paid once already for")
        print("      taking a stub's constants for the real ones.)")

    # --pgrid, §8·26. Registered before the code.
    print("\n  --pgrid, §8·26's 2x2 and the grid bound:")

    def _pg(rows):
        """rows: (P_orig, P_sub, derived, u0). Returns the payload."""
        pg = pgrid_new_acc()
        for r in rows:
            pgrid_file(pg, *r)
        return pgrid_payload(pg)

    #: `1e-6` is the published definition, so the fixture has to straddle it
    #: rather than sit comfortably on one side.
    _P = 1000.0
    _same = (_P, _P * (1 + 1e-9), True, 200_000.0)     # consistent
    _diff = (_P, _P * (1 + 1e-3), True, 200_000.0)     # not consistent

    _r = _pg([_same] * 10 + [(_P, _P * (1 + 1e-9), False, 200_000.0)] * 0
             + [_diff] * 10)
    chk("    the 2x2's four cells partition the paired loops",
        sum(_r["cell"].values()), _r["n_paired"])
    chk("    consistency is judged at the published 1e-6, not near it",
        (_r["cell"]["cq"], _r["cell"]["xq"]), (10, 10))

    #: **Containment, both directions, and the identical case named apart.**
    #: **Both margins have to sit below 1 for the lift to say anything.** The
    #: first version of this fixture had every loop qualifying, so `p_q` was
    #: 1.0 and `lift_if_contained` collapsed onto the independence anchor at
    #: 1.0 — the two anchors coincided and `lift_nearer` had nothing to
    #: compare. That is correct behaviour and a useless fixture, so the third
    #: block below is what keeps `p_q` off the ceiling.
    _cont = _pg([_same] * 10 + [(_P, _P * (1 + 1e-3), True, 2e5)] * 5
                + [(_P, _P * (1 + 1e-3), False, 2e5)] * 5)
    chk("    consistent inside qualified reads FIRST BRANCH",
        (_cont["overlap_verdict"], _cont["contained_direction"]),
        ("contained", "consistent inside qualified"))
    chk("    and its margins are both off the ceiling, so the lift can speak",
        (_cont["p_consistent"], _cont["p_qualified"]), (0.5, 0.75))
    _cont2 = _pg([_same] * 10 + [(_P, _P * (1 + 1e-9), False, 2e5)] * 5)
    chk("    and qualified inside consistent reads it the other way",
        (_cont2["overlap_verdict"], _cont2["contained_direction"]),
        ("contained", "qualified inside consistent"))
    _ident = _pg([_same] * 10 + [(_P, _P * (1 + 1e-3), False, 2e5)] * 5)
    chk("    two identical sets are named as identical, not as one direction",
        _ident["contained_direction"], "the two sets are identical")
    _disj = _pg([(_P, _P * (1 + 1e-9), False, 2e5)] * 10
                + [(_P, _P * (1 + 1e-3), True, 2e5)] * 10)
    chk("    an empty corner cell reads SECOND BRANCH",
        (_disj["overlap_verdict"], _disj["cell"]["cq"]), ("disjoint", 0))
    _mix = _pg([_same] * 6 + [(_P, _P * (1 + 1e-9), False, 2e5)] * 4
               + [(_P, _P * (1 + 1e-3), True, 2e5)] * 4
               + [(_P, _P * (1 + 1e-3), False, 2e5)] * 6)
    chk("    and anything else is mixed, which is a reading not a failure",
        _mix["overlap_verdict"], "mixed")

    #: **The two lift anchors are computed from the margins.** On the mixed
    #: fixture the margins are 0.5 and 0.5, so `lift_if_contained` must be 2.0
    #: and a perfectly independent table must read a lift of 1.
    chk("    lift_if_independent is 1 and lift_if_contained comes from margins",
        (_mix["lift_if_independent"], round(_mix["lift_if_contained"], 6)),
        (1.0, 2.0))
    chk("    an independent table reads lift 1 and is nearer that anchor",
        (round(_mix["lift"], 6), _mix["lift_nearer"]), (1.2, "independent"))
    chk("    and a contained table is nearer the contained anchor",
        (_cont["lift_nearer"], round(_cont["lift"], 6),
         round(_cont["lift_if_contained"], 6)), ("same", 1.333333, 1.333333))
    chk("    a saturated margin makes the two anchors coincide, and it says so",
        _pg([_same] * 10
            + [(_P, _P * (1 + 1e-3), True, 2e5)] * 5)["lift_nearer"],
        "anchors coincide")
    print(f"     mixed fixture: lift {_mix['lift']:.4f} against anchors "
          f"1.0000 / {_mix['lift_if_contained']:.4f} -> {_mix['lift_nearer']}")

    #: §8·26·2. The bound is `500/u0`, so the same `|dP|/P` is over or under
    #: depending on the loan. **That is what makes the separation test able to
    #: fail**, and a fixture where it cannot fail would test nothing.
    _under = (_P, _P * (1 + 1e-3), True, 200_000.0)   # 1e-3 vs 2.5e-3 -> under
    _over = (_P, _P * (1 + 1e-3), True, 1_000_000.0)  # 1e-3 vs 5e-4 -> over
    chk("    the same |dP|/P is over on one loan and under on another",
        (_pg([_under])["n_over"], _pg([_over])["n_over"]), (0, 1))
    chk("    nothing over the bound reads FIRST BRANCH",
        _pg([_under] * 10)["tail_verdict"], "grid_explains_all")
    _sep = _pg([(_P, _P * (1 + 1e-4), True, 200_000.0)] * 10   # rel 1e-4 under
               + [(_P, _P * (1 + 1e-2), True, 200_000.0)] * 5)  # rel 1e-2 over
    chk("    two non-overlapping |dP|/P ranges read SECOND BRANCH",
        (_sep["tail_verdict"], _sep["separated"], _sep["n_over"]),
        ("two_populations", True, 5))
    #: **The over set's `rel` has to be SMALLER than the under set's**, or the
    #: ranges cannot overlap and this fixture just repeats the previous one.
    #: The first version used 1e-4 against a 5e-4 bound, which is under the
    #: bound, so it read zero exceedances and `grid_explains_all` — the
    #: opposite branch. Bound on the second group is 500/1e6 = 5e-4, so 8e-4
    #: is over it while still sitting below the first group's 1e-3.
    _ovl = _pg([(_P, _P * (1 + 1e-3), True, 200_000.0)] * 5     # 1e-3 under
               + [(_P, _P * (1 + 8e-4), True, 1_000_000.0)] * 5)  # 8e-4 over
    chk("    overlapping ranges read THIRD BRANCH, even with the same counts",
        (_ovl["tail_verdict"], _ovl["separated"], _ovl["n_over"]),
        ("mixed", False, 5))
    print("     (the last two fixtures have the SAME number of exceedances")
    print("      and different verdicts, so the branch is the separation and")
    print("      not the count. A count-based line would call them the same.)")

    #: §8·26·3 item 2: unreadable origination balance is its own bucket.
    _nou = _pg([_same] * 5 + [(_P, _P * (1 + 1e-3), True, None)] * 3
               + [(_P, _P * (1 + 1e-3), True, 0.0)] * 2)
    chk("    an unreadable u0 is counted apart, not as `not over`",
        (_nou["no_u0"], _nou["n_over"], _nou["ratio_n"]), (5, 0, 5))
    chk("    but it still lands in the 2x2, which needs no u0",
        _nou["n_paired"], 10)
    chk("    a missing payment lands in neither, and is counted",
        (_pg([(None, _P, True, 2e5), (_P, None, True, 2e5)])["no_pair"],
         _pg([(None, _P, True, 2e5)])["n_paired"]), (2, 0))
    print("     (`no_pair`, `no_u0` and the four cells are three different")
    print("      refusals and three different counters. §11 item 6.)")

    for _tag, _pl, _want in (("first", _pg([_same] * 10 + [_diff] * 5),
                              "FIRST"),
                             ("second", _disj, "SECOND"),
                             ("third", _mix, "THIRD")):
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_pgrid(_pl)
        finally:
            sys.stdout = _keep
        _tp = _buf.getvalue()
        _o = {"FIRST", "SECOND", "THIRD"} - {_want}
        chk(f"    print_pgrid reads the {_tag} branch for §8·26·1",
            (f"§8·26·1 -> {_want} BRANCH" in _tp)
            and not any(f"§8·26·1 -> {o} BRANCH" in _tp for o in _o), True)
    for _tag, _pl, _want in (("first", _pg([_under] * 10), "FIRST"),
                             ("second", _sep, "SECOND"),
                             ("third", _ovl, "THIRD")):
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_pgrid(_pl)
        finally:
            sys.stdout = _keep
        _tp = _buf.getvalue()
        _o = {"FIRST", "SECOND", "THIRD"} - {_want}
        chk(f"    print_pgrid reads the {_tag} branch for §8·26·2",
            (f"§8·26·2 -> {_want} BRANCH" in _tp)
            and not any(f"§8·26·2 -> {o} BRANCH" in _tp for o in _o), True)
    _pblob = json.dumps({"stage": "B10", "step": "pgrid", **_mix},
                        indent=2, sort_keys=True)
    print(f"     printer and json.dumps both exercised, {len(_pblob):,} bytes")

    chk("    an empty accumulator reads no verdict rather than a false one",
        (_pg([])["overlap_verdict"], _pg([])["lift"]), ("mixed", None))

    #: **規矩 19, run rather than asserted, and at zero scan cost.** §8·26 puts
    #: a new subtree in `omega_new_acc`, and the claim is that `b10_omega.json`
    #: and `b10_noise.json` do not move because no payload reads it. That claim
    #: is checkable here: fill the subtree and diff the payloads. Asking for
    #: two 27-archive re-scans to learn the same thing would cost hours and
    #: prove less, because it would only cover the archives on this disk.
    _oa = omega_new_acc()
    _b4 = json.dumps(omega_payload(_oa), sort_keys=True)
    _nb4 = json.dumps(noise_payload(noise_new_acc(), _oa), sort_keys=True)
    for _r in [_same] * 7 + [_diff] * 3 + [(None, _P, True, 2e5)]:
        pgrid_file(_oa["pgrid"], *_r)
    chk("    filling §8·26's subtree leaves omega_payload byte for byte",
        json.dumps(omega_payload(_oa), sort_keys=True) == _b4, True)
    chk("    and noise_payload too, which reads the same accumulator",
        json.dumps(noise_payload(noise_new_acc(), _oa),
                   sort_keys=True) == _nb4, True)
    chk("    while the subtree really did fill, so neither test is vacuous",
        (_oa["pgrid"]["n"], _oa["pgrid"]["no_pair"],
         sum(_oa["pgrid"]["cell"].values())), (11, 1, 10))
    print("     (規矩 19 wants the comparison RUN. This is it: the two files")
    print("      §8·26 could have disturbed are produced by two functions, and")
    print("      both are shown to ignore the new subtree on a filled one.)")

    #: §8·27, registered before the code.
    print("\n  --pgrid, §8·27's horizon leg:")

    def _hrow(age, rem, bal=200_000.0, rate=6.0):
        return (200001, "00", "", age, bal, rate, rem, 0.0)

    def _cp(b, i, n):
        """The level payment, written here **only for the fixture**."""
        if i <= 0:
            return b / n
        return b * i / (1.0 - (1.0 + i) ** (-n))

    chk("    substitution_payment's override changes only the horizon",
        (round(substitution_payment(_hrow(60, 300), _cp), 6),
         round(substitution_payment(_hrow(60, 300), _cp, n_override=300), 6)),
        (round(substitution_payment(_hrow(60, 300), _cp), 6),) * 2)
    chk("    and a different horizon really does give a different payment",
        substitution_payment(_hrow(60, 300), _cp)
        != substitution_payment(_hrow(60, 300), _cp, n_override=240), True)
    chk("    a non-positive override is refused like a non-positive rem",
        substitution_payment(_hrow(60, 300), _cp, n_override=0), None)

    def _pgh(rows):
        """rows: (P_orig, P_sub, derived, u0, t0, term)."""
        pg = pgrid_new_acc()
        for r in rows:
            pgrid_file(pg, r[0], r[1], r[2], r[3], t0=r[4], term=r[5],
                       contract_payment=_cp)
        return pgrid_payload(pg)

    #: A loan exactly on schedule: age 60, rem 300, term 360 -> h = 0, and the
    #: substitution on either horizon is the same number.
    _t_ok = _hrow(60, 300)
    _P_ok = substitution_payment(_t_ok, _cp)
    _h0 = _pgh([(_P_ok, _P_ok, True, 200_000.0, _t_ok, 360)] * 5)
    chk("    an on-schedule loan reads h = 0 and never exceeds the bound",
        (_h0["h_zero"], _h0["h_distinct"], _h0["n_over_h"], _h0["n_over"]),
        (5, 1, 0, 0))
    chk("    and with nothing over to start with there is NO READING",
        _h0["horizon_verdict"], "no_reading")
    print("     (a correction cannot remove what was not there. That is why")
    print("      the empty case is named apart from the first branch.)")

    #: **The horizon is the whole cause**: `rem` is reported two months long,
    #: so `P_sub` is computed on 302 while `P_orig` amortises 300. Correcting
    #: to `term - age` puts it back and the exceedance goes away.
    _t_lag = _hrow(60, 302)
    _P_lag = substitution_payment(_t_lag, _cp)
    _all = _pgh([(_P_ok, _P_lag, True, 200_000.0, _t_lag, 360)] * 5)
    chk("    a horizon-only defect reads h != 0 on every loop",
        (_all["h_distinct"], list(_all["h_hist"])), (1, ["2"]))
    chk("    it exceeds the bound on the reported horizon",
        _all["n_over"], 5)
    chk("    and the fixed horizon rescues every one -> FIRST BRANCH",
        (_all["n_over_h"], _all["rescued"], _all["horizon_verdict"]),
        (0, 5, "horizon_is_all"))

    #: **The horizon is innocent**: h = 0 on every loop and the balance is the
    #: one that is off, so correcting the horizon changes nothing at all.
    _t_cur = _hrow(60, 300, bal=150_000.0)
    _P_cur = substitution_payment(_t_cur, _cp)
    _none = _pgh([(_P_ok, _P_cur, False, 200_000.0, _t_cur, 360)] * 5)
    chk("    a balance-only defect reads h = 0 on every loop",
        (_none["h_zero"], _none["h_distinct"]), (5, 1))
    chk("    and the fixed horizon rescues none -> SECOND BRANCH",
        (_none["n_over"], _none["n_over_h"], _none["rescued"],
         _none["newly_over"], _none["horizon_verdict"]),
        (5, 5, 0, 0, "horizon_is_none"))
    print("     (h == 0 everywhere and the exceedance survives untouched. The")
    print("      two fixtures differ ONLY in which field is wrong, and the")
    print("      branch follows the field. That is what makes it a test.)")

    _mixh = _pgh([(_P_ok, _P_lag, True, 200_000.0, _t_lag, 360)] * 5
                 + [(_P_ok, _P_cur, False, 200_000.0, _t_cur, 360)] * 5)
    chk("    both together read THIRD BRANCH with the share printed",
        (_mixh["horizon_verdict"], _mixh["rescued"],
         round(_mixh["rescued_share"], 6)), ("mixed", 5, 0.5))
    #: §8·27·2 item 2, all three of its outcomes. **`None` is not `False`**:
    #: with nothing on the under side the question has no two sets to ask
    #: about, and the empty set is vacuously disjoint from everything, which
    #: would read as the strongest possible evidence for the horizon.
    chk("    with nothing under the bound, disjointness cannot be asked",
        (_mixh["h_sets_disjoint"], sorted(_mixh["h_over_hist"])),
        (None, ["0", "2"]))
    _under_ok = (_P_ok, _P_ok, True, 2e5, _t_ok, 360)
    _disjh = _pgh([(_P_ok, _P_lag, True, 2e5, _t_lag, 360)] * 5
                  + [_under_ok] * 5)
    chk("    h = 2 over and h = 0 under reads disjoint",
        (_disjh["h_sets_disjoint"], sorted(_disjh["h_over_hist"]),
         sorted(_disjh["h_under_hist"])), (True, ["2"], ["0"]))
    _ovlh = _pgh([(_P_ok, _P_cur, False, 2e5, _t_cur, 360)] * 5
                 + [_under_ok] * 5)
    chk("    and h = 0 on both sides reads not disjoint",
        (_ovlh["h_sets_disjoint"], sorted(_ovlh["h_over_hist"]),
         sorted(_ovlh["h_under_hist"])), (False, ["0"], ["0"]))
    print("     (disjoint / not disjoint / cannot be asked, three outcomes and")
    print("      three fixtures. §8·27·2 item 2 calls disjointness the")
    print("      strongest shape a horizon cause has, so it must not be")
    print("      reachable by an empty side.)")

    #: §8·27·3 items 1 and 2: three different refusals, three counters.
    _t_past = _hrow(400, 10)
    _bad = _pgh([(_P_ok, _P_ok, True, 2e5, None, 360),
                 (_P_ok, _P_ok, True, 2e5, _t_ok, None),
                 (_P_ok, _P_ok, True, 2e5, _hrow(None, 300), 360),
                 (_P_ok, substitution_payment(_t_past, _cp), True, 2e5,
                  _t_past, 360)])
    chk("    a missing t0, term or age is `h could not be asked`",
        _bad["h_bad"], 3)
    chk("    and a loan past its original term is its own count, not that one",
        (_bad["term_le_age"], _bad["h_n"]), (1, 1))
    print("     (h_bad, term_le_age and no_ph are three refusals and three")
    print("      counters. §8·27·3, and §11 item 6 underneath it.)")

    for _tag, _pl, _want in (("first", _all, "FIRST"),
                             ("second", _none, "SECOND"),
                             ("third", _mixh, "THIRD")):
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_pgrid(_pl)
        finally:
            sys.stdout = _keep
        _tp = _buf.getvalue()
        _o = {"FIRST", "SECOND", "THIRD"} - {_want}
        chk(f"    print_pgrid reads the {_tag} branch for §8·27·1",
            (f"§8·27·1 -> {_want} BRANCH" in _tp)
            and not any(f"§8·27·1 -> {o} BRANCH" in _tp for o in _o), True)
    _buf, _keep = io.StringIO(), sys.stdout
    sys.stdout = _buf
    try:
        print_pgrid(_h0)
    finally:
        sys.stdout = _keep
    chk("    and the empty case prints NO READING, not a branch",
        ("§8·27·1 -> NO READING" in _buf.getvalue())
        and not any(f"§8·27·1 -> {o} BRANCH" in _buf.getvalue()
                    for o in ("FIRST", "SECOND", "THIRD")), True)

    #: 規矩 19 for §8·27: `substitution_payment` grew a parameter, and the four
    #: files that call it through `loop_payments` must not move. **Compared,
    #: not asserted**: the same row through the default path must give the
    #: identical float it gave before the parameter existed.
    chk("    §8·23's loop_payments still gets the un-overridden payment",
        loop_payments([_t_ok, _t_ok], {"t_A": 0, "t_B": 1}, None, _cp)["sub"],
        (substitution_payment(_t_ok, _cp), substitution_payment(_t_ok, _cp)))

    # --gridvar, §8·25. Registered before the code.
    print("\n  --gridvar, §8·25's ladder on the second carrier:")

    chk("    defer_xtab_key: column 12 unreadable is not a cell",
        defer_xtab_key(None, "P"), None)
    chk("    every readable pair lands in a declared cell",
        sorted({defer_xtab_key(c, f)
                for c in (-1.0, 0.0, 1e-9, 5.0)
                for f in ("P", "C", "", "X", "p", "  ")}),
        sorted(GV_DEFER_CELLS))
    chk("    zero on column 12 is the negative side, not unreadable",
        defer_xtab_key(0.0, "P"), "col12-_f25+")
    chk("    and a lower-case p is a different value, not a P",
        defer_xtab_key(1.0, "p"), "col12+_f25-")
    print("     (§8·14·5: blank and zero are structurally opposite on column")
    print("      12, so the unreadable rows stand outside the table rather")
    print("      than being counted as `not positive`. 失效模式 20.)")

    try:
        sys.path.insert(0, str(ROOT / "experiments"))
        import b10_support as _SUP                  # noqa: E402
        import b10_holonomy_ladder as _HL           # noqa: E402
        import numpy as _np                         # noqa: E402
        import zlib as _zlib                        # noqa: E402
        _gvwhy = None
    except Exception as _e:                         # pragma: no cover
        _SUP = _HL = _np = _zlib = None
        _gvwhy = f"{type(_e).__name__}: {_e}"

    if _SUP is None:
        print(f"    §8·25 SKIPPED here: the imports would not load ({_gvwhy}).")
        print("    cmd_gridvar imports the same modules at the top and refuses")
        print("    to read an archive without them. A skip is printed, never")
        print("    silent.")
    else:
        _ALPHA = ["00", "01", "09", "12", "90", "99", "RA", "XX", "R", "",
                  "0", "0A", "  ", "003"]
        chk("    state_delinq: two digits pass, RA passes, the rest are UNK",
            [state_delinq(x, _SUP) for x in _ALPHA],
            ["00", "01", "09", "12", "90", "99", "RA"] + [_SUP.UNK] * 7)
        _tal = Counter()
        for _x in _ALPHA:
            state_delinq(_x, _SUP, _tal)
        chk("    the tally holds the RAW value, so the alphabet enumerates",
            (_tal["XX"], _tal["RA"], _tal[""], len(_tal)), (1, 1, 1, 14))
        print("     (C0b: every value it saw, not the ones it expected. §8·15")
        print("      cost this station a re-run for exactly the other habit.)")

        _gd = dict(_SUP.GRIDS)
        chk("    the ladder's rungs all exist in b10_support.GRIDS",
            [g in _gd for g in _HL.VAR_LADDER], [True] * 3)
        chk("    UNK is its own node on every rung",
            [_gd[g](_SUP.UNK) for g in _HL.VAR_LADDER], [_SUP.UNK] * 3)
        chk("    and RA is its own node, counted apart from it",
            [_gd[g](_SUP.RA) for g in _HL.VAR_LADDER], [_SUP.RA] * 3)
        chk("    a raw unnameable string WOULD have folded, which is the point",
            (_gd["g1"]("XX"), _gd["g2"]("XX")), ("90+", "delinquent"))
        print("     (the last line is §8·15's failure mode written as a test:")
        print("      an unnamed value that keeps its raw form gets read as a")
        print("      deep delinquency by g1 and as delinquent by g2. §8·25·3")
        print("      gives it a node BEFORE it bites, not after.)")

        #: The fixture is the shape §8·22·9 measured: Freddie writes the
        #: modification flag on the cure row, so `t_M == t_B` and the onset row
        #: reads `00`. `find_loops_rows` is called for real; the indices are
        #: B8's, not this test's.
        def _gvrow(per, dq, mf, upb=100_000.0, rem=300, dfr=0.0):
            return (per, dq, mf, 10, upb, 6.0, rem, dfr)

        #: **The leading current row is not decoration.** `find_loops_rows`
        #: refuses a window whose `t_A` is the loan's first row
        #: (`departure_is_first_row`), and the first draft of this fixture
        #: landed exactly there and read `ok` as False. That is the second
        #: time this station has written that fixture; the check that caught
        #: it both times is `all(rec["ok"].values())`, which is why it is
        #: asserted here rather than assumed.
        _late = [_gvrow(200001, "00", ""), _gvrow(200002, "00", ""),
                 _gvrow(200003, "01", ""), _gvrow(200004, "00", "Y")]
        _lp = find_loops_rows(_late, ("Y", "P"))[0]
        chk("    the fixture is one kept loop with t_M == t_B",
            (len(_lp), _lp[0]["t_A"], _lp[0]["t_M"], _lp[0]["t_B"],
             all(_lp[0]["ok"].values())), (1, 1, 3, 3, True))
        _sr, _sq, _atM = gridvar_states(_late, _lp[0], _SUP)
        chk("    gridvar_states reads the onset row BEFORE relabelling it",
            (_sr, _atM, _sq), ("00", "00", ["01", _SUP.MODIFIED]))
        _red = gridvar_reduce(_sr, _sq, _gd["g2"], _HL.reduce_closed_walk)
        chk("    and the walk is closed by hand, so an empty leg 3 is a cycle",
            (_red, _HL.is_cycle(_red)),
            (("current", "delinquent", "modified", "current"), True))
        print("     (the closing step is b10_holonomy_ladder's correction one.")
        print("      Without it this loop stops at `modified` and reads as no")
        print("      cycle at all, on the whole arm.)")

        #: The interior must read the delinquency field only. A stale flag two
        #: rows before the event is a mark, not a vertex; reading it invented a
        #: `current -> modified -> deferred -> current` class on the other side.
        _stale = [_gvrow(200001, "00", ""), _gvrow(200002, "00", ""),
                  _gvrow(200003, "01", "Y"), _gvrow(200004, "02", "Y"),
                  _gvrow(200005, "00", "Y")]
        _lps = find_loops_rows(_stale, ("Y", "P"))[0]
        _sr2, _sq2, _ = gridvar_states(_stale, _lps[0], _SUP)
        chk("    a flag that persists inside the window is not a vertex",
            (_sq2, all(_lps[0]["ok"].values())),
            ([_SUP.MODIFIED, "02", "00"], True))
        chk("    and the event sits at B8's t_M, by index and by arm",
            (_lps[0]["t_M"], _lps[0]["arm"]), (2, "mod"))

        #: The out-and-back. A one-month window whose only interior row is the
        #: event reduces to a single node, and a single node is not a cycle.
        _oab = [_gvrow(200001, "00", ""), _gvrow(200002, "00", ""),
                _gvrow(200003, "01", "Y"), _gvrow(200004, "00", "")]
        _lpo = find_loops_rows(_oab, ("Y", "P"))[0]
        _sr3, _sq3, _ = gridvar_states(_oab, _lpo[0], _SUP)
        _red3 = gridvar_reduce(_sr3, _sq3, _gd["g2"],
                               _HL.reduce_closed_walk)
        chk("    an out-and-back reduces to one node and is not a cycle",
            (_lpo[0]["t_M"], _lpo[0]["t_B"], all(_lpo[0]["ok"].values()),
             _red3, _HL.is_cycle(_red3)),
            (2, 3, True, ("current",), False))
        print("     (so `not_cycle` CAN fire, which is what makes counting it")
        print("      a count and not decoration. §11 item 13.)")

        #: `t_M` outside its own window raises rather than tallying. The
        #: fixture has to be built by hand because `find_loops_rows` cannot
        #: produce it, and that is exactly the argument for raising.
        try:
            gridvar_states(_late, {**_lp[0], "t_M": 9}, _SUP)
            _raised = False
        except RuntimeError:
            _raised = True
        chk("    t_M outside its own window raises, it does not tally",
            _raised, True)

        #: `gridvar_cell`. The label explains everything, the label explains
        #: nothing, and the two refusals.
        _seedy = _HL.PERM_SEED
        _perf = gridvar_cell([("a",)] * 40 + [("b",)] * 40,
                             [1.0] * 40 + [2.0] * 40,
                             _HL.r2_of, _HL.r2_null, _np, _seedy)
        chk("    a label that explains omega exactly reads R2 = 1",
            (round(_perf["r2"], 12), _perf["classes"], _perf["n"]),
            (1.0, 2, 80))
        chk("    and it sits above every draw of its own null",
            _perf["pct"], 1.0)
        _nul = gridvar_cell([("a",) if i % 2 == 0 else ("b",)
                             for i in range(80)],
                            [float(i) for i in range(80)],
                            _HL.r2_of, _HL.r2_null, _np, _seedy)
        chk("    a label uncorrelated with omega does not clear the null",
            _nul["pct"] < 0.95, True)
        chk("    a cell whose omega is constant has no referent, not a zero",
            gridvar_cell([("a",), ("b",)], [3.0, 3.0], _HL.r2_of,
                         _HL.r2_null, _np, _seedy)["r2"], None)
        chk("    and one point has nothing to explain either",
            gridvar_cell([("a",)], [3.0], _HL.r2_of, _HL.r2_null, _np,
                         _seedy)["n"], 1)
        chk("    the thinnest class is reported, not just the class count",
            gridvar_cell([("a",)] * 39 + [("b",)], [1.0] * 39 + [2.0],
                         _HL.r2_of, _HL.r2_null, _np, _seedy)["min_class"], 1)
        print(f"     perfect cell: R2 {_perf['r2']:.6f}  null p50 "
              f"{_perf['null_p50']:.6f}  E {_perf['E']:+.6f}  pct "
              f"{_perf['pct']:.3f}")
        print(f"     null cell:    R2 {_nul['r2']:.6f}  null p50 "
              f"{_nul['null_p50']:.6f}  E {_nul['E']:+.6f}  pct "
              f"{_nul['pct']:.3f}")

        #: The payload's shape must come from the ladder and not from the
        #: data. A grid with no cycles at all still prints its row.
        _gacc = gridvar_new_acc()
        _gacc["loans"], _gacc["loops"], _gacc["measurable"] = 3, 4, 4
        _gacc["alphabet"].update(["00", "01", "XX", "RA"])
        _gacc["defer_rows"] = 100
        _gacc["defer_col12_unreadable"] = 7
        for _k, _n in zip(GV_DEFER_CELLS, (10, 3, 5, 75)):
            _gacc["defer_xtab"][_k] = _n
        _gacc["not_cycle"]["g2"] = {"mod": 2, "defer": 1}
        _gacc["by_vintage"][2001] = {
            "g2": {"mod": {"keys": [("c", "d", "m", "c")] * 20
                                   + [("c", "m", "c", "c")] * 20,
                           "om": [1.0] * 20 + [2.0] * 20},
                   "defer": {"keys": [("c", "d", "f", "c")] * 20
                                     + [("c", "f", "c", "c")] * 20,
                             "om": [1.0] * 20 + [2.0] * 20}}}
        _gpl = gridvar_payload(_gacc, _HL.VAR_LADDER, _HL.r2_of, _HL.r2_null,
                               _HL.PERM_SEED, 99, _np, _zlib)
        chk("    every rung of the ladder gets a row, empty or not",
            sorted(_gpl["grids"]), sorted(_HL.VAR_LADDER))
        chk("    an empty rung reads n = 0, it does not vanish",
            (_gpl["grids"]["g1"]["mod"]["n"],
             _gpl["grids"]["g1"]["mod"]["r2"]), (0, None))
        chk("    not_cycle gets a row for every rung too",
            sorted(_gpl["not_cycle"]), sorted(_HL.VAR_LADDER))
        chk("    the alphabet splits named / RA / UNK three ways",
            (_gpl["alphabet"]["named_reads"], _gpl["alphabet"]["ra_reads"],
             _gpl["alphabet"]["unk_reads"]), (2, 1, 1))
        chk("    and the two definitions' agreement is a rate on the four",
            round(_gpl["defer_agree"], 6), round(85 / 93, 6))
        print("     (93 and not 100: the seven unreadable rows are outside the")
        print("      table by construction, and the denominator says so.)")

        _gblob = json.dumps({"stage": "B10", "step": "gridvar", **_gpl},
                            indent=2, sort_keys=True)
        print(f"     printer and json.dumps both exercised, "
              f"{len(_gblob):,} bytes")

        def _gv_mut(e_mod, e_def):
            """Set E(g0m) - E(g2) per arm without touching anything else."""
            q = {**_gpl, "grids": {g: {a: dict(_gpl["grids"][g][a])
                                       for a in ("mod", "defer")}
                                   for g in _gpl["ladder"]}}
            for arm, e in (("mod", e_mod), ("defer", e_def)):
                for g in q["ladder"]:
                    q["grids"][g][arm] = {**q["grids"][g][arm], "r2": 0.5,
                                          "null_p50": 0.1, "null_p95": 0.2,
                                          "pct": 0.5, "classes": 2,
                                          "min_class": 5, "n": 40,
                                          "top_path": "c -> d -> c",
                                          "E": 0.0}
                if e is None:
                    q["grids"]["g0m"][arm] = {**q["grids"]["g0m"][arm],
                                              "E": None, "r2": None}
                else:
                    q["grids"]["g0m"][arm] = {**q["grids"]["g0m"][arm],
                                              "E": e}
            return q

        for _tag, _em, _ed, _want in (("first", 0.2, 0.3, "FIRST"),
                                      ("second", -0.2, -0.1, "SECOND"),
                                      ("third", 0.2, -0.1, "THIRD")):
            _buf, _keep = io.StringIO(), sys.stdout
            sys.stdout = _buf
            try:
                print_gridvar(_gv_mut(_em, _ed))
            finally:
                sys.stdout = _keep
            _tg = _buf.getvalue()
            _oth = {"FIRST", "SECOND", "THIRD"} - {_want}
            chk(f"    print_gridvar reads the {_tag} branch for §8·25·4",
                (f"§8·25·4 -> {_want} BRANCH" in _tg)
                and not any(f"§8·25·4 -> {o} BRANCH" in _tg for o in _oth),
                True)
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_gridvar(_gv_mut(None, 0.3))
        finally:
            sys.stdout = _keep
        _tg = _buf.getvalue()
        chk("    an arm with no referent gives NO READING, not `mixed`",
            ("§8·25·4 -> NO READING" in _tg)
            and not any(f"§8·25·4 -> {o} BRANCH" in _tg
                        for o in ("FIRST", "SECOND", "THIRD")), True)
        print("     (a missing sign is a missing sign. Folding it into the")
        print("      mixed branch would put `no referent` and `the two arms")
        print("      disagree` in one bucket, which is §11 item 6.)")

        #: §8·25·6 item 2 has to be in the printer's own first branch, because
        #: that is the branch it exists to guard against being read backwards.
        _buf, _keep = io.StringIO(), sys.stdout
        sys.stdout = _buf
        try:
            print_gridvar(_gv_mut(0.2, 0.3))
        finally:
            sys.stdout = _keep
        chk("    the first branch carries §8·25·6's sentence with it",
            "not** §1.1 being closed" in _buf.getvalue(), True)

    _selftest_windows(fails)
    print("\n  " + ("FAILED: " + ", ".join(fails) if fails else "all pass."))
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--depth", action="store_true")
    ap.add_argument("--triangles", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--windows", action="store_true",
                    help="§9·7: the width curve on all five windows")
    ap.add_argument("--floor", action="store_true",
                    help="§8·16: the noise floor's construction half")
    ap.add_argument("--curve", action="store_true",
                    help="§8·17: does the CMT curve reach Freddie's horizons")
    ap.add_argument("--resid", action="store_true",
                    help="§8·19: the residual driver. No omega.")
    ap.add_argument("--signal", action="store_true",
                    help="§8·24: the triangle omega against the clean-cure "
                         "floor, raw and with leg 1's closed form removed.")
    ap.add_argument("--legs", action="store_true",
                    help="§8·23: omega on the loop windows, three legs. "
                         "Read against no floor.")
    ap.add_argument("--loops", action="store_true",
                    help="§8·22: the triangle loop windows and their census. "
                         "No omega.")
    ap.add_argument("--noise", action="store_true",
                    help="§8·21: B8-0b's floor, on never-delinquent windows. "
                         "Recomputes §8·20 on the same scan as a check.")
    ap.add_argument("--o18join", action="store_true",
                    help="§8·28: §8·26·2's over-bound loops against §12 "
                         "item 9's O18 months, joined on the loan.")
    ap.add_argument("--pgrid", action="store_true",
                    help="§8·26: the two items §8·20·8 left open in §12. "
                         "One scan, one population.")
    ap.add_argument("--gridvar", action="store_true",
                    help="§8·25: §8·12 re-asked on Freddie. The grid ladder "
                         "against omega on §8·22's loop windows.")
    ap.add_argument("--omega", action="store_true",
                    help="§8·20: the clean-cure loop sum, against B8's "
                         "closed form. No never-delinquent floor, no "
                         "triangle loop.")
    ap.add_argument("--rescan", action="store_true")
    ap.add_argument("--only", action="append")
    a = ap.parse_args(argv)
    if a.selftest:
        return cmd_selftest()
    if a.depth:
        return cmd_depth(a.only)
    if a.triangles:
        return cmd_triangles(a.only)
    if a.run:
        return cmd_run(a.only, a.rescan)
    if a.windows:
        return cmd_windows(a.only, a.rescan)
    if a.floor:
        return cmd_floor(a.only)
    if a.curve:
        return cmd_curve(a.only)
    if a.resid:
        return cmd_resid(a.only)
    if a.omega:
        return cmd_omega(a.only)
    if a.noise:
        return cmd_noise(a.only)
    if a.loops:
        return cmd_loops(a.only)
    if a.legs:
        return cmd_legs(a.only)
    if a.signal:
        return cmd_signal(a.only)
    if a.gridvar:
        return cmd_gridvar(a.only)
    if a.pgrid:
        return cmd_pgrid(a.only)
    if a.o18join:
        return cmd_o18join(a.only)
    print(__doc__)
    print("  --triangles and --run are §24.6 steps two and three. They are "
          "absent, not stubbed:\n  a stub that prints nothing reads like a step "
          "that found nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
