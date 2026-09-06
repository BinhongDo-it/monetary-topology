"""B34, LFS arm, step 2: the p(a, t) profile. Draw only, judge nothing.

Name
----
The LFS arm and the ASHE arm both have a "step 2" and they are different
pipelines. `b34_step2_extract.py` and `b34_step3_did.py` belong to the ASHE
arm (arm five, closed). This file is the LFS arm and follows
`b34_step1_cells.py`. Do not renumber either set: results documents cite both
by file name.

What this step does
-------------------
For each single year of age `a`, compute

    p(a, t) = share of employees at that age whose hourly pay is below R(t)

where R(t) is ONE threshold applied to every age. Using each age's own
statutory rate would carve the answer out of the question, which is the
circularity this design exists to avoid. Under a common threshold the profile
does not know where the band boundaries are, so where it bends is a reading.

Rate year 2021-22 (1 April 2021 to 31 March 2022), from SI 2021/329:

    main  R = 8.91   national living wage, aged 23 or over  (reg 2(2))
    alt   R = 8.36   aged 21 but under 23                   (reg 2(3)(a))

Both are drawn. Neither is picked here. Which one carries the reading is a
resolution question and the table below is what answers it: an age whose p
sits against 0 or against 1 has no room left to bend.

This step judges nothing. It prints no PASS and no FAIL. The record it writes
carries `diagnostic_only` for that reason.

Order of the printout, and why
------------------------------
1. Definitional self-report: which source variable each role matched, per file.
2. Enumerate before selecting: every value of the status column with its
   count, on the subset that has hourly pay. Nothing is filtered by status
   here; the enumeration is what a later step selects from.
3. Objects, not counts: the twenty smallest and twenty largest hourly pay
   values with the age and status attached to each. A profile of shares below
   a threshold is exactly as good as the tail it is reading.
4. The profile itself, per single year of age, unweighted and income
   weighted, both thresholds, with the distance to 0 and to 1.
5. First differences, printed, not judged.

Known qualifications carried into this step
-------------------------------------------
- The accommodation offset (8.36 per day for this rate year, reg 16(1)) is
  invisible in this pay variable, so a lawfully paid worker can appear below
  the threshold. Raises p.
- The apprentice rate (4.30) applies to an apprentice in the first twelve
  months of employment OR under nineteen, so it is not an age band and a
  twenty-five year old first-year apprentice is lawfully at 4.30. Raises p at
  the young end without placing a boundary anywhere. No apprentice indicator
  was extracted in step 1, so this cannot be marked on the profile yet. It is
  registered, not done.
- Average hourly pay is derived from gross weekly pay and hours, so it carries
  overtime premium, which statutory compliance excludes. Lowers p.
The three directions differ, so they do not compose into a correction.

Usage
-----
    python experiments/b34_lfs_step2_profile.py
    python experiments/b34_lfs_step2_profile.py --age-lo 16 --age-hi 30
"""

import argparse
import gzip
import json
import pathlib
import time

import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[1]
CACHE = REPO / "data" / "b34" / "cache"
OUT = REPO / "results" / "b34_lfs_profile.json"

# Country scopes. COUNTRY carries five categories and the two Scottish ones are
# added, so a scope is a set of COUNTRY codes rather than a single value. The
# reason a scope exists at all: participation in education or training to 18 is
# compulsory in England and not in the other three countries, so an account of
# the profile that runs through the education exit at 18-19 is an account about
# England. The default is the whole UK and reproduces the record built before
# this option existed.
SCOPES = {
    "uk": None,
    "england": (1.0,),
    "non-england": (2.0, 3.0, 4.0, 5.0),
}
SCOPE_SOURCE = ("COUNTRY, labelled 'Country within UK': 1 England, 2 Wales, "
                "3 Scotland, 4 Scotland North of Caledonian Canal, "
                "5 Northern Ireland. Checked against CTRY9D row by row.")

