"""B13 verdict sheet: assemble ``results/b13_zero_domain.json`` from the products.

**Why this file exists.** B13 wrote no JSON record, so the stage that produced
this programme's first zero domain was absent from the file everyone else
reads. This is the same repair
``b8_verdicts.py`` is, and it carries the same number check from the start rather
than acquiring it two days later.

**Where B13's products live, and why they are copied.** The station's console
outputs were written under ``data/raw/b13/``, which ``.gitignore`` excludes
because that tree also holds 6.8 GB of packet captures. The outputs themselves
are 60 KB of plain text and they are the evidence. Each run copies them into
``results/`` so the record travels with the repository; the copies are a pure
function of the originals and are overwritten rather than edited.

**What it claims.** Nothing it did not read. Every number in a criterion must be
printed by one of that criterion's own sources, rendered to as many significant
digits as the quote carries, with no tolerance invented. Numbers that are not
readings are in ``EXEMPT`` with the reason each is not one.

**One thing it deliberately does not carry.** The station's own record once
attributed the exact equality on six products to those products having only one
derivation path. `b13_path_multiplicity.py` read the instrument listing and found
every one of the eight roots multi-path, on both sides of the split. The reading
stays; the explanation is gone, and criterion B13-2 says so.

Run ``python experiments/b13_verdicts.py`` and then re-render RESULTS.md.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RAW = ROOT / "data" / "raw" / "b13"

#: Console outputs copied into `results/` on every run, under a `b13_` prefix.
PRODUCTS = (
    "gate0_CLZ3-CLZ4_AB.txt",
    "gate0_oos_20230717.txt",
    "gate0_oos_ch386_NG.txt",
    "gate0_oos_ch360_COMEX.txt",
    "tick_ch382.txt",
    "tick_ch386.txt",
    "tick_ch360.txt",
    "b4_split_ch382.txt",
    "two_classes_ch382.txt",
    "path_multiplicity.txt",
)


def copied(name: str) -> str:
    return "b13_" + name


SOURCES: dict[str, tuple[str, ...]] = {
    "B13-0": ("b13_gate0_CLZ3-CLZ4_AB.txt",),
    "B13-1": ("b13_gate0_oos_20230717.txt", "b13_gate0_oos_ch386_NG.txt",
              "b13_gate0_oos_ch360_COMEX.txt"),
    "B13-2": ("b13_gate0_oos_ch386_NG.txt", "b13_gate0_oos_ch360_COMEX.txt",
              "b13_path_multiplicity.txt"),
    "B13-3": ("b13_gate0_oos_20230717.txt", "b13_gate0_oos_ch386_NG.txt",
              "b13_gate0_oos_ch360_COMEX.txt"),
    "B13-4": ("b13_tick_ch382.txt", "b13_tick_ch386.txt", "b13_tick_ch360.txt"),
    "B13-5": ("b13_b4_split_ch382.txt",),
    "B13-6": ("b13_two_classes_ch382.txt",),
}

CRITERIA: list[dict] = [
    {"name": "B13-0  the gate: one spread, both multicast sides, a book class "
             "that implements every action it is sent",
     "passed": True, "detail":
     "34923 end-of-event states with a book change on one of the three "
     "instruments, 2442 of them republished the spread's implied book and are "
     "paired. Update actions this book class does not implement: 0. Reading "
     "only the A-side of an A+B deduplicated capture had cost 2 per cent of "
     "updates and produced a bid agreement of 0.9229 that looked like a "
     "finding; with both sides it is 0.9990"},
    {"name": "B13-1  section 4.A.2, load-bearing: the exchange's published "
             "implied price is never worse than the two-leg derivation",
     "passed": True, "detail":
     "0 violations in 63168 states on ch382, 0 in 5336 on ch386 and 0 in 13464 "
     "on ch360, over nine products and three channels. The criterion is a "
     "one-sided inequality and not an equality, which is what makes zero "
     "violations the whole of it"},
    {"name": "B13-2  on six of the nine products the inequality is an equality, "
             "bit for bit, and why those six is not established",
     "passed": True, "detail":
     "equality rate 1.0000 on both sides of both ch386 and ch360, which is "
     "2668 offer and 2668 bid states there and 6732 of each on ch360, 18800 in "
     "all. **The explanation the station first gave is withdrawn**: it said "
     "those products have only one derivation path, and the instrument listing "
     "says otherwise for every root measured, CL 906 of 906 multi-path, NG 1124 "
     "of 1127, GC 231 of 231, HG 820 of 820, MHG 780 of 780, QI 55 of 55. The "
     "reading stands and the attribution does not"},
    {"name": "B13-3  the same apparatus on the directly quoted member of the "
             "same family returns non-zero",
     "passed": True, "detail":
     "share of states with a non-zero gap between the directly quoted book and "
     "the two-leg derivation, by channel: 0.8751 offer and 0.9240 bid on ch382, "
     "0.7470 and 0.6516 on ch386, 0.9478 and 0.9610 on ch360. Nine products, no "
     "exception. **Not an economic statement**: it is ordinary queueing and "
     "market-making difference, and the design file forbids reading it as more"},
    {"name": "B13-4  section 5.2's precondition: the spread quotes on the same "
             "grid as its legs",
     "passed": True, "detail":
     "equal 10 different 0 no data 0 on ch382, equal 7 different 0 no data 0 on "
     "ch386, equal 8 different 0 no data 0 on ch360. **This registered check was "
     "skipped when the gate first ran and was performed afterwards**, so the "
     "readings above stood on luck until it passed. Measured as the gcd of the "
     "observed prices rather than read off the definition field"},
    {"name": "B13-5  B4's section 5.1 split, both halves computed on live "
             "quotes for the first time in this repository",
     "passed": True, "detail":
     "the split is available in 49116 of 50055 states, 0.981; Theorem 6(1)'s "
     "sign constraint has 0 counterexamples in those 49116; the index part is "
     "exactly zero in 12637 of them. B5 could report the index half and never "
     "the friction half, and this is the first carrier that quotes all four "
     "legs natively"},
    {"name": "B13-6  Theorem 6(4)'s bound, and section 5.1's own criterion for "
             "two agent classes, adjudicated per position edge",
     "passed": True, "detail":
     "0 violations of |S - S'| <= -(S + S') in 49116 states; rho median 0.2000 "
     "with 0 states at rho = 1. Under the parity control the index is zero in "
     "0.5649 of the states where zero was available: CLU3-CLV3 takes it 716 "
     "times out of 716 and is one class, RBU3-RBX3 takes it 88 times out of "
     "1978 and RBU3-RBV3 155 out of 1895, and those two are two classes"},
]

EXEMPT: dict[str, str] = {
    "382": "a CME channel number",
    "386": "a CME channel number",
    "360": "a CME channel number",
    "18800": "the sum of the four equality counts the two products print, "
             "2668 and 2668 on ch386 and 6732 and 6732 on ch360. **Added by "
             "hand here and printed by no product**, which is the same shape "
             "as the one figure b8_verdicts.py had to admit it could not trace",
    "0.981": "49116 / 50055, a ratio this sheet forms from two counts the "
             "product prints separately",
    "0.9229": "**the one number here that no product carries.** It is the bid "
              "agreement from the A-side-only run, whose output was never "
              "saved. It is kept because the defect it records is the most "
              "expensive one this station hit, and the corrected 0.9990 beside "
              "it is printed",
    "5.2": "a section number in the design file, not a reading",
    "4.A.2": "a section number in the design file, not a reading",
    "5.1": "a section number in B4's document, not a reading",
    "6": "Theorem 6, a theorem number",
    "4": "Theorem 4 and Theorem 6(4), theorem numbers",
    "2": "'2 per cent of updates', a figure from the diagnosis of the A-side "
         "defect that the gate product does not print; the corrected and "
         "uncorrected agreements beside it, 0.9990 and 0.9229, do",
    "1": "'one-sided', 'one derivation path', 'one class', prose",
    "9": "nine products, a count of the instrument list rather than a reading",
    "3": "three channels, likewise",
    "6.8": "the capture size in gigabytes, named in this file's docstring",
    "60": "the products' size in kilobytes, likewise",
}

NOTE = (
    "B13 wrote no JSON, so the stage that produced this programme's first zero "
    "domain did not appear in RESULTS.md at all. This sheet is the bridge and "
    "re-measures nothing. Its guarantee is that every number quoted below is "
    "printed by one of the products that criterion names, checked at the "
    "quote's own precision, with the products themselves copied into results/ "
    "so the evidence travels with the repository. The station's design and "
    "result files are held outside this repository; docs/b9_zero_holonomy.md "
    "section 57 is where the station was specified and handed off."
)

NUM = re.compile(r"[+-]?\d[\d,]*(?:\.\d+)?(?:[eE][+-]?\d+)?")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _tokens(text: str) -> list[str]:
    text = DATE.sub(" ", text)
    out = []
    for m in NUM.finditer(text):
        tok = m.group(0).rstrip(",.")
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
    mant = tok.lstrip("+-").replace(",", "").split("e")[0].split("E")[0]
    return len(mant.replace(".", "").lstrip("0")) or 1


def _backed(tok: str, values: list[float]) -> bool:
    q = float(tok.replace(",", ""))
    n = _sig(tok) - 1
    want = "%.*e" % (n, q)
    return any("%.*e" % (n, v) == want for v in values)


def unbacked() -> list[tuple[str, str]]:
    out = []
    for c in CRITERIA:
        vals: list[float] = []
        for f in SOURCES[c["name"].split()[0]]:
            p = RESULTS / f
            if p.exists():
                vals += _values(p.read_text(encoding="utf-8", errors="replace"))
        for tok in sorted(set(_tokens(c["detail"]))):
            if tok in EXEMPT:
                continue
            if not _backed(tok, vals):
                out.append((c["name"].split()[0], tok))
    return out


def copy_products() -> list[str]:
    """Copy the console outputs into results/. Missing ones are returned."""
    gone = []
    RESULTS.mkdir(parents=True, exist_ok=True)
    for name in PRODUCTS:
        src = RAW / name
        if not src.exists():
            gone.append(str(Path("data/raw/b13") / name))
            continue
        shutil.copyfile(src, RESULTS / copied(name))
    return gone


def write_verdicts() -> Path:
    gone = copy_products()
    if gone:
        raise FileNotFoundError(
            "these B13 products back a criterion and are not on disk: "
            + ", ".join(gone)
            + ". Re-run the station's scripts rather than editing this file."
        )

    named = {c["name"].split()[0] for c in CRITERIA}
    if named != set(SOURCES):
        raise AssertionError(
            "every criterion names its sources and every named source belongs "
            f"to a criterion; the difference is {named ^ set(SOURCES)}"
        )

    loose = unbacked()
    if loose:
        raise AssertionError(
            "these numbers appear in a criterion and in none of that "
            "criterion's own products: "
            + ", ".join(f"{c} {t}" for c, t in loose)
            + ". Fix the sheet, or add the number to EXEMPT with the reason it "
            "is not a reading."
        )

    out = RESULTS / "b13_zero_domain.json"
    out.write_text(
        json.dumps(
            {
                "stage": "B13",
                "states_gate": 81968,
                "states_exact_equality": 18800,
                "products": 9,
                "channels": 3,
                "capture_day": "2023-07-17",
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
    print(f"wrote {out.relative_to(ROOT)}: {len(CRITERIA)}/{len(CRITERIA)} pass, "
          f"{len(PRODUCTS)} products copied into results/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
