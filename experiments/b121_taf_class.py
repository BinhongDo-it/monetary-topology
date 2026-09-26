"""B121 arm E, part one: which Call Report filers borrowed from the Term Auction Facility.

The dated designs of this station ran into the calendar: in 2007-09 many policies moved in the same
week, so a move on one day cannot be given to one facility. This arm compares, inside one quarter, the
banks that were on the new edge with the banks that were not. Whatever else moved that quarter moved
for both, and the difference between them is what the edge carries.

Part one builds the class and prints it. The TAF loan file names each borrower by an abbreviated name,
a city and a state (data/raw/b121/taf.csv); the Call Report names each filer in full with the city and
state of its charter. Every match is printed so it can be read.

  not filers    foreign banks' branches and agencies (they file the FFIEC 002), savings institutions
                (they filed the OTS Thrift Financial Report in these years), credit unions
  matched       same state, the name's words after abbreviations are expanded, one clear best
  nationwide    no clear match in the state, one clear best across the country on a stricter bar,
                which is how a national bank whose loans name one city and whose charter names another
                is found
  unresolved    printed, left outside the class; a borrower left outside moves the class difference
                toward zero, never away from it

    python experiments/b121_taf_class.py
"""

from __future__ import annotations

import collections
import csv
import io
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALL = ROOT / "data" / "raw" / "CallReport"
TAF = ROOT / "data" / "raw" / "b121" / "taf.csv"
OUT = ROOT / "results" / "b121_taf_class.json"
POR_ARCHIVES = ["FFIEC CDR Call Bulk All Schedules 03312008.zip",
                "FFIEC CDR Call Bulk All Schedules 12312008.zip",
                "FFIEC CDR Call Bulk All Schedules 03312010.zip"]
YEAR_ARCHIVES = ["FFIEC CDR Call Bulk Subset of Schedules 2009.zip"]

WORD = {"BK": "BANK", "BKG": "BANKING", "AMER": "AMERICA", "SVC": "SERVICES", "SVCS": "SERVICES",
        "CMNTY": "COMMUNITY", "NATL": "NATIONAL", "FIN": "FINANCIAL", "SVGS": "SAVINGS", "SVG": "SAVINGS",
        "TR": "TRUST", "CTR": "CENTER", "INTL": "INTERNATIONAL", "MTG": "MORTGAGE", "CTY": "COUNTY",
        "CNTY": "COUNTY", "VLY": "VALLEY", "MRCH": "MERCHANTS", "MERCH": "MERCHANTS", "CAP": "CAPITAL",
        "CMRC": "COMMERCE", "ASSN": "ASSOCIATION", "MT": "MOUNT", "1ST": "FIRST", "B": "BANK", "TC": "TRUST",
        "NB": "BANK", "ST": "STATE", "FNCL": "FINANCIAL", "CMRL": "COMMERCIAL", "BKR": "BANKERS",
        "PRIV": "PRIVATE", "W": "WEST", "N": "NORTH"}
PHRASE = [(r"\bB\s*&\s*TC\b", " BANK TRUST "), (r"\bB\s*&\s*T\b", " BANK TRUST "), (r"\bT\s*&\s*SB\b", " TRUST SAVINGS BANK ")]
STATES = {"AL": "ALABAMA", "AK": "ALASKA", "AZ": "ARIZONA", "AR": "ARKANSAS", "CA": "CALIFORNIA", "CO": "COLORADO",
          "CT": "CONNECTICUT", "DE": "DELAWARE", "FL": "FLORIDA", "GA": "GEORGIA", "HI": "HAWAII", "ID": "IDAHO",
          "IL": "ILLINOIS", "IN": "INDIANA", "IA": "IOWA", "KS": "KANSAS", "KY": "KENTUCKY", "LA": "LOUISIANA",
          "ME": "MAINE", "MD": "MARYLAND", "MA": "MASSACHUSETTS", "MI": "MICHIGAN", "MN": "MINNESOTA",
          "MS": "MISSISSIPPI", "MO": "MISSOURI", "MT": "MONTANA", "NE": "NEBRASKA", "NV": "NEVADA",
          "NH": "HAMPSHIRE", "NJ": "JERSEY", "NM": "MEXICO", "NY": "YORK", "NC": "CAROLINA", "ND": "DAKOTA",
          "OH": "OHIO", "OK": "OKLAHOMA", "OR": "OREGON", "PA": "PENNSYLVANIA", "RI": "RHODE", "SC": "CAROLINA",
          "SD": "DAKOTA", "TN": "TENNESSEE", "TX": "TEXAS", "UT": "UTAH", "VT": "VERMONT", "VA": "VIRGINIA",
          "WA": "WASHINGTON", "WV": "VIRGINIA", "WI": "WISCONSIN", "WY": "WYOMING", "PR": "PUERTO"}
