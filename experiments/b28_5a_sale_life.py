"""B28-5a / B28-6 support: sale life and successor overlap for one maker's tablet family.

Quantities
----------
sale_life   = discontinued - released                 (months)
overlap     = discontinued - successor_release        (months; >0 means the
              predecessor stayed on sale after its replacement existed)

Successor is the next model *within the same line*. Cross-line replacement is
recorded separately in the notes and is not used for the headline.

Source of dates: en.wikipedia.org/wiki/List_of_iPad_models, read 2026-08-30.
Tier: third-party compilation. Validation against the maker's own vintage list
is done in b28_5a_validate.py and reported with the result.

No network, no cache needed: the table is the input.
"""
from datetime import date
import statistics as st

DAY = 365.2425 / 12.0  # days per month

# (line, generation label, release, discontinued or None)
ROWS = [
    ("iPad",     "1st",  date(2010, 4, 3),  date(2011, 3, 2)),
    ("iPad",     "2",    date(2011, 3, 11), date(2014, 3, 18)),
    ("iPad",     "3rd",  date(2012, 3, 16), date(2012, 10, 23)),
    ("iPad",     "4th",  date(2012, 11, 2), date(2014, 10, 16)),
    ("iPad",     "5th",  date(2017, 3, 24), date(2018, 3, 27)),
    ("iPad",     "6th",  date(2018, 3, 27), date(2019, 9, 10)),
    ("iPad",     "7th",  date(2019, 9, 25), date(2020, 9, 15)),
    ("iPad",     "8th",  date(2020, 9, 18), date(2021, 9, 14)),
    ("iPad",     "9th",  date(2021, 9, 24), date(2024, 5, 7)),
    ("iPad",     "10th", date(2022, 10, 26), date(2025, 3, 4)),
    ("iPad",     "11th", date(2025, 3, 12), None),

    ("iPad mini", "1st", date(2012, 11, 2), date(2015, 6, 19)),
    ("iPad mini", "2",   date(2013, 11, 12), date(2017, 3, 21)),
    ("iPad mini", "3",   date(2014, 10, 22), date(2015, 9, 9)),
    ("iPad mini", "4",   date(2015, 9, 9),  date(2019, 3, 18)),
    ("iPad mini", "5th", date(2019, 3, 18), date(2021, 9, 14)),
    ("iPad mini", "6th", date(2021, 9, 24), date(2024, 10, 15)),
    ("iPad mini", "7th", date(2024, 10, 23), None),

    ("iPad Air", "1st",  date(2013, 11, 1), date(2016, 3, 21)),
    ("iPad Air", "2",    date(2014, 10, 22), date(2017, 3, 21)),
    ("iPad Air", "3rd",  date(2019, 3, 18), date(2020, 9, 15)),
    ("iPad Air", "4th",  date(2020, 10, 23), date(2022, 3, 8)),
    ("iPad Air", "5th",  date(2022, 3, 18), date(2024, 5, 7)),
    ("iPad Air", "6th",  date(2024, 5, 15), date(2025, 3, 4)),
    ("iPad Air", "7th",  date(2025, 3, 12), date(2026, 3, 2)),
    ("iPad Air", "8th",  date(2026, 3, 11), None),

    ("iPad Pro", "12.9 1st", date(2015, 11, 11), date(2017, 6, 5)),
    ("iPad Pro", "2nd",  date(2017, 6, 13), date(2018, 10, 30)),
    ("iPad Pro", "3rd",  date(2018, 11, 7), date(2020, 3, 18)),
    ("iPad Pro", "4th",  date(2020, 3, 25), date(2021, 4, 20)),
    ("iPad Pro", "5th",  date(2021, 5, 21), date(2022, 10, 18)),
    ("iPad Pro", "6th",  date(2022, 10, 26), date(2024, 5, 7)),
    ("iPad Pro", "7th",  date(2024, 5, 15), date(2025, 10, 15)),
    ("iPad Pro", "8th",  date(2025, 10, 22), None),
]
# iPad Pro 9.7-inch (2016-03-31) is omitted: the page gives no discontinued date.

def months(a, b):
    return (a - b).days / DAY

