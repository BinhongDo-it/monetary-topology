"""B11: what the contract route actually covers, before C11-1 is ruled on.

A fill rate is a proxy. The question C11-1 exists to answer is whether ``V`` can
be computed for the loops B11 is going to count, and that is a different number:
the marker lives in Fitch (``RD``) and the contract terms live in Moody's, so
every loop that wants a ``V`` has to survive a cross-agency join first. A file
can report coupons on 94% of its rows and still cover almost none of the 276
obligors that carry the marker.

**This does not count loops.** No investment-grade condition is applied and no
rating path is walked, so C11-0 is untouched. What is measured here is
availability, which is what the registered gate C11-1 asks for: the fill rate
of the contract fields.

Usage::

    python experiments/b11_coverage.py

    python experiments/b11_coverage.py --marker-agency Fitch --terms-agency Moody

The four numbers it returns
---------------------------
Starting from every obligor carrying a limited-default symbol in the marker
agency, each step can only lose obligors, and the report names what each step
costs:

1. carries the marker at all
2. has an LEI, either on the marker row or on another row of the same name
3. that LEI is present in the terms agency
4. and that obligor has at least one instrument there with coupon, maturity and
   par value all present, and which is not a bank credit facility

**Step 4 is the population a contract-priced ``V`` can exist for.** If it is
small, C11-1's 0.90 threshold is answering a question that does not bind, and
the ruling should be made on step 4 rather than on the fill rate.

A yardstick, not a proposal
---------------------------
The report also prints how many obligors carry the terms agency's *own* default
symbol, which needs no join at all. That route was ruled out before the gate
was written, because Moody's ``D-PD`` does not separate a distressed exchange
from a bankruptcy. It is printed because the gap between it and step 4 is what
the cross-agency join costs, and that cost is the thing being weighed.

Three tiers of match, never one number
--------------------------------------
GLEIF's relationship file supplies the ownership edges, so the entity mismatch
can be repaired. **Repairing it too hard is its own error**: rolling every LEI
up to its ultimate parent will match subsidiary A, whose bond was exchanged,
against subsidiary B of the same conglomerate, whose bond was not. ``V`` would
then be computed from a contract that no loop ever touched.

So the match is reported at three tiers and never collapsed:

``T0`` exact LEI. Same legal entity. No inference.
``T1`` immediate family: one is the other's direct or ultimate parent, or the
       two share one parent. The economic unit that issued and restructured is
       almost always inside this.
``T2`` same ultimate root, any distance. An upper bound. A conglomerate with
       forty subsidiaries collapses to one node here, and two of its arms have
       no more to do with each other than two unrelated firms do.
``T3`` the same security, by CUSIP-8. **The strongest tier there is**, and the
       only one where the contract ``V`` is built from is the contract the
       exchange actually rewrote. No entity inference at all.
``T4`` the same issuer, by CUSIP-6. Upper bound on T3, and it carries T2's
       defect in a smaller form: the terms come from another bond of the same
       issuer rather than the exchanged one.

The LEI tiers were run first and came back nearly empty (27 exact, 29 after the
full GLEIF rollup, 2026-08-17). **That refuted the entity-mismatch hypothesis**:
the cause is not that the two agencies rate different arms of a family, it is
that Moody's publishes an LEI for only 4,023 distinct entities across 557,736
rows. CUSIP is on 57% of Moody's rows and 66% of Fitch's, so it is the key the
data actually supports.

**The ruling on C11-1 should be made on T1.** T0 is too strict, because a
finance subsidiary issuing under a parent guarantee is the ordinary structure
in this market and not a mismatch. T2 is too loose for the reason above. T0 and
T2 are printed as the bracket around it.

Two things about the GLEIF file, recorded before any number is read
-------------------------------------------------------------------
**Fund relationships are excluded.** ``IS_FUND-MANAGED_BY``, ``IS_SUBFUND_OF``
and ``IS_FEEDER_TO`` are 223,728 of the file's 484,559 rows, and a fund managed
by a bank is not the bank's subsidiary in any sense B11 uses.
``IS_INTERNATIONAL_BRANCH_OF`` is kept, because a branch is the same legal
person as its head office.

**Level 2 coverage is partial by design.** An entity may file a reporting
exception instead of a parent, and then it has no edge here at all. The rollup
can therefore only raise the match count, and the part it fails to raise is not
evidence that the two agencies rated unrelated companies.
"""

