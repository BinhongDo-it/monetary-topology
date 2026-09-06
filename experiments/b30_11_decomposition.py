"""B30-11: can a cost decomposition produce the observed city price ratio?

The framework's claim is one sided. It says that where one seller posts a single
national number, the ratio is pinned at 1 and local input costs are ignored. It
says nothing about what happens otherwise: that side is ordinary factor-price
economics, since land cannot move and labour moves at a cost, so local inputs are
dearer in the richer city.

So the test is not "does LOCAL sit at the income ratio". It is:

    can any cost decomposition produce this item's ratio at all?

An item made only from local inputs has a ratio that is a convex combination of
its input ratios, so it must lie inside the interval spanned by them. Each input
ratio is measured from a DIFFERENT item class than the one being predicted, so
nothing here is circular.

Items outside that interval cannot be produced by any weighting of local inputs.
They are pinned by something that is not cost, and that is the framework's object.

Weights are used only for the one worked example, from the industry "343" rule
(rent 30, ingredients 40, labour 30 among the three main inputs). The interval
test needs no weights at all.
"""
import statistics as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from b30_7_city_pair import STATE, LADDER, FRESH, LOCAL, INCOME

# input ratios, each measured on a class other than the one being predicted
# Corrected 2026-08-30. The first version put utilities in this basket, which
# contradicted the item table where utilities is already classified STATE, a
# regulated tariff. It also ran the wrong way (1.223, the colder city pays more
# for heating, which is a quantity effect and not a local factor price) and it
# raised the ceiling until the test stopped discriminating. Removing it makes the
# script agree with a classification fixed before the data was seen.
INPUTS = {
    "labour (net salary)":              3966.67 / 11674.92,
    "rent, 1BR centre":                 2166.67 / 6643.48,
    "food ingredients (FRESH median)":  None,     # filled below
}


def ratios(rows):
    return [b / a for _, a, b in rows]


def main():
    INPUTS["food ingredients (FRESH median)"] = st.median(ratios(FRESH))
    lo, hi = min(INPUTS.values()), max(INPUTS.values())
    print("input ratios, each measured on a different class:")
    for k, v in INPUTS.items():
        print(f"  {k:34} {v:.3f}")
    print(f"\nany item built only from local inputs must land in [{lo:.3f}, {hi:.3f}]")
    print("an item outside that interval cannot be produced by ANY cost weighting\n")

    print(f"{'class':8} {'n':>3} {'above ceiling':>14} {'share':>7} {'median':>8}")
    for name, rows in (("LADDER", LADDER), ("FRESH", FRESH),
                       ("LOCAL", LOCAL), ("STATE", STATE)):
        r = ratios(rows)
        above = sum(1 for x in r if x > hi)
        print(f"{name:8} {len(r):3d} {above:14d} {above/len(r):7.2f} {st.median(r):8.3f}")

    print("\nworked example, the matched restaurant pair, no free parameters fitted:")
    w = {"ingredients": 0.40, "labour": 0.30, "rent": 0.30}
    pred = (w["ingredients"] * INPUTS["food ingredients (FRESH median)"]
            + w["labour"] * INPUTS["labour (net salary)"]
            + w["rent"] * INPUTS["rent, 1BR centre"])
    print(f"  weights are the industry 343 rule as published, {w}, nothing fitted")
    print(f"  predicted ratio for a restaurant meal        {pred:.3f}")
    print(f"  observed, inexpensive meal, no national menu 0.500   error {abs(0.500-pred)/0.500:+.1%}")
    print(f"  observed, burger combo, national menu        1.029   error {abs(1.029-pred)/1.029:+.1%}")
    print(f"  naive benchmark, pinned at one               1.000   error on the local meal {abs(0.500-1.0)/0.500:+.1%}")
    print(f"  naive benchmark, pure income scaling         {INPUTS['labour (net salary)']:.3f}"
          f"   error on the local meal {abs(0.500-INPUTS['labour (net salary)'])/0.500:+.1%}")
    print(f"\n  the burger sits OUTSIDE [{lo:.3f}, {hi:.3f}] by {1.029/hi:.2f}x.")
    print("  No weighting of local inputs reaches it. The local meal sits inside.")
    print(f"  size of the override: {1.029/pred:.2f}x the cost-implied ratio")


if __name__ == "__main__":
    main()