# Rate year 2021-22, SI 2021/329. Statute, not an estimate, so it is a
# constant here and its provenance is recorded with it.
# Per rate year, because the whole point of the second year is that the
# statutory boundary moved. A common threshold means one threshold for every
# AGE inside a year, not one threshold across years: comparing 2019 pay to a
# 2021 floor would read inflation, not a band.
THRESHOLDS = {
    2018: {"main_nlw_25plus": 7.83, "alt_21_under_25": 7.38},
    2019: {"main_nlw_25plus": 8.21, "alt_21_under_25": 7.70},
    2021: {"main_nlw_23plus": 8.91, "alt_21_under_23": 8.36},
    2022: {"main_nlw_23plus": 9.50, "alt_21_under_23": 9.18},
}
THRESHOLD_SOURCE = {
    2018: "SI 2018/455 reg 2(2) and reg 2(3)(a), in force 1 April 2018",
    2019: "SI 2019/603 reg 2(2) and reg 2(3), in force 1 April 2019",
    2021: "SI 2021/329 reg 2(2) and reg 2(3)(a), in force 1 April 2021",
    2022: "SI 2022/382 reg 2, in force 1 April 2022",
}
RATE_YEAR = {2018: "2018-19", 2019: "2019-20",
             2021: "2021-22", 2022: "2022-23"}
# Every statutory rate in force that year, for the mode table. The living wage
# age is 25 in the first year and 23 in the second; that move is the treatment.
STATUTORY_RATES = {
    2018: (7.83, 7.38, 5.90, 4.20, 3.70),
    2019: (8.21, 7.70, 6.15, 4.35, 3.90),
    2021: (8.91, 8.36, 6.56, 4.62, 4.30),
    2022: (9.50, 9.18, 6.83, 4.81, 4.81),
}

PAY_COLS = ("hourpay", "hrrate")

# HRRATE carries special codes in the value range. LFS User Guide volume 3,
# the HRRATE entry, verbatim:
#     (1-994) Amount in pounds and pence
#     (995)   GBP 995 or more
#     (998)   Don't know
#     (999)   Refusal
# 998 and 999 are missing and must be dropped. They are POSITIVE and larger
# than any threshold, so a naive comparison counts them as "not below" and
# pushes the share down. Measured before this filter existed: 4,176 rows at
# 998 and 173 at 999, 32.2 percent of non-null HRRATE, and the 998 share rises
# monotonically with age (18.0 percent at 16, 34.8 percent at 28), so the bias
# is age dependent and it deforms the profile rather than shifting it.
# 995 is a top code, a real high value, and it is kept: it is above every
# threshold either way.
# The same entry gives the coverage: HRRATE "applies to all respondents who
# are paid a fixed hourly rate", asked in waves 1 and 5 only. So this column
# is a selected subset of employees, not all of them.
MISSING_CODES = {"hrrate": (998.0, 999.0)}
MISSING_CODES_SOURCE = "LFS User Guide volume 3, HRRATE entry"

# HOURPAY is derived and its flowchart maps missing inputs to -9, which
# pandas reads as NaN. Measured: exactly one non-null value at or above 900
# across all four quarters (1351.35), and it is a real outlier rather than a
# code. No filter is applied to it.


def drop_codes(frame, pay):
    """Drop the documented special codes for this column. Returns (kept, dropped)."""
    codes = MISSING_CODES.get(pay, ())
    if not codes:
        return frame, 0
    bad = frame[pay].isin(codes)
    return frame[~bad], int(bad.sum())
WEIGHTS = ("unweighted", "incwt")


def load_cache(cache_dir):
    """Read every cached quarter. Returns the frame and a per-file self-report."""
    frames, report = [], []
    for gz in sorted(cache_dir.glob("*.csv.gz")):
        t0 = time.time()
        d = pd.read_csv(gz)
        cols_path = gz.with_suffix("").with_suffix(".cols.json")
        matched = {}
        if cols_path.exists():
            matched = json.loads(cols_path.read_text(encoding="utf-8")).get("matched", {})
        report.append({
            "file": gz.name,
            "rows": int(d.shape[0]),
            "matched": matched,
            "seconds": round(time.time() - t0, 2),
        })
        frames.append(d)
    if not frames:
        raise SystemExit("no cache found under %s; run step 1 first" % cache_dir)
    return pd.concat(frames, ignore_index=True), report


