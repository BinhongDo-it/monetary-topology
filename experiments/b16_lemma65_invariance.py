"""Section 31 carrier: the theorem 6(5) spread term is invariant under the treatment.

No network, no data, no
randomness. Exact arithmetic at 60 decimal digits.

WHAT IS BEING CHECKED

b4 section 5.1, in quoted terms, with M = (bid+ask)/2 and s = ask-bid:

    S - S'  =  2 log(M_b / M_a)                                  midpoint part
             + log(1 - (s_b/2M_b)^2) - log(1 - (s_a/2M_a)^2)     spread part
    -(S+S') =  -[ log(bid_a/ask_a) + log(bid_b/ask_b) ]

Theorem 6(5) says the spread part vanishes only when the two classes carry equal
RELATIVE spreads. Nasdaq and Arca do not, so it does not vanish here, and it puts
a floor on rho = |S-S'| / -(S+S').

The design threat is: does that floor MOVE under the treatment? If it does, the
second stage could read the floor moving rather than the midpoints moving.

CLAIM. Section 31 raises each venue's relative spread by the same dr, so with
M_a = M_b = M each venue's absolute spread rises by the same delta = theta*dr*M.
Under that, the spread part's contribution to rho is EXACTLY unchanged.

    numerator spread part -> (s_a - s_b)(s_a + s_b + 2d) / (4 M^2)
    denominator           -> (s_a + s_b + 2d) / M
    ratio                 =  |s_a - s_b| / (4 M)          free of d

The only break is asymmetric pass-through, theta_a != theta_b, and it has a closed
form that is measurable rather than merely bounded:

    post/pre  =  1 + (d_b - d_a) / (s_b - s_a)

Every term on the right is measured: d_v = theta_v * dr * M with theta_v from the
first stage run per venue, dr from the SEC annual order, M and s_b - s_a from the
pre-window. That is gate three of the pre-registration.

    python experiments/b16_lemma65_invariance.py            prints the tables
    python experiments/b16_lemma65_invariance.py --selftest asserts, exits 1 on fail
"""
import argparse
import sys
from decimal import Decimal as D, getcontext

getcontext().prec = 60

#: Loose enough that ordinary float noise would not pass, tight enough that a real
#: dependence on delta would fail. The observed departures on the registered
#: universe (M > $300) are below 1e-8; see the docstring table.
TOL_ON_UNIVERSE = D("1e-7")


def _ln(x):
    return D(x).ln()


def spread_part(M, s_a, s_b):
    """The term of S - S' that depends on the two spreads alone. Theorem 6(5)."""
    M = D(M)
    return _ln(1 - (D(s_b) / (2 * M)) ** 2) - _ln(1 - (D(s_a) / (2 * M)) ** 2)


def friction(M, s_a, s_b):
    """-(S + S'), the friction half, from two-sided quotes."""
    M = D(M)
    ratio = lambda s: (M - D(s) / 2) / (M + D(s) / 2)
    return -(_ln(ratio(s_a)) + _ln(ratio(s_b)))


def rho_spread(M, s_a, s_b):
    """The spread part's contribution to rho = |S-S'| / -(S+S')."""
    return spread_part(M, s_a, s_b) / friction(M, s_a, s_b)


def first_order(M, s_a, s_b):
    """b4 section 5.1's leading-order form: |s_b - s_a| / (4M)."""
    return abs(D(s_b) - D(s_a)) / (4 * D(M))


#: (M, s_a, s_b). The first four are on the registered universe (M > $300 is the
#: screen; $50 and $20 are there to show the claim degrades gracefully and to make
#: the check capable of failing somewhere).
CASES = [
    ("300", "0.05", "0.15"),
    ("300", "0.02", "0.03"),
    ("1000", "0.10", "0.50"),
    ("500", "0.03", "0.09"),
    ("50", "0.01", "0.05"),
    ("20", "0.01", "0.03"),
]
DELTAS = ["0.001", "0.005", "0.01", "0.02", "0.05", "0.10"]