from __future__ import annotations

import argparse
import collections
import csv
import io
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROCR = ROOT / "data" / "raw" / "rocr"
GLEIF = ROOT / "data" / "raw" / "gleif"
RESULTS = ROOT / "results"

#: Ownership, and only ownership. See the module docstring for why the fund
#: relationships are dropped and why a branch is kept.
GLEIF_OWNERSHIP = frozenset(
    {"IS_ULTIMATELY_CONSOLIDATED_BY", "IS_DIRECTLY_CONSOLIDATED_BY", "IS_INTERNATIONAL_BRANCH_OF"}
)
GLEIF_COLUMNS = (
    "Relationship.StartNode.NodeID",
    "Relationship.StartNode.NodeIDType",
    "Relationship.EndNode.NodeID",
    "Relationship.EndNode.NodeIDType",
    "Relationship.RelationshipType",
    "Relationship.RelationshipStatus",
    "Registration.RegistrationStatus",
)
#: A guard, not a parameter. Real ownership chains in this file are a handful of
#: hops; anything longer is a reporting cycle, and the count of walks that hit
#: this is printed so it can never be silently absorbed.
MAX_CHAIN = 16

VALID_NAME = re.compile(r"^(\d{8}) (.+) (Corporate|Financial|Insurance)\.csv$")

CONTRACT_COLUMNS = ("coupon_date", "maturity_date", "par_value")
NO_FIXED_COUPON_TERM = re.compile(r"Bank Credit Facility", re.IGNORECASE)

LIMITED_DEFAULT_SUFFIX = re.compile(r"/(LD|D)$")
LIMITED_DEFAULT_EXACT = frozenset({"RD", "SD"})
DEFAULT_EXACT = frozenset({"D", "DD", "DDD", "D-PD"})
PROVISIONAL = re.compile(r"^\(P\)")
NATIONAL_SCALE = re.compile(r"\.[a-z]{2}$")

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LEI_SHAPE = re.compile(r"^[A-Z0-9]{20}$")

#: Characters 1-6 name the issuer, 7-8 the issue, 9 is a check digit. Publishers
#: differ on whether they carry the check digit, so both sides are cut to 8
#: before comparison. Truncating there is exact rather than lossy: the check
#: digit is a function of the first eight, so it distinguishes nothing.
CUSIP_SHAPE = re.compile(r"^[A-Z0-9]{8,9}$")

WINDOWS = (
    ("energy", "2015-01-01", "2016-12-31"),
    ("covid", "2020-01-01", "2021-12-31"),
    ("rates", "2022-01-01", "2023-12-31"),
)

#: Legal-form tails carry no identity. Dropped before names are compared, and
#: the name join is reported separately from the LEI join so its contribution is
#: always visible rather than folded into one total.
LEGAL_FORMS = re.compile(
    r"\b(INC|INCORPORATED|CORP|CORPORATION|CO|COMPANY|LTD|LIMITED|PLC|LLC|LP|LLP|"
    r"SA|SAS|SPA|NV|BV|AG|GMBH|AB|AS|OYJ|PTE|PTY|SE|KK|HOLDINGS?|GROUP|"
    r"THE|AND|OF)\b",
    re.IGNORECASE,
)
PUNCT = re.compile(r"[^A-Z0-9 ]+")
SPACES = re.compile(r"\s+")


def normalise_name(raw: str) -> str:
    value = PUNCT.sub(" ", (raw or "").upper())
    value = LEGAL_FORMS.sub(" ", value)
    return SPACES.sub(" ", value).strip()


def base_symbol(rating: str) -> str:
    value = PROVISIONAL.sub("", rating.strip()).strip('"')
    return NATIONAL_SCALE.sub("", value)


def classify_rating(rating: str) -> str | None:
    value = rating.strip()
    if not value:
        return None
    base = base_symbol(value)
    if LIMITED_DEFAULT_SUFFIX.search(value) or base in LIMITED_DEFAULT_EXACT:
        return "limited_default"
    if base in DEFAULT_EXACT:
        return "default"
    return None


#: Columns that identify the rated entity rather than the security. Names are
#: deliberately absent: this set indexes the CUSIP lookup, and two unrelated
#: firms can share an exact name string while two identifier values cannot.
ID_COLUMNS = ("obligor_identifier", "legal_entity_identifier", "issuer_identifier")


