"""B21 gate zero, the counting half: how many A+H pairs sit where the floor is low.

One HTTP request. Nothing is bought and nothing is deleted.

Section 8 of the pre-work sheet computed the resolution floor from the exchange
rulebook rather than from data: it runs from about 10 to 47 basis points and is
set almost entirely by the Hong Kong tick, since the mainland tick is a flat
0.01 yuan. The best band is an H price of 20 to 50 HKD, where the tick fell 60
per cent on 2025-08-04 and the floor is 10 to 14 bp.

**The question this file answers, and the only one.** Of the roughly 150 A+H
pairs, how many are in that band? That number decides whether the tick-change
arm has a sample at all, and it costs one page fetch.

Reads and prints the pairs themselves, not only the counts: a count is what the
twelfth category error leaves intact while the identities go wrong.

Usage::

    python experiments/b21_probe.py            # fetch if absent, then count
    python experiments/b21_probe.py --recount  # parse the cached page only

The fetched page is cached under ``data/raw/b21/``. **It is never deleted.** A
short or unparseable download is renamed with a ``.partial`` suffix and the next
run fetches again, so a truncated file can never be read as if it were whole.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "raw" / "b21"
PAGE = CACHE / "aastocks_ah.html"
SRC = "https://www.aastocks.com/en/stocks/market/ah.aspx"

# A browser string. The plain urllib default is refused by this host.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# No Accept-Encoding header: urllib does not decompress, and a gzip body read as
# text fails on byte 0x8b. That cost a run once already.

MIN_PAIRS = 100          # the index carried 149 in July 2026; well under it is a bad page

# The Hong Kong spread table, read from the rulebook rather than assumed.
# (lower, upper, tick) with lower exclusive, upper inclusive.
SPREAD_OLD = [(0.01, 0.25, 0.001), (0.25, 0.50, 0.005), (0.50, 10, 0.010),
              (10, 20, 0.020), (20, 100, 0.050)]
SPREAD_P1 = [(0.01, 0.25, 0.001), (0.25, 0.50, 0.005), (0.50, 10, 0.010),
             (10, 20, 0.010), (20, 50, 0.020), (50, 100, 0.050)]
SPREAD_P2 = [(0.01, 0.25, 0.001), (0.25, 0.50, 0.005), (0.50, 10, 0.005),
             (10, 20, 0.010), (20, 50, 0.020), (50, 100, 0.050)]
PHASES = [("to 2025-08-03", SPREAD_OLD),
          ("2025-08-04 on", SPREAD_P1),
          ("2026-08-03 on", SPREAD_P2)]

TICK_A = 0.01            # flat, every price, both mainland exchanges
FX = 0.91                # CNY per HKD, order of magnitude only; the FX leg is < 3 bp
TICK_FX = 1e-4


def tick(price: float, table) -> float | None:
    for lo, hi, t in table:
        if lo < price <= hi:
            return t
    return None


def floor_bp(price_a: float, price_h: float, tick_h: float) -> float:
    """Eight legs, each carrying half a tick, summed without assuming cancellation."""
    return 1e4 * (2 * 0.5 * TICK_A / price_a
                  + 2 * 0.5 * tick_h / price_h
                  + 4 * 0.5 * TICK_FX / FX)


# --------------------------------------------------------------------------


def fetch() -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    if PAGE.exists() and PAGE.stat().st_size > 0:
        print(f"cached  {PAGE}  {PAGE.stat().st_size:,} bytes")
        return PAGE
    print(f"fetching {SRC}")
    req = urllib.request.Request(SRC, headers={"User-Agent": UA})
    body = urllib.request.urlopen(req, timeout=60).read()
    text = body.decode("utf-8", errors="replace")
    PAGE.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote   {PAGE}  {len(text):,} chars")
    return PAGE


def quarantine(path: Path, reason: str) -> None:
    """Rename rather than delete, so a bad page is still on disk to look at.

    Takes the path it was handed. An earlier version renamed the module-level
    ``PAGE`` instead, which raised ``FileNotFoundError`` from inside the error
    handler whenever the parsed file was anything else -- the error surfacing one
    layer away from where it was, which is the shape this repository keeps
    paying for.
    """
    n = 0
    while True:
        dest = path.with_suffix(f".html.partial{'' if n == 0 else n}")
        if not dest.exists():
            break
        n += 1
    path.rename(dest)
    print(f"!! {reason}")
    print(f"!! renamed to {dest.name}. Nothing was deleted. Run again to refetch.")
    sys.exit(2)


def parse(path: Path, min_pairs: int = MIN_PAIRS) -> list[dict]:
    """Pair every H code with the next A code, and read the two prices between.

    Fragile by nature, so it self-checks: the two code counts must match and the
    total must be plausible. A page that changed shape fails loudly here rather
    than returning a short list that looks like a finding.
    """
    html = path.read_text(encoding="utf-8")
    n_h = len(re.findall(r"\b\d{5}\.HK\b", html))
    n_a = len(re.findall(r"\b\d{6}\.(?:SH|SZ)\b", html))
    print(f"codes on page: {n_h} H, {n_a} A")
    if n_h == 0 or n_a == 0:
        quarantine(path, "no codes found; the page is not the A+H table")
    if n_h != n_a:
        print(f"!! the two sides do not match: {n_h} H against {n_a} A, "
              f"a difference of {abs(n_h - n_a)}.")
        print("!! Not fatal and not ignored. One side carries a code the other "
              "does not, so at\n!! least one row is malformed or one code "
              "appears somewhere that is not a row.\n!! Reported here because a "
              "run that prints only totals would never show it.")

    row = re.compile(
        r">([A-Z0-9][A-Z0-9 .,&'/()-]{2,40})<.*?"
        r"(\d{5})\.HK.*?"
        r"([0-9]+\.[0-9]+).*?"
        r"(\d{6})\.(SH|SZ).*?"
        r"([0-9]+\.[0-9]+)",
        re.S,
    )
    out = []
    for m in row.finditer(html):
        name, h_code, h_px, a_code, mkt, a_px = m.groups()
        try:
            h, a = float(h_px), float(a_px)
        except ValueError:
            continue
        if not (0 < h < 100000 and 0 < a < 100000):
            continue
        out.append({"name": name.strip()[:24], "h": f"{h_code}.HK",
                    "a": f"{a_code}.{mkt}", "px_h": h, "px_a": a})
    seen, uniq = set(), []
    for r in sorted(out, key=lambda r: r["h"]):
        if r["h"] in seen:
            continue
        seen.add(r["h"])
        uniq.append(r)
    print(f"pairs parsed: {len(uniq)} unique of {len(out)} matched "
          f"({len(out) / max(1, len(uniq)):.2f} appearances each)")
    if len(uniq) < min_pairs:
        quarantine(path,
                   f"only {len(uniq)} pairs parsed, under the floor of {min_pairs}")
    return uniq


def report(pairs: list[dict]) -> None:
    print()
    print("=" * 78)
    print("B21-0  where the pairs sit, by Hong Kong price band")
    print("=" * 78)
    bands = [(0.0, 0.5), (0.5, 10), (10, 20), (20, 50), (50, 100), (100, 1e9)]
    print(f"{'H price band':>16} {'pairs':>7}   {'floor now (bp), min..med..max':>34}")
    for lo, hi in bands:
        sel = [r for r in pairs if lo < r["px_h"] <= hi]
        if not sel:
            print(f"{f'{lo:g} - {hi:g}':>16} {0:>7}")
            continue
        f = sorted(floor_bp(r["px_a"], r["px_h"], tick(r["px_h"], SPREAD_P2) or 0.05)
                   for r in sel)
        med = f[len(f) // 2]
        print(f"{f'{lo:g} - {hi:g}':>16} {len(sel):>7}   "
              f"{f[0]:>10.1f} {med:>10.1f} {f[-1]:>10.1f}")

    target = sorted((r for r in pairs if 20 < r["px_h"] <= 50), key=lambda r: r["h"])
    print()
    print(f"B21-0  the band section 8 picked, 20 < H <= 50 HKD: {len(target)} pairs")
    print("       printed in full, because a count is what stays right when the "
          "identities go wrong")
    print(f"{'H':>12} {'A':>12} {'px_H':>9} {'px_A':>9} "
          + "  ".join(f"{lab:>14}" for lab, _ in PHASES))
    for r in target:
        line = f"{r['h']:>12} {r['a']:>12} {r['px_h']:>9.3f} {r['px_a']:>9.3f}"
        for _, tbl in PHASES:
            t = tick(r["px_h"], tbl)
            line += f"{floor_bp(r['px_a'], r['px_h'], t):>14.1f}" if t else f"{'-':>14}"
        print(line)

    print()
    print("B21-0  what changed on 2025-08-04 for this band, and for whom")
    moved = [r for r in target
             if tick(r["px_h"], SPREAD_OLD) != tick(r["px_h"], SPREAD_P1)]
    print(f"       pairs whose Hong Kong tick fell on that date: {len(moved)} of {len(target)}")
    if moved:
        drop = sorted(
            1 - floor_bp(r["px_a"], r["px_h"], tick(r["px_h"], SPREAD_P1))
            / floor_bp(r["px_a"], r["px_h"], tick(r["px_h"], SPREAD_OLD))
            for r in moved)
        print(f"       floor fell by {drop[0]:.1%} to {drop[-1]:.1%}, "
              f"median {drop[len(drop)//2]:.1%}")
    print()
    print("=" * 78)
    print("B21-1  the two tick cuts, and who is treated at each")
    print("=" * 78)
    bands2 = [(0.5, 10), (10, 20), (20, 50), (50, 100), (100, 1e9)]
    print(f"{'H price band':>16} {'pairs':>7} {'2025-08-04':>13} {'2026-08-03':>13}")
    flip = 0
    for lo, hi in bands2:
        sel = [r for r in pairs if lo < r["px_h"] <= hi]
        if not sel:
            continue
        mid = (lo + min(hi, lo * 3)) / 2
        e1 = "treated" if tick(mid, SPREAD_OLD) != tick(mid, SPREAD_P1) else "control"
        e2 = "treated" if tick(mid, SPREAD_P1) != tick(mid, SPREAD_P2) else "control"
        if e1 != e2:
            flip += len(sel)
        print(f"{f'{lo:g} - {hi:g}':>16} {len(sel):>7} {e1:>13} {e2:>13}"
              + ("   <- flips" if e1 != e2 else ""))
    print()
    print(f"       {flip} pairs change side between the two events, and the pairs "
          f"above\n       HKD 50 are control at both. **A band-specific trend "
          f"cannot produce two\n       opposite assignments**, so this is a "
          f"crossover and not a single before-and-after.")

    print()
    print("=" * 78)
    print("B21-2  the worst cell, not the average cell")
    print("=" * 78)
    import math

    def sig(r):
        """Raw premium in basis points. An upper bound on the index, and the
        order of magnitude the floor has to be read against."""
        return 1e4 * abs(math.log((r["px_a"] / FX) / r["px_h"]))

    def ratio(r):
        return sig(r) / floor_bp(r["px_a"], r["px_h"],
                                 tick(r["px_h"], SPREAD_P2) or 0.05)

    print("       **The worst cell is not the one with the highest floor.** The "
          "floor spans one\n       order of magnitude across the page and the "
          "premium spans three, so what\n       decides readability is the "
          "premium sitting near zero, not the tick being\n       coarse. Ranked "
          "by premium over floor, lowest first:")
    print(f"{'name':>26} {'H':>10} {'px_H':>8} {'floor':>7} {'prem bp':>9} {'ratio':>7}")
    for r in sorted(pairs, key=ratio)[:12]:
        f = floor_bp(r["px_a"], r["px_h"], tick(r["px_h"], SPREAD_P2) or 0.05)
        print(f"{r.get('name', '?'):>26} {r['h']:>10} {r['px_h']:>8.3f} "
              f"{f:>7.1f} {sig(r):>9.0f} {ratio(r):>7.1f}")
    print()
    for cut in (2, 3, 5, 10):
        n = sum(1 for r in pairs if ratio(r) < cut)
        print(f"       premium under {cut:>2}x the floor: {n:>3} of {len(pairs)} pairs")
    print()
    print("       **These are not screened out.** A pair whose index sits under a "
          "few times\n       the floor lands in the third verdict, undecidable, "
          "which is where it belongs.\n       Screening on the premium would be "
          "selecting on the outcome; the floor is\n       known from the "
          "rulebook before any price is read, so the ratio can decide the\n"
          "       verdict per pair per day without any screen at all.")
    for cut in (50, 100, 150):
        n = sum(1 for r in pairs
                if floor_bp(r["px_a"], r["px_h"],
                            tick(r["px_h"], SPREAD_P2) or 0.05) > cut)
        print(f"       (floor above {cut:>3} bp: {n:>3} of {len(pairs)} pairs)")

    print()
    print("       Prices here are one snapshot and a stock moves between bands, so "
          "this is\n       the order of magnitude of the sample, not the sample. "
          "The panel has to\n       assign the band per day.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recount", action="store_true",
                    help="parse the cached page and do not fetch")
    args = ap.parse_args()
    if args.recount and not PAGE.exists():
        print(f"no cached page at {PAGE}")
        return 2
    report(parse(PAGE if args.recount else fetch()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