def share_below(sub, pay, thr, weight):
    """Share below a threshold, and the n behind it. No judgement attached."""
    s = sub[sub[pay].notna()]
    s, _ = drop_codes(s, pay)
    if s.empty:
        return None, 0, 0.0
    below = s[pay] < thr
    if weight == "unweighted":
        n = float(s.shape[0])
        p = float(below.sum()) / n
        return p, int(s.shape[0]), n
    w = s["incwt"] if "incwt" in s.columns else None
    if w is None or w.notna().sum() == 0 or float(w.fillna(0.0).sum()) <= 0.0:
        return None, int(s.shape[0]), 0.0
    w = w.fillna(0.0)
    tot = float(w.sum())
    p = float(w[below].sum()) / tot
    return p, int(s.shape[0]), tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--age-lo", type=int, default=16)
    ap.add_argument("--age-hi", type=int, default=30)
    ap.add_argument("--cache", type=pathlib.Path, default=CACHE)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--scope", choices=sorted(SCOPES), default="uk",
                    help="restrict to a set of UK countries; uk is everything")
    args = ap.parse_args()

    df, report = load_cache(args.cache)

    keep = SCOPES[args.scope]
    if keep is not None:
        if "country" not in df.columns:
            raise SystemExit("the cache carries no country column; rebuild step 1")
        before = int(len(df))
        missing = int(df["country"].isna().sum())
        df = df[df["country"].isin(keep)].copy()
        print("scope %s: kept %d of %d rows; %d rows carry no country at all"
              % (args.scope, len(df), before, missing))
        print("scope definition: %s" % SCOPE_SOURCE)

    print("=" * 74)
    print("B34 LFS arm, step 2: the p(a,t) profile. Draw only, judge nothing.")
    for _y in sorted(THRESHOLDS):
        print("rate year %s, thresholds %s, from %s"
              % (RATE_YEAR[_y],
                 " / ".join("%.2f" % v for v in THRESHOLDS[_y].values()),
                 THRESHOLD_SOURCE[_y]))
    print("=" * 74)

    print("\n1. what each role matched, per file")
    for r in report:
        print("   %-28s rows=%-7d read in %.2fs" % (r["file"], r["rows"], r["seconds"]))
        for role in sorted(r["matched"]):
            print("        %-8s <- %s" % (role, r["matched"][role]))
    total_rows = int(df.shape[0])
    print("   total rows across quarters: %d" % total_rows)

    # 2. enumerate before selecting
    print("\n2. every status value on the subset that has hourly pay")
    print("   nothing is filtered by status in this step")
    paid = df[df["hourpay"].notna()]
    if "status" in df.columns:
        vc = paid["status"].value_counts(dropna=False).sort_index()
        for k, v in vc.items():
            print("   status=%-6s n=%d" % (k, int(v)))
        src = sorted(set(df["status_src"].dropna().unique())) if "status_src" in df.columns else []
        print("   source variable(s): %s" % (", ".join(map(str, src)) or "none recorded"))
    print("   rows with hourpay: %d of %d" % (int(paid.shape[0]), total_rows))
    if "hrrate" in df.columns:
        print("   rows with hrrate:  %d of %d" % (int(df["hrrate"].notna().sum()), total_rows))

    # 3. objects, not counts
    print("\n3. the tail this profile reads, printed as objects")
    for pay in PAY_COLS:
        if pay not in df.columns:
            continue
        s = df[df[pay].notna()][["age", pay, "status", "srcfile"]]
        s, _ = drop_codes(s, pay)
        if s.empty:
            continue
        lo = s.nsmallest(20, pay)
        hi = s.nlargest(20, pay)
        print("   --- %s, twenty smallest ---" % pay)
        for _, r in lo.iterrows():
            print("       %8.2f  age=%-4s status=%-6s %s"
                  % (r[pay], r["age"], r["status"], r["srcfile"]))
        print("   --- %s, twenty largest ---" % pay)
        for _, r in hi.iterrows():
            print("       %8.2f  age=%-4s status=%-6s %s"
                  % (r[pay], r["age"], r["status"], r["srcfile"]))

    # 3a. the documented special codes, per age. An object, not a count.
    print("\n3a. documented special codes dropped, per single year of age")
    print("    source: %s" % MISSING_CODES_SOURCE)
    codes_report = {}
    d_codes = df[(df["age"] >= args.age_lo) & (df["age"] <= args.age_hi)]
    for pay, codes in sorted(MISSING_CODES.items()):
        if pay not in d_codes.columns:
            continue
        print("    --- %s, codes %s ---" % (pay, ", ".join("%.0f" % c for c in codes)))
        rows = []
        for a in range(args.age_lo, args.age_hi + 1):
            sub = d_codes[(d_codes["age"] == a) & d_codes[pay].notna()]
            tot = int(sub.shape[0])
            bad = int(sub[pay].isin(codes).sum())
            share = (bad / tot) if tot else float("nan")
            print("        age %-3d non-null=%-6d coded=%-5d share=%.4f"
                  % (a, tot, bad, share))
            rows.append({"age": a, "non_null": tot, "coded": bad,
                         "share": round(share, 6) if tot else None})
        codes_report[pay] = rows

    # 3b. which values people actually report. Objects again, not counts.
    print("\n3b. the twenty most frequently reported values, ages %d-%d"
          % (args.age_lo, args.age_hi))
    print("    Statutory rates in force this rate year: 8.91 / 8.36 / 6.56 /")
    print("    4.62 / 4.30 apprentice. A directly asked rate can land on that")
    print("    grid; a rate derived from weekly pay and hours need not.")
    band_hits = {}
    d_modes_all = df[(df["age"] >= args.age_lo) & (df["age"] <= args.age_hi)]
    for year in sorted(THRESHOLDS):
        d_modes = d_modes_all[d_modes_all["year"] == year]
        for pay in PAY_COLS:
            if pay not in d_modes.columns or d_modes.empty:
                continue
            s = drop_codes(d_modes[d_modes[pay].notna()], pay)[0][pay]
            if s.empty:
                continue
            vc = s.value_counts().head(20)
            on_grid = 0
            print("    --- %s %s, n=%d ---" % (RATE_YEAR[year], pay, int(s.shape[0])))
            for val, cnt in vc.items():
                mark = ""
                for other in STATUTORY_RATES[year]:
                    if abs(float(val) - other) < 0.005:
                        mark = "  <- statutory %.2f" % other
                if mark:
                    on_grid += int(cnt)
                print("        %8.2f  n=%-6d  share=%.4f%s"
                      % (float(val), int(cnt), int(cnt) / float(s.shape[0]), mark))
            band_hits["%d|%s" % (year, pay)] = {
                "n": int(s.shape[0]), "on_statutory_value": on_grid,
                "share_on_statutory_value": round(on_grid / float(s.shape[0]), 6)}
            print("        of the top twenty, %d of %d observations sit exactly on a"
                  % (on_grid, int(s.shape[0])))
            print("        statutory rate for this rate year (share %.4f)"
                  % (on_grid / float(s.shape[0])))

    # 4. the profile
    ages = list(range(args.age_lo, args.age_hi + 1))
    d_all = df[(df["age"] >= args.age_lo) & (df["age"] <= args.age_hi)]
    profile = {}
    for year in sorted(THRESHOLDS):
      d = d_all[d_all["year"] == year]
      if d.empty:
        continue
      for pay in PAY_COLS:
        if pay not in d.columns:
            continue
        for tname, thr in sorted(THRESHOLDS[year].items()):
            for weight in WEIGHTS:
                key = "%d|%s|%s|%s" % (year, pay, tname, weight)
                rows = []
                print("\n4. profile  year=%s  pay=%s  threshold=%s (%.2f)  weight=%s"
                      % (RATE_YEAR[year], pay, tname, thr, weight))
                print("   %-5s %-8s %-9s %-9s %-9s"
                      % ("age", "n", "p", "to_edge", "se_binom"))
                for a in ages:
                    sub = d[d["age"] == a]
                    p, n, _ = share_below(sub, pay, thr, weight)
                    if p is None:
                        print("   %-5d %-8d %-9s %-9s %-9s"
                              % (a, n, "n/a", "n/a", "n/a"))
                        rows.append({"age": a, "n": n, "p": None})
                        continue
                    se = (p * (1.0 - p) / n) ** 0.5 if n > 0 else float("nan")
                    edge = min(p, 1.0 - p)
                    print("   %-5d %-8d %-9.4f %-9.4f %-9.4f"
                          % (a, n, p, edge, se))
                    rows.append({"age": a, "n": n, "p": round(p, 6),
                                 "to_edge": round(edge, 6),
                                 "se_binom": round(se, 6)})
                # 5. first differences, printed not judged
                print("   first differences p(a+1) - p(a), printed, not judged")
                for i in range(len(rows) - 1):
                    a, b = rows[i], rows[i + 1]
                    if a["p"] is None or b["p"] is None:
                        continue
                    print("       %2d -> %2d   %+0.4f" % (a["age"], b["age"],
                                                          b["p"] - a["p"]))
                profile[key] = rows

    # 5. the apprentice difference, two cells apart. New section; every table
    # above is unchanged to the digit, so the default output still reproduces.
    #
    # The apprentice rate is not an age band: reg 5(1) of the 2015 regulations
    # gives it to an apprentice in the first twelve months of employment OR
    # under nineteen. Turning nineteen therefore removes it from anyone past
    # their first year, and that is a boundary the minimum wage age bands do
    # not have. The first-year half of the condition has no LFS counterpart
    # (APPST12 only splits before/after the year 2000), so only the under
    # nineteen half is observable here.
    #
    # The question this answers is not where apprentices sit. It is what
    # dropping them does to the profile: two cells differing in one term.
    appr_report = {}
    if "apprcurr" in df.columns:
        print("\n5. apprentices: the same profile with them and without them")
        print("   current apprentice = APPRCURR == 1")
        d_ap_all = df[(df["age"] >= args.age_lo) & (df["age"] <= args.age_hi)]
        n_dk = int((d_ap_all["apprcurr"] == 3).sum())
        print("   APPRCURR == 3 (don't know) in this age range: %d rows, left in"
              % n_dk)
        for year in sorted(THRESHOLDS):
          d_ap = d_ap_all[d_ap_all["year"] == year]
          if d_ap.empty:
            continue
          for pay in PAY_COLS:
            if pay not in d_ap.columns:
                continue
            for tname, thr in sorted(THRESHOLDS[year].items()):
                key = "%d|%s|%s" % (year, pay, tname)
                print("   --- %s %s, threshold %s (%.2f), unweighted ---"
                      % (RATE_YEAR[year], pay, tname, thr))
                print("   %-5s %-7s %-6s %-9s %-9s %-9s"
                      % ("age", "n_all", "n_appr", "p_all", "p_noappr", "diff"))
                rows = []
                for a in range(args.age_lo, args.age_hi + 1):
                    sub = d_ap[d_ap["age"] == a]
                    p_all, n_all, _ = share_below(sub, pay, thr, "unweighted")
                    sub2 = sub[sub["apprcurr"] != 1]
                    p_no, n_no, _ = share_below(sub2, pay, thr, "unweighted")
                    n_ap = n_all - n_no
                    if p_all is None or p_no is None:
                        print("   %-5d %-7d %-6d %-9s %-9s %-9s"
                              % (a, n_all, n_ap, "n/a", "n/a", "n/a"))
                        continue
                    print("   %-5d %-7d %-6d %-9.4f %-9.4f %+9.4f"
                          % (a, n_all, n_ap, p_all, p_no, p_no - p_all))
                    rows.append({"age": a, "n_all": n_all, "n_appr": n_ap,
                                 "p_all": round(p_all, 6),
                                 "p_no_appr": round(p_no, 6),
                                 "diff": round(p_no - p_all, 6)})
                print("   first differences, both versions")
                print("   %-10s %-11s %-11s %-11s"
                      % ("pair", "all", "no appr", "change"))
                for i in range(len(rows) - 1):
                    x, y = rows[i], rows[i + 1]
                    d_all = y["p_all"] - x["p_all"]
                    d_no = y["p_no_appr"] - x["p_no_appr"]
                    print("   %2d -> %-5d %+11.4f %+11.4f %+11.4f"
                          % (x["age"], y["age"], d_all, d_no, d_no - d_all))
                appr_report[key] = rows

    record = {
        "stage": "B34-LFS-step2",
        "diagnostic_only": True,
        "diagnostic_reason": (
            "Step 2 of the LFS arm draws the profile and judges nothing. "
            "No criterion is scored here; arms one to four are scored later."
        ),
        "config": {
            "rate_years": {str(k): v for k, v in RATE_YEAR.items()},
            "thresholds": {str(k): v for k, v in THRESHOLDS.items()},
            "threshold_source": {str(k): v for k, v in THRESHOLD_SOURCE.items()},
            "statutory_rates": {str(k): list(v) for k, v in STATUTORY_RATES.items()},
            "age_lo": args.age_lo,
            "age_hi": args.age_hi,
            "pay_columns": list(PAY_COLS),
            "weights": list(WEIGHTS),
            "status_filter": None,
            "missing_codes": {k: list(v) for k, v in MISSING_CODES.items()},
            "missing_codes_source": MISSING_CODES_SOURCE,
            "cache_files": [r["file"] for r in report],
            "rows_total": total_rows,
            "scope": args.scope,
            "scope_codes": list(SCOPES[args.scope]) if SCOPES[args.scope] else None,
            "scope_source": SCOPE_SOURCE,
        },
        "files": [{k: v for k, v in r.items() if k != "seconds"} for r in report],
        "on_statutory_value": band_hits,
        "special_codes_dropped": codes_report,
        "apprentice_two_cells": appr_report,
        "profile": profile,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    print("\nwrote %s" % args.out.name)
    print("This step judged nothing. Read the profile, then decide step 3.")


if __name__ == "__main__":
    main()
