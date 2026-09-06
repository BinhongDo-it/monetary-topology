"""B28-6: does a new name reset the anchor?

Criterion fixed in b28_prereg.md section 3, before any of this was collected:
  ratio disperses widely across successive generations -> each name carries an
    anchor set independently
  ratio clusters near one -> the new name inherits the old anchor and the
    independence reading fails
  otherwise -> undecided

Carrier: one maker's base handset, China launch price, RMB, by generation.
Sources are per row. The 2010 and 2024 endpoints are verbatim quotations from
dated trade reports; the middle of the series is one compilation dated 2022-10-16
plus one 2023 launch report.

Note on the line: the premium model introduced in 2017 is a separate line and is
not in this series, so the 2017 base and the 2018 base are consecutive here.
"""
import math, statistics as st

SERIES = [
    ("iPhone 4",  2010, 4999, "verbatim, 2010-09-25 trade report"),
    ("iPhone 4S", 2011, 4988, "compilation 2022-10-16"),
    ("iPhone 5",  2012, 5399, "compilation 2022-10-16"),
    ("iPhone 5S", 2013, 5288, "compilation 2022-10-16"),
    ("iPhone 6",  2014, 5288, "compilation 2022-10-16"),
    ("iPhone 6S", 2015, 5288, "compilation 2022-10-16"),
    ("iPhone 7",  2016, 5388, "compilation 2022-10-16"),
    ("iPhone 8",  2017, 5388, "compilation 2022-10-16"),
    ("iPhone XR", 2018, 6499, "compilation 2022-10-16"),
    ("iPhone 11", 2019, 5499, "compilation 2022-10-16"),
    ("iPhone 12", 2020, 6299, "compilation 2022-10-16"),
    ("iPhone 13", 2021, 5999, "compilation 2022-10-16"),
    ("iPhone 14", 2022, 5999, "compilation 2022-10-16"),
    ("iPhone 15", 2023, 5999, "launch reports 2023-09-13"),
    ("iPhone 16", 2024, 5999, "verbatim, 2024-09-10 launch report"),
]


def main():
    print(f"{'transition':26} {'from':>6} {'to':>6} {'ratio':>8} {'pct':>8}")
    rs = []
    for (n0, y0, p0, _), (n1, y1, p1, _) in zip(SERIES, SERIES[1:]):
        r = p1 / p0
        rs.append((f"{n0} to {n1}", y1, r))
        print(f"{n0+' to '+n1:26} {p0:6d} {p1:6d} {r:8.4f} {(r-1)*100:+7.2f}%")

    v = [r for _, _, r in rs]
    flat = [t for t, _, r in rs if abs(r - 1) < 1e-9]
    lg = [math.log(r) for r in v]
    print()
    print(f"transitions            {len(v)}")
    print(f"exactly flat           {len(flat)}  ({len(flat)/len(v):.0%})")
    for t in flat:
        print(f"   {t}")
    print(f"range                  {min(v):.4f} to {max(v):.4f}, span {max(v)/min(v):.4f}")
    print(f"log sd                 {st.stdev(lg):.4f}")
    print(f"median ratio           {st.median(v):.4f}")
    print(f"geometric mean         {math.exp(sum(lg)/len(lg)):.4f}")
    print(f"first to last          {SERIES[-1][2]/SERIES[0][2]:.4f} over "
          f"{SERIES[-1][1]-SERIES[0][1]} years")

    print()
    print("the 2018 to 2021 run, checked rather than asserted:")
    run = [(t, (r - 1) * 100) for t, y, r in rs if 2018 <= y <= 2021]
    for t, p in run:
        print(f"   {t:26} {p:+7.2f}%")
    signs = [p > 0 for _, p in run]
    amps = [abs(p) for _, p in run]
    print(f"   signs strictly alternating: "
          f"{all(a != b for a, b in zip(signs, signs[1:]))}")
    print(f"   amplitude strictly decreasing: "
          f"{all(a > b for a, b in zip(amps, amps[1:]))}")
    print(f"   and what follows it: "
          f"{[f'{(r-1)*100:+.2f}%' for t, y, r in rs if y > 2021]}")

    print()
    print("criterion, as registered:")
    print(f"   clusters near one?  median {st.median(v):.4f}, log sd {st.stdev(lg):.4f}, "
          f"{len(flat)} of {len(v)} exactly equal")
    print("   -> SECOND BRANCH: the new name inherits the old anchor.")
    print("      The independence reading fails on this line.")


if __name__ == "__main__":
    main()
