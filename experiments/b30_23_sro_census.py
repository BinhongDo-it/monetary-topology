"""Which exchanges stopped filing their own fee schedule, and when.

The arm asks whether a procedure travels with a change of control. Two attempts on
insurance rate filings returned negatives with a structural cause: a filed rating
plan is observable because it is lodged per entity, and being lodged per entity is
what stops it moving. This file runs the same question on a carrier where keeping
the incumbent procedure is not an option, because the licence itself is retired.

A US exchange fee schedule is published, tiered, and every amendment to it is filed
under Rule 19b-4 and printed in the Federal Register with a date. When an exchange
stops operating, its fee filings stop and its members are priced by another
exchange's schedule.

WHAT THIS PRINTS. Per entity: how many notices, first and last date, and the same
for the subset whose title touches fees. Entities whose filings have stopped are
named. For each stopped entity, every entity whose filings began within two years
either side is listed as a candidate successor. NOTHING IS PAIRED AUTOMATICALLY and
no threshold is placed on any date: the candidates are printed and the pairing is a
reading of what the successor filing says it is, which is a separate step.

The census is the reading, not a search for one case. Across N retirements, how many
end with the schedule replaced is the quantity; zero would be an answer too.

    python experiments/b30_23_sro_census.py
"""
import collections
import json
import os
import re

RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "raw", "fr_sec")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "results", "b30_23_sro_census.json")

# Titles come in four shapes and the fourth is why the names are parsed rather than
# taken whole. Three put the entity in its own semicolon segment; the oldest ones
# separate it from the action with a comma instead, so a raw segment-two count reads
# 391 distinct entities where there are 189.
PREFIX = ("self-regulatory organizations", "self regulatory organizations")
ACTION = re.compile(r"^(Notice|Order|Proposed Rule|Filing|Suspension|Designation"
                    r"|Immediate|Joint|Withdrawal|Institution|Response|Self)", re.I)
CUT = re.compile(r",\s*(Notice|Order|Proposed Rule|Filing|Declaration|Institution)\b",
                 re.I)
SUFFIX = re.compile(r",?\s+(Inc|Incorporated|LLC|LCC|L\.L\.C|Corp|Corporation"
                    r"|Limited)$", re.I)
# A title naming several entities at once is a joint filing and belongs to none of
# them, so it is dropped rather than assigned to the first name in the list.
MULTI = re.compile(r",\s*(and\s+)?[A-Z][^,]*\b(Exchange|LLC|Inc|Corporation|Board"
                   r"|Authority)\b")
FEE = re.compile(r"fee|fees schedule|price list|pricing", re.I)

MIN_FILINGS = 25          # below this an entity is a stub or a parse remnant
STOPPED_BEFORE = "2024-01-01"
WINDOW_DAYS = 730


def normalise(raw):
    s = CUT.split(raw)[0]
    s = re.sub(r"\s*\([^)]*\)", "", s).replace("“", '"').replace("”", '"')
    s = re.sub(r"\s+", " ", s).strip().rstrip(".,")
    s = SUFFIX.sub("", s)
    return re.sub(r"^The\s+", "", s, flags=re.I).lower().rstrip(".,")


def load():
    rows = []
    for name in sorted(os.listdir(RAW)):
        if not name.endswith(".jsonl"):
            continue
        with open(os.path.join(RAW, name), encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i == 0 or not line.strip():
                    continue
                rows.append(json.loads(line))
    return rows


def group(rows):
    by = collections.defaultdict(list)
    dropped = collections.Counter()
    for r in rows:
        title = r["title"]
        if not title.lower().startswith(PREFIX):
            dropped["not a self-regulatory notice"] += 1
            continue
        parts = [x.strip() for x in title.split(";")]
        if len(parts) < 2 or not parts[1] or ACTION.match(parts[1]):
            dropped["entity is inside the action clause"] += 1
            continue
        if MULTI.search(CUT.split(parts[1])[0]):
            dropped["several entities in one notice"] += 1
            continue
        by[normalise(parts[1])].append(r)
    return by, dropped


def days_between(a, b):
    import datetime
    fmt = "%Y-%m-%d"
    return abs((datetime.datetime.strptime(a, fmt)
                - datetime.datetime.strptime(b, fmt)).days)


def main():
    rows = load()
    by, dropped = group(rows)

    ents = []
    for name, rs in by.items():
        if len(rs) < MIN_FILINGS:
            continue
        dates = sorted(r["publication_date"] for r in rs)
        fees = sorted(r["publication_date"] for r in rs if FEE.search(r["title"]))
        ents.append(dict(entity=name, notices=len(rs), first=dates[0], last=dates[-1],
                         fee_notices=len(fees),
                         fee_first=fees[0] if fees else None,
                         fee_last=fees[-1] if fees else None,
                         stopped=dates[-1] < STOPPED_BEFORE))
    ents.sort(key=lambda e: e["last"])

    print(f"notices read                    : {len(rows)}")
    for k, v in dropped.most_common():
        print(f"  dropped, {k:32s}: {v}")
    print(f"distinct entities               : {len(by)}")
    print(f"entities with >= {MIN_FILINGS} notices     : {len(ents)}")
    stopped = [e for e in ents if e["stopped"]]
    print(f"of those, filings have stopped  : {len(stopped)}")
    print()
    print(f"{'entity':42s}{'all':>5s}{'first':>12s}{'last':>12s}"
          f"{'fee':>5s}{'fee first':>12s}{'fee last':>12s}")
    for e in ents:
        print(f"{e['entity'][:42]:42s}{e['notices']:5d}{e['first']:>12s}"
              f"{e['last']:>12s}{e['fee_notices']:5d}"
              f"{str(e['fee_first']):>12s}{str(e['fee_last']):>12s}"
              f"{'   stopped' if e['stopped'] else ''}")

    print("\ncandidate successors: every entity whose filings began within "
          f"{WINDOW_DAYS} days of a stopped entity's last filing.")
    print("Printed, not paired. Which of these is a replacement rather than a "
          "rename is read off the successor's own filing.\n")
    seams = []
    for s in stopped:
        cands = [e["entity"] for e in ents
                 if e["entity"] != s["entity"]
                 and days_between(e["first"], s["last"]) <= WINDOW_DAYS]
        seams.append(dict(stopped=s["entity"], last=s["last"], candidates=cands))
        print(f"  {s['entity'][:38]:38s} last {s['last']}  -> "
              f"{', '.join(cands) if cands else 'none'}")

    rec = dict(notices=len(rows), distinct_entities=len(by),
               min_filings=MIN_FILINGS, stopped_before=STOPPED_BEFORE,
               window_days=WINDOW_DAYS, dropped=dict(dropped),
               entities=ents, seams=seams)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"\nwritten results/{os.path.basename(OUT)}")


if __name__ == "__main__":
    main()
