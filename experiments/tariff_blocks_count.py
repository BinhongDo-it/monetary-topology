"""How many values does a published block tariff produce, against how many blocks it draws.

The counting law says a published procedure that partitions a set produces as many
values as it writes DISTINCT class values, not as many as it draws blocks. A block
tariff is that object in its plainest form: the schedule states the number of
blocks and then states a charge against each one, and any two blocks carrying the
same charge are one value.

Corpus: the residential annex of a published global survey of electricity tariff
design, which gives per country the number of blocks and the charge on each. It is
the only one of that survey's five annexes with a block structure; the other four
carry demand and time-of-use charges and have no blocks to count.

Two things this file does not do. It does not treat the block count as the answer,
which is what the survey itself reports and what the literature reports. And it
does not claim the collisions are exact: the survey rounds charges to two decimals,
so equal printed charges may be unequal underlying ones. **The collision count is
therefore an upper bound at the published resolution**, and that is stated in the
reading rather than worked around.

The parse is checked against the survey's own summary statistic, which is the one
number in the document that this file can be wrong about and be caught.

    python experiments/tariff_blocks_count.py data/raw/falling_short_layout.txt
    python experiments/tariff_blocks_count.py <path to the survey pdf>
"""
import collections
import json
import os
import re
import subprocess
import sys

LABELS = ["Country", "Tariff schedule", "Type of", "Nr of", "Block sizes",
          "Block charges", "Power con-", "Operating,", "Average unit", "Monthly"]
NAMES = ["country", "organized_by", "type", "n_blocks", "block_sizes",
         "block_charges", "consumption", "op_cost", "avg_tariff", "bill"]
NUM = re.compile(r"^-?\d+(?:\.\d+)?$")
SKIP = ("organized by", "tariff structure", "(kWh", "(USD", "blocks",
        "sumption", "limited", "capital")


def pdf_pages(path):
    """Layout-preserving text, one string per page. The columns are the data.

    A .txt path is taken as the output of `pdftotext -layout` already, so the
    reading reproduces without the pdf and without pdftotext installed. The page
    split is the form feed either way.
    """
    if path.lower().endswith(".txt"):
        with open(path, encoding="utf-8") as f:
            return f.read().split("\f")
    out = subprocess.run(["pdftotext", "-layout", path, "-"],
                         capture_output=True, check=True)
    return out.stdout.decode("utf-8", "replace").split("\f")


def parse_page(page):
    """Column bounds come from that page's own header, not from a fixed table.

    Every continuation page of the annex repeats the header at its own column
    positions, and they differ page to page. Taking the bounds from the first page
    and applying them to the rest shifts every field by a few characters and
    produces rows that look parsed and are not.
    """
    lines = page.split("\n")
    hi = next((i for i, l in enumerate(lines)
               if "Nr of" in l and "Block charges" in l), None)
    if hi is None:
        return []
    header = lines[hi]
    starts = [header.find(lab) for lab in LABELS]
    for i, s in enumerate(starts):          # a label absent from line one of the
        if s < 0:                           # header inherits its neighbour's edge
            starts[i] = starts[i - 1] + 1
    bounds = list(zip(starts, starts[1:] + [10 ** 6]))

    recs, cur = [], None
    for line in lines[hi + 1:]:
        if not line.strip() or line.strip().startswith(SKIP):
            continue
        cells = [line[a:b].strip() for a, b in bounds]
        # A long country name wraps to a second line that also starts in column
        # zero, so "starts in column zero" alone splits six countries in half and
        # invents six rows carrying the back half of their fields. Two of the six
        # carry data in other columns on the wrap line, so "every other column is
        # empty" is not the test either.
        #
        # The test is the structure column. Every schedule in the annex states a
        # structure type, and it is printed on the row's own first line. A line
        # beginning in column zero with no structure type is a wrapped name.
        starts_row = bool(line[:1].strip()) and bool(cells[NAMES.index("type")])
        if starts_row:
            if cur:
                recs.append(cur)
            cur = dict(zip(NAMES, cells))
        elif cur:                           # a wrapped continuation of the row
            for k, v in zip(NAMES, cells):
                if v:
                    cur[k] = (cur[k] + " " + v).strip()
    if cur:
        recs.append(cur)
    return recs


