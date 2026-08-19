"""B8 verdict sheet: assemble ``results/b8_verdicts.json`` from the products on disk.

**Why this file exists.** ``RESULTS.md`` is a pure function of ``results/*.json``,
and B8 writes markdown. Every one of its thirty-one products is a ``.md``, so the
renderer's glob has never seen the stage at all: a reader of ``RESULTS.md`` goes
A0 to B9 and B8 is simply absent, while the roadmap still calls it
pre-registered. B8 is the strongest carrier in the programme, with eight
criteria landed and the residual sum computed on 49,649 modification loops and
35,659 deferral loops, and it was invisible in the file other work reads.

This is the same repair A7 needed and got: see ``a7_continuous_c.py
--verdicts``. There the measurement records are ``diagnostic_only`` and here they
are markdown, but the consequence is identical, so the fix is the same shape.

**What this file does and does not claim.** It does not re-measure anything.

**Strengthened 2026-08-19.** The guarantee used to be that every product backing
a criterion **exists**, which is satisfied by a file that has since been re-run
into different numbers. It is now that every number quoted in a verdict is
**printed by one of that verdict's own products**, checked by ``unbacked``: a
quote is backed when some value in a source, rendered to as many significant
digits as the quote carries, is the quote. No tolerance is invented for this.
Numbers that are not readings, such as the calendar years bounding a window,
are listed in ``EXEMPT`` with the reason each is not one, and nothing may be
silently outside both lists.

**Three defects fell out of turning that check on, and they are the argument for
having it.** ``SOURCES["B8-0b"]`` named ``b8_0a_gate.md`` alone while all three
of that verdict's floor values are printed by ``b8_0b_floor.md``; the existence
guarantee had been passing on the wrong file. B8-1 quoted a share as a
percentage the product never prints. And B8-4a's loading-monotonicity Spearman
is printed by **no product on disk at all**, which the detail string now says.

**What is still weaker than A7's sheet**, which reads its numbers out of JSON
rather than transcribing them: a number here could coincidentally match an
unrelated value in the same file, and the check would not know. **The durable
repair remains for B8's writers to emit a small JSON beside each markdown
product, and for this sheet to read those.**

Run ``python experiments/b8_verdicts.py`` and then re-render RESULTS.md.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

# Every criterion names the product it is read from. A missing product raises;
# it is not skipped, and the sheet is not written partially.
SOURCES: dict[str, tuple[str, ...]] = {
    "B8-0a": ("b8_0a_gate.md",),
    # **Corrected 2026-08-19 by the number check below.** This named
    # `b8_0a_gate.md` alone, and none of B8-0b's three floor values occurs in
    # that file: they are printed by `b8_0b_floor.md`. The existence guarantee
    # was passing because the wrong file exists too.
    "B8-0b": ("b8_0a_gate.md", "b8_0b_floor.md"),
    "B8-1": ("b8_1_signal.md", "b8_residue.md"),
    "B8-2": ("b8_2_windows.md", "b8_2_curve.md"),
    "B8-3": ("b8_3_paths.md", "b8_3_curve.md"),
    "B8-4a": ("b8_4_class.md", "b8_c9_cells.md"),
    "B8-4b": ("b8_c9_cells.md",),
    "B8-5": ("b8_5_hole.md",),
    "B8-6": ("b8_2_windows.md", "b8_5_hole.md"),
}

CRITERIA: list[dict] = [
    {"name": "B8-0a", "passed": True, "detail":
     "the gate holds on the split registered after the closed form was found. "
     "(i-a) runs on the clean cures whose every quiet month sits in its "
     "segment's modal cluster and requires an exact return to zero within "
     "floating-point tolerance; all six vintages pass. (i-b) is a reading and "
     "not a gate. What passes it is the qualifying count and not the ratio: "
     "max ratio reads 0.399 to 0.400 in every vintage because the path "
     "tolerance and the agreement bound share one 1/B, so the ratio is capped "
     "by the path filter itself and carries no independent information"},
    {"name": "B8-0b", "passed": True, "detail":
     "the floor is MAD(omega - closed) on the clean-cure arm, 2.68e-08 to "
     "5.22e-08, against a construction that predicts half a cent divided by "
     "the median balance, 3.03e-08. Two further quantities in this repository "
     "are also called a floor and one of them is a signal; they are named "
     "N_cure, N_placebo(L) and IB_RESIDUAL, and any quotation of a floor has "
     "to say which"},
    {"name": "B8-1", "passed": True, "detail":
     "necessary condition holds in all six vintages. Ratio 2,412,840 to "
     "6,765,767; subtract the closed form for leg 1 and it is 2,135,051.8 to "
     "6,632,538.5, a net-to-raw of 0.8849 to 1.0224, so at most 11.5 percent of "
     "the signal is construction. The threshold was demoted to a readability "
     "line rather than a significance test: corr(omega, closed) is +1.0000 in "
     "five of six vintages, which makes the residual instrument resolution "
     "rather than a sampling distribution. The leg-1 shortfall behind that "
     "subtraction is a constant integer month count, n1 - eff of 3.98 to "
     "4.99, and not a proportion; section 21.6's discriminant does not settle "
     "it, since flat equals round(eff) on 0.5525 to 0.7137 of loops and "
     "on none of the six archives outright, though the residual class that "
     "would break the reading is zero at the median in all six. B8-1's "
     "verdict does not move on it: section 21.6 registered in advance that "
     "removing a quantity 1.2 to 1.6 times the measured leg 1 changes the net "
     "ratio by at most 11.5 per cent"},
    {"name": "B8-2", "passed": True, "detail":
     "sign agreement across windows. 29 readable cells of 32, all 29 same-sign "
     "with intervals clear of zero, in all five windows, and re-run under the "
     "far-corner curve construction with zero cells flipping. leg 2 came back "
     "positive in every readable cell where section 14.3 had registered "
     "negative, and is not small: |leg2|/|leg1| has a median of 3.67"},
    {"name": "B8-3", "passed": True, "detail":
     "the two paths to the same state differ, and the verdict is carried by "
     "per-cell signs and permutation rather than by margin. Re-run under the "
     "far-corner construction: all six vintages keep their sign, permutation p "
     "is 0.001 throughout, and the per-cell sign counts are identical under "
     "both constructions. delta/N_cure is 5.78e4 to 4.30e6. The earlier "
     "exemption, that the gap ran two to four orders above the curve spread, "
     "used the wrong denominator and is withdrawn; at 2007Q1 the two are 1.4 "
     "times apart, not an order of magnitude"},
    {"name": "B8-4a", "passed": True, "detail":
     "class ordering reproduces on fico_llpa9, the finest grid that clears "
     "both gates. Six vintages same direction, sign test p = 0.0312, three "
     "significant on their own and surviving equal-n. The loading monotonicity, "
     "median Spearman -0.82 and 6/6 negative, is a post-hoc reading, is "
     "labelled as one, and **no product on disk prints it**: section 3 of "
     "b8_4_class.md carries mean rank and span, not a Spearman, so that "
     "number is carried by this sheet alone and cannot be checked against the "
     "stage's own output (found 2026-08-19 by the number check below). Of eleven grids only five clear the floor of 20 and "
     "hang on the borrower rather than the house or the location, and the "
     "comfortable ones among them are the coarse ones"},
    {"name": "B8-4b", "passed": False, "void": True, "detail":
     "does not run, for want of C9. On (class x origination cohort) inside the "
     "Flex window every one of eleven grids has a minimum of 0 or 1. This is "
     "not a thin-cohort problem but the quantified form of a comparability "
     "one: the Flex window is 2017-2019, so the 2019Q1 vintage has at most a "
     "year of age in it and cannot complete a triangle, while 2002Q1 has "
     "fifteen. Section 15.3 registers this as not a failure of B8, and the "
     "branch table sends the second domain to corporate credit"},
    {"name": "B8-5", "passed": True, "detail":
     "read per cell and not pooled. 554 cells, 132 endpoint-stable, 20 with p "
     "< 0.05. Twelve of the twenty are on the two FICO grids and all twelve "
     "point the same way: conditional on already being delinquent, the lower "
     "the score the higher the share modified, with no counterexample across "
     "six vintages, three windows, five entry tiers and two grids. The label "
     "is an admission threshold that differs by class, not a hole: section 5 "
     "asks whether an edge never exists, and what was measured is a rate"},
    {"name": "B8-6", "passed": True, "detail":
     "satisfied by construction on B8-2 and a real test on B8-5, per sections "
     "20.2 and 22.2"},
]

NOTE = (
    "B8 writes markdown rather than JSON, so none of its thirty-one products "
    "reaches RESULTS.md through the renderer's glob and the stage was absent "
    "from this file entirely. This sheet is the bridge. It re-measures nothing: "
    "each verdict names the products it is read from, and every one of them "
    "must be present on disk or the sheet is not written. The durable repair is "
    "for the writers to emit JSON beside each markdown product; until then the "
    "guarantee here is that every number quoted below is printed by one of the "
    "products that verdict names, checked at the quote's own precision, with "
    "the non-readings listed separately and the one number no product carries "
    "said so in place."
)


#: Numbers in the details that are **not** quantities read off a product, and
#: the reason each one is not. Everything else must be traceable: `unbacked`
#: below fails the sheet on any number that is neither here nor printed by one
#: of the criterion's own sources.
EXEMPT: dict[str, str] = {
    "2017": "calendar year, the near edge of the Flex window, a definition",
    "2019": "calendar year, the far edge of the Flex window, a definition",
    "1.4": "a ratio this sheet forms from two numbers b8_3_paths.md prints "
           "separately; no product prints the ratio itself",
    "-0.82": "**the one real gap.** The loading monotonicity's median Spearman "
             "is printed by no product on disk. Section 3 of b8_4_class.md "
             "carries mean rank and span. The detail string says so.",
}

NUM = re.compile(r"[+-]?\d[\d,]*(?:\.\d+)?(?:[eE][+-]?\d+)?")
#: ISO dates are prose. Removed before tokenising so `2026-08-19` does not
#: arrive as the three quantities 2026, -08 and -19.
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _tokens(text: str) -> list[str]:
    r"""Number-like substrings, with trailing sentence punctuation removed.

    The regex's `[\d,]*` happily eats the comma that ends a clause, which
    turned `6,632,539` into `6,632,539,` and reported a real number as
    unbacked. Stripping here rather than tightening the pattern keeps
    `2,412,840` whole.
    """
    text = DATE.sub(" ", text)
    out = []
    for m in NUM.finditer(text):
        tok = m.group(0).rstrip(",.")
        # `2017-2019` is a range and `-2019` is not a negative quantity. A sign
        # is only a sign when nothing numeric precedes it.
        if tok[:1] in "+-" and m.start() and text[m.start() - 1].isdigit():
            tok = tok[1:]
        if tok:
            out.append(tok)
    return out


def _values(text: str) -> list[float]:
    out = []
    for t in _tokens(text):
        try:
            out.append(float(t.replace(",", "")))
        except ValueError:
            pass
    return out


def _sig(tok: str) -> int:
    """Significant digits in a quoted number, as written."""
    mant = tok.lstrip("+-").replace(",", "").split("e")[0].split("E")[0]
    return len(mant.replace(".", "").lstrip("0")) or 1


def _backed(tok: str, values: list[float]) -> bool:
    """Is the quote the source's own value, shown at the quote's precision?

    **No tolerance is invented here.** The test is that some value printed by
    one of the criterion's sources, rendered to as many significant digits as
    the quote carries, is the quote. So `2.68e-08` is backed by the product's
    `2.6803e-08` and would not be backed by `2.71e-08`.

    What this does not catch, stated rather than implied: a number that
    coincidentally matches something unrelated in the same file. The check is a
    guard against the sheet drifting away from re-run products, not a proof of
    provenance.
    """
    q = float(tok.replace(",", ""))
    n = _sig(tok) - 1
    want = "%.*e" % (n, q)
    return any("%.*e" % (n, v) == want for v in values)


def unbacked() -> list[tuple[str, str]]:
    """(criterion, number) for every quoted number with no source behind it."""
    out = []
    for c in CRITERIA:
        vals: list[float] = []
        for f in SOURCES[c["name"]]:
            path = RESULTS / f
            if path.exists():
                vals += _values(path.read_text(encoding="utf-8"))
        for tok in sorted(set(_tokens(c["detail"]))):
            if tok in EXEMPT:
                continue
            if not _backed(tok, vals):
                out.append((c["name"], tok))
    return out


def missing_sources() -> list[str]:
    """Products named by a criterion that are not on disk."""
    want = sorted({name for names in SOURCES.values() for name in names})
    return [n for n in want if not (RESULTS / n).exists()]


def write_verdicts() -> Path:
    gone = missing_sources()
    if gone:
        raise FileNotFoundError(
            "these B8 products back a verdict and are not on disk: "
            + ", ".join(gone)
            + ". Re-run the stage rather than editing this file."
        )

    loose = unbacked()
    if loose:
        raise AssertionError(
            "these numbers appear in a verdict and in none of that verdict's "
            "own products: "
            + ", ".join(f"{c} {t}" for c, t in loose)
            + ". Either the product was re-run and this sheet was not, or the "
            "number came from somewhere the sheet does not name. Fix the sheet "
            "or add the number to EXEMPT with the reason it is not a reading."
        )

    named = {c["name"] for c in CRITERIA}
    if named != set(SOURCES):
        raise AssertionError(
            "every criterion must name its sources and every named source must "
            f"belong to a criterion; the difference is {named ^ set(SOURCES)}"
        )

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "b8_verdicts.json"
    out.write_text(
        json.dumps(
            {
                "stage": "B8",
                # `n_loans` is read by the renderer's subtitle line, which
                # otherwise prints "no sample metadata recorded" for a record
                # that carries the largest sample in the repository.
                "n_loans": 2942295,
                "n_rows": 170013011,
                "vintages": 6,
                "loops_modification": 49649,
                "loops_deferral": 35659,
                "note": NOTE,
                "sources": {k: list(v) for k, v in sorted(SOURCES.items())},
                "numbers_not_read_off_a_product": EXEMPT,
                "criteria": CRITERIA,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return out


def main(argv=None) -> int:
    out = write_verdicts()
    passed = sum(1 for c in CRITERIA if c.get("passed"))
    void = sum(1 for c in CRITERIA if c.get("void"))
    print(f"wrote {out.relative_to(ROOT)}: {passed}/{len(CRITERIA)} pass, "
          f"{void} void", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
