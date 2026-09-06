"""B43: the counting law's proposition (i), enumerated before it is proved.

The law says a published procedure shared by all parties draws a partition on the
set of positions, and that the number of values it produces equals the number of
classes it wrote. Section 2.3 of the general theory splits that into two cases,
and this station is registered on both:

  (i-two-sided)  an equality constraint. The procedure writes the term itself and
                 every position in a class receives exactly that number, so the
                 partition of produced values equals the partition the procedure
                 wrote.

  (i-one-sided)  an inequality constraint. The procedure writes a bound, every
                 position receives at least (or at most) that number, and the two
                 partitions agree only on the union of the subsets where the bound
                 binds.

This file does not prove either. **It enumerates.** Small configurations are built
exhaustively, both partitions are computed, and the claims are checked on every
one. A counterexample is worth more than a proof attempt here, because the
statement was read off a corpus of twenty-three cases rather than derived, and the
corpus cannot show which side conditions it was silently relying on.

Criteria are counts of counterexamples with the offending configuration printed.
There is no threshold anywhere and no sampling: the space is small and is walked
in full.

Run:

    python experiments\\b43_counting_enumerate.py
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "b43_counting_enumerate.json"

BASELINES = (1, 2, 3)          # what a position would take with no procedure
TERMS = (1, 2, 3)              # rates a class may be assigned, and bounds likewise


def partitions(items):
    """Every set partition of items, as a tuple of frozensets."""
    items = list(items)
    if not items:
        yield ()
        return
    first, rest = items[0], items[1:]
    for smaller in partitions(rest):
        for i in range(len(smaller)):
            yield smaller[:i] + (smaller[i] | {first},) + smaller[i + 1:]
        yield smaller + (frozenset({first}),)


def as_partition(value_of):
    """Group keys by the value they carry. This is P_read."""
    buckets = {}
    for k, v in value_of.items():
        buckets.setdefault(v, set()).add(k)
    return frozenset(frozenset(s) for s in buckets.values())


def written(classes):
    return frozenset(frozenset(c) for c in classes)


def two_sided(classes, terms, _baseline):
    """Equality constraint: every position in class a receives term a."""
    return {p: terms[i] for i, c in enumerate(classes) for p in c}


def one_sided_floor(classes, bounds, baseline):
    """Inequality constraint: every position receives at least its class bound."""
    return {p: max(baseline[p], bounds[i]) for i, c in enumerate(classes) for p in c}


def binding(classes, bounds, baseline):
    """S_a: the positions where the bound actually binds, unioned over classes."""
    return {p for i, c in enumerate(classes) for p in c if baseline[p] < bounds[i]}


def one_sided_cap(classes, bounds, baseline):
    """The mirror: every position receives at most its class bound."""
    return {p: min(baseline[p], bounds[i]) for i, c in enumerate(classes) for p in c}


def binding_cap(classes, bounds, baseline):
    return {p for i, c in enumerate(classes) for p in c if baseline[p] > bounds[i]}


def walk(n):
    """Every (partition, assignment, baseline) on n positions."""
    pos = list(range(n))
    for classes in partitions(pos):
        k = len(classes)
        for terms in itertools.product(TERMS, repeat=k):
            for base in itertools.product(BASELINES, repeat=n):
                yield classes, terms, {p: base[i] for i, p in enumerate(pos)}


def main():
    print("=" * 78)
    print("B43: proposition (i) of the counting law, enumerated")
    print("=" * 78)
    rec = {}
    for n in (3, 4, 5):
        cfgs = 0
        two_all, two_distinct = [], []
        one_all, one_distinct = [], []
        cap_all, cap_distinct = [], []
        for classes, terms, base in walk(n):
            cfgs += 1
            distinct = len(set(terms)) == len(terms)

            # --- (i-two-sided) ---
            read = as_partition(two_sided(classes, terms, base))
            if read != written(classes):
                two_all.append((classes, terms, base))
                if distinct:
                    two_distinct.append((classes, terms, base))

            # --- (i-one-sided) ---
            val = one_sided_floor(classes, terms, base)
            S = binding(classes, terms, base)
            # the claim: restricted to S, the two partitions agree
            read_S = frozenset(frozenset(b & S) for b in as_partition(val) if b & S)
            writ_S = frozenset(frozenset(c & S) for c in classes if c & S)
            if read_S != writ_S:
                one_all.append((classes, terms, base, sorted(S)))
                if distinct:
                    one_distinct.append((classes, terms, base, sorted(S)))

            # --- (i-one-sided), the mirror: an upper bound ---
            valc = one_sided_cap(classes, terms, base)
            Sc = binding_cap(classes, terms, base)
            read_Sc = frozenset(frozenset(b & Sc) for b in as_partition(valc) if b & Sc)
            writ_Sc = frozenset(frozenset(c & Sc) for c in classes if c & Sc)
            if read_Sc != writ_Sc:
                cap_all.append((classes, terms, base, sorted(Sc)))
                if distinct:
                    cap_distinct.append((classes, terms, base, sorted(Sc)))

        print("\n  n = %d positions, %d configurations walked in full" % (n, cfgs))
        print("  %-52s %8s %8s" % ("", "all", "distinct terms"))
        print("  %-52s %8d %8d"
              % ("(i-two-sided) counterexamples", len(two_all), len(two_distinct)))
        print("  %-52s %8d %8d"
              % ("(i-one-sided) lower bound, on the binding set",
                 len(one_all), len(one_distinct)))
        print("  %-52s %8d %8d"
              % ("(i-one-sided) UPPER bound, on the binding set",
                 len(cap_all), len(cap_distinct)))
        for lab, lst in (("two-sided", two_all), ("one-sided", one_all)):
            if lst:
                c = lst[0]
                print("     first %s counterexample: classes %s terms %s baseline %s"
                      % (lab, [sorted(x) for x in c[0]], list(c[1]),
                         [c[2][p] for p in sorted(c[2])]))
        # every counterexample, classified: is it always two classes sharing a term
        def collides(c):
            return len(set(c[1])) != len(c[1])
        two_by_collision = sum(1 for c in two_all if collides(c))
        one_by_collision = sum(1 for c in one_all if collides(c))
        cap_by_collision = sum(1 for c in cap_all if collides(c))
        print("  %-52s %8d %8d"
              % ("upper bound: by shared term / other shape",
                 cap_by_collision, len(cap_all) - cap_by_collision))
        print("  %-52s %8d %8d"
              % ("of those, explained by two classes sharing a term",
                 two_by_collision, one_by_collision))
        print("  %-52s %8s %8s"
              % ("residual counterexamples of any other shape",
                 len(two_all) - two_by_collision, len(one_all) - one_by_collision))
        rec["n%d" % n] = {
            "two_sided_by_shared_term": two_by_collision,
            "one_sided_by_shared_term": one_by_collision,
            "two_sided_other_shape": len(two_all) - two_by_collision,
            "one_sided_other_shape": len(one_all) - one_by_collision,
            "upper_bound_counterexamples": len(cap_all),
            "upper_bound_distinct_terms": len(cap_distinct),
            "upper_bound_by_shared_term": cap_by_collision,
            "upper_bound_other_shape": len(cap_all) - cap_by_collision,
            "configurations": cfgs,
            "two_sided_counterexamples": len(two_all),
            "two_sided_counterexamples_distinct_terms": len(two_distinct),
            "one_sided_counterexamples": len(one_all),
            "one_sided_counterexamples_distinct_terms": len(one_distinct),
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True), encoding="utf-8")
    print("\nwritten: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