def obligor_key(row: dict) -> str:
    for column in ("obligor_identifier", "legal_entity_identifier", "issuer_identifier",
                   "obligor_name", "issuer_name"):
        value = (row.get(column) or "").strip()
        if value:
            return f"{column}:{value}"
    return ""


def all_ids(row: dict) -> set[str]:
    """Every identifier a row carries, not just the one ``obligor_key`` picks.

    ``obligor_key`` returns a single winner by priority, and that is right for
    counting distinct obligors but wrong for looking anything up. Fitch fills
    ``obligor_identifier`` on 1.7% of rows and ``issuer_identifier`` on 85.6%,
    so an ``RD`` row that happens to carry both keys under the first while the
    same company's instrument rows key under the second. A lookup keyed on the
    winner then finds nothing, and the report says the company has no CUSIP when
    what happened is that two views of one company never met.

    **This is why the first CUSIP reading was 8 of 276.** Indexing on every
    identifier present is the fix, and it cannot over-merge: two rows join only
    when they carry the same value in the same identifier column.
    """
    out = set()
    for column in ID_COLUMNS:
        value = (row.get(column) or "").strip()
        if value:
            out.add(f"{column}:{value}")
    return out


def any_name(row: dict) -> str:
    return (row.get("obligor_name") or "").strip() or (row.get("issuer_name") or "").strip()


def lei_of(row: dict) -> str:
    value = (row.get("legal_entity_identifier") or "").strip().upper()
    return value if LEI_SHAPE.match(value) else ""


def cusip8_of(row: dict) -> str:
    value = (row.get("CUSIP_number") or "").strip().upper()
    return value[:8] if CUSIP_SHAPE.match(value) else ""


def window_of(date: str) -> str:
    for name, start, end in WINDOWS:
        if start <= date <= end:
            return name
    return "outside"