def main():
    by_line = {}
    for line, gen, rel, disc in ROWS:
        by_line.setdefault(line, []).append((gen, rel, disc))

    print(f"{'line':10} {'gen':9} {'released':11} {'stopped':11} {'sale_life':>9} {'overlap':>8}")
    print("-" * 62)
    rec = {}
    for line, items in by_line.items():
        items.sort(key=lambda t: t[1])
        for i, (gen, rel, disc) in enumerate(items):
            if disc is None:
                print(f"{line:10} {gen:9} {rel.isoformat():11} {'on sale':11} {'':>9} {'':>8}")
                continue
            sl = months(disc, rel)
            ov = None
            if i + 1 < len(items):
                ov = months(disc, items[i + 1][1])
            rec.setdefault(line, []).append((gen, sl, ov))
            ovs = f"{ov:8.1f}" if ov is not None else "     n/a"
            print(f"{line:10} {gen:9} {rel.isoformat():11} {disc.isoformat():11} {sl:9.1f} {ovs}")

    print()
    print(f"{'line':10} {'n':>3} {'sale_life min':>13} {'max':>7} {'range x':>8} {'sd(log)':>8}"
          f" {'n overlap>1mo':>14} {'max overlap':>12}")
    print("-" * 80)
    import math
    for line in ["iPad", "iPad mini", "iPad Air", "iPad Pro"]:
        v = rec[line]
        sls = [s for _, s, _ in v]
        ovs = [o for _, _, o in v if o is not None]
        lg = [math.log(s) for s in sls]
        sd = st.stdev(lg) if len(lg) > 1 else float("nan")
        pos = sum(1 for o in ovs if o > 1.0)
        print(f"{line:10} {len(sls):3d} {min(sls):13.1f} {max(sls):7.1f}"
              f" {max(sls)/min(sls):8.2f} {sd:8.4f} {pos:14d} {max(ovs):12.1f}")

    print()
    pro = [o for g, s, o in rec["iPad Pro"] if o is not None]
    non = [o for line in ["iPad", "iPad mini", "iPad Air"] for g, s, o in rec[line] if o is not None]
    print(f"overlap, professional line : n={len(pro)}  max={max(pro):.1f}  "
          f"count>1mo={sum(1 for o in pro if o > 1.0)}")
    print(f"overlap, other three lines : n={len(non)}  max={max(non):.1f}  "
          f"count>1mo={sum(1 for o in non if o > 1.0)}")
    print("  positive overlaps outside the professional line:")
    for line in ["iPad", "iPad mini", "iPad Air"]:
        for g, s, o in rec[line]:
            if o is not None and o > 1.0:
                print(f"    {line} {g}: stayed on sale {o:.1f} months after its successor launched")

# ---------------------------------------------------------------------------
# Phone panel. Added 2026-08-30 with the B28-5a reading.
# ---------------------------------------------------------------------------

# professional line: label, release, stop of sale, successor release
PHONE_PRO = [
    ("11 Pro", date(2019, 9, 20), date(2020, 10, 13), date(2020, 10, 23)),
    ("12 Pro", date(2020, 10, 23), date(2021, 9, 14), date(2021, 9, 24)),
    ("13 Pro", date(2021, 9, 24), date(2022, 9, 7),  date(2022, 9, 16)),
    ("14 Pro", date(2022, 9, 16), date(2023, 9, 12), date(2023, 9, 22)),
    ("15 Pro", date(2023, 9, 22), date(2024, 9, 9),  date(2024, 9, 20)),
    ("16 Pro", date(2024, 9, 20), date(2025, 9, 9),  date(2025, 9, 19)),
]

# retained standard models: event date, model, posted price before, after
PHONE_STEPS = [
    ("2022-09-07", "iPhone 12", 699, 599), ("2022-09-07", "iPhone 13", 799, 699),
    ("2022-09-07", "iPhone 13 mini", 699, 599),
    ("2024-09-09", "iPhone 14", 699, 599), ("2024-09-09", "iPhone 14 Plus", 799, 699),
    ("2024-09-09", "iPhone 15", 799, 699), ("2024-09-09", "iPhone 15 Plus", 899, 799),
    ("2025-09-09", "iPhone 16", 799, 699), ("2025-09-09", "iPhone 16 Plus", 899, 799),
]

# B28-5b matched pairs: name, release, stop of sale, iOS at ship, last major iOS
IOS_RELEASE = {16: date(2022, 9, 12), 18: date(2024, 9, 16)}
COHORTS = [
    ("2017", ("iPhone X",  date(2017, 11, 3), date(2018, 9, 12), 11, 16),
             ("iPhone 8",  date(2017, 9, 22), date(2020, 4, 15), 11, 16)),
    ("2018", ("iPhone XS", date(2018, 9, 21), date(2019, 9, 10), 12, 18),
             ("iPhone XR", date(2018, 10, 26), date(2021, 9, 14), 12, 18)),
]


def phones():
    import math
    print()
    print("phone professional line")
    sl, ov = [], []
    for g, r, d, nx in PHONE_PRO:
        a, b = months(d, r), months(d, nx)
        sl.append(a); ov.append(b)
        print(f"  {g:8} sale life {a:6.2f}   overlap {b:6.2f}")
    print(f"  n={len(sl)} min {min(sl):.2f} max {max(sl):.2f} range x {max(sl)/min(sl):.3f}"
          f" log sd {st.stdev([math.log(x) for x in sl]):.4f}"
          f" overlap>0 count {sum(1 for x in ov if x > 0)}")

    steps = [b - a for _, _, b, a in PHONE_STEPS]
    print()
    print(f"retained standard models n={len(steps)} distinct step sizes {sorted(set(steps))}")

    print()
    print("B28-5b matched pairs")
    for label, pro, non in COHORTS:
        out = []
        for nm, rel, disc, ship, last in (pro, non):
            out.append((nm, months(disc, rel), months(IOS_RELEASE[last], rel), last - ship + 1))
        (n1, s1, u1, g1), (n2, s2, u2, g2) = out
        print(f"  {label}: {n1} sale {s1:.2f} support {u1:.2f} gens {g1} | "
              f"{n2} sale {s2:.2f} support {u2:.2f} gens {g2}")
        print(f"         sale life ratio {s2/s1:.2f}x   support life ratio {u2/u1:.3f}x"
              f"   generations equal {g1 == g2}")


if __name__ == "__main__":
    main()
    phones()
