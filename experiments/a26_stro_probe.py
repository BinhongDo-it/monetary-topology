"""A26 carrier probe: can the Sound Toll pair panel be built at all.

Three questions, in the order rule 13 puts them, and none of them is a test.
This runs before any criterion is scored, because what it may return is that
the carrier cannot carry the reading, and that answer is cheaper here than
after a design has been written against it.

1. **What is in the port fields.** The stage needs pairs of ports, so the first
   thing to look at is what a port is in this data: how many distinct strings,
   how the mass is distributed over them, and whether the same place appears
   under more than one string. Printed as the objects, not as a summary.
2. **When the fields are populated.** Both fields exist for the whole span in
   the schema. Whether they are filled is a different question and it is
   answered per year.
3. **What a top-N restriction would cost.** The distribution is the reason
   somebody will propose keeping the common strings and dropping the tail. That
   is a decision this stage cannot make on the usual grounds, because the tail
   is where thin pairs live and thin pairs dying is the reading.

Everything here is one pass per file, no sampling, no repetitions.

Usage::

    python experiments/a26_stro_probe.py
"""

from __future__ import annotations

import collections
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "stro"
RESULTS = ROOT / "results"
RECORD = RESULTS / "a26_stro_probe.json"

SEP = ";"
PLACEHOLDER = "-"

#: Year marks printed in full. The dense ones around the middle 1660s are there
#: because that is where the destination field is said to begin, and a claim
#: about a start date is worth reading year by year rather than at a decade.
MARKS = (1497, 1550, 1574, 1575, 1600, 1625, 1650, 1660, 1661, 1662, 1663,
         1664, 1665, 1666, 1667, 1668, 1670, 1675, 1700, 1725, 1750, 1775,
         1800, 1825, 1850, 1857)

#: Groups of strings that are the same place under different spellings, used to
#: show that the fields are not standardised rather than to standardise them.
#: Read off the head of the frequency table, so each member is common enough to
#: be beyond doubt. **Not a mapping and not fit for one**: it covers a handful
#: of the largest ports and says nothing about the tail, which is the part that
#: matters for this stage.
SPELLING_PROBE = {
    "Danzig": ("Dantzig", "Danzig", "Danschen", "Dantzick", "Dantzik"),
    "Copenhagen": ("Kiøbenhavn", "Kjøbenhavn", "Kiøbenh.", "Kjøbenh."),
    "Amsterdam": ("Amsterdam", "Amsterd.", "Amsterdm", "Amst."),
    "Konigsberg": ("Kønigsberg", "Konigsberg", "Königsberg", "Kønigsb."),
    "St Petersburg": ("Petersborg", "St. Petersborg", "Petersb."),
}


def rows(name: str):
    with (RAW / name).open("r", encoding="utf-8", errors="replace",
                           newline="") as f:
        yield from csv.DictReader(f, delimiter=SEP)


def load_years() -> dict[str, int]:
    out = {}
    for r in rows("customs_entries.csv"):
        try:
            out[r["ce_id"]] = int(r["year"])
        except (ValueError, TypeError, KeyError):
            pass
    return out


def field_profile(name: str, key: str) -> tuple[collections.Counter, dict]:
    c: collections.Counter = collections.Counter()
    n = blank = placeholder = 0
    for r in rows(name):
        n += 1
        v = (r.get(key) or "").strip()
        if not v:
            blank += 1
        elif v == PLACEHOLDER:
            placeholder += 1
        else:
            c[v] += 1
    named = sum(c.values())
    cover = {}
    run = 0
    for i, (_k, v) in enumerate(c.most_common(), 1):
        run += v
        for tgt in (50, 80, 90, 95, 99):
            if tgt not in cover and run / named >= tgt / 100:
                cover[tgt] = i
    once = sum(1 for v in c.values() if v == 1)
    return c, {
        "rows": n, "blank": blank, "placeholder": placeholder, "named": named,
        "placeholder_share": placeholder / n if n else 0.0,
        "distinct": len(c),
        "strings_to_cover": cover,
        "hapax": once,
        "hapax_share_of_distinct": once / len(c) if c else 0.0,
        "hapax_share_of_rows": once / named if named else 0.0,
        "top20": c.most_common(20),
    }


def per_year(name: str, key: str, years: dict) -> dict:
    got: collections.Counter = collections.Counter()
    tot: collections.Counter = collections.Counter()
    for r in rows(name):
        y = years.get(r["ce_id"])
        if y is None:
            continue
        tot[y] += 1
        v = (r.get(key) or "").strip()
        if v and v != PLACEHOLDER:
            got[y] += 1
    return {"named": dict(got), "total": dict(tot)}


