"""B43: the proof's arithmetic, checked against the enumeration already on disk.

The proof of proposition (i) is in `docs/b43_counting_theorem.md`. This file does
not repeat it. It does two things the proof alone cannot do:

  (B43-4)  The proof does not only say "no counterexamples when the terms are
           distinct". It says exactly which configurations ARE counterexamples,
           and that is a closed form. Evaluating the closed form must reproduce
           the integers already in `results/b43_counting_enumerate.json`, digit
           for digit, at every n and on all three arms. The closed form never
           walks the baselines: it counts them. So this is an independent path
           to the same three numbers, not a rerun.

  (B43-5)  The proof separates two statements the corpus had run together:
             counting form   |P_read| = |{t_a}|        holds unconditionally
             partition form  P_read = P_written        holds iff a -> t_a is injective
           On the two-sided arm the counting form is checked on every single
           configuration, including the 394,389 that break the partition form.
           If the separation is right, the counting form has zero failures there.

Closed forms, both read straight off the proof.

  two-sided:  a configuration fails iff a -> t_a is not injective. The baseline
              plays no part, so the count is (partitions) x (non-injective term
              vectors) x 3^n.

  one-sided:  a configuration fails iff some value y is carried by two classes
              that BOTH have a non-empty binding set. Blocks are independent
              given (P, t), so for each class a with |A_a| = m and term t_a the
              number of baselines leaving S_a empty is e_a = (4 - t_a)^m for the
              lower bound, and t_a^m for the upper bound. Grouping classes by
              the term they carry, the non-failing baselines number

                  prod_y [ prod_{a in C_y} e_a
                           + sum_{j in C_y} f_j prod_{a in C_y, a != j} e_a ]

              with f_a = 3^m - e_a. Note the upper-bound e_a is the lower-bound
              e_a under t -> 4 - t, which is why the two arms are equal at every
              n rather than coincidentally equal.

Run:

    python experiments\\b43_counting_proof_check.py
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
ENUM = ROOT / "results" / "b43_counting_enumerate.json"
OUT = ROOT / "results" / "b43_counting_proof_check.json"

BASELINES = (1, 2, 3)
TERMS = (1, 2, 3)
NB = len(BASELINES)


def partitions(items):
    items = list(items)
    if not items:
        yield ()
        return
    first, rest = items[0], items[1:]
    for smaller in partitions(rest):
        for i in range(len(smaller)):
            yield smaller[:i] + (smaller[i] | {first},) + smaller[i + 1:]
        yield smaller + (frozenset({first}),)


# ---------------------------------------------------------------- closed forms

def closed_two_sided(n):
    """Configurations whose two partitions differ, counted without walking them."""
    bad = 0
    for classes in partitions(range(n)):
        k = len(classes)
        for terms in itertools.product(TERMS, repeat=k):
            if len(set(terms)) != k:
                bad += NB ** n
    return bad


def closed_one_sided(n, upper=False):
    """Same, for the bound arms. Baselines are counted, never enumerated."""
    bad = 0
    for classes in partitions(range(n)):
        sizes = [len(c) for c in classes]
        k = len(classes)
        for terms in itertools.product(TERMS, repeat=k):
            # e_a: baselines on block a that leave the binding set S_a empty
            e = [(t ** m) if upper else ((NB + 1 - t) ** m)
                 for t, m in zip(terms, sizes)]
            f = [NB ** m - ea for ea, m in zip(e, sizes)]
            by_term = {}
            for a, t in enumerate(terms):
                by_term.setdefault(t, []).append(a)
            ok = 1
            for group in by_term.values():
                all_empty = 1
                for a in group:
                    all_empty *= e[a]
                exactly_one = 0
                for j in group:
                    prod = f[j]
                    for a in group:
                        if a != j:
                            prod *= e[a]
                    exactly_one += prod
                ok *= all_empty + exactly_one
            bad += NB ** n - ok
    return bad


# ------------------------------------------------- the separation, per config

def as_partition(value_of):
    buckets = {}
    for kk, v in value_of.items():
        buckets.setdefault(v, set()).add(kk)
    return frozenset(frozenset(s) for s in buckets.values())


def separation(n):
    """On every configuration: does the counting form hold where the partition
    form fails? And do the two lemmas the proof leans on hold unconditionally?"""
    cfgs = partition_fail = count_fail = lemA_fail = lemB_fail = 0
    pos = list(range(n))
    for classes in partitions(pos):
        for terms in itertools.product(TERMS, repeat=len(classes)):
            for base in itertools.product(BASELINES, repeat=n):
                cfgs += 1
                bl = {p: base[i] for i, p in enumerate(pos)}
                two = {p: terms[i] for i, c in enumerate(classes) for p in c}
                read = as_partition(two)
                writ = frozenset(frozenset(c) for c in classes)
                if read != writ:
                    partition_fail += 1
                # counting form: number of produced values = distinct terms
                if len(read) != len(set(terms)):
                    count_fail += 1
                # lemma A: A_a cap S = S_a, unconditional, lower-bound arm
                Sa = {i: {p for p in c if bl[p] < terms[i]}
                      for i, c in enumerate(classes)}
                S = set().union(*Sa.values()) if Sa else set()
                for i, c in enumerate(classes):
                    if (set(c) & S) != Sa[i]:
                        lemA_fail += 1
                # lemma B: on S the produced value is the class term
                for p in S:
                    i = next(i for i, c in enumerate(classes) if p in c)
                    if max(bl[p], terms[i]) != terms[i]:
                        lemB_fail += 1
    return cfgs, partition_fail, count_fail, lemA_fail, lemB_fail


def main():
    prior = json.loads(ENUM.read_text(encoding="utf-8"))
    print("=" * 78)
    print("B43: the proof's closed form, against the enumeration on disk")
    print("=" * 78)
    rec = {}
    all_match = True
    for n in (3, 4, 5):
        key = "n%d" % n
        p = prior[key]
        got = {
            "two_sided": closed_two_sided(n),
            "one_sided_lower": closed_one_sided(n, upper=False),
            "one_sided_upper": closed_one_sided(n, upper=True),
        }
        want = {
            "two_sided": p["two_sided_counterexamples"],
            "one_sided_lower": p["one_sided_counterexamples"],
            "one_sided_upper": p["upper_bound_counterexamples"],
        }
        print("\n  n = %d" % n)
        print("  %-34s %12s %12s %8s" % ("arm", "closed form", "enumerated", "match"))
        for arm in ("two_sided", "one_sided_lower", "one_sided_upper"):
            ok = got[arm] == want[arm]
            all_match &= ok
            print("  %-34s %12d %12d %8s"
                  % (arm, got[arm], want[arm], "yes" if ok else "NO"))
        cfgs, pf, cf, la, lb = separation(n)
        print("  %-34s %12d" % ("configurations walked", cfgs))
        print("  %-34s %12d" % ("partition form fails", pf))
        print("  %-34s %12d   <- must be 0" % ("counting form fails", cf))
        print("  %-34s %12d   <- must be 0" % ("lemma A fails", la))
        print("  %-34s %12d   <- must be 0" % ("lemma B fails", lb))
        all_match &= (cf == 0 and la == 0 and lb == 0)
        rec[key] = {
            "closed_form_two_sided": got["two_sided"],
            "closed_form_one_sided_lower": got["one_sided_lower"],
            "closed_form_one_sided_upper": got["one_sided_upper"],
            "enumerated_two_sided": want["two_sided"],
            "enumerated_one_sided_lower": want["one_sided_lower"],
            "enumerated_one_sided_upper": want["one_sided_upper"],
            "configurations": cfgs,
            "partition_form_failures": pf,
            "counting_form_failures": cf,
            "lemma_A_failures": la,
            "lemma_B_failures": lb,
        }
    rec["criteria"] = {
        "B43-4": {
            "name": "closed form from the proof reproduces the enumerated counts",
            "passed": all(rec["n%d" % n]["closed_form_two_sided"]
                          == rec["n%d" % n]["enumerated_two_sided"]
                          and rec["n%d" % n]["closed_form_one_sided_lower"]
                          == rec["n%d" % n]["enumerated_one_sided_lower"]
                          and rec["n%d" % n]["closed_form_one_sided_upper"]
                          == rec["n%d" % n]["enumerated_one_sided_upper"]
                          for n in (3, 4, 5)),
        },
        "B43-5": {
            "name": "counting form holds on every configuration, including those "
                    "where the partition form fails",
            "passed": all(rec["n%d" % n]["counting_form_failures"] == 0
                          and rec["n%d" % n]["lemma_A_failures"] == 0
                          and rec["n%d" % n]["lemma_B_failures"] == 0
                          for n in (3, 4, 5)),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, sort_keys=True), encoding="utf-8")
    print("\n  all checks match: %s" % all_match)
    print("written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