DROP = {"THE", "NATIONAL", "ASSOCIATION", "NA", "A", "INC", "CORP", "CORPORATION", "COMPANY", "CO", "OF",
        "AND", "FSB", "SSB", "SB", "USA", "U", "S", "OF", "&"}
NOT_FILER = [("branch or agency of a foreign bank", re.compile(r"\b(BR|BRANCH|AGY|AGENCY)\b")),
             ("savings institution (files the OTS Thrift Financial Report)",
              re.compile(r"\b(FSB|F S B|FS&LA|FS & LA|S&LA|SVG|SVGS|SAVINGS)\b")),
             ("credit union", re.compile(r"\b(FCU|CU|CREDIT UNION)\b"))]


def tokens(name: str, keep_state_words: bool = True) -> frozenset[str]:
    s = re.sub(r"\bN\.?\s*A\.?(?=\s|$|,)", " NA ", name.upper())
    for pat, rep in PHRASE:
        s = re.sub(pat, rep, s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s.replace("&", " AND "))
    out = []
    for t in s.split():
        t = WORD.get(t, t)
        if keep_state_words and t in STATES and t not in ("OR", "IN", "ME", "OH"):
            t = STATES[t]
        if t and t not in DROP:
            out.append(t)
    return frozenset(out)


def filers() -> dict[str, dict]:
    out: dict[str, dict] = {}

    def add(rssd, name, city, st):
        out[rssd] = {"name": name.strip(), "city": city.strip().upper(), "state": st.strip().upper(),
                     "tokens": tokens(name)}
    for arc in POR_ARCHIVES:
        z = zipfile.ZipFile(CALL / arc)
        m = next(n for n in z.namelist() if "POR" in n)
        rows = list(csv.reader(z.read(m).decode("latin-1").splitlines(), delimiter="\t"))
        h = [c.strip('"') for c in rows[0]]
        for r in rows[1:]:
            if len(r) >= len(h):
                add(r[h.index("IDRSSD")], r[h.index("Financial Institution Name")],
                    r[h.index("Financial Institution City")], r[h.index("Financial Institution State")])
    for arc in YEAR_ARCHIVES:
        z = zipfile.ZipFile(CALL / arc)
        for n in z.namelist():
            if not n.endswith(").txt"):
                continue
            rd = csv.reader(io.TextIOWrapper(z.open(n), encoding="latin-1"), delimiter="\t")
            h = next(rd)
            i = {k: h.index(k) for k in ("IDRSSD", "Financial Institution Name",
                                         "Financial Institution City", "Financial Institution State")}
            for r in rd:
                if len(r) > max(i.values()):
                    add(r[i["IDRSSD"]], r[i["Financial Institution Name"]],
                        r[i["Financial Institution City"]], r[i["Financial Institution State"]])
    return out


def borrowers() -> dict[tuple, dict]:
    rows = list(csv.reader(TAF.open(encoding="utf-8-sig")))
    hi = next(i for i, r in enumerate(rows) if r and r[0].strip().lower() == "loan date")
    h = [c.strip() for c in rows[hi]]
    ib, ic, isn, ia, idate = (h.index(k) for k in ("Borrower", "Borrower city", "Borrower state",
                                                     "Loan amount", "Loan date"))
    out: dict[tuple, dict] = collections.defaultdict(lambda: {"loans": 0, "amount_mn": 0.0, "dates": set()})
    import datetime as dt
    for r in rows[hi + 1:]:
        if not r or not r[ib].strip():
            continue
        k = (r[ib].strip(), r[ic].strip().upper(), r[isn].strip().upper())
        out[k]["loans"] += 1
        out[k]["amount_mn"] += float(r[ia].replace(",", ""))
        out[k]["dates"].add(dt.datetime.strptime(r[idate].strip(), "%b %d %Y").date().isoformat())
    return out