def load_gleif(path: Path) -> dict:
    """Parent edges, keyed child -> parent, from the Golden Copy relationship file.

    Refuses on a missing column rather than reading blanks: a header that moved
    would otherwise produce an empty map and a report that says the rollup
    bought nothing, which is the same output a real absence of parents gives.
    """
    parent_u: dict[str, str] = {}
    parent_d: dict[str, str] = {}
    kept = collections.Counter()
    dropped = collections.Counter()
    status = collections.Counter()

    with zipfile.ZipFile(path) as bundle:
        members = [m for m in bundle.namelist() if m.lower().endswith(".csv")]
        if len(members) != 1:
            raise SystemExit(f"Expected one CSV inside {path.name}, found {len(members)}.")
        with bundle.open(members[0]) as handle:
            reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8", errors="replace", newline=""))
            missing = [c for c in GLEIF_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise SystemExit(f"{path.name} is missing columns {missing}. The layout moved.")
            for row in reader:
                kind = row["Relationship.RelationshipType"]
                if kind not in GLEIF_OWNERSHIP:
                    dropped[kind] += 1
                    continue
                if row["Relationship.RelationshipStatus"] != "ACTIVE":
                    dropped[f"{kind}/INACTIVE"] += 1
                    continue
                if row["Relationship.StartNode.NodeIDType"] != "LEI" or row["Relationship.EndNode.NodeIDType"] != "LEI":
                    dropped[f"{kind}/non-LEI node"] += 1
                    continue
                child = row["Relationship.StartNode.NodeID"].strip().upper()
                parent = row["Relationship.EndNode.NodeID"].strip().upper()
                if not (LEI_SHAPE.match(child) and LEI_SHAPE.match(parent)) or child == parent:
                    dropped[f"{kind}/unusable"] += 1
                    continue
                kept[kind] += 1
                status[row["Registration.RegistrationStatus"]] += 1
                if kind == "IS_ULTIMATELY_CONSOLIDATED_BY":
                    parent_u.setdefault(child, parent)
                else:
                    parent_d.setdefault(child, parent)

    return {
        "ultimate": parent_u,
        "direct": parent_d,
        "kept": dict(kept.most_common()),
        "dropped": dict(dropped.most_common()),
        "registration_status": dict(status.most_common()),
    }


def make_root(gleif: dict):
    """``lei -> ultimate root``, memoised, with the cycle and depth guards counted."""
    ultimate, direct = gleif["ultimate"], gleif["direct"]
    memo: dict[str, str] = {}
    hits = collections.Counter()

    def root(lei: str) -> str:
        if lei in memo:
            return memo[lei]
        trail: list[str] = []
        seen: set[str] = set()
        current = lei
        while True:
            if current in seen:
                hits["cycle"] += 1
                break
            seen.add(current)
            trail.append(current)
            nxt = ultimate.get(current) or direct.get(current)
            if not nxt or nxt == current:
                break
            if len(trail) >= MAX_CHAIN:
                hits["depth_cap"] += 1
                break
            current = nxt
        for node in trail:
            memo[node] = current
        return current

    root.guard_hits = hits  # type: ignore[attr-defined]
    return root


def one_hop(gleif: dict, lei: str) -> str | None:
    return gleif["ultimate"].get(lei) or gleif["direct"].get(lei)


def pick_files(agency: str) -> list[Path]:
    out = []
    for path in sorted(ROCR.glob("*.csv")):
        match = VALID_NAME.match(path.name)
        if match and agency.lower() in match.group(2).lower():
            out.append(path)
    return out


def read_marker_side(paths: list[Path]) -> dict:
    """Every obligor carrying a limited-default symbol, with what identifies it."""
    marked: dict[str, dict] = {}
    lei_by_name: dict[str, set[str]] = collections.defaultdict(set)
    cusip_by_key: dict[str, set[str]] = collections.defaultdict(set)
    rows_seen = 0
    cusip_rows = 0

    for path in paths:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            for row in csv.DictReader(handle):
                rows_seen += 1
                name = normalise_name(any_name(row))
                lei = lei_of(row)
                if name and lei:
                    lei_by_name[name].add(lei)
                # Every row of every obligor, not only the marker row: the
                # exchanged bond and the rating action on it are usually
                # separate rows, and a CUSIP recorded anywhere under the same
                # obligor is still that obligor's security.
                cusip = cusip8_of(row)
                if cusip:
                    cusip_rows += 1
                    for identifier in all_ids(row):
                        cusip_by_key[identifier].add(cusip)
                if classify_rating((row.get("rating") or "")) != "limited_default":
                    continue
                key = obligor_key(row)
                if not key:
                    continue
                date = (row.get("rating_action_date") or "").strip()
                entry = marked.setdefault(
                    key,
                    {"key": key, "names": set(), "leis": set(), "ids": set(),
                     "dates": [], "files": set()},
                )
                entry["files"].add(path.name)
                entry["ids"] |= all_ids(row)
                if name:
                    entry["names"].add(name)
                if lei:
                    entry["leis"].add(lei)
                if ISO_DATE.match(date):
                    entry["dates"].append(date)

    # Second chance for an LEI: the marker row may not carry one while another
    # row of the same normalised name does. Counted separately below, because a
    # name-derived LEI is a weaker claim than one read off the row itself.
    from_row = sum(1 for e in marked.values() if e["leis"])
    for entry in marked.values():
        if entry["leis"]:
            continue
        for name in entry["names"]:
            entry["leis"] |= lei_by_name.get(name, set())

    reached_by = collections.Counter()
    for entry in marked.values():
        cusips: set[str] = set()
        for identifier in entry["ids"]:
            found = cusip_by_key.get(identifier)
            if found:
                cusips |= found
                reached_by[identifier.split(":", 1)[0]] += 1
        entry["cusips"] = cusips

    return {
        "rows": rows_seen,
        "cusip_rows": cusip_rows,
        "marked": marked,
        "lei_on_marker_row": from_row,
        "lei_after_name_lookup": sum(1 for e in marked.values() if e["leis"]),
        "with_cusip": sum(1 for e in marked.values() if e["cusips"]),
        "with_any_id": sum(1 for e in marked.values() if e["ids"]),
        "cusip_reached_by_column": dict(reached_by.most_common()),
        "cusip_index_keys": len(cusip_by_key),
    }


def read_terms_side(paths: list[Path]) -> dict:
    """LEIs and names that have at least one priceable instrument."""
    lei_present: set[str] = set()
    name_present: set[str] = set()
    lei_priceable: set[str] = set()
    name_priceable: set[str] = set()
    cusip_priceable: set[str] = set()
    own_default_keys: set[str] = set()
    rows_seen = 0
    priceable_rows = 0

    for path in paths:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            for row in csv.DictReader(handle):
                rows_seen += 1
                lei = lei_of(row)
                name = normalise_name(any_name(row))
                if lei:
                    lei_present.add(lei)
                if name:
                    name_present.add(name)
                if classify_rating((row.get("rating") or "")) in ("limited_default", "default"):
                    key = obligor_key(row)
                    if key:
                        own_default_keys.add(key)
                if (row.get("object_type_rated") or "").strip() != "Instrument":
                    continue
                term = (row.get("rating_type_term") or "").strip()
                if NO_FIXED_COUPON_TERM.search(term):
                    continue
                if not all((row.get(c) or "").strip() for c in CONTRACT_COLUMNS):
                    continue
                priceable_rows += 1
                if lei:
                    lei_priceable.add(lei)
                if name:
                    name_priceable.add(name)
                cusip = cusip8_of(row)
                if cusip:
                    cusip_priceable.add(cusip)

    return {
        "rows": rows_seen,
        "priceable_rows": priceable_rows,
        "lei_present": lei_present,
        "name_present": name_present,
        "lei_priceable": lei_priceable,
        "name_priceable": name_priceable,
        "cusip_priceable": cusip_priceable,
        "own_default_obligors": len(own_default_keys),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--marker-agency", default="Fitch")
    parser.add_argument("--terms-agency", default="Moody")
    args = parser.parse_args(argv)

    marker_paths = pick_files(args.marker_agency)
    terms_paths = pick_files(args.terms_agency)
    if not marker_paths or not terms_paths:
        print(f"Need files for both agencies in {ROCR}.")
        print(f"  {args.marker_agency}: {[p.name for p in marker_paths]}")
        print(f"  {args.terms_agency}: {[p.name for p in terms_paths]}")
        return 2

    print(f"marker side : {[p.name for p in marker_paths]}")
    print(f"terms side  : {[p.name for p in terms_paths]}")
    print()

    marker = read_marker_side(marker_paths)
    terms = read_terms_side(terms_paths)
    marked = marker["marked"]

    archives = sorted(GLEIF.glob("*rr-golden-copy.csv.zip")) if GLEIF.exists() else []
    gleif = load_gleif(archives[-1]) if archives else None
    if gleif is None:
        print(f"No GLEIF relationship file in {GLEIF}; only the exact-LEI tier is available.")
        print("Run: python data/fetch_gleif.py --pull")
        print()
    root = make_root(gleif) if gleif else None

    n0 = len(marked)
    with_lei = [e for e in marked.values() if e["leis"]]
    n1 = len(with_lei)
    matched = [e for e in with_lei if e["leis"] & terms["lei_present"]]
    n2 = len(matched)
    priceable = [e for e in matched if e["leis"] & terms["lei_priceable"]]
    n3 = len(priceable)

    # T1 and T2. Both are computed against the priceable side only, because a
    # match to an entity with no usable contract terms buys nothing.
    t1 = t2 = None
    if gleif:
        terms_priceable = terms["lei_priceable"]
        parents_of_terms = collections.defaultdict(set)
        for lei in terms_priceable:
            hop = one_hop(gleif, lei)
            if hop:
                parents_of_terms[hop].add(lei)
        roots_of_terms = collections.defaultdict(set)
        for lei in terms_priceable:
            roots_of_terms[root(lei)].add(lei)

        def family_match(entry: dict) -> bool:
            for lei in entry["leis"]:
                if lei in terms_priceable:          # T0, kept inside T1
                    return True
                if lei in parents_of_terms:         # the terms entity's parent is this obligor
                    return True
                hop = one_hop(gleif, lei)
                if hop and (hop in terms_priceable or hop in parents_of_terms):
                    return True                     # its parent is rated, or is a shared parent
            return False

        t1 = [e for e in with_lei if family_match(e)]
        t2 = [e for e in with_lei if any(root(lei) in roots_of_terms for lei in e["leis"])]

    # CUSIP. Independent of every LEI tier, so it is computed over all marked
    # obligors rather than only those that had an LEI.
    cusip_priceable = terms["cusip_priceable"]
    issuer6_priceable = {c[:6] for c in cusip_priceable}
    with_cusip = [e for e in marked.values() if e["cusips"]]
    t3 = [e for e in with_cusip if e["cusips"] & cusip_priceable]
    t4 = [e for e in with_cusip if {c[:6] for c in e["cusips"]} & issuer6_priceable]

    # What the name join adds on top, kept apart so it is never folded in.
    name_only = [
        e for e in marked.values()
        if not (e["leis"] & terms["lei_priceable"]) and (e["names"] & terms["name_priceable"])
    ]
    n3_plus_names = n3 + len(name_only)

    def per_window(entries: list[dict]) -> dict:
        counter: collections.Counter = collections.Counter()
        for entry in entries:
            for bucket in {window_of(d) for d in entry["dates"]}:
                counter[bucket] += 1
        return dict(sorted(counter.items()))

    print("-- from marker to a computable V, one step at a time --")
    print(f"  1. carries a limited-default symbol            {n0:>6,}")
    print(f"  2. has an LEI                                  {n1:>6,}   "
          f"({marker['lei_on_marker_row']:,} on the marker row itself, "
          f"{marker['lei_after_name_lookup'] - marker['lei_on_marker_row']:,} via same-name lookup)")
    print(f"  3. that LEI appears in the terms agency        {n2:>6,}")
    print(f"  4. and it has a priceable instrument there     {n3:>6,}   "
          f"<-- the population a contract-priced V can exist for")
    print(f"     plus obligors reached only by name match    {len(name_only):>6,}   "
          f"(total {n3_plus_names:,}, reported apart because a name match is weaker)")
    print()
    print(f"  retention, step 1 to step 4 : {n3 / n0:.4f}" if n0 else "  no marked obligors")
    print()

    print("-- the same step 4, by tier --")
    print(f"  T0 exact LEI                      {len(priceable):>6,}")
    if gleif:
        print(f"  T1 immediate family               {len(t1):>6,}")
        print(f"  T2 same ultimate root, any depth  {len(t2):>6,}   (upper bound on the LEI route)")
    print(f"  T3 same security, CUSIP-8         {len(t3):>6,}   <-- strongest tier: the contract")
    print("                                              V uses is the one that was rewritten")
    print(f"  T4 same issuer, CUSIP-6           {len(t4):>6,}   (upper bound on T3)")
    print(f"  marked obligors carrying any CUSIP {marker['with_cusip']:>5,} of {n0:,}   "
          f"(with any identifier at all: {marker['with_any_id']:,})")
    print(f"  reached through which column       {marker['cusip_reached_by_column']}")
    print(f"  priceable CUSIP-8 on the terms side {len(cusip_priceable):>5,}")
    print()
    if gleif:
        print(f"  ownership edges kept : {gleif['kept']}")
        print(f"  registration status  : {gleif['registration_status']}")
        print(f"  guards hit           : {dict(root.guard_hits)}")
        print(f"  dropped, top 4       : {dict(list(gleif['dropped'].items())[:4])}")
        print()

    print("-- per registered window, obligors surviving step 4 --")
    print(f"  step 1 : {per_window(list(marked.values()))}")
    print(f"  T0     : {per_window(priceable)}")
    if gleif:
        print(f"  T1     : {per_window(t1)}")
        print(f"  T2     : {per_window(t2)}")
    print(f"  T3     : {per_window(t3)}")
    print(f"  T4     : {per_window(t4)}")
    print()

    print("-- the yardstick, not a proposal --")
    print(f"  obligors carrying the TERMS agency's own default symbol : {terms['own_default_obligors']:,}")
    print("  That route needs no join, and it was ruled out because it does")
    print("  not separate a distressed exchange from a bankruptcy. The gap between")
    print(f"  {terms['own_default_obligors']:,} and {n3:,} is what the cross-agency join costs.")
    print()
    print(f"  priceable instrument rows in the terms agency : {terms['priceable_rows']:,}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    record = {
        "stage": "B11-coverage",
        "diagnostic_only": True,
        "diagnostic_reason": (
            "Availability measurement for the C11-1 ruling. No investment-grade condition "
            "is applied and no rating path is walked, so C11-0 is not evaluated here."
        ),
        "criteria": [
            {
                "name": "T0 exact LEI: a contract-priced V can exist for >= 200 marked obligors",
                "passed": n3 >= 200,
                "diagnostic": True,
                "detail": (
                    f"{n3} of {n0} obligors carrying the marker survive to a priceable "
                    f"instrument ({n3 / n0:.4f} retention)" if n0 else "no marked obligors"
                ),
            },
            {
                "name": "T1 immediate family: same, allowing one ownership hop",
                "passed": bool(t1) and len(t1) >= 200,
                "diagnostic": True,
                "detail": (
                    f"{len(t1)} of {n0} ({len(t1) / n0:.4f} retention). A finance subsidiary "
                    "issuing under a parent guarantee is the ordinary structure here, so T0 "
                    "understates. This is the tier C11-1 should be ruled on."
                    if t1 is not None and n0 else "GLEIF relationship file absent"
                ),
            },
            {
                "name": "T2 same ultimate root: upper bound only",
                "passed": bool(t2) and len(t2) >= 200,
                "diagnostic": True,
                "detail": (
                    f"{len(t2)} of {n0} ({len(t2) / n0:.4f} retention). Collapses every arm of "
                    "a conglomerate to one node, so a match here can pair an exchanged bond "
                    "with a contract from an unrelated affiliate. Not a basis for a ruling."
                    if t2 is not None and n0 else "GLEIF relationship file absent"
                ),
            },
            {
                "name": "T3 same security by CUSIP-8: a contract-priced V for >= 200 marked obligors",
                "passed": len(t3) >= 200,
                "diagnostic": True,
                "detail": (
                    f"{len(t3)} of {n0} ({len(t3) / n0:.4f} retention). No entity inference: the "
                    "contract V is built from is the security the exchange rewrote. This is the "
                    "tier C11-1 should be ruled on if it clears the LEI tiers."
                    if n0 else "no marked obligors"
                ),
            },
            {
                "name": "T4 same issuer by CUSIP-6: upper bound on T3",
                "passed": len(t4) >= 200,
                "diagnostic": True,
                "detail": (
                    f"{len(t4)} of {n0} ({len(t4) / n0:.4f} retention). Terms may come from a "
                    "different bond of the same issuer than the one exchanged."
                    if n0 else "no marked obligors"
                ),
            },
        ],
        "parameters": {
            "marker_agency": args.marker_agency,
            "terms_agency": args.terms_agency,
            "marker_files": [p.name for p in marker_paths],
            "terms_files": [p.name for p in terms_paths],
            "no_fixed_coupon_term": NO_FIXED_COUPON_TERM.pattern,
            "contract_columns": list(CONTRACT_COLUMNS),
            "windows": [list(w) for w in WINDOWS],
        },
        "funnel": {
            "1_carries_marker": n0,
            "2_has_lei": n1,
            "2a_lei_on_marker_row": marker["lei_on_marker_row"],
            "3_lei_in_terms_agency": n2,
            "4_has_priceable_instrument": n3,
            "4b_reached_only_by_name": len(name_only),
            "4_T1_immediate_family": len(t1) if t1 is not None else None,
            "4_T2_same_ultimate_root": len(t2) if t2 is not None else None,
            "4_T3_same_security_cusip8": len(t3),
            "4_T4_same_issuer_cusip6": len(t4),
            "marked_with_any_cusip": marker["with_cusip"],
            "marked_with_any_identifier": marker["with_any_id"],
            "cusip_reached_by_column": marker["cusip_reached_by_column"],
            "cusip_index_keys": marker["cusip_index_keys"],
            "terms_priceable_cusip8": len(cusip_priceable),
            "per_window_step1": per_window(list(marked.values())),
            "per_window_step4": per_window(priceable),
            "per_window_T1": per_window(t1) if t1 is not None else None,
            "per_window_T2": per_window(t2) if t2 is not None else None,
            "per_window_T3": per_window(t3),
            "per_window_T4": per_window(t4),
        },
        "gleif": None if gleif is None else {
            "file": archives[-1].name,
            "ownership_edges_kept": gleif["kept"],
            "registration_status": gleif["registration_status"],
            "dropped": gleif["dropped"],
            "guard_hits": dict(root.guard_hits),
            "ownership_types": sorted(GLEIF_OWNERSHIP),
            "max_chain": MAX_CHAIN,
        },
        "terms_side": {
            "rows": terms["rows"],
            "priceable_rows": terms["priceable_rows"],
            "own_default_obligors": terms["own_default_obligors"],
            "distinct_leis": len(terms["lei_present"]),
            "distinct_leis_priceable": len(terms["lei_priceable"]),
        },
        "marker_side": {"rows": marker["rows"]},
    }
    out = RESULTS / f"b11_coverage_{args.marker_agency.lower()}_{args.terms_agency.lower()}.json"
    out.write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print()
    print(f"written: {out}  (diagnostic_only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
