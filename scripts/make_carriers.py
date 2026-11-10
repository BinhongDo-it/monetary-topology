"""Build CARRIERS.md: what this programme has read, and what each reading asks.

A carrier here is one object in the world that a station took a reading off:
a loan book, a quote feed, a published price list, a statute, an archive. It is
not a station and not a file. Several stations can share one carrier, and one
station can stand on two.

The table below is curated rather than derived, because whether two files are one
carrier is a judgement and not a string match. What is checked mechanically is
that every station named here is a station the ledger carries, so a row cannot
point at something that does not exist, and that the counts printed in the file
are computed from the table rather than typed into it.

Two counts come out of the same table and they answer different questions:

  carriers        distinct objects in the world, each counted once however many
                  stations read it and however many economies it spans
  units inside    for the carriers that are themselves cross-sectional, how many
                  economies, provinces or schedules sit inside them

The first is the conservative one. The second is the one that says how wide the
reach is. Neither is typed anywhere: both are computed here.

    python scripts/make_carriers.py              write CARRIERS.md
    python scripts/make_carriers.py --check      exit non-zero if CARRIERS.md is stale
    python scripts/make_carriers.py --selftest   plant faults and check they are caught

Derived-file discipline: no clock, no paths, no host, encoding pinned at both
ends, iteration order fixed.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "RESULTS.md"
CARRIERS = ROOT / "CARRIERS.md"

# Kind: what sort of object it is. Question: what the readings off it ask.
#
# Every row is (name, kind, question, stations, span). `span` is the number of
# economies, jurisdictions, provinces or separate published schedules inside a
# carrier that is itself a cross-section, and 1 where the carrier is one object.
# `stations` are ledger station ids and are checked against RESULTS.md.

MICRO = "household and mortgage administrative microdata"
QUOTE = "exchange, dealer and posted quotes"
LIST = "published price lists, tariffs and fee schedules"
LAW = "statute, regulation and the official record"
STATS = "official statistics and administrative panels"
ARCHIVE = "historical archives"
DECLARED = "declared conversion systems outside money"

LOOP = "loop sum against a scalar field's zero"
COUNT = "the counting law on written class values"
REACH = "reachability, and the registration point that opens an edge"
ZERO = "the zero domain, where the framework predicts zero"
RANK = "the rank of the obstruction"
CUT = "an edge cut or restored, and what it rewrites"
STAY = "where new claims enter, and how long they stay"
INDEXN = "an index number read as a projection"

CARRIER_ROWS = [
    # ---- household and mortgage administrative microdata ----
    ("US mortgage application and origination records, loan level",
     MICRO, LOOP, ["B2A", "B2B", "B2c", "B1", "B7"], 1,
     "20,071,740 loans in 1,103,962 position-and-date cells"),
    ("One guarantor's single-family loan performance file",
     MICRO, LOOP, ["B8"], 1,
     "2,942,295 loans; 49,649 modification and 35,659 deferral loops"),
    ("A second guarantor's single-family loan performance file",
     MICRO, LOOP, ["B10", "B12"], 1,
     "1,362,490 loans, 74,937,616 monthly rows, 28 vintages"),
    ("A published household balance-sheet cross-section",
     MICRO, LOOP, ["A1a", "A1b", "A1c", "A1d"], 1,
     "the one place the simulation track is asked to meet a measured population"),

    # ---- exchange, dealer and posted quotes ----
    ("One exchange's implied and directly quoted spread markets",
     QUOTE, ZERO, ["B13", "B18"], 1,
     "81,968 bid and offer readings over eight products and three channels"),
    ("An exchange-traded fund's creation and redemption triangle",
     QUOTE, LOOP, ["B9"], 1,
     "the published fee schedule plus the venue quotes on both legs"),
    ("A dated, symmetric tick-size change and its control group",
     QUOTE, LOOP, ["B14", "L2"], 1,
     "two rounds, 618 and 2,110 symbols, read on the symbols they share"),
    ("Dual-listed A and H share pairs",
     QUOTE, LOOP, ["B21", "B24"], 1,
     "62 pairs, 465 same-bell pairings, 4,226 leg-years"),
    ("One country's simultaneously quoted legal conversion tracks",
     QUOTE, RANK, ["B5", "B17"], 1,
     "daily, several tracks quoted at once and all of them legal"),
    ("A central bank's own published segment table",
     QUOTE, REACH, ["B6-A"], 1, "207 publication days"),
    ("A peer-collected informal exchange rate for the same country",
     QUOTE, REACH, ["B6-B"], 1, "the instrument B6's reading is calibrated against"),
    ("A central bank's daily reference rate, as an outside referee",
     QUOTE, REACH, ["B6-A"], 1, "the one source in that station it does not own"),
    ("A second country with an official rate and a parallel market",
     QUOTE, REACH, ["B15"], 1, "B6's zero calibration, judged on B6's own thresholds"),
    ("Covered interest parity legs on government bonds",
     QUOTE, LOOP, ["B3"], 1, "cycles that never touch one issuer"),
    ("A third party's daily implied-rate posts",
     QUOTE, CUT, ["B48", "B62"], 1,
     "287 daily posts over two years, and three dated removals of its input"),
    ("One agency's corporate long-term issuer ratings",
     QUOTE, REACH, ["B11"], 1, "259 issuers carrying the distressed-exchange marker"),
    ("Airline fares", QUOTE, LOOP, ["B30"], 1, "one of three quote carriers opened together"),
    ("A sovereign constant-maturity yield curve", QUOTE, LOOP, ["B30"], 1, "same batch"),
    ("An overnight rate panel", QUOTE, LOOP, ["B30"], 1, "same batch"),
    ("A-share private placements, their unlock batches and daily bars",
     QUOTE, REACH, ["B110", "B120"], 1,
     "an edge into new shares open to at most 35 named investors"),
    ("Soybean futures and basis on both sides of one tariff",
     QUOTE, CUT, ["B115"], 1, "Dalian against the US Gulf, with the currency removed"),
    ("Sorghum and corn free-on-board tables",
     QUOTE, CUT, ["B115"], 1, "a deposit imposed and refunded, read against corn"),
    ("Black Sea grain prices on both sides of a corridor loss",
     QUOTE, CUT, ["B111"], 2, "909 cells transcribed by hand, one source URL each"),
    ("An exchange's registered deliverable grain workbooks",
     QUOTE, REACH, ["B42"], 1, "a published quantity carrying a commodity index"),
    ("State daily cash grain bids",
     QUOTE, LOOP, ["B41"], 1, "thirty daily reports and four commodities"),
    ("Daily arrivals and prices at regulated agricultural markets",
     QUOTE, LOOP, ["B60", "B61"], 1, "market-level daily series across several states"),
    ("A crowd-sourced international price archive",
     QUOTE, RANK, ["B38", "B38b", "B38c", "B38d", "B30-5"], 64,
     "53 items on the 1,263 cities carrying all of them; the bulk packaging covers 64 countries"),
    ("An independently collected posted price, as referee",
     QUOTE, RANK, ["B39"], 1, "a source with no contact with the first one"),
    ("Public auction results and retail listings for one wine appellation's vintages",
     QUOTE, LOOP, ["B126"], 1, "505 vintage pages of 32 wines; squares of two vintages by two auction houses"),
    ("An auction house's handbag sale results, every public lot from 2021 to 2026",
     QUOTE, LOOP, ["B127"], 1, "46 sales; the resale price over the boutique price of one bag at one position"),

    # ---- published price lists, tariffs and fee schedules ----
    ("An international end-use energy price data set",
     LIST, LOOP, ["B49"], 13, "the two carriers in it that cannot be resold past the meter"),
    ("A bi-annual European energy price panel",
     LIST, LOOP, ["B50", "B52"], 33,
     "every geography the source carries, 38 semesters, three tax bases"),
    ("The residential annex of a global electricity tariff survey",
     LIST, COUNT, ["Counting", "B58"], 53, "53 national residential schedules"),
    ("Chinese residential block electricity tariffs",
     LIST, COUNT, ["B102"], 2, "two published block schedules on one position axis"),
    ("A utility's net metering price sheets, two vintages",
     LIST, LOOP, ["B98"], 1, "one kilowatt hour, one meter, one hour, two vintages"),
    ("A wholesale nodal price published with its own components",
     LIST, ZERO, ["B98"], 1, "the publisher printed the answer before the station read it"),
    ("Published tuition schedules across a national higher-education census",
     LIST, COUNT, ["B53"], 1, "three classes per school, figures in whole dollars"),
    ("A state's hunting and fishing licence fee schedule",
     LIST, COUNT, ["B55"], 1, "104 cells carrying 45 distinct figures"),
    ("Monument admission priced by nationality",
     LIST, COUNT, ["B56", "B57"], 1, "the class line is checked at the gate"),
    ("Reduced transit fares required as a condition of federal assistance",
     LIST, COUNT, ["B56", "B57"], 1, "three named classes, and the schedules that write fewer figures"),
    ("A national fee schedule's split of a surgical package",
     LIST, ZERO, ["B100"], 1, "three published shares that the publisher says sum to one"),
    ("One card network's US interchange schedule",
     LIST, LOOP, ["B123"], 1, "a class line drawn by the statute and one drawn by the network, on one schedule"),
    ("A second card network's US interchange schedule, two editions",
     LIST, LOOP, ["B123"], 1, "the same two class lines drawn by a second designer"),
    ("An airport operator's charges per departure airport",
     LIST, LOOP, ["B125"], 1, "passenger, security and reduced-mobility charges by airport group and season"),
    ("Public service reference fares on inter-island air routes",
     LIST, LOOP, ["B125"], 2, "13 routes in one archipelago and 3 in the other, with statutory social fare floors"),
    ("Boutique list prices for rationed handbags, from price trackers",
     LIST, LOOP, ["B127"], 1, "two trackers agree on every shared figure; complete for two sizes in one leather"),

    # ---- statute, regulation and the official record ----
    ("A national wage supplement scheme's regulations",
     LAW, COUNT, ["B33"], 1, "five classes, their clause vectors, and where they fold"),
    ("A national tax code's filing statuses, and the table built on them",
     LAW, COUNT, ["B33"], 1,
     "five registration classes, four printed cells, and the published aggregate beside them"),
    ("The rule excluding one class from interest on central bank balances",
     LAW, LOOP, ["B59"], 1,
     "same obligor, same instrument, and a published rate one class cannot earn"),
    ("Regulatory bank call reports",
     LAW, LOOP, ["B59"], 1, "2009Q1 to 2026Q2, what each size class pays overnight"),
    ("A central bank's discount window loan files",
     LAW, REACH, ["B113"], 1, "56 quarterly workbooks"),
    ("A bilateral tax treaty network",
     LAW, COUNT, ["B23"], 20, "sixteen of twenty countries carry a binding wedge"),
    ("A statutory minimum wage with moving age boundaries, and the labour survey under it",
     LAW, COUNT, ["B34"], 1, "four boundary moves, and the break moves with the statute"),
    ("A city's two parallel allocation legs for one licence",
     LAW, REACH, ["B45"], 1, "a lottery and an auction, same city, same month, no swap"),
    ("A capital control imposed and lifted class of edge by class of edge",
     LAW, CUT, ["B97"], 1, "eight dated relaxations, sequenced by the authorities themselves"),
    ("An import quota and the plant registrations beside it",
     LAW, REACH, ["B36"], 1, "the quota did not bind and the registration date did"),
    ("A bound import duty schedule across reporters",
     LAW, COUNT, ["B30"], 190, "190 reporters on one tariff line"),
    ("A corpus of national currency reforms and their texts",
     LAW, COUNT, ["B46", "B47", "B30"], 9,
     "nine reforms re-coded by what each class receives, and more in the corpus behind them"),
    ("A privatisation agency's firm-level disposal record, released under freedom of information",
     LAW, REACH, ["B40"], 1, "13,378 firms in seven disposal classes"),
    ("A value added tax law's input deduction by buyer class",
     LAW, LOOP, ["B122"], 1, "three rates by three buyer classes, nine squares, four independent"),
    ("A consumption tax's invoice transition schedule by seller class",
     LAW, LOOP, ["B122"], 1, "one loop read as a dose over five dated steps"),
    ("An island resident air fare discount and the statute that sets its base",
     LAW, LOOP, ["B125"], 1, "a share of the fare with three airport charges taken out of the base, and its dated history"),
    ("A city's rent cap statute and the rent index its table was derived from",
     LAW, COUNT, ["B129"], 1, "twelve values for one kind of dwelling, each a 2013 rent-index base times one factor"),

    # ---- official statistics and administrative panels ----
    ("A national statistical yearbook's city panel",
     STATS, RANK, ["B30-5"], 1, "an administrative list of cities rather than a selection"),
    ("A multi-country growth and labour accounts database",
     STATS, INDEXN, ["B101", "B106"], 34, "34 countries and 60 industries"),
    ("An international price comparison programme's benchmark rounds",
     STATS, INDEXN, ["B83"], 1, "two published rounds and two published price indices"),
    ("A monetary union's reserve and cross-border payment statistics",
     STATS, STAY, ["B112"], 21, "21 national components of one system"),
    ("A community currency's complete transfer archive",
     STATS, STAY, ["B114", "B117"], 1, "every transfer over seventeen months, with timestamps"),
    ("One country's domestic prices against its own border prices",
     STATS, LOOP, ["B31"], 1, "four commodities, 79 commodity-years, 106 writable squares"),
    ("A central bank's average interchange fee by network, as referee",
     STATS, LOOP, ["B123"], 1, "the statutory cap read back on 220 network-years"),

    # ---- historical archives ----
    ("A four-century toll register",
     ARCHIVE, COUNT, ["B44"], 1, "2,152,670 passages, a flag class recorded on both sides of two treaties"),
    ("A two-tier gold market and the official stock behind it",
     ARCHIVE, REACH, ["B64"], 1, "the classes that could still walk the conversion"),
    ("A national population series by single year of age",
     ARCHIVE, COUNT, ["B46"], 1, "read as the difference of two series"),

    # ---- declared conversion systems outside money ----
    ("Global warming potentials across every assessment report",
     DECLARED, LOOP, ["C1"], 11, "105 species, 11 published standards, 339 independent loops"),
    ("Provincial admission filing lines after one national examination",
     DECLARED, COUNT, ["C3", "E1"], 15, "5,771 institution entries, 2,077,374 determined comparisons"),
    ("A second administrative system of the same kind, as a control",
     DECLARED, COUNT, ["C2"], 1, "115 colleges, 84,018 placements, six parallel schemes at once"),
    ("A storefront's tag directory and its price enumeration",
     DECLARED, COUNT, ["B30"], 1, "a price list nobody has to agree with anybody about"),
]

KIND_ORDER = [MICRO, QUOTE, LIST, LAW, STATS, ARCHIVE, DECLARED]

HEAD = """# Carriers