def charges(field):
    """The charges of one row, with a footnote marker glued to the last one cut.

    The last charge in a row is followed by the page's footnote marker with only
    a space between them, so the cell reads `0.13 34`. Taking the first
    whitespace token of each comma field cuts it. That step cannot quietly invent
    a charge, because the count it produces still has to equal the block count the
    row declares, and a row where it does not is excluded.
    """
    out = []
    for cell in field.split(","):
        tok = cell.split()
        if tok and NUM.match(tok[0]):
            out.append(tok[0])
    return out


def main(pdf):
    pages = pdf_pages(pdf)
    rows = []
    for i, p in enumerate(pages):
        if "Nr of" in p and "Block charges" in p:
            rows += parse_page(p)
    rows = [r for r in rows
            if r["country"] and not r["country"].lower().startswith(("source", "note"))]

    clean, mismatch = [], []
    for r in rows:
        nb, ch = r["n_blocks"], charges(r["block_charges"])
        if not nb.isdigit() or not ch:
            continue
        (clean if int(nb) == len(ch) else mismatch).append(
            dict(country=r["country"], n=int(nb), charges=ch, type=r["type"],
                 sizes=charges(r["block_sizes"]),
                 consumption=charges(r["consumption"])))

    blocks = sum(c["n"] for c in clean)
    values = sum(len(set(c["charges"])) for c in clean)
    coll = [c for c in clean if len(set(c["charges"])) < c["n"]]
    multi = [c for c in clean if c["n"] > 1]
    mean_blocks_multi = sum(c["n"] for c in multi) / len(multi)

    print(f"rows parsed                 : {len(rows)}")
    print(f"usable, count matches list  : {len(clean)}")
    print(f"excluded, count disagrees   : {len(mismatch)}")
    print()
    print(f"blocks drawn                : {blocks}")
    print(f"DISTINCT values written     : {values}")
    print(f"collisions                  : {blocks - values} "
          f"({(blocks - values) / blocks * 100:.1f}% of blocks)")
    print(f"schedules with a collision  : {len(coll)} of {len(clean)} "
          f"({len(coll) / len(clean) * 100:.1f}%)")
    print()
    print("blocks : " + str(dict(sorted(collections.Counter(
        c["n"] for c in clean).items()))))
    print("values : " + str(dict(sorted(collections.Counter(
        len(set(c["charges"])) for c in clean).items()))))
    print()
    print("KNOWN ANSWER. The survey states the mean block count over its "
          "block-tariff countries")
    print(f"is four. This parse gives {mean_blocks_multi:.2f} over "
          f"{len(multi)} multi-block schedules.")
    print()
    print("schedules writing fewer values than blocks:")
    for c in sorted(coll, key=lambda x: x["n"] - len(set(x["charges"])),
                    reverse=True):
        print(f"  {c['country'][:26]:<28}{c['type'][:22]:<24}"
              f"{c['n']} -> {len(set(c['charges']))}    {', '.join(c['charges'])}")

    # --- how much of the collision count the printed resolution forces ---------
    #
    # The charges are printed to two decimals. A schedule whose own printed span
    # is narrow cannot write one value per block however many blocks it draws,
    # because there are not that many grid points inside its span. That part of
    # the collision count is arithmetic and carries nothing. The rest is not.
    #
    # The ceiling is read off the schedule's own printed span, so for a schedule
    # that prints every block at the same charge the span is zero and the ceiling
    # is one BY CONSTRUCTION. Those rows are flagged: the grid does not explain
    # them, it is only being handed the answer.
    ceil_rows, forced_tot, excess_tot = [], 0, 0
    for c in clean:
        vals = [float(x) for x in c["charges"]]
        n_str, n_flt = len(set(c["charges"])), len(set(round(v, 2) for v in vals))
        span = max(vals) - min(vals)
        ceiling = round(span / 0.01) + 1
        collisions = c["n"] - n_flt
        forced = max(0, c["n"] - ceiling)
        excess = collisions - forced
        forced_tot += forced
        excess_tot += excess
        if collisions:
            ceil_rows.append(dict(country=c["country"], n=c["n"], values=n_flt,
                                  span=round(span, 2), ceiling=ceiling,
                                  collisions=collisions, forced=forced,
                                  excess=excess, top=max(vals),
                                  span_is_zero=(n_flt == 1),
                                  str_float_agree=(n_str == n_flt)))

    print()
    print("KNOWN ANSWER 2. Distinct counted on the printed strings and on the "
          "rounded floats")
    print(f"must agree, or the token '0.1' and the token '0.10' are being split. "
          f"Rows disagreeing: "
          f"{sum(1 for r in ceil_rows if not r['str_float_agree'])}.")
    print()
    print(f"collisions forced by the two-decimal grid : {forced_tot}")
    print(f"collisions the grid does not force        : {excess_tot}")
    print()
    print(f"{'country':<26}{'B':>2} {'V':>2} {'span':>5} {'ceil':>5} "
          f"{'coll':>5} {'forced':>7} {'excess':>7} {'top':>6}")
    for r in sorted(ceil_rows, key=lambda x: (-x["excess"], -x["collisions"])):
        flag = "   span zero by construction, ceiling not independent" \
            if r["span_is_zero"] else ""
        print(f"{r['country'][:26]:<26}{r['n']:>2} {r['values']:>2} "
              f"{r['span']:>5.2f} {r['ceiling']:>5} {r['collisions']:>5} "
              f"{r['forced']:>7} {r['excess']:>7} {r['top']:>6.2f}{flag}")

    # --- the second reading: the first block against average consumption -------
    #
    # The survey states, alongside the survey, that the first block should fall
    # well below average consumption, so that a majority of customers do not sit
    # inside it. The same annex prints both quantities, so whether a schedule
    # satisfies that is a division. "Well below" is qualitative and the two
    # readings below bracket it rather than resolve it.
    ratios = []
    for c in clean:
        if c["n"] < 2 or not c["sizes"] or not c["consumption"]:
            continue
        first, avg = float(c["sizes"][0]), float(c["consumption"][0])
        if avg <= 0:
            continue
        ratios.append((first / avg, c["country"], first, avg))
    ratios.sort()
    under_1 = sum(1 for r, *_ in ratios if r < 1.0)
    under_h = sum(1 for r, *_ in ratios if r < 0.5)
    mid = ratios[len(ratios) // 2][0]
    print()
    print(f"first block against average consumption, on {len(ratios)} "
          f"multi-block schedules printing both")
    print(f"  below average           : {under_1} "
          f"({under_1 / len(ratios) * 100:.0f}%)")
    print(f"  below half of average   : {under_h} "
          f"({under_h / len(ratios) * 100:.0f}%)")
    print(f"  range {ratios[0][0]:.2f} ({ratios[0][1][:18]}) "
          f"to {ratios[-1][0]:.2f} ({ratios[-1][1][:18]}), median {mid:.2f}")
    print("  the five largest:")
    for r, name, first, avg in ratios[-5:][::-1]:
        print(f"    {name[:24]:<26}{r:6.2f}   first block {first:g} kWh, "
              f"average consumption {avg:g} kWh")

    rec = dict(n_rows=len(rows), n_clean=len(clean), n_excluded=len(mismatch),
               blocks=blocks, distinct_values=values,
               collisions=blocks - values,
               schedules_with_collision=len(coll),
               mean_blocks_multi=mean_blocks_multi,
               block_hist=dict(collections.Counter(c["n"] for c in clean)),
               value_hist=dict(collections.Counter(
                   len(set(c["charges"])) for c in clean)),
               forced_by_grid=forced_tot, excess_of_grid=excess_tot,
               ratio_n=len(ratios), ratio_under_1=under_1,
               ratio_under_half=under_h, ratio_median=mid,
               ratios=[dict(country=n, ratio=r, first_block=f, consumption=a)
                       for r, n, f, a in ratios],
               ceiling_rows=ceil_rows,
               clean=clean, excluded=mismatch)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "results", "tariff_blocks_count.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"\nwritten {os.path.relpath(out, root)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("give the path to the survey pdf")
    main(sys.argv[1])
