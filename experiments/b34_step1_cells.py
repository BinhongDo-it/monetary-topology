"""B34 step 1: count the cells, and nothing else.

This is the resolution gate from B34_design section 2 and section 5.3. It does
three things and stops:

  1. Opens every Labour Force Survey file it is pointed at, and PRINTS THE
     COLUMN NAMES IT MATCHED rather than assuming any. LFS variable names move
     between years, so the script discovers them and shows its work.
  2. Builds a compact cache (one parquet per source file) holding only the four
     or five columns this station needs, so later steps never re-read the raw
     files.
  3. Counts the cell "single year of age x year x non-missing hourly pay" and
     prints THE SMALLEST THREE, not the average.

Nothing is judged here. No profile is drawn, no discontinuity is estimated. If
the smallest cells are too thin, the station does not open, and the remaining
steps are not run.

Usage
-----
    python b34_step1_cells.py --src D:/data/lfs --cache D:/data/lfs_cache
    python b34_step1_cells.py --src D:/data/lfs --cache D:/data/lfs_cache --rebuild

Reads .dta and .tab/.csv with pandas alone; .sav additionally needs
pyreadstat. The cache is parquet when pyarrow or fastparquet is installed and
gzipped csv otherwise. Writes only inside --cache. Deletes nothing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Candidate name patterns, in priority order. The script reports which one it
# matched for every file, so a wrong match is visible rather than silent.
WANTED = {
    "age": [r"^AGE$", r"^AGES$", r"^AGE1$"],
    # HRRATE is the directly asked hourly rate and carries much less error than
    # HOURPAY, which is derived from weekly pay over hours. Both are kept when
    # present; step 2 decides which to lead with, and both get reported.
    "hrrate": [r"^HRRATE$", r"^HOURLYRATE$"],
    "hourpay": [r"^HOURPAY$", r"^HRLYPAY$"],
    # Income variables need the income weight, not the person weight.
    "incwt": [r"^PIWT\d*$", r"^INCWT\d*$", r"^PIWTA\d*$"],
    "perwt": [r"^PWT\d*$", r"^PWTA\d*$"],
    "status": [r"^INECAC05$", r"^ILODEFR$", r"^INECACA$"],
    "hiqual": [r"^HIQUAL\d*$", r"^HIQULD?\d*$"],
    # The five wave rotation is why a pooled row count is person-quarters and
    # not persons. THISWV says which wave a row is, W1YR and QRTR say which
    # quarter the address entered, and the three together locate the row in
    # absolute time without reading the file name.
    "wave": [r"^THISWV$"],
    "w1yr": [r"^W1YR$"],
    "entryq": [r"^QRTR$"],
    # The apprentice rate is not an age band. Under the 2015 regulations it
    # applies to an apprentice in the first twelve months of employment OR
    # under nineteen, so the disjunction means it reaches across the age
    # bands, and losing it at nineteen is a boundary the minimum wage age
    # bands do not have. APPRCURR is "currently an apprentice" (1 yes, 2 no,
    # 3 don't know); APPSAM says whether the apprenticeship is part of the
    # main job, which is the job the pay questions ask about.
    # What cannot be read here: APPST12 only splits before/after the year
    # 2000, so the "first twelve months of employment" half of the statutory
    # condition has no LFS counterpart. Only the "under nineteen" half is
    # observable.
    "apprcurr": [r"^APPRCURR$"],
    "appsam": [r"^APPSAM$"],
    # Country within the UK. Participation in education or training to 18 is
    # compulsory in England and not in Scotland, Wales or Northern Ireland, so
    # any account of the profile that runs through the education exit has a
    # country dimension. COUNTRY carries five categories, not four: England,
    # Wales, Scotland, Scotland North of Caledonian Canal, Northern Ireland.
    # The two Scottish categories are added. CTRY9D is the nine-digit country
    # code and is kept as an independent second copy, so the collapse can be
    # checked against something that was not derived from it.
    "country": [r"^COUNTRY$"],
    "ctry9d": [r"^CTRY9D$"],
}

NUMERIC = ("age", "hrrate", "hourpay", "incwt", "perwt", "status", "country",
           "wave", "w1yr", "entryq", "apprcurr", "appsam")

# Roles that are classifications rather than measurements. LFS renumbers these
# when the coding frame changes (HIQUAL15 became HIQUAL22 at the end of 2021,
# and the categories moved with it), so the matched source name travels with
# the data. Two vintages in one column is the thing this prevents.
# `incwt` is here for the same reason, and it is not a classification: the
# income weight is renumbered when the population base is revised, and the two
# rate years on disk do not share one. Measured: PIWT18 for the first three
# quarters of the 2019-20 rate year and PIWT22 from its fourth quarter onward,
# which is the same quarter ONS names for the move to telephone first contact
# and for tenure weighting. Carrying the source name through means a weighted
# reading can never silently pool two population bases.
CLASSIFIED = ("status", "hiqual", "apprcurr", "appsam", "incwt", "country",
              "ctry9d")


def match_columns(cols):
    """Return {role: column} plus the misses, without guessing."""
    found, missed = {}, []
    upper = {c.upper(): c for c in cols}
    for role, pats in WANTED.items():
        hit = None
        for pat in pats:
            for cu, c in upper.items():
                if re.match(pat, cu):
                    hit = c
                    break
            if hit:
                break
        if hit:
            found[role] = hit
        else:
            missed.append(role)
    return found, missed


def year_from_name(path: Path):
    """Pull a four digit year out of the file name; None if not found."""
    m = re.search(r"(19[89]\d|20[0-4]\d)", path.stem)
    return int(m.group(1)) if m else None


def columns_of(path: Path):
    """Variable names without reading a single row of data.

    An LFS quarter carries around 850 variables and this station keeps nine of
    them. Reading the header first and asking for those nine turns a multi
    gigabyte load into a few megabytes, and it changes no value: the columns
    requested are exactly the columns the old path kept after loading.
    """
    suf = path.suffix.lower()
    if suf == ".dta":
        with pd.io.stata.StataReader(str(path)) as r:
            return list(r.variable_labels().keys())
    if suf == ".sav":
        try:
            import pyreadstat
        except ImportError:
            raise SystemExit(
                "pyreadstat is needed for .sav files: pip install pyreadstat. "
                ".dta and .tab need nothing beyond pandas."
            )
        _, meta = pyreadstat.read_sav(str(path), metadataonly=True)
        return list(meta.column_names)
    sep = "\t" if suf in (".tab", ".tsv") else ","
    return list(pd.read_csv(path, sep=sep, nrows=0).columns)


def cache_paths(cache_dir: Path, stem: str):
    """Parquet when an engine is installed, gzipped csv when it is not.

    The kept subset is nine columns, so the fallback costs little and it means
    a missing optional dependency cannot end the run halfway through the third
    file. Which one was used is visible in the file name.
    """
    for mod in ("pyarrow", "fastparquet"):
        try:
            __import__(mod)
            return cache_dir / (stem + ".parquet"), "parquet"
        except ImportError:
            continue
    return cache_dir / (stem + ".csv.gz"), "csv.gz"


def read_cache(path: Path, kind: str) -> pd.DataFrame:
    return pd.read_parquet(path) if kind == "parquet" else pd.read_csv(path)


def write_cache(df: pd.DataFrame, path: Path, kind: str):
    if kind == "parquet":
        df.to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False, compression="gzip")


def read_any(path: Path, usecols=None) -> pd.DataFrame:
    suf = path.suffix.lower()
    if suf == ".dta":
        # pandas reads Stata natively, so this path has no third party
        # dependency. Categoricals stay off: the negative not-applicable and
        # refusal codes must arrive as literal numbers, because the only place
        # a value is allowed to become missing is the explicit rule below.
        return pd.read_stata(str(path), convert_categoricals=False,
                             columns=usecols)
    if suf == ".sav":
        try:
            import pyreadstat
        except ImportError:
            raise SystemExit(
                "pyreadstat is needed for .sav files: pip install pyreadstat. "
                ".dta and .tab need nothing beyond pandas."
            )
        # user_missing=True is load bearing. Left at its default, pyreadstat
        # turns SPSS user-defined missing values into NaN before this script
        # sees them, so the explicit rule below never fires and .sav stops
        # agreeing with .dta on any column that rule does not cover. Keep the
        # codes, and let one visible rule decide what missing means.
        df, _ = pyreadstat.read_sav(str(path), apply_value_formats=False,
                                    user_missing=True, usecols=usecols)
        return df
    if suf in (".tab", ".tsv"):
        return pd.read_csv(path, sep="\t", low_memory=False, usecols=usecols)
    if suf == ".csv":
        return pd.read_csv(path, low_memory=False, usecols=usecols)
    raise SystemExit("unrecognised extension: %s" % path)


def extract(path: Path, cache_dir: Path, rebuild: bool):
    out, kind = cache_paths(cache_dir, path.stem)
    meta_path = cache_dir / (path.stem + ".cols.json")
    if out.exists() and meta_path.exists() and not rebuild:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return read_cache(out, kind), meta, True

    cols = columns_of(path)
    found, missed = match_columns(cols)
    if "age" not in found:
        raise SystemExit("no age column found in %s" % path.name)
    if "hrrate" not in found and "hourpay" not in found:
        raise SystemExit("no hourly pay column found in %s" % path.name)

    keep = {role: col for role, col in found.items()}
    df = read_any(path, list(keep.values()))
    sub = df[list(keep.values())].copy()
    sub.columns = list(keep.keys())
    for role in NUMERIC:
        if role in sub.columns:
            sub[role] = pd.to_numeric(sub[role], errors="coerce")
    # LFS uses large negative codes for not-applicable and refusal. Anything
    # below zero is set missing rather than dropped, so the row still counts as
    # a respondent for the denominator when we want it to.
    for role in ("hrrate", "hourpay", "incwt", "perwt", "country"):
        if role in sub.columns:
            sub.loc[sub[role] <= 0, role] = np.nan
    for role in CLASSIFIED:
        if role in sub.columns:
            sub[role + "_src"] = keep[role]
    sub["year"] = year_from_name(path)
    sub["srcfile"] = path.name

    # COUNTRY collapsed to four countries must equal the first character of
    # CTRY9D, which is a separate variable in the source and not derived from
    # it. Mismatching rows are printed rather than counted, and nothing is
    # dropped: this is a check on the collapse, not a filter on the data.
    if "country" in sub.columns and "ctry9d" in sub.columns:
        letter = sub["country"].map({1.0: "E", 2.0: "W", 3.0: "S",
                                     4.0: "S", 5.0: "N"})
        other = sub["ctry9d"].astype(str).str[:1]
        bad = sub[(letter != other) & sub["country"].notna()]
        print("   country collapse against CTRY9D: %d row(s) differ" % len(bad))
        for _, r in bad.head(10).iterrows():
            print("      country=%s ctry9d=%r age=%s hourpay=%s"
                  % (r.get("country"), r.get("ctry9d"), r.get("age"),
                     r.get("hourpay")))
        blank = sub[sub["country"].isna()]
        if len(blank):
            print("   rows with no country at all: %d, of which all-empty: %d"
                  % (len(blank), int(blank["age"].isna().sum())))

    cache_dir.mkdir(parents=True, exist_ok=True)
    write_cache(sub, out, kind)
    yr = sub["year"].iloc[0] if len(sub) else None
    meta = {"file": path.name, "matched": keep, "missed": missed,
            "rows": int(len(sub)),
            # numpy scalars are not JSON serialisable, and pandas hands one
            # back from .iloc even when the column was set from a python int.
            "year": None if yr is None or pd.isna(yr) else int(yr)}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    return sub, meta, False


def wave_report(df, age_lo, age_hi):
    """Step 1c: what the five wave rotation costs the independent count.

    The LFS interviews an address in five successive quarters, so four
    consecutive quarters share respondents and a pooled row count is
    person-quarters rather than persons. Nothing is judged here. The point is
    to put both ends of the range on the table, so no later step can read a
    resolution gate on a count that was never a count of people.
    """
    print()
    print("=" * 78)
    print("STEP 1c: the wave rotation. Pooled rows are person-quarters.")
    print("=" * 78)

    need = ("wave", "w1yr", "entryq")
    if any(c not in df.columns for c in need):
        print("  missing %s, so the overlap cannot be characterised from the"
              % ", ".join(c for c in need if c not in df.columns))
        print("  files themselves. Report this rather than assuming no overlap.")
        return

    d = df.dropna(subset=["wave", "w1yr", "entryq"]).copy()
    for c in need:
        d[c] = d[c].astype(int)

    # Known answer check, costs one pass and no data. An address entering in
    # quarter (w1yr, entryq) is at wave w exactly (w - 1) quarters later, so
    # this index must come out identical for every row of one file. If a file
    # shows more than one value, the wave semantics assumed here are wrong and
    # everything below it is void.
    #
    # W1YR is the LAST DIGIT of the entry year, so it wraps: an address that
    # entered in 2019 carries 9 and one that entered in 2020 carries 0. An
    # index built as w1yr * 4 is therefore not monotone across a decade
    # boundary, and it drops by forty quarters exactly there. Measured on
    # 2020 Q1, where both cohorts are present: the 2019 entrants gave 40 and
    # the 2020 entrants gave 0, and the guard fired.
    #
    # Carrying the offset into the year first removes the wrap. Only the last
    # digit of the CURRENT year is needed, and that is unique inside any forty
    # quarter span, which is far wider than the four quarter window this
    # station uses.
    _off = (d["entryq"] - 1) + (d["wave"] - 1)
    d["qidx"] = ((d["w1yr"] + _off // 4) % 10) * 4 + (_off % 4)
    # Known answer check. A file's rows should all resolve to one survey
    # quarter, and the majority always does. Individual records whose W1YR,
    # QRTR and THISWV are mutually inconsistent do occur: measured, one row in
    # 69,437 of the 2022 Q3 file says entry 2021 Q1 at wave 5, which lands two
    # quarters away from every other row in that file.
    #
    # That single row is a record level inconsistency, not a wave semantics
    # error, and it is reported rather than allowed to stop the run. What this
    # check guards is the collision table below, which asks whether one person
    # appears twice in the window; one misfiled row does not change that answer
    # but it would contaminate the table, so the minority rows are named,
    # counted, and held out of the collision analysis. No threshold is set: the
    # minority is defined as "not equal to this file's modal quarter", and the
    # count is printed for reading rather than compared against a line.
    print("\nknown answer check: one survey quarter per file")
    modal = {}
    for f, g in d.groupby("srcfile"):
        vc = g["qidx"].value_counts()
        m = int(vc.index[0])
        modal[f] = m
        others = vc.iloc[1:]
        if others.empty:
            print("   %-28s qidx=%d  OK" % (f, m))
        else:
            print("   %-28s qidx=%d  plus %d row(s) at %s, held out below"
                  % (f, m, int(others.sum()),
                     ", ".join(str(int(x)) for x in others.index[:4])))
    d["_modal"] = d["srcfile"].map(modal)
    n_before = int(d.shape[0])
    d = d[d["qidx"] == d["_modal"]].drop(columns=["_modal"])
    held = n_before - int(d.shape[0])
    if held:
        print("   %d row(s) of %d held out of the collision analysis (%.5f%%)."
              % (held, n_before, 100.0 * held / n_before))
        print("   They stay in the data and in every cell count; only the")
        print("   duplicate check excludes them, because a misfiled entry")
        print("   quarter would otherwise read as a cohort seen twice.")

    print("\nwave distribution, share of rows")
    tab = d.groupby(["srcfile", "wave"]).size().unstack(fill_value=0)
    tab = tab.div(tab.sum(axis=1), axis=0)
    for f, row in tab.iterrows():
        print("   %-28s %s" % (f, "  ".join("w%d=%.3f" % (int(w), v)
                                            for w, v in row.items())))

    # Whether the window actually contains anyone twice, asked of the data
    # instead of argued from the rotation. A person can appear twice only
    # inside one entry cohort, so a cohort seen at two survey quarters is the
    # only way a duplicate can exist. Zero such cohorts means the pooled count
    # is a count of people.
    #
    # It matters because the earnings questions are asked at waves 1 and 5
    # only, and those are four quarters apart, so a four consecutive quarter
    # window cannot hold both. Widen the window to five and that stops being
    # true. The check is what tells you which case you are in.
    d["cohort"] = d["w1yr"] * 4 + (d["entryq"] - 1)
    pay_cols = [c for c in ("hrrate", "hourpay") if c in d.columns]
    d = d[(d["age"] >= age_lo) & (d["age"] <= age_hi)]

    # The window is one rate year, four consecutive quarters, so the question
    # is asked inside each rate year and then across them. Those are different
    # questions with different answers, and pooling them hides both.
    #
    # Two rate years that are ADJACENT do overlap: an address entering in the
    # last quarter of one is at wave 5 four quarters later, which is inside the
    # next one. 2019-20 and 2021-22 are separated by the skipped 2020-21 year
    # and cannot overlap; 2021-22 and 2022-23 are adjacent and do.
    print("\ncan one person appear twice? asked per pay variable, per rate year")
    clean = True
    for pay in pay_cols:
        s_all = d[d[pay].notna()]
        if s_all.empty:
            print("   %-10s no observations" % pay)
            continue
        parts = []
        for yr, s in s_all.groupby("year"):
            ct = pd.crosstab(s["cohort"], s["qidx"])
            multi = int(((ct > 0).sum(axis=1) > 1).sum())
            clean = clean and multi == 0
            parts.append("%s: %d cohort(s), %d seen twice" % (int(yr), len(ct), multi))
        ct_all = pd.crosstab(s_all["cohort"], s_all["qidx"])
        multi_all = int(((ct_all > 0).sum(axis=1) > 1).sum())
        print("   %-10s rows=%-7d waves present=%s"
              % (pay, len(s_all), sorted(int(w) for w in s_all["wave"].unique())))
        print("       within rate year   %s" % "   ".join(parts))
        print("       across rate years  %d cohort(s) seen at more than one quarter%s"
              % (multi_all, "" if multi_all == 0 else
                 "   <- pooling ACROSS years would double count these"))
    # The same question without the earnings filter, so a zero above is known
    # to mean something. Variables collected every wave do overlap, and if this
    # line also reads zero then the check is not discriminating and the reading
    # above carries nothing.
    ct = pd.crosstab(d["cohort"], d["qidx"])
    span = (ct > 0).sum(axis=1).value_counts().sort_index()
    print("   %-10s %s" % ("contrast",
                           "no earnings filter, cohorts by quarters spanned: "
                           + ", ".join("%d quarter(s): %d" % (k, v)
                                       for k, v in span.items())))
    if clean:
        print("\n   Inside each rate year no cohort is seen twice, so the per-year")
        print("   n below counts people. That is the number every reading uses,")
        print("   because the profile is built per rate year against that year's")
        print("   own threshold. A fifth consecutive quarter inside one year")
        print("   would break it; widen by rate year, never by one more quarter.")
        print("   Across ADJACENT rate years the same person can appear twice,")
        print("   at wave 1 in the last quarter of one and wave 5 in the next.")
        print("   So a count pooled across years is person-quarters. Do not")
        print("   pool; read each year separately, which is what the design does.")
    else:
        print("\n   A cohort appears at more than one quarter INSIDE one rate")
        print("   year, so that year's n is person-quarters. Narrow the window")
        print("   rather than deflating n.")

    for pay in pay_cols:
        print("\n   --- %s, n by single year of age ---" % pay)
        for a in range(age_lo, age_hi + 1):
            n = int(d[(d["age"] == a) & d[pay].notna()].shape[0])
            se10 = np.sqrt(0.10 * 0.90 / n) if n else float("nan")
            se25 = np.sqrt(0.25 * 0.75 / n) if n else float("nan")
            print("   age %-3d n=%-6d se(p) at p=.10: %.4f   at p=.25: %.4f"
                  % (a, n, se10, se25))
        print("   se is printed at two values of p because p is not known until")
        print("   step 2. The gate is read at the statutory boundary ages, not")
        print("   at whichever age this window happens to make thinnest.")

    print("\n   Nothing is judged here. The gate is a comparison between the")
    print("   se above at the boundary ages and the effect the station is")
    print("   looking for, and it is not made in this script.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="directory of LFS files")
    ap.add_argument("--cache", required=True, help="directory for the parquet cache")
    ap.add_argument("--rebuild", action="store_true",
                    help="re-extract even if a cache file exists")
    ap.add_argument("--age-lo", type=int, default=16)
    ap.add_argument("--age-hi", type=int, default=30)
    args = ap.parse_args()

    src = Path(args.src)
    cache = Path(args.cache)
    files = sorted(
        p for p in src.iterdir()
        if p.suffix.lower() in (".sav", ".dta", ".tab", ".tsv", ".csv")
    )
    if not files:
        raise SystemExit("no readable files in %s" % src)

    print("=" * 78)
    print("STEP 1a: what each file gave, per file. Read this before anything else.")
    print("=" * 78)
    frames = []
    for p in files:
        sub, meta, cached = extract(p, cache, args.rebuild)
        frames.append(sub)
        tag = "cached" if cached else "built "
        print("%s %-38s rows=%-8d year=%s" % (tag, meta["file"], meta["rows"],
                                              meta["year"]))
        print("        matched: %s" % json.dumps(meta["matched"], ensure_ascii=False))
        if meta["missed"]:
            print("        MISSED : %s" % ", ".join(meta["missed"]))

    df = pd.concat(frames, ignore_index=True)
    if df["year"].isna().any():
        bad = sorted(set(df.loc[df["year"].isna(), "srcfile"]))
        print("\nWARNING: no year parsed from these file names, so they cannot be")
        print("         placed on the time axis. Rename them or pass a mapping:")
        for b in bad:
            print("         %s" % b)

    print()
    print("=" * 78)
    print("STEP 1b: the cell count. The gate reads the smallest cells, not the mean.")
    print("=" * 78)

    df = df[(df["age"] >= args.age_lo) & (df["age"] <= args.age_hi)]
    pay_cols = [c for c in ("hrrate", "hourpay") if c in df.columns]

    for pay in pay_cols:
        g = (df.dropna(subset=[pay])
               .groupby(["year", "age"], dropna=True)
               .size()
               .rename("n")
               .reset_index())
        if g.empty:
            print("\n%s: no non-missing observations at all." % pay)
            continue
        print("\n--- pay variable: %s ---" % pay)
        print("cells: %d   total obs: %d" % (len(g), int(g["n"].sum())))
        print("SMALLEST THREE CELLS (this is the gate):")
        for _, r in g.nsmallest(3, "n").iterrows():
            n = int(r["n"])
            # Worst case binomial standard error of a proportion at this n.
            se = 0.5 / np.sqrt(n) if n > 0 else float("nan")
            print("   year=%s age=%s  n=%-6d  worst-case se(p)=%.4f"
                  % (int(r["year"]), int(r["age"]), n, se))
        print("median cell n: %d   (printed for context only, NOT the gate)"
              % int(g["n"].median()))

        # Per year, the thinnest age cell. A year whose thinnest cell is too
        # small cannot carry a profile even if its total is large.
        worst = g.loc[g.groupby("year")["n"].idxmin()].sort_values("year")
        print("thinnest age cell in each year:")
        for _, r in worst.iterrows():
            print("   %s: age %2d, n=%d" % (int(r["year"]), int(r["age"]),
                                            int(r["n"])))

    wave_report(df, args.age_lo, args.age_hi)

    if any(c.endswith("_src") for c in df.columns):
        print()
        print("classification vintages actually used, per role:")
        for c in sorted(c for c in df.columns if c.endswith("_src")):
            seen = sorted(set(df[c].dropna()))
            flag = "" if len(seen) <= 1 else "   *** more than one coding frame ***"
            print("   %-12s %s%s" % (c[:-4], ", ".join(map(str, seen)), flag))
        print("   A role with more than one source name is two different")
        print("   classifications sharing a column. Do not pool it.")

    print()
    print("=" * 78)
    print("STEP 1 ends here by design. Nothing has been judged.")
    print("Read the smallest cells above against the effect the station is")
    print("looking for. B34_design section 5.3: if they are too thin, the")
    print("station does not open and steps 2 to 6 are not run.")
    print("=" * 78)


if __name__ == "__main__":
    sys.exit(main())