**A carrier is one object in the world that a station took a reading off**: a loan
book, a quote feed, a published price list, a statute, an archive. It is not a
station and not a file. Several stations can share one carrier, and one station
can stand on two.

**[RESULTS.md](RESULTS.md) is the record and the authority**, and the station
column below is where each carrier's readings are. [INDEX.md](INDEX.md) maps the
ledger by station; this file maps it by what was read.

**Two counts come out of the table and they answer different questions.** The
first counts objects in the world, each once, however many stations read it and
however many economies it spans. The second counts the economies, provinces and
separate published schedules inside the carriers that are themselves
cross-sectional. Both are computed from the table by
`scripts/make_carriers.py`, which also checks that every station named here is
one the ledger carries.

**The simulation track has no carrier in this sense.** It builds its own
population, and the stations from B63 to B96, which recover standard price
theories as special cases, read no data at all. What is counted here is the
measurement work.
"""


def stations_in_results():
    ids = set()
    for line in RESULTS.read_text(encoding="utf-8").split("\n"):
        if not line.startswith("## "):
            continue
        m = re.match(r"^([A-Za-z]+\d+(?:[A-Za-z](?![A-Za-z])|_[A-Za-z0-9]+|-[A-Za-z0-9]+)*)",
                     line[3:].strip())
        if m:
            ids.add(m.group(1))
        else:
            ids.add(line[3:].strip().split()[0])
    return ids


def unknown_stations(rows, known):
    bad = []
    for name, _kind, _q, sts, _span, _note in rows:
        for s in sts:
            if s not in known:
                bad.append((name, s))
    return bad


def build(rows):
    out = [HEAD]
    by_kind = {}
    for r in rows:
        by_kind.setdefault(r[1], []).append(r)

    carriers = len(rows)
    spans = sum(r[4] for r in rows)
    stations = sorted({s for r in rows for s in r[3]})

    out.append("## What the counts are\n")
    out.append("| | |")
    out.append("|---|---|")
    out.append("| carriers, each object counted once | **%d** |" % carriers)
    out.append(
        "| economies, jurisdictions and separate schedules inside them | **%d** |" % spans
    )
    out.append("| kinds of object | **%d** |" % len(by_kind))
    out.append("| stations standing on them | **%d** |" % len(stations))
    out.append("")
    out.append(
        "**The first row is the number to use where one is wanted.** The second is "
        "larger because several carriers are themselves cross-sections, and it is "
        "the reach rather than the count.\n"
    )

    for kind in KIND_ORDER:
        group = by_kind.get(kind, [])
        if not group:
            continue
        out.append("## " + kind[0].upper() + kind[1:] + "\n")
        out.append("| carrier | what the readings ask | stations | what is inside it |")
        out.append("|---|---|---|---|")
        for name, _k, q, sts, _span, note in group:
            out.append(
                "| %s | %s | %s | %s |" % (name, q, ", ".join(sts), note)
            )
        out.append("")
    return "\n".join(out).replace("\n\n\n", "\n\n") + "\n"


def render():
    return build(CARRIER_ROWS)


def selftest():
    failures = []
    known = stations_in_results()

    bad = unknown_stations(CARRIER_ROWS, known)
    if bad:
        failures.append(
            "rows name stations the ledger does not carry: "
            + "; ".join("%s -> %s" % (n, s) for n, s in bad[:6])
        )

    # A row pointing at a station that does not exist has to be reported.
    planted = list(CARRIER_ROWS) + [("a planted carrier", MICRO, LOOP, ["B9999"], 1, "")]
    if not unknown_stations(planted, known):
        failures.append("a planted unknown station id was not reported")

    # The counts must come off the table rather than out of the prose.
    one = build([("x", MICRO, LOOP, ["B8"], 7, "n")])
    if "| carriers, each object counted once | **1** |" not in one:
        failures.append("the carrier count is not computed from the table")
    if "separate schedules inside them | **7** |" not in one:
        failures.append("the span count is not computed from the table")

    # Two rows on one carrier's span must add, not replace.
    two = build([("x", MICRO, LOOP, ["B8"], 7, "n"), ("y", QUOTE, LOOP, ["B9"], 5, "n")])
    if "separate schedules inside them | **12** |" not in two:
        failures.append("spans do not add across rows")

    # Every kind in the order list has to reach the file, whole and on one line.
    for kind in KIND_ORDER:
        probe = build([("x", kind, LOOP, ["B8"], 1, "n")])
        want = "## " + kind[0].upper() + kind[1:]
        if want not in probe.split("\n"):
            failures.append("the heading for kind %r is not one line" % kind)
    # No carrier may be listed twice under one name.
    names = [r[0] for r in CARRIER_ROWS]
    if len(set(names)) != len(names):
        dup = sorted({n for n in names if names.count(n) > 1})
        failures.append("a carrier is listed twice: " + ", ".join(dup))

    for f in failures:
        print("SELFTEST FAIL:", f)
    if failures:
        return 1
    print(
        "selftest ok, %d carriers, %d units inside them, %d stations"
        % (
            len(CARRIER_ROWS),
            sum(r[4] for r in CARRIER_ROWS),
            len({s for r in CARRIER_ROWS for s in r[3]}),
        )
    )
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    bad = unknown_stations(CARRIER_ROWS, stations_in_results())
    if bad:
        for n, s in bad:
            print("unknown station %s on row %r" % (s, n))
        return 1

    text = render()
    if args.check:
        if not CARRIERS.exists():
            print("CARRIERS.md is missing; run scripts/make_carriers.py")
            return 1
        if CARRIERS.read_text(encoding="utf-8") != text:
            print("CARRIERS.md is stale; run scripts/make_carriers.py")
            return 1
        print("CARRIERS.md is current")
        return 0

    CARRIERS.write_text(text, encoding="utf-8", newline="\n")
    print(
        "wrote CARRIERS.md, %d carriers, %d units inside them"
        % (len(CARRIER_ROWS), sum(r[4] for r in CARRIER_ROWS))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