#: A ladder of mechanical rewrites, each one applied on top of the last. The
#: point is to measure how much of the distinct-string count is orthography
#: rather than geography, so every rung has to be something a scribe could vary
#: without meaning a different place, and nothing here is allowed to decide that
#: two spellings are the same town.
#:
#: The last two rungs are not mechanical in that sense and are marked. Danish
#: and Norwegian ``i`` against ``j`` before a vowel is a language fact rather
#: than a typography fact, and dropping a leading saint's title merges places
#: whose names differ by it. They are on the ladder so that what each buys and
#: what each risks can be read off separately, not so that they can be used.
NORD = str.maketrans({"ø": "o", "Ø": "o", "å": "aa", "Å": "aa",
                      "æ": "ae", "Æ": "ae", "ö": "o", "ä": "a", "ü": "u",
                      "é": "e", "è": "e", "ê": "e", "ç": "c", "ñ": "n"})


def rung_space(s: str) -> str:
    return " ".join(s.split())


def rung_case(s: str) -> str:
    return s.casefold()


def rung_marks(s: str) -> str:
    import unicodedata
    s = s.translate(NORD)
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def rung_punct(s: str) -> str:
    keep = [c for c in s if c.isalnum() or c.isspace()]
    return " ".join("".join(keep).split())


def rung_ij(s: str) -> str:
    """Danish and Norwegian i against j before a vowel. **Not mechanical.**"""
    import re as _re
    return _re.sub(r"\bkj", "ki", _re.sub(r"([a-z])j([aeiouy])", r"\1i\2", s))


def rung_saint(s: str) -> str:
    """Drop a leading saint's title. **Not mechanical, and it merges places.**"""
    import re as _re
    return _re.sub(r"^(st|sankt|sanct|sct|san|sao|saint)\s+", "", s)


LADDER = (
    ("raw", lambda s: s),
    ("+ whitespace", rung_space),
    ("+ case", rung_case),
    ("+ diacritics", rung_marks),
    ("+ punctuation", rung_punct),
    ("+ i/j  (not mechanical)", rung_ij),
    ("+ saint (not mechanical)", rung_saint),
)


def normalise_ladder(counter, label: str) -> dict:
    """How far the distinct count falls at each rung, and what merged.

    Two numbers per rung and neither is a summary of the other: how many
    distinct strings survive, and how many of the strings that occurred exactly
    once have joined a string that occurs often. The second is the one that
    decides something, because the argument against dropping the tail is that
    the tail is thin traffic. If most of it is misspelling of thick traffic
    then it is not thin traffic and the argument does not apply to it.
    """
    import collections
    raw_once = {k for k, v in counter.items() if v == 1}
    out = []
    fns: list = []
    for name, fn in LADDER:
        fns.append(fn)

        def apply(s, _fns=tuple(fns)):
            for f in _fns:
                s = f(s)
            return s

        merged: collections.Counter = collections.Counter()
        members: dict = collections.defaultdict(list)
        for k, v in counter.items():
            key = apply(k)
            merged[key] += v
            members[key].append((k, v))
        # A once-only string has joined thick traffic when its normalised form
        # is shared with strings totalling a hundred passages or more. The
        # hundred is not a threshold on an estimator: it is printed beside the
        # counts at several levels so the reading does not depend on it.
        rescued = {}
        for cut in (10, 100, 1000):
            n = 0
            for k in raw_once:
                key = apply(k)
                if merged[key] - 1 >= cut:
                    n += 1
            rescued[cut] = n
        big = sorted(((len(m), key, m) for key, m in members.items()
                      if len(m) > 1), reverse=True)[:5]
        out.append({"rung": name, "distinct": len(merged),
                    "hapax_joined_traffic": rescued,
                    "largest_merges": [
                        {"normalised": key,
                         "members": sorted(m, key=lambda kv: -kv[1])[:8]}
                        for _n, key, m in big]})
    print(f"\n{label}: distinct strings down the ladder, "
          f"and where the once-only strings went")
    print("  rung                        distinct   once-only strings that "
          "joined a form with >=10 / >=100 / >=1000 other passages")
    for r in out:
        j = r["hapax_joined_traffic"]
        print(f"  {r['rung']:26s} {r['distinct']:9,}   "
              f"{j[10]:6,} / {j[100]:6,} / {j[1000]:6,}")
    print("  largest groups at the last mechanical rung (+ punctuation):")
    for g in out[4]["largest_merges"]:
        print(f"    {g['normalised']!r}: " + ", ".join(
            f"{k}={v:,}" for k, v in g["members"]))
    return {"ladder": out, "raw_hapax": len(raw_once)}


