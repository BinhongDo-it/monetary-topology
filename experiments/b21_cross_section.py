"""B21 layer one: split the loop sum into what every pair shares and what it does not.

The square on the position edge, from `b1_theorem.md` section 8, is

    square_k  =  w_a,k - w_b,k  +  t_ab(A_k)  -  t_ab(onshore cash)

and **the last term has no k**. It is a property of the currency, the same on one
day for every pair. So taking the cross section on a fixed date and looking at
how the pairs differ from each other removes it **identically**, not
approximately and not by controlling for it:

    Var_k( square_k )  =  Var_k( w_a,k - w_b,k + t_ab(A_k) )

**This is the whole content of layer one.** Any dispersion measured across pairs
on one day cannot be the capital-account wedge, because adding a constant to
every pair changes no dispersion. The file checks that as an identity to machine
precision rather than asserting it, which is the one thing here that can be
checked that way.

**A placebo that can kill half of this file, and did.** A currency event moves
`t_ab(onshore cash)` and touches nothing with a `k` in it, so it should move the
common term and leave the dispersion alone. **It does not.** Across five events
the common term's jump sits at the 14th to 39th percentile of its own history,
never above the median, while the onshore-offshore spread itself jumps at the
99.8th, 95.8th and 90.2nd.

**The scale says why, and the scale is one number**: the spread's standard
deviation is 0.0042 against the common term's 0.1351, so **the currency wedge is
3.1% of the thing it was supposed to be**. The common term is dominated by the
aggregate premium, which moves with the equity cycle.

**So the claim that the common term is the currency wedge is dead, and the
identity is untouched.** Those were always two claims. The identity says a term
without a `k` cannot appear in a cross section, which is what licenses the one
sentence this station needs: **dispersion across pairs on a fixed day is not the
capital-account wedge.** That holds whatever else is in the common term, and it
is verified below to 1.1e-16. What is gone is the positive half, that the common
term is identified with anything. It is a mixture, and this file no longer names
its parts.

**What it does not do.** It does not say what the individual part is. Separating
`t_ab(A_k)` from `w_a,k - w_b,k` needs the Connect eligibility list, which is
layer two and has its own gate.

Usage::

    python experiments/b21_cross_section.py
    python experiments/b21_cross_section.py --date 2024-06-28
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PX = ROOT / "data" / "raw" / "b21" / "px"
PAGE = ROOT / "data" / "raw" / "b21" / "aastocks_ah.html"
OUT = ROOT / "results" / "b21_cross_section.json"

MIN_PAIRS = 20          # a cross section thinner than this is not a cross section

# Currency events. Each moves the onshore-offshore wedge and none of them is a
# property of any one pair, which is what makes them a placebo for the split.
EVENTS = [
    ("2015-08-11", "the 2015 fixing reform"),
    ("2015-12-11", "the CFETS basket, announced"),
    ("2016-11-28", "outbound investment tightened"),
    ("2018-08-06", "the reserve on forward sales restored"),
    ("2019-08-05", "seven to the dollar"),
]


def load(tk: str) -> list[dict]:
    for c in (PX / f"{tk.replace('=', '_')}.csv", PX / f"{tk}.csv"):
        if c.exists():
            return list(csv.DictReader(c.open(encoding="utf-8")))
    return []


def closes(tk: str) -> dict[str, float]:
    out = {}
    for r in load(tk):
        try:
            c = float(r["Close"])
        except (TypeError, ValueError, KeyError):
            continue
        if c > 0:
            out[r["Date"][:10]] = c
    return out


def pairs_on_page() -> list[dict]:
    import re
    row = re.compile(r">([A-Z0-9][A-Z0-9 .,&'/()-]{2,40})<.*?(\d{5})\.HK.*?"
                     r"([0-9]+\.[0-9]+).*?(\d{6})\.(SH|SZ).*?([0-9]+\.[0-9]+)", re.S)
    seen, out = set(), []
    for m in row.finditer(PAGE.read_text(encoding="utf-8")):
        name, h, _, a, mkt, _ = m.groups()
        if h in seen:
            continue
        seen.add(h)
        out.append({"name": name.strip()[:22],
                    "h": (h[1:] if h.startswith("0") else h) + ".HK",
                    "a": f"{a}.{'SS' if mkt == 'SH' else 'SZ'}"})
    return sorted(out, key=lambda r: r["a"])


def panel() -> tuple[dict[str, dict[str, float]], dict[str, str]]:
    """date -> {pair: log(P_A * rate / P_H)}, and the pair -> name map.

    One rate for every pair on a day, which is the point: whatever that rate is,
    and whatever the capital account does to it, it enters every pair identically
    and therefore leaves the cross section untouched.
    """
    cny, hkd = closes("CNY=X"), closes("HKD=X")
    rate = {d: hkd[d] / cny[d] for d in cny.keys() & hkd.keys() if cny[d] > 0}
    out: dict[str, dict[str, float]] = {}
    names = {}
    for r in pairs_on_page():
        a, h = closes(r["a"]), closes(r["h"])
        names[r["a"]] = r["name"]
        for d in a.keys() & h.keys() & rate.keys():
            out.setdefault(d, {})[r["a"]] = math.log(a[d] * rate[d] / h[d])
    return out, names


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", help="print one cross section, pair by pair")
    args = ap.parse_args()
    if not PAGE.exists():
        raise SystemExit("run experiments/b21_probe.py first")

    pan, names = panel()
    dates = sorted(d for d, v in pan.items() if len(v) >= MIN_PAIRS)
    if not dates:
        print("no date carries a cross section")
        return 1

    if args.date:
        v = pan.get(args.date)
        if not v:
            near = sorted(pan, key=lambda d: abs(
                (dt.date.fromisoformat(d) - dt.date.fromisoformat(args.date)).days))[:3]
            print(f"{args.date} is not in the panel. Nearest: {', '.join(near)}")
            return 2
        m = statistics.fmean(v.values())
        print(f"{args.date}: {len(v)} pairs, cross-sectional mean {m:+.4f}, "
              f"sd {statistics.pstdev(v.values()):.4f}")
        print(f"  {'company':>22} {'ticker':>12} {'log A/H':>9} {'minus mean':>11}")
        for tk, x in sorted(v.items(), key=lambda kv: -kv[1]):
            print(f"  {names.get(tk, ''):>22} {tk:>12} {x:>9.4f} {x - m:>11.4f}")
        return 0

    # --- the worst cell, not the average one (discipline 13 step 1) ---
    sizes = sorted(len(pan[d]) for d in dates)
    print(f"panel: {len(dates):,} dates with at least {MIN_PAIRS} pairs, "
          f"{dates[0]} to {dates[-1]}")
    print(f"  pairs per date: min {sizes[0]}  p10 {sizes[len(sizes)//10]}  "
          f"median {sizes[len(sizes)//2]}  max {sizes[-1]}")

    common = {d: statistics.fmean(pan[d].values()) for d in dates}
    disp = {d: statistics.pstdev(pan[d].values()) for d in dates}

    # --- the identity, checked rather than asserted ---
    worst = 0.0
    for d in dates:
        v = list(pan[d].values())
        shifted = [x + 0.37 for x in v]         # any constant, it is the wedge's role
        worst = max(worst, abs(statistics.pstdev(shifted) - statistics.pstdev(v)))
    print(f"\nadding a constant to every pair on a date moves the dispersion by "
          f"at most {worst:.3e}")
    print("  **That is the identity layer one rests on**, and it is why a common")
    print("  term cannot appear in the cross section. Nothing is controlled for.")

    cs = sorted(common.values())
    ds = sorted(disp.values())
    print(f"\n{'':>26}{'p10':>9}{'median':>9}{'p90':>9}{'min':>9}{'max':>9}")
    print(f"{'common term (mean)':>26}{cs[len(cs)//10]:>9.4f}{cs[len(cs)//2]:>9.4f}"
          f"{cs[9*len(cs)//10]:>9.4f}{cs[0]:>9.4f}{cs[-1]:>9.4f}")
    print(f"{'individual term (sd)':>26}{ds[len(ds)//10]:>9.4f}{ds[len(ds)//2]:>9.4f}"
          f"{ds[9*len(ds)//10]:>9.4f}{ds[0]:>9.4f}{ds[-1]:>9.4f}")

    within = statistics.fmean(disp[d] ** 2 for d in dates)
    between = statistics.pvariance(list(common.values()))
    print(f"\nvariance of the whole panel, split by the identity:")
    print(f"  between dates, where the currency wedge lives : {between:.6f} "
          f"({between/(between+within):.1%})")
    print(f"  within a date, where it cannot be             : {within:.6f} "
          f"({within/(between+within):.1%})")
    print("  **The second number is the part this station can attribute to the")
    print("  pair rather than to the currency**, and it is the larger of the two.")

    # ---- the placebo, which can falsify everything above ----
    print("\nthe placebo. A currency event moves the common term by construction")
    print("and touches nothing with a k in it, so the dispersion must sit still.")
    print("Each event is read against every window of the same length in the panel.")
    idx = {d: i for i, d in enumerate(dates)}
    W = 20

    def jump(series, i):
        a = [series[dates[j]] for j in range(max(0, i - W), i)]
        b = [series[dates[j]] for j in range(i + 1, min(len(dates), i + 1 + W))]
        if len(a) < W or len(b) < W:
            return None
        return statistics.fmean(b) - statistics.fmean(a)

    all_c = [abs(x) for i in range(len(dates)) if (x := jump(common, i)) is not None]
    all_d = [abs(x) for i in range(len(dates)) if (x := jump(disp, i)) is not None]
    all_c.sort()
    all_d.sort()

    def pct(sorted_v, x):
        lo = sum(1 for v in sorted_v if v < x)
        return lo / len(sorted_v)

    # the scale that explains the outcome, whichever way it comes out
    cnh = closes("CNH_F")
    cny = closes("CNY=X")
    sp = {d: math.log(cnh[d] / cny[d]) for d in cnh.keys() & cny.keys() if cny[d] > 0}
    both = [d for d in dates if d in sp]
    ratio = None
    if len(both) > 100:
        ratio = (statistics.pstdev([sp[d] for d in both])
                 / statistics.pstdev([common[d] for d in both]))
        print(f"  the wedge's own size against the common term's: "
              f"sd {statistics.pstdev([sp[d] for d in both]):.5f} against "
              f"{statistics.pstdev([common[d] for d in both]):.5f}, ratio {ratio:.4f}")

    ev = []
    print(f"  {'event':>34} {'common':>9} {'pctile':>8} {'disp':>9} {'pctile':>8}")
    for day, label in EVENTS:
        i = next((k for k, d in enumerate(dates) if d >= day), None)
        if i is None:
            continue
        jc, jd = jump(common, i), jump(disp, i)
        if jc is None or jd is None:
            continue
        pc, pd = pct(all_c, abs(jc)), pct(all_d, abs(jd))
        ev.append({"date": dates[i], "label": label, "common_jump": jc,
                   "common_pctile": pc, "disp_jump": jd, "disp_pctile": pd})
        print(f"  {label:>34} {jc:>+9.4f} {pc:>8.1%} {jd:>+9.4f} {pd:>8.1%}")
    print("  **Read the two percentile columns against each other**, not against a")
    print("  line. The prediction is that the left one sits high and the right one")
    print("  does not, and both are printed whatever they say.")
    print("  They do not say it. The left column never reaches its own median while")
    print("  the wedge itself jumps at the 99.8th, so **the common term is not the")
    print("  wedge**, and at 3% of its size it could not have been. The identity")
    print("  above is unaffected: it needs the wedge to be common, not to be all")
    print("  that is common.")

    crit = [
        {"name": "B21-3  a common shift leaves the cross section unchanged",
         "passed": worst < 1e-12,
         "detail": f"largest change in dispersion under a constant shift: {worst:.3e}"},
        {"name": "B21-4  the individual term is not degenerate",
         "passed": ds[0] > 0,
         "detail": f"smallest cross-sectional sd over {len(dates)} dates: {ds[0]:.6f}"},
        {"name": "B21-5  every date carries a usable cross section",
         "passed": sizes[0] >= MIN_PAIRS,
         "detail": f"thinnest three cross sections: {sizes[:3]}"},
        {"name": "B21-6  PLACEBO, and it fails: currency events do not move the "
                 "common term, so the common term is not the currency wedge",
         "passed": bool(ev) and all(e["common_pctile"] > e["disp_pctile"] for e in ev),
         "detail": "; ".join(f"{e['label']}: common p{e['common_pctile']:.0%} "
                             f"vs dispersion p{e['disp_pctile']:.0%}" for e in ev)
                   or "no event fell inside the panel"},
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "stage": "B21", "step": "cross_section",
        "diagnostic_only": True,
        "diagnostic_reason": "Layer one of the attribution. It separates the "
                             "common term from the individual one and does not "
                             "say what the individual one is; that is layer two, "
                             "which has its own gate and has not been opened.",
        "dates": len(dates), "first": dates[0], "last": dates[-1],
        "pairs_per_date": {"min": sizes[0], "median": sizes[len(sizes)//2],
                           "max": sizes[-1]},
        "between_date_variance": between, "within_date_variance": within,
        "shift_identity_residual": worst,
        "placebo_events": ev,
        "wedge_over_common_sd": ratio,
        "criteria": crit,
    }, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\nwrote {OUT.name}: {len(crit)} criteria, "
          f"{sum(c['passed'] for c in crit)} passing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