def score(a: frozenset, b: frozenset) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def match(name, city, st, fl, by_state) -> tuple[str, dict]:
    for label, rx in NOT_FILER:
        if rx.search(name.upper()):
            return label, {}
    t = tokens(name)
    cands = sorted(((score(t, f["tokens"]) + (0.1 if f["city"] == city else 0.0), r)
                    for r in by_state.get(st, ())
                    for f in (fl[r],)), reverse=True)
    gap = cands[0][0] - cands[1][0] if len(cands) > 1 else 1.0
    if cands and cands[0][0] >= 0.75 and gap >= 0.15:
        return "matched in state", {"rssd": cands[0][1], "score": round(cands[0][0], 3)}
    # Every word the same and the same city, and the next best short of that: a tie of two words
    # does not move a bank from one city to another.
    if cands and cands[0][0] >= 1.05 and gap >= 0.05:
        return "matched in state", {"rssd": cands[0][1], "score": round(cands[0][0], 3)}
    # Only a national bank's loans can name a city its charter does not; the first version searched
    # the whole country for every borrower and matched four banks to namesakes in other states.
    wide = []
    if re.search(r"\bNA$", name.upper().replace(".", "").strip()):
        wide = sorted(((score(t, f["tokens"]), r) for r, f in fl.items()
                       if re.search(r"NATIONAL ASSOCIATION|\bN\.?\s?A\.?$", f["name"].upper())), reverse=True)
        if wide and wide[0][0] >= 0.99 and (len(wide) == 1 or wide[0][0] - wide[1][0] >= 0.2):
            return "matched nationwide", {"rssd": wide[0][1], "score": round(wide[0][0], 3)}
    best = (cands or wide)[:2]
    return "unresolved", {"best": [{"rssd": r, "score": round(s, 3), "name": fl[r]["name"],
                                    "city": fl[r]["city"], "state": fl[r]["state"]} for s, r in best]}


def main() -> int:
    fl = filers()
    by_state = collections.defaultdict(list)
    for r, f in fl.items():
        by_state[f["state"]].append(r)
    bor = borrowers()
    total = sum(v["amount_mn"] for v in bor.values())
    print(f"{len(fl):,} Call Report filers named in the 2008Q1, 2008Q4, 2009 and 2010Q1 panels")
    print(f"{len(bor)} TAF borrowers, {sum(v['loans'] for v in bor.values()):,} loans, ${total / 1000:,.1f} bn")

    result, groups = {}, collections.defaultdict(list)
    for (name, city, st), v in sorted(bor.items(), key=lambda kv: -kv[1]["amount_mn"]):
        kind, info = match(name, city, st, fl, by_state)
        rec = {"name": name, "city": city, "state": st, "loans": v["loans"],
               "amount_mn": round(v["amount_mn"], 1), "first": min(v["dates"]), "last": max(v["dates"]),
               "kind": kind, **info}
        if "rssd" in info:
            f = fl[info["rssd"]]
            rec["filer"] = {"name": f["name"], "city": f["city"], "state": f["state"]}
        result[f"{name}|{city}|{st}"] = rec
        groups[kind].append(rec)

    print()
    for kind, recs in sorted(groups.items(), key=lambda kv: -sum(r["amount_mn"] for r in kv[1])):
        amt = sum(r["amount_mn"] for r in recs)
        print(f"  {kind:<62} {len(recs):>4} borrowers  ${amt / 1000:8.1f} bn  {100 * amt / total:5.1f}%")
    for kind in ("matched nationwide", "matched in state", "unresolved"):
        print(f"\n===== {kind}")
        for r in groups.get(kind, []):
            tail = (f"-> {r['filer']['name']} ({r['filer']['city']}, {r['filer']['state']}) {r['score']}"
                    if "filer" in r else f"-> best {[(b['name'], b['state'], b['score']) for b in r.get('best', [])]}")
            print(f"  {r['amount_mn'] / 1000:7.1f}bn  {r['name']} ({r['city']}, {r['state']})  {tail}")

    rssds = sorted({r["rssd"] for r in result.values() if "rssd" in r})
    record = {"stage": "B121", "diagnostic_only": True,
              "diagnostic_reason": "Arm E, part one: the class of Call Report filers that borrowed from the "
                                   "TAF, printed for reading before any price is read against it.",
              "config": {"por_archives": POR_ARCHIVES, "year_archives": YEAR_ARCHIVES,
                         "in_state_bar": 0.75, "nationwide_bar": 0.99, "clear_margin": [0.15, 0.2]},
              "source": {"borrowers": "Board of Governors, TAF transaction data, taf.csv",
                         "filers": "FFIEC CDR Call Report bulk files, panel of reporters"},
              "counts": {k: {"borrowers": len(v), "amount_mn": round(sum(r["amount_mn"] for r in v), 1)}
                         for k, v in groups.items()},
              "class_rssd": rssds, "borrowers": result}
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    print(f"\n{len(rssds)} filers in the class.  written: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