def main() -> int:
    if not (RAW / "departure.csv").exists():
        print(f"no data at {RAW}. Run data/fetch_stro.py first.")
        return 1
    RESULTS.mkdir(exist_ok=True)

    print("A26 carrier probe: Sound Toll Registers, the port fields\n")
    profiles = {}
    counters = {}
    for name, key in (("departure.csv", "departure"),
                      ("destination.csv", "destination")):
        c, p = field_profile(name, key)
        counters[key] = c
        profiles[key] = p
        print(f"{key}: {p['rows']:,} rows, {p['placeholder']:,} placeholder "
              f"({p['placeholder_share']*100:.1f}%), {p['blank']} blank, "
              f"{p['distinct']:,} distinct strings")
        print("   strings needed to cover the named rows: " + "  ".join(
            f"{t}%={p['strings_to_cover'][t]:,}" for t in (50, 80, 90, 95, 99)))
        print(f"   appearing exactly once: {p['hapax']:,} "
              f"({p['hapax_share_of_distinct']*100:.1f}% of distinct, "
              f"{p['hapax_share_of_rows']*100:.3f}% of named rows)")
        print("   top 10: " + ", ".join(f"{k}={v:,}"
                                        for k, v in p["top20"][:10]))
        print()

    # Whether the same place appears under more than one string. Printed as the
    # strings and their counts, because a count of variants is exactly what a
    # reader cannot check and the strings are exactly what they can.
    print("the same place under more than one string, on the common ports:")
    spelling = {}
    for place, variants in SPELLING_PROBE.items():
        row = {}
        for key in ("departure", "destination"):
            hits = {v: counters[key][v] for v in variants if counters[key][v]}
            if hits:
                row[key] = hits
        spelling[place] = row
        shown = row.get("departure") or row.get("destination") or {}
        print(f"  {place:16s} " + ", ".join(f"{k}={v:,}"
                                            for k, v in sorted(
                                                shown.items(),
                                                key=lambda kv: -kv[1])))
    print()

    years = load_years()
    span = [y for y in years.values() if 1400 < y < 1900]
    print(f"customs entries with a year: {len(years):,}, "
          f"range {min(span)}-{max(span)}\n")

    cov = {k: per_year(f, k, years)
           for f, k in (("departure.csv", "departure"),
                        ("destination.csv", "destination"))}
    print("  year   entries   departure named   destination named")
    for y in MARKS:
        dt = cov["destination"]["total"].get(y, 0)
        if not dt:
            continue
        pn = cov["departure"]["named"].get(y, 0)
        pt = cov["departure"]["total"].get(y, 1)
        dn = cov["destination"]["named"].get(y, 0)
        print(f"  {y}  {dt:8,}  {100*pn/max(pt,1):14.1f}%  "
              f"{100*dn/max(dt,1):16.1f}%")

    # The first year from which both fields are populated in nearly every row,
    # printed with the rule that picked it rather than as a bare number.
    both = sorted(
        y for y in cov["destination"]["total"]
        if 1400 < y < 1900
        and cov["destination"]["total"][y] >= 500
        and cov["departure"]["named"].get(y, 0)
        / max(cov["departure"]["total"].get(y, 1), 1) >= 0.95
        and cov["destination"]["named"].get(y, 0)
        / max(cov["destination"]["total"][y], 1) >= 0.95)
    runs = []
    for y in both:
        if runs and y == runs[-1][-1] + 1:
            runs[-1].append(y)
        else:
            runs.append([y])
    longest = max(runs, key=len) if runs else []
    if longest:
        print(f"\n  longest unbroken run with both fields at 95 per cent or "
              f"better, on years with at least 500 entries: "
              f"{longest[0]}-{longest[-1]}, {len(longest)} years")

    norms = {k: normalise_ladder(counters[k], k)
             for k in ("departure", "destination")}

    doc = {
        "stage": "A26",
        "sections": {"stro_probe": {
            "criteria": [{
                "name": "A26-5",
                "passed": bool(longest),
                "detail": (
                    "carrier probe, no threshold on any estimator. The port "
                    "fields carry "
                    f"{profiles['departure']['distinct']:,} and "
                    f"{profiles['destination']['distinct']:,} distinct strings "
                    "and are not standardised; the placeholder covers "
                    f"{profiles['departure']['placeholder_share']*100:.1f} and "
                    f"{profiles['destination']['placeholder_share']*100:.1f} "
                    "per cent of rows; both fields reach 95 per cent from "
                    + (f"{longest[0]} to {longest[-1]}" if longest else "no year")
                    + ". Whether a pair panel can be built from this is a "
                      "question about standardisation, not about coverage")}],
            "profiles": profiles,
            "normalisation_ladder": norms,
            "spelling_probe": spelling,
            "coverage_by_year": cov,
            "both_fields_95_run": [longest[0], longest[-1]] if longest else None,
            "diagnostic_only": True,
            "diagnostic_reason": (
                "carrier availability probe. No A26 criterion is scored on "
                "this data and none can be until the port strings are anchored "
                "to something outside the register")}}}
    RECORD.write_text(json.dumps(doc, ensure_ascii=False, indent=2,
                                 sort_keys=True) + "\n", encoding="utf-8")
    print(f"\n   record: {RECORD.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