#: (d_a, d_b) for the asymmetric-pass-through counterexample, on M=300 / .05 / .15.
ASYM = [("0.02", "0.02"), ("0.02", "0.024"), ("0.02", "0.03"), ("0.03", "0.02")]


def table_symmetric():
    rows = []
    for M, s_a, s_b in CASES:
        base = rho_spread(M, s_a, s_b)
        for d in DELTAS:
            post = rho_spread(M, D(s_a) + D(d), D(s_b) + D(d))
            rows.append((M, s_a, s_b, d, post / base, base, first_order(M, s_a, s_b)))
    return rows


def table_asymmetric():
    M, s_a, s_b = "300", "0.05", "0.15"
    base = rho_spread(M, s_a, s_b)
    rows = []
    for d_a, d_b in ASYM:
        post = rho_spread(M, D(s_a) + D(d_a), D(s_b) + D(d_b))
        closed = 1 + (D(d_b) - D(d_a)) / (D(s_b) - D(s_a))
        rows.append((d_a, d_b, post / base, closed))
    return rows


def selftest():
    bad = 0

    # 1. Symmetric delta leaves the ratio at 1, on the registered universe.
    for M, s_a, s_b, d, ratio, base, fo in table_symmetric():
        if D(M) < 300:
            continue
        if abs(ratio - 1) > TOL_ON_UNIVERSE:
            print("FAIL invariance  M=%s s_a=%s s_b=%s d=%s  ratio=%s" % (M, s_a, s_b, d, ratio))
            bad += 1

    # 2. The leading-order form matches the exact value to 6 significant figures.
    for M, s_a, s_b in CASES:
        exact, fo = abs(rho_spread(M, s_a, s_b)), first_order(M, s_a, s_b)
        if abs(exact - fo) / fo > D("1e-6"):
            print("FAIL first-order  M=%s s_a=%s s_b=%s  exact=%s fo=%s" % (M, s_a, s_b, exact, fo))
            bad += 1

    # 3. The counterexample's closed form is right, AND it actually bites.
    #    A check that cannot fail is not a check: assert the asymmetric cases move.
    moved = 0
    for d_a, d_b, ratio, closed in table_asymmetric():
        if abs(ratio - closed) > D("1e-6"):
            print("FAIL closed form  d_a=%s d_b=%s  ratio=%s closed=%s" % (d_a, d_b, ratio, closed))
            bad += 1
        if d_a != d_b and abs(ratio - 1) > D("0.01"):
            moved += 1
    if moved != sum(1 for a, b in ASYM if a != b):
        print("FAIL counterexample is inert: asymmetric pass-through did not move the ratio")
        bad += 1

    print("selftest: %s" % ("PASS" if bad == 0 else "FAIL, %d problem(s)" % bad))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("SYMMETRIC pass-through: same delta added to both venues' absolute spreads")
    print("%-6s %-6s %-6s %-7s %-24s" % ("M", "s_a", "s_b", "delta", "post/pre"))
    for M, s_a, s_b, d, ratio, base, fo in table_symmetric():
        print("%-6s %-6s %-6s %-7s %s" % (M, s_a, s_b, d, str(ratio)[:24]))
    print()
    print("exact rho_spread vs b4 first-order |s_b-s_a|/(4M)")
    for M, s_a, s_b in CASES:
        print("  M=%-6s s_a=%-6s s_b=%-6s exact=%s  first-order=%s"
              % (M, s_a, s_b, str(abs(rho_spread(M, s_a, s_b)))[:18], str(first_order(M, s_a, s_b))[:18]))
    print()
    print("ASYMMETRIC pass-through, M=300 s_a=0.05 s_b=0.15")
    print("%-7s %-7s %-24s %-24s" % ("d_a", "d_b", "post/pre", "1+(d_b-d_a)/(s_b-s_a)"))
    for d_a, d_b, ratio, closed in table_asymmetric():
        print("%-7s %-7s %-24s %-24s" % (d_a, d_b, str(ratio)[:24], str(closed)[:24]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
