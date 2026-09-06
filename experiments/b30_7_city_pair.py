"""B30-7 cell B: item-level price ratios between two cities of one country.

EVERY item in the source table is classified and none is dropped, because dropping
items after seeing their ratios is the failure this station exists to avoid. The
only omission is the mortgage interest rate, which is not a price.

Class rule, fixed before the table was fetched (b30_prereg.md section 1,
b30_propagation.md section 12.9). Assignment is made from the item's description,
never from its ratio, so any row can be re-argued by a reader.

  STATE   a government sets or guides the number. B30-9: the regulator supplies the
          anchor, so these are informative about posted numbers in general and are
          not evidence about market anchoring. Reported separately.
  LADDER  one brand or seller posts a single number nationally.
  FRESH   locally produced food. A tradable object with no national posted number.
  LOCAL   no national number exists and the thing is produced where it is sold.

Prediction fixed in advance, and it is one sided: LADDER near ratio 1, because a
single national number pins the price and ignores local input costs. The low side
is not this project's claim. Income scaling there belongs to the standard
non-tradables account and is carried only as the arm's live alternative.
A single local price level would put every item on one ratio.

Source: crowdsourced cost-of-living database, Shanghai updated 2026-08-28, Harbin
2026-07-15. Third-party tier, self-selected contributors, loose item definitions.

Three assignments are judgement calls and are marked (*) in the output: cappuccino
to LADDER because national chains post the number for that cup in this country,
and mobile and broadband to LADDER because three national carriers post the
tariffs, though they do vary them by province.
"""
import statistics as st

INCOME = ("average monthly net salary", 11674.92, 3966.67)

STATE = [
    ("gasoline, 1L",              8.58,     8.66),
    ("cigarettes, Marlboro 20",  25.00,    17.00),
    ("transit, one way",          4.00,     2.00),
    ("transit, monthly pass",   200.00,    73.88),
    ("taxi, start fare",         15.50,     9.00),
    ("taxi, per mile",            4.83,     3.22),
    ("taxi, hourly waiting",     60.00,    24.00),
    ("utilities, basic monthly",419.21,   512.50),
]
LADDER = [
    ("VW Golf 1.5",           129900.00, 129900.00),
    ("Toyota Corolla 1.6",    120784.62, 103400.00),
    ("McDonald's combo meal",     35.00,     36.00),
    ("milk, 1L",                  13.56,     13.67),
    ("white bread, 1lb",          11.80,     12.10),
    ("rice, 1lb",                  3.01,      3.02),
    ("imported beer, market",     10.61,     10.50),
    ("bottled water, 50oz",        4.53,      5.33),
    ("wine, mid-range bottle",    75.00,    120.00),
    ("domestic beer, market",      6.07,      4.00),
    ("Nike running shoes",       511.65,    483.33),
    ("summer dress, chain",      258.53,    200.00),
    ("Levi's 501 jeans",         352.38,    200.00),
    ("men's leather shoes",      709.25,   2000.00),
    ("cappuccino (*)",            22.13,     19.33),
    ("mobile plan (*)",           53.06,     98.50),
    ("broadband (*)",             69.67,     81.33),
]
FRESH = [
    ("eggs, 12",           12.34,  9.14), ("local cheese, 1lb", 51.00, 27.22),
    ("chicken fillets, 1lb",10.04,  7.71), ("beef round, 1lb",  40.26, 36.29),
    ("apples, 1lb",         6.92,  4.84), ("bananas, 1lb",       5.44,  4.08),
    ("oranges, 1lb",        6.08,  3.78), ("tomatoes, 1lb",      5.43,  2.95),
    ("potatoes, 1lb",       2.53,  1.59), ("onions, 1lb",        2.95,  4.54),
    ("lettuce, 1 head",     4.38,  3.00),
]
LOCAL = [
    ("inexpensive restaurant meal",   30.00,    15.00),
    ("mid-range meal for two",       200.00,   150.00),
    ("draft beer, restaurant",         8.00,     5.50),
    ("imported beer, restaurant",     18.00,    11.00),
    ("soft drink, restaurant",         3.93,     3.00),
    ("bottled water, restaurant",      2.23,     1.82),
    ("cinema ticket",                 60.00,    40.00),
    ("fitness membership, monthly",  462.03,   566.67),
    ("tennis court, 1 hour",         112.08,   200.00),
    ("preschool, monthly",          9456.41,  2000.00),
    ("international primary, year",189375.00, 70000.00),
    ("rent 1BR centre",             6643.48,  2166.67),
    ("rent 1BR outside",            3885.71,  3066.67),
    ("rent 3BR centre",            15666.67,  9063.62),
    ("rent 3BR outside",            8117.65,  3500.00),
    ("apartment/sqft, centre",      8616.69,  1988.11),
    ("apartment/sqft, outside",     4158.31,   836.12),
]


def show(name, rows, inc):
    print(f"\n{name}  (n = {len(rows)})")
    print(f"  {'item':30} {'Shanghai':>11} {'Harbin':>10} {'ratio':>7} {'/income':>8}")
    rs = []
    for n, a, b in rows:
        r = b / a; rs.append(r)
        print(f"  {n:30} {a:11.2f} {b:10.2f} {r:7.3f} {r/inc:8.2f}")
    m = st.median(rs)
    print(f"  {'median':30} {'':>11} {'':>10} {m:7.3f} {m/inc:8.2f}")
    return rs


def main():
    inc = INCOME[2] / INCOME[1]
    print(f"income ratio ({INCOME[0]}): {INCOME[2]:.2f} / {INCOME[1]:.2f} = {inc:.4f}")
    print("a single city price level would put every item on one ratio")
    S = show("STATE: a government sets the number (B30-9, reported apart)", STATE, inc)
    L = show("LADDER: one seller posts a single number nationally", LADDER, inc)
    F = show("FRESH: locally produced food, no national number", FRESH, inc)
    C = show("LOCAL: no national number, produced where sold", LOCAL, inc)
    print()
    for nm, v in (("STATE", S), ("LADDER", L), ("FRESH", F), ("LOCAL", C)):
        print(f"  median {nm:7} {st.median(v):.3f}   over income ratio {st.median(v)/inc:.2f}")
    allr = S + L + F + C
    print(f"\nseparation LADDER over LOCAL: {st.median(L)/st.median(C):.2f}x")
    print(f"full spread, all {len(allr)} items: {min(allr):.3f} to {max(allr):.3f}, "
          f"{max(allr)/min(allr):.1f}x")
    print("\nmatched pair, one prepared restaurant meal, same city, same day:")
    print(f"  national posted menu  McDonald's combo  {36.00/35.00:.3f}")
    print(f"  no national menu      inexpensive meal  {15.00/30.00:.3f}")
    print(f"  ratio of ratios                         {(36.00/35.00)/(15.00/30.00):.2f}x")


if __name__ == "__main__":
    main()
