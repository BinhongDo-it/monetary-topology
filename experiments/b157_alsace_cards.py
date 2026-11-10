"""B157: Alsace and Lorraine 1918, the mark exchange and the identity cards, read as two partitions.

Object.  Two procedures sorted the same population in the same weeks.  The arrêté of
26 November 1918 (Journal officiel, 7 December 1918, p. 10544) wrote one exchange rate,
1 fr. 25 per mark, at three positions: cash in circulation (art. 3), bank deposits (art. 9)
and contracts written in marks (art. 11), each with its own list of eligible holders.  The
arrêté of 14 December 1918 on police in the liberated communes (reported in Le Temps,
18 December 1918; articles 2 and 4 transcribed by the Archives d'Alsace from the printed
copy AVES 503 Fi 72) issued four identity cards a to d by birthplace and parents' origin,
and wrote a travel range per card.  Class: the holder's standing as each text writes it.
Value: francs per mark; "unwritten" (no exchange path at that position) is a value.  The
market price of the mark (about 0.70) is the price of a different path and is not counted.

Every item names its source file in data/raw/b157/ and a quote that must be found in that
file after Unicode and whitespace normalisation (OCR errors are kept as they stand); items
from pages that were read and not stored say so.

Criteria (kind in brackets):
  B157-1 [bookkeeping]  item table and coverage table: every item has a source and a grade
                        (official / research / other), and an item from a stored file has a
                        quote found in that file; every file in data/raw/b157, any extension,
                        is listed with its SHA-256, recomputed
  B157-2 [own_reading]  class values per position, read from the arrêté's own articles: the
                        rate is parsed from each article and the classes it names are quoted
                        from that article; distinct values per position and the partition each
                        position draws; flag: every cell filled, every naming quote inside its
                        article, one rate per article, articles 1 to 12 present
  B157-3 [own_reading]  card x exchange-class cross table at the cash position, over seven
                        population types; state per card: one class / spans two /
                        undeterminable; flag: the card rule as executed is a partition and
                        gives the cards documented for the Cassel family (AD67 286 D 175)
  B157-4 [own_reading]  travel range per card in both transcriptions; distinct ranges; flag:
                        both give the same range for every card
  B157-5 [own_reading]  the loop "an eligible holder exchanges an ineligible holder's marks",
                        article by article: cut / priced / open, and a state per path
  B157-6 [own_reading]  changing a card: edge absent / procedural edge / undeterminable, read
                        from the dated steps of the Cassel file

Run:  python -B experiments/b157_alsace_cards.py            (writes results/b157_alsace_cards.json)
      python -B experiments/b157_alsace_cards.py --selftest (planted errors, each must flip)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b157"
RECORD = ROOT / "results" / "b157_alsace_cards.json"
SESSION = "B157"

# ---------------------------------------------------------------------------
# Files and sources
# ---------------------------------------------------------------------------
FILES = {  # every file in data/raw/b157 -> SHA-256 of the stored bytes
    "jo_1918-12-07_p10544_ocr.txt": "2e2e434a91dbfdf7017657cd54b4a315dc1e27d1255b0390ba8f868d5619155c",
    "le_temps_1918-12-18_alsace_ocr.txt": "4a67727f37e90bc4a6e787c7c1471f4d13150208c7b03563b1c0184b3fbcba80",
    "ad67_fiche07_triage_cartes.pdf": "b73cebea3b137413ccc9b6d1f8a862fb89f089ab3bafd9dd3a7856de2a2a1000",
    "ad67_fiche07_triage_cartes_text.txt": "c6fc0210482a0cd8b8aa770c34cfbb7a0ad71895038a8e7e8177ddb47c4235d7",
}
TEXT_FILES = {
    "JO": "jo_1918-12-07_p10544_ocr.txt",
    "LT": "le_temps_1918-12-18_alsace_ocr.txt",
    "AD67": "ad67_fiche07_triage_cartes_text.txt",
}
SOURCE_NAMES = {
    "JO": "Journal officiel 1918-12-07 p. 10544, arrêté of 26 November 1918 (Gallica OCR)",
    "LT": "Le Temps 1918-12-18, report of the arrêté on identity cards (Gallica OCR)",
    "AD67": "Archives d'Alsace, Service éducatif, Fiche 07 (PDF text layer)",
}
GRADES = ("official", "research", "other")
NOT_STORED = {
    "WEIL": "geldscheine-online, 'Die Einführung der französischen Währung in Elsaß-Lothringen 1918', "
            "summarising Bruno Weil (1921); page read, not stored",
    "NITHART": "nithart.com, 'Les 4 cartes d'identité après 1918'; page read, not stored",
}
NOT_OPENED = [
    ("AD 67, 121 AL 1020", "execution file of the mark exchange, 1918-1919: instructions and general "
                           "correspondence; cited by the teaching sheet, not opened"),
    ("Bulletin officiel d'Alsace et de Lorraine", "where the card arrêté's own text would sit; not on Gallica"),
    ("Le Temps 1918-12-01 to 1919-01-31", "62 issues searched for the cards and the exchange in one place; "
                                          "4 read (no item), 58 refused by the server's rate limit"),
]


def norm(s: str) -> str:
    """NFKC (ligatures to letters), typographic apostrophes and hyphens to ASCII, whitespace collapsed."""
    s = unicodedata.normalize("NFKC", s)
    for a, b in (("’", "'"), ("‘", "'"), ("‐", "-"), ("‑", "-")):
        s = s.replace(a, b)
    return " ".join(s.split())


def frags(quote):
    return (quote,) if isinstance(quote, str) else tuple(quote)


def find_seq(text: str, quote) -> bool:
    """Every fragment of the quote is found in the text, in order."""
    pos = 0
    for f in frags(quote):
        f = norm(f)
        i = text.find(f, pos)
        if i < 0:
            return False
        pos = i + len(f)
    return True


def load_texts(raw=RAW):
    return {k: norm((raw / f).read_text(encoding="utf-8")) for k, f in TEXT_FILES.items()}


def folder_names(names):
    """Every file in the folder takes part in the coverage check, whatever its extension, except .expired copies."""
    return sorted(n for n in names if ".expired" not in n)


def load_folder(raw=RAW):
    keep = set(folder_names(f.name for f in raw.iterdir() if f.is_file()))
    return {f.name: f.read_bytes() for f in sorted(raw.iterdir()) if f.name in keep}

# ---------------------------------------------------------------------------
# The exchange arrêté of 26 November 1918, article by article
# ---------------------------------------------------------------------------
ART_RE = re.compile(r"Art[.,]\s*(\d+)(?:er)?\s*[.,]")
RATE_RE = re.compile(r"(\d+)\s*fr\.\s*(\d+)\s*pour\s*1\s*mark")
ARRETE_START = "ministre de la guerre, Arrête"
ARRETE_END = "Paris, le 26 novembre 1918."
UNWRITTEN = "unwritten"


def articles(jo: str) -> dict:
    body = jo[jo.index(ARRETE_START):jo.index(ARRETE_END)]
    hits = list(ART_RE.finditer(body))
    return {int(m.group(1)): body[m.end():hits[k + 1].start() if k + 1 < len(hits) else len(body)]
            for k, m in enumerate(hits)}


def rates_in(body: str) -> list:
    return sorted({f"{int(a)}.{int(b):02d}" for a, b in RATE_RE.findall(body)})


CLASSES = ("AL", "FR", "AN_PRE", "AN_POST", "OTHER")
CLASS_NAMES = {
    "AL": "Alsatians and Lorrainers",
    "FR": "French",
    "AN_PRE": "allied or neutral nationals resident before 1 August 1914",
    "AN_POST": "allied or neutral nationals who came later",
    "OTHER": "German, Austro-Hungarian, Turkish and Bulgarian subjects",
}
POSITIONS = {  # position -> (article, quote naming the eligible classes, classes it names)
    "cash": (3, "aux Alsaciens, aux Lorrains et à ceux des ressortissants alliés ou neutres qui résidaient "
                "en Alsace ou en Lorraine avant le", ("AL", "AN_PRE")),
    "deposit": (9, "titulaires alsaciens, lorrains, français et par ceux des ressortissants de pays alliés ou "
                   "neutres qui étaient domicilies en Alsace ou en Lorraine avant le 1er août 1914",
                ("AL", "FR", "AN_PRE")),
    "contract": (11, "soit entre Alsaciens, soit entre Lorrains, soit entre Alsaciens et Lorrains, soit entre "
                     "Alsaciens ou Lorrains d'une part, et Français d'autre part", ("AL", "FR")),
}
CONTRACT_NOTE = "a contract counts when both parties are named: AL with AL, or AL with FR; FR with FR is not named"
FORK_121_AL_1020 = ("OTHER", "cash", "0.70")  # the teaching sheet's figure for card D, if it were a written rate


def per_position(table, positions=POSITIONS):
    out = {}
    for p in positions:
        groups = {}
        for c in CLASSES:
            groups.setdefault(table.get((c, p)), []).append(c)
        keys = sorted(groups, key=str)
        out[p] = {"distinct": len(groups), "values": keys, "partition": {str(v): groups[v] for v in keys}}
    return out


def b157_2(texts, positions=POSITIONS):
    arts = articles(texts["JO"])
    rows, table, ok = [], {}, True
    for pos, (art, quote, named) in positions.items():
        body = arts.get(art, "")
        rates = rates_in(body)
        inside = find_seq(body, quote)
        ok = ok and inside and len(rates) == 1
        for c in CLASSES:
            table[(c, pos)] = (rates[0] if len(rates) == 1 else None) if c in named else UNWRITTEN
        rows.append({"position": pos, "article": art, "rates_in_article": rates, "classes_named": list(named),
                     "naming_quote_inside_article": inside})
    complete = all(table[(c, p)] is not None for c in CLASSES for p in positions)
    arrete_rates = sorted({r for b in arts.values() for r in rates_in(b)})
    written = sorted({v for v in table.values() if v not in (UNWRITTEN, None)})
    per = per_position(table, positions)
    shapes = {frozenset(frozenset(g) for g in d["partition"].values()) for d in per.values()}
    moves = {c: [table[(c, p)] for p in positions] for c in CLASSES}
    movers = sorted(c for c, v in moves.items() if len(set(v)) > 1)
    fork = dict(table)
    fork[FORK_121_AL_1020[:2]] = FORK_121_AL_1020[2]
    passed = ok and complete and written == arrete_rates and sorted(arts) == list(range(1, 13))
    return passed, {"articles_found": sorted(arts), "rates_in_arrete": arrete_rates, "rows": rows,
                    "table": {f"{c}/{p}": table[(c, p)] for c in CLASSES for p in positions},
                    "per_position": per, "distinct_partitions": len(shapes),
                    "classes_changing_value_across_positions": {c: moves[c] for c in movers},
                    "contract_note": CONTRACT_NOTE,
                    "fork_121_AL_1020": {"cell": "/".join(FORK_121_AL_1020[:2]), "value": FORK_121_AL_1020[2],
                                         "cash_distinct": per_position(fork, positions)["cash"]["distinct"]}}, table

# ---------------------------------------------------------------------------
# The cards: population types, card rules, exchange class per type
# ---------------------------------------------------------------------------
TYPES = {
    "p1": "French, not born in Alsace-Lorraine",
    "p2": "born in Alsace-Lorraine, both parents of French origin",
    "p3": "born in Alsace-Lorraine, one parent of French origin and one not",
    "p4": "born in Alsace-Lorraine, neither parent of French origin",
    "p5": "allied or neutral national, resident before 1 August 1914",
    "p6": "allied or neutral national, came after 1 August 1914",
    "p7": "German, Austro-Hungarian, Turkish or Bulgarian subject born outside Alsace-Lorraine",
}
CARD_RULES = {
    # b as executed: one parent not of French origin (the transcription's bracket); a child of two
    # immigrant parents takes d (nithart.com).  Checked against the Cassel file below.
    "executed": {"a": {"p1", "p2"}, "b": {"p3"}, "c": {"p5", "p6"}, "d": {"p4", "p7"}},
    # b as Le Temps prints it: both parents not of French origin.  d read as immigrants and their
    # children; read as legal nationality in 1918 it would take p2 and p3 as well.
    "literal_le_temps": {"a": {"p1", "p2"}, "b": {"p4"}, "c": {"p5", "p6"}, "d": {"p4", "p7"}},
}
EXCHANGE_CLASS = {  # type -> class at the cash position (None: the text does not settle it)
    # "Alsaciens-Lorrains" as executed: the teaching sheet ("dans la pratique les titulaires des cartes
    # A et B") and Weil 1921 (lost French nationality in 1871, or at least one parent who did).
    "executed": {"p1": "FR", "p2": "AL", "p3": "AL", "p4": "OTHER", "p5": "AN_PRE", "p6": "AN_POST", "p7": "OTHER"},
    # the arrêté alone does not define "Alsacien"; p2 is inside any reading of the word, p3 and p4 are not settled
    "text_only": {"p1": "FR", "p2": "AL", "p3": None, "p4": None, "p5": "AN_PRE", "p6": "AN_POST", "p7": "OTHER"},
}
CASSEL = [  # person, type from the letter, card the file documents, quote for each
    ("Anna Cassel", "p4", "d",
     ("Je suis née à Strasbourg le 18 aout 1880 de parents originaires du Palatinat", "moi seule j'ai la carte D")),
    ("her two children (father of old Alsatian stock)", "p3", "b",
     ("alsacien de vieille souche", "Mes deux enfants ont la carte B")),
]


def card_state(values):
    known = {v for v in values if v is not None}
    if len(known) >= 2:
        return "spans two"
    if None in values:
        return "undeterminable"
    return "one class"


def cross(table, card_rule, exchange_rule, rules=CARD_RULES):
    cards = rules[card_rule]
    cls_of = EXCHANGE_CLASS[exchange_rule]
    member = {t: sorted(k for k, s in cards.items() if t in s) for t in TYPES}
    rows = {}
    for card in sorted(cards):
        cells = [{"type": t, "class": cls_of[t], "value": table[(cls_of[t], "cash")] if cls_of[t] else None}
                 for t in sorted(cards[card])]
        rows[card] = {"cells": cells, "state": card_state([c["value"] for c in cells])}
    states = [r["state"] for r in rows.values()]
    overall = ("a card spans two" if "spans two" in states else
               "undeterminable" if "undeterminable" in states else "every card in one class")
    cassel = [{"person": n, "type": t, "documented": d, "by_rule": member[t], "agrees": member[t] == [d]}
              for n, t, d, _q in CASSEL]
    return {"rows": rows, "overall": overall, "types_with_no_card": [t for t, m in member.items() if not m],
            "types_with_two_cards": [t for t, m in member.items() if len(m) > 1], "cassel": cassel}


TIMELINE = [  # date, event, source, quote
    ("1918-11-26", "exchange arrêté signed", "JO", "Paris, le 26 novembre 1918"),
    ("1918-12-06", "declaration deadline; class declared by the holder", "JO",
     ("avant le 6 décembre 1918, à minuit", "affirmation de la qualité d'Alsacien ou de Lorrain")),
    ("1918-12-14", "card arrêté", "AD67", "Arrêté du 14 décembre 1918 relatif à la police dans les communes"),
    ("1918-12-15", "cash exchange opens, at the counter named on the declaration", "JO",
     ("entre le 15 et le 23 décembre 1918", "L'échange ne pourra avoir lieu que dans le bureau désigné")),
    ("1918-12-23", "cash exchange closes", "JO", "entre le 15 et le 23 décembre 1918"),
    ("1918-12-24", "mayors' lists due; cards follow the lists", "LT",
     ("qu'avant le 24 décembre il sera établi par le soin des maires une liste", "Il sera ensuite délivré")),
]


def b157_3(texts, table):
    main = cross(table, "executed", "executed")
    alts = {f"{c}+{e}": cross(table, c, e) for c in CARD_RULES for e in EXCHANGE_CLASS if (c, e) != ("executed", "executed")}
    quotes = all(find_seq(texts["AD67"], q) for *_x, q in CASSEL)
    order = [d for d, *_r in TIMELINE]
    tl_ok = order == sorted(order) and all(find_seq(texts[s], q) for _d, _e, s, q in TIMELINE)
    declared_before_card = TIMELINE[1][0] < TIMELINE[2][0]
    partition = not main["types_with_no_card"] and not main["types_with_two_cards"]
    passed = partition and all(c["agrees"] for c in main["cassel"]) and quotes and tl_ok
    return passed, {"types": TYPES, "executed": main, "alternatives": alts,
                    "timeline": [{"date": d, "event": e, "source": s} for d, e, s, _q in TIMELINE],
                    "class_declared_before_card_arrete": declared_before_card,
                    "cassel_quotes_found": quotes, "timeline_quotes_found_and_ordered": tl_ok}

# ---------------------------------------------------------------------------
# Travel ranges
# ---------------------------------------------------------------------------
TERR, CERCLE, COMMUNE = "liberated territory", "own cercle and adjacent cercles", "own commune"
RANGE_ORDER = (COMMUNE, CERCLE, TERR)  # each contained in the next
TRAVEL = {  # (source, card) -> (range, quote)
    ("LT", "a"): (TERR, ("catégorie a (Français d'origine)", "dans toute l'étendue du territoire libéré de l'Alsace "
                         "et de la Lorraine, à l'exception de la zone spéciale longeant la frontière suisse")),
    ("LT", "b"): (CERCLE, ("catégories b et c, munies de leur carte d'identité",
                           "dans le cercle où elles résident et dans les cercles limitrophes")),
    ("LT", "c"): (CERCLE, ("catégories b et c, munies de leur carte d'identité",
                           "dans le cercle où elles résident et dans les cercles limitrophes")),
    ("LT", "d"): (COMMUNE, ("catégorie d, munies de leur carte d'identité", "la commune où elles résident")),
    ("AD67", "a"): (TERR, ("catégorie A (français d'origine)", "dans toute l'étendue du territoire libéré de "
                           "l'Alsace et de la Lorraine")),
    ("AD67", "b"): (CERCLE, ("catégories B et C, munies de leur carte d'identité",
                             "dans le cercle où elles résident et dans les cercles limitrophes")),
    ("AD67", "c"): (CERCLE, ("catégories B et C, munies de leur carte d'identité",
                             "dans le cercle où elles résident et dans les cercles limitrophes")),
    ("AD67", "d"): (COMMUNE, ("catégorie D, munies de leur carte d'identité", "dans la commune où elles résident")),
}


def b157_4(texts, travel=TRAVEL):
    rows = [{"source": s, "card": c, "range": r, "quote_found": find_seq(texts[s], q)}
            for (s, c), (r, q) in sorted(travel.items())]
    by = {}
    for r in rows:
        by.setdefault(r["card"], {})[r["source"]] = r["range"]
    agree = sorted(by) == ["a", "b", "c", "d"] and all(set(v) == {"LT", "AD67"} and len(set(v.values())) == 1
                                                         for v in by.values())
    groups = {}
    for c in sorted(by):
        groups.setdefault(by[c].get("LT"), []).append(c)
    nested = all(r in RANGE_ORDER for r in groups)
    passed = agree and nested and all(r["quote_found"] for r in rows)
    return passed, {"rows": rows, "per_card": by, "groups": {str(k): v for k, v in groups.items()},
                    "distinct_ranges": len(groups), "nesting": list(RANGE_ORDER),
                    "no_motor_vehicles": "all four classes: no car, no motorcycle",
                    "note": "the archive's transcription of class a elides the Swiss-border and Rhine zone with (…)"}

# ---------------------------------------------------------------------------
# The proxy loop
# ---------------------------------------------------------------------------
STATES = ("cut", "priced", "open")
PROXY_PATHS = ("cash", "deposit moved before 11 Nov", "deposit moved 11 to 30 Nov", "deposit moved after 30 Nov")
LOOP = [  # article, quote, path it acts on, state
    (2, "Est interdite l'importation de la monnaie divisionnaire", "marks brought in from outside", "cut"),
    (4, ("affirmation de la qualité d'Alsacien ou de Lorrain", "que les marks à échanger n'ont pas été introduits"),
     "cash", "priced"),
    (5, "la confiscation des sommes indûment présentées à l'échange et un emprisonnement de six mois à deux ans",
     "cash", "priced"),
    (6, "L'échange ne pourra avoir lieu que dans le bureau désigné sur la déclaration", "the same marks at two counters",
     "cut"),
    (7, "si leur détenteur peut justifier de l'origine des billets", "cash", "priced"),
    (9, "dans la limite des montants arrêtés au 30 novembre 1918 à minuit", "deposit moved after 30 Nov", "cut"),
    (10, "effectué entre le 11 novembre inclus et le 30 novembre 1918 à minuit, sera soumis à vérification",
     "deposit moved 11 to 30 Nov", "priced"),
]
NOT_WRITTEN_IN_ARRETE = ["a ceiling per holder on cash", "a link between the exchange and the identity card"]
MARKET_PRICE = "0.70"  # about 70 centimes per mark: Weil 1921 via geldscheine-online; the teaching sheet for card D


def b157_5(texts, loop=LOOP):
    arts = articles(texts["JO"])
    rows = [{"article": a, "path": p, "state": s, "on_proxy_loop": p in PROXY_PATHS,
             "quote_inside_article": find_seq(arts.get(a, ""), q)} for a, q, p, s in loop]
    per_path = {}
    for p in PROXY_PATHS:
        st = {r["state"] for r in rows if r["path"] == p}
        per_path[p] = "cut" if "cut" in st else "priced" if "priced" in st else "open"
    premium = int(round(125 - float(MARKET_PRICE) * 100))
    passed = all(r["quote_inside_article"] and r["state"] in STATES for r in rows)
    return passed, {"rows": rows, "per_path": per_path, "not_written": NOT_WRITTEN_IN_ARRETE,
                    "premium_per_mark": f"0.{premium:02d}",
                    "premium_over_market": f"{premium / (float(MARKET_PRICE) * 100):.3f}"}

# ---------------------------------------------------------------------------
# Changing a card
# ---------------------------------------------------------------------------
CASSEL_STEPS = [  # date (None: undated), step, kind, quote
    ("1919-05-14", "Anna Cassel asks the Commissaire général for an A card in place of her D card", "request",
     ("Westhoffen, le 14 mai 1919", "une carte A à la place de la carte D qui m'a été remise")),
    ("1919-05-16", "the administrator at Molsheim sends it to the mayor for an opinion", "inquiry",
     ("Requête transmise à Monsieur le Maire de Westhoffen", "Molsheim, le 16 mai 1919")),
    (None, "the mayor recommends it", "opinion", "je me sens tenu de recommander la dite demande"),
    ("1919-05-21", "the administrator forwards it to the Commissaire de la République at Strasbourg; the "
                   "screening commission has no competence to decide", "forward",
     ("Transmis à Monsieur le Commissaire de la République à Strasbourg la requête de la veuve Cassel",
      "de triage n'est pas compétente pour donner une solution", "Molsheim, le 21 mai 1919")),
]
CASSEL_COST = ("ce qui est un réel préjudice pour moi",  # the letter, then the mayor's note
               "Ayant une carte D, il ne serait possible à Mme Cassel d'obtenir un emploi")


def b157_6(texts, steps=CASSEL_STEPS):
    rows = [{"date": d, "step": s, "kind": k, "quote_found": find_seq(texts["AD67"], q)} for d, s, k, q in steps]
    kinds = {r["kind"] for r in rows if r["quote_found"]}
    state = ("edge absent" if "refusal" in kinds else
             "procedural edge" if "forward" in kinds else "undeterminable")
    dated = [r["date"] for r in rows if r["date"]]
    days = None
    if "forward" in kinds and dated:
        fwd = next(r["date"] for r in rows if r["kind"] == "forward")
        days = (date.fromisoformat(fwd) - date.fromisoformat(dated[0])).days
    passed = all(r["quote_found"] for r in rows) and dated == sorted(dated) and find_seq(texts["AD67"], CASSEL_COST)
    return passed, {"steps": rows, "state": state, "days_request_to_deciding_office": days,
                    "outcome_in_file": None, "stated_cost": "with a D card she cannot find work (mayor and letter)"}

# ---------------------------------------------------------------------------
# Items and coverage
# ---------------------------------------------------------------------------
SUMMARY_ITEMS = [  # id, source, grade, quote, what it says
    ("card_arrete", "AD67", "official", ("Arrêté du 14 décembre 1918 relatif à la police dans les communes d'Alsace "
                                         "et de Lorraine libérées", "AVES, 503 Fi 72"),
     "the card arrêté is dated 14 December 1918; printed copy AVES 503 Fi 72"),
    ("card_issuer_ad67", "AD67", "official", "Le Général Commandant l'Armée", "issued by the army commander"),
    ("card_issuer_lt", "LT", "other", "Un arrêté pris par les généraux commandant les armées françaises",
     "issued by the generals commanding the French armies"),
    ("cards_from_14_dec", "AD67", "research", "attribuées par les mairies à partir du 14 décembre 1918",
     "cards issued by the town halls from 14 December 1918"),
    ("a_lt", "LT", "other", "les Français et les personnes nées en Alsace-Lorraine dont les père et mère étaient "
                            "eux-mêmes d'origine française", "class a"),
    ("a_ad67", "AD67", "official", "Les Français et les personnes nées en Alsace-Lorraine dont les père et mère "
                                   "étaient eux-mêmes d'origine française", "class A"),
    ("b_lt", "LT", "other", "dont les deux ascendants n'étaient pas d'origine française",
     "class b: both parents not of French origin"),
    ("b_ad67", "AD67", "official", "dont [l'un des] deux ascendants n'était pas d'origine française",
     "class B: one of the two parents not of French origin, the bracket is the transcriber's"),
    ("c_both", "LT", "other", "citoyens ou sujets étrangers", "class c"),
    ("c_ad67", "AD67", "official", "C. Les citoyens ou sujets étrangers", "class C"),
    ("d_lt", "LT", "other", "sujets allemands, austro-hongrois, turcs et bulgares", "class d"),
    ("d_ad67", "AD67", "official", "D. Les sujets allemands, austro-hongrois, turcs et bulgares", "class D"),
    ("summary_ab", "AD67", "research", "dans la pratique les titulaires des cartes A et B",
     "the 'Alsaciens-Lorrains' of the exchange were in practice the A and B card holders"),
    ("summary_rate", "AD67", "research", "bénéficient d'un change favorable à 1,25 franc pour un mark",
     "they exchanged at 1.25, with allied and neutral residents (cards C)"),
    ("summary_d", "AD67", "research", "les titulaires d'une carte D échangent leurs marks pour soixante-dix centimes",
     "card D holders got 70 centimes per mark"),
    ("execution_file", "AD67", "research", "AD 67, 121 AL 1020", "the execution file the summary cites"),
    ("postal_two_rates", "LT", "other", ("les taxes exprimées en pfennigs ont été comptées",
                                         "les taxes exprimées en marks ont été calculées au itaux de 1 fr. 25"),
     "postage: pfennig rates one for one in centimes, mark rates at 1.25 (by unit of account, not by holder)"),
]
UNSTORED_ITEMS = [  # id, source, grade, what it says
    ("al_definition_weil", "WEIL", "other",
     "1.25 for those who lost French nationality under the Treaty of Frankfurt and for those born later with "
     "at least one such parent; the remaining Germans could not exchange and were in general to leave"),
    ("market_price", "WEIL", "other", "the mark was worth about 70 centimes on the market"),
    ("d_for_immigrant_children", "NITHART", "other",
     "persons born in Alsace-Lorraine of German immigrant parents received card D"),
]


def all_items():
    items = []
    for pos, (art, q, _n) in POSITIONS.items():
        items.append({"id": f"naming_{pos}", "source": "JO", "grade": "official", "quote": q, "says": f"art. {art}"})
    for a, q, p, _s in LOOP:
        items.append({"id": f"loop_art{a}", "source": "JO", "grade": "official", "quote": q, "says": p})
    for (s, c), (_r, q) in sorted(TRAVEL.items()):
        items.append({"id": f"travel_{s}_{c}", "source": s, "grade": "official" if s == "AD67" else "other",
                      "quote": q, "says": f"travel {c}"})
    for n, _t, d, q in CASSEL:
        items.append({"id": f"cassel_{d}", "source": "AD67", "grade": "official", "quote": q, "says": n})
    for d, s, _k, q in CASSEL_STEPS:
        items.append({"id": f"step_{d or 'undated'}", "source": "AD67", "grade": "official", "quote": q, "says": s})
    for d, e, s, q in TIMELINE:
        items.append({"id": f"date_{d}", "source": s, "grade": "official" if s in ("JO", "AD67") else "other",
                      "quote": q, "says": e})
    for i, s, g, q, w in SUMMARY_ITEMS:
        items.append({"id": i, "source": s, "grade": g, "quote": q, "says": w})
    for i, s, g, w in UNSTORED_ITEMS:
        items.append({"id": i, "source": s, "grade": g, "quote": None, "says": w})
    return items


def b157_1(texts, items, folder, listed=FILES):
    rows, ok = [], True
    for it in items:
        stored = it.get("source") in TEXT_FILES
        found = find_seq(texts[it["source"]], it["quote"]) if stored else None
        good = it.get("grade") in GRADES and (found is True if stored else
                                             it.get("source") in NOT_STORED and it.get("quote") is None)
        ok = ok and good
        rows.append({"id": it["id"], "source": it.get("source"), "grade": it.get("grade"), "stored": stored,
                     "quote_found": found, "ok": good})
    files = []
    for name in sorted(set(listed) | set(folder)):
        data = folder.get(name)
        sha = hashlib.sha256(data).hexdigest() if data is not None else None
        files.append({"file": name, "listed": name in listed, "on_disk": data is not None,
                      "sha256_equal": sha == listed.get(name),
                      "items": sum(1 for r in rows if TEXT_FILES.get(r["source"]) == name)})
    ok = ok and all(f["listed"] and f["on_disk"] and f["sha256_equal"] for f in files)
    return ok, {"items": rows, "files": files, "not_stored": NOT_STORED,
                "not_opened": [{"what": w, "state": s} for w, s in NOT_OPENED],
                "per_grade": {g: sum(1 for r in rows if r["grade"] == g) for g in GRADES}}

# ---------------------------------------------------------------------------
# 11c mapping
# ---------------------------------------------------------------------------
MAPPING = [
    ("B157-3", "every card in one class", "card partition is the price partition"),
    ("B157-3", "a card spans two", "the two partitions differ"),
    ("B157-3", "undeterminable", None),
    ("B157-5", "cut", "path removed"),
    ("B157-5", "priced", "path kept at a price"),
    ("B157-5", "open", "path kept"),
    ("B157-6", "edge absent", "no written way to change a card"),
    ("B157-6", "procedural edge", "a written way, decided case by case"),
    ("B157-6", "undeterminable", None),
]
UNDECIDED = {("B157-3", "undeterminable"), ("B157-6", "undeterminable")}


def mapping_ok() -> bool:
    return all((m[2] is None) == ((m[0], m[1]) in UNDECIDED) for m in MAPPING) and \
        all(any((m[0], m[1]) == u for m in MAPPING) for u in UNDECIDED)

# ---------------------------------------------------------------------------
# Self-test: one planted error per criterion, answer-known fixtures, mapping
# ---------------------------------------------------------------------------

def selftest() -> int:
    results = run_selftest(verbose=True)
    fails = [r for r in results if not r["ok"]]
    print(f"selftest: {len(results)} checks, {len(fails)} failure(s)")
    return 1 if fails else 0


def run_selftest(verbose=False):
    results = []

    def expect(cond, msg):
        cond = bool(cond)
        if verbose:
            print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        results.append({"check": msg, "ok": cond})

    texts = load_texts()
    folder = load_folder()
    expect(norm("Westhoﬀen l’Alsace‐Lorraine") == "Westhoffen l'Alsace-Lorraine",
           "norm: ligature, apostrophe and hyphen mapped")
    expect(find_seq("a b c d", ("a", "c")) and not find_seq("a b c d", ("c", "a")), "find_seq keeps the order")
    # B157-1
    items = all_items()
    expect(b157_1(texts, items, folder)[0], "B157-1 passes on the stored files")
    bad = [dict(i) for i in items]
    bad[0]["quote"] = "aux Alsaciens, aux Prussiens"
    expect(not b157_1(texts, bad, folder)[0], "B157-1 flips when a quote is not in its file")
    bad = [dict(i) for i in items]
    bad[3]["grade"] = None
    expect(not b157_1(texts, bad, folder)[0], "B157-1 flips when an item has no grade")
    f2 = dict(folder)
    f2["extra.pdf"] = b"x"
    expect(not b157_1(texts, items, f2)[0], "B157-1 flips with one unlisted file, any extension")
    f3 = dict(folder)
    f3[TEXT_FILES["LT"]] = f3[TEXT_FILES["LT"]][:-1] + b"#"
    expect(not b157_1(texts, items, f3)[0], "B157-1 flips when one byte of a stored file changes")
    expect(folder_names(["a.txt", "b.pdf", "a.txt.expired_x"]) == ["a.txt", "b.pdf"], "loader drops .expired only")
    # B157-2
    p2, r2, table = b157_2(texts)
    expect(p2, "B157-2 passes on the arrêté")
    expect(r2["articles_found"] == list(range(1, 13)) and r2["rates_in_arrete"] == ["1.25"],
           "B157-2 reads twelve articles and one rate, 1.25")
    expect([r2["per_position"][p]["distinct"] for p in POSITIONS] == [2, 2, 2]
           and r2["distinct_partitions"] == 3, "B157-2 known reading: 2 values at each position, 3 partitions")
    wrong = dict(POSITIONS)
    wrong["cash"] = (9,) + POSITIONS["cash"][1:]
    expect(not b157_2(texts, wrong)[0], "B157-2 flips when the cash naming quote is looked for in the wrong article")
    t2 = dict(texts)
    t2["JO"] = texts["JO"].replace("lorrains, français et par ceux des ressortissants de pays alliés ou neutres qui "
                                   "étaient domicilies en Alsace ou en Lorraine avant le 1er août 1914, sera "
                                   "effectué par les banques et établissements de crédit fonctionnant dans les "
                                   "districs de haute Alsace, basse Alsace et Lorraine, au taux de 1 fr. 25",
                                   "lorrains, français et par ceux des ressortissants de pays alliés ou neutres qui "
                                   "étaient domicilies en Alsace ou en Lorraine avant le 1er août 1914, sera "
                                   "effectué par les banques")
    expect(t2["JO"] != texts["JO"] and not b157_2(t2)[0], "B157-2 flips when article 9 loses its rate (planted)")
    t3 = dict(texts)
    t3["JO"] = texts["JO"].replace("1914 contre billets et monnaies ayant cours en France, au taux de 1 fr. 25",
                                   "1914 contre billets et monnaies ayant cours en France, au taux de 1 fr. 30")
    r3t = b157_2(t3)[2]
    expect(t3["JO"] != texts["JO"] and r3t[("AL", "cash")] == "1.30" and r3t[("AL", "deposit")] == "1.25",
           "B157-2 table follows the file: a planted 1.30 in art. 3 reads as 1.30 at cash only")
    fork = dict(table)
    fork[("OTHER", "cash")] = "0.70"
    expect(per_position(fork)["cash"]["distinct"] == 3, "fixture: a written 0.70 for the last class gives 3 at cash")
    # B157-3
    p3, r3 = b157_3(texts, table)
    expect(p3, "B157-3 passes on the executed rule")
    ex = r3["executed"]
    expect([ex["rows"][c]["state"] for c in "abcd"] == ["spans two", "one class", "spans two", "one class"]
           and ex["overall"] == "a card spans two", "B157-3 known reading: a and c span two, b and d one class")
    lit = cross(table, "literal_le_temps", "executed")
    expect(lit["types_with_no_card"] == ["p3"] and lit["types_with_two_cards"] == ["p4"]
           and not all(c["agrees"] for c in lit["cassel"]),
           "B157-3 literal rule: p3 has no card, p4 has two, and the Cassel cards are not reproduced")
    rules = {"x": {"a": {"p1", "p2"}, "b": {"p3"}, "c": {"p5"}, "d": {"p4", "p6", "p7"}}}
    expect(cross(table, "x", "executed", rules)["rows"]["c"]["state"] == "one class",
           "fixture: card c without late arrivals is one class")
    expect(cross(table, "executed", "text_only")["rows"]["b"]["state"] == "undeterminable",
           "B157-3 with the arrêté alone, card b is undeterminable")
    bad_tl = list(TIMELINE)
    bad_tl[2] = ("1918-12-14", "card arrêté", "AD67", "Arrêté du 13 décembre 1918")
    saved = TIMELINE[:]
    TIMELINE[:] = bad_tl
    try:
        expect(not b157_3(texts, table)[0], "B157-3 flips when a timeline quote is not in its file")
    finally:
        TIMELINE[:] = saved
    # B157-4
    p4, r4 = b157_4(texts)
    expect(p4 and r4["distinct_ranges"] == 3, "B157-4 passes, 3 distinct ranges")
    tr = dict(TRAVEL)
    tr[("AD67", "b")] = (COMMUNE, TRAVEL[("AD67", "b")][1])
    expect(not b157_4(texts, tr)[0], "B157-4 flips when one transcription gives card b another range")
    tr = {k: v for k, v in TRAVEL.items() if k != ("LT", "d")}
    expect(not b157_4(texts, tr)[0], "B157-4 flips when one card is missing from one source")
    # B157-5
    p5, r5 = b157_5(texts)
    expect(p5 and r5["per_path"]["cash"] == "priced" and r5["per_path"]["deposit moved after 30 Nov"] == "cut"
           and r5["per_path"]["deposit moved before 11 Nov"] == "open", "B157-5 known reading per path")
    lp = [(3,) + LOOP[1][1:]] + LOOP[2:]
    expect(not b157_5(texts, lp)[0], "B157-5 flips when an article's quote is looked for in another article")
    lp = LOOP + [(5, LOOP[2][1], "cash", "cut")]
    expect(b157_5(texts, lp)[1]["per_path"]["cash"] == "cut", "fixture: a cutting article on cash gives cut")
    # B157-6
    p6, r6 = b157_6(texts)
    expect(p6 and r6["state"] == "procedural edge" and r6["days_request_to_deciding_office"] == 7,
           "B157-6 known reading: procedural edge, 7 days to the deciding office")
    expect(b157_6(texts, CASSEL_STEPS[:3])[1]["state"] == "undeterminable",
           "B157-6 without the forwarding step is undeterminable")
    st = CASSEL_STEPS + [("1919-05-22", "fixture refusal", "refusal", "Westhoffen, le 14 mai 1919")]
    expect(b157_6(texts, st)[1]["state"] == "edge absent", "fixture: a documented refusal gives edge absent")
    st = [CASSEL_STEPS[0], ("1919-05-16",) + CASSEL_STEPS[1][1:3] + ("Requête transmise au préfet",)] + CASSEL_STEPS[2:]
    expect(not b157_6(texts, st)[0], "B157-6 flips when a step's quote is not in the file")
    expect(mapping_ok(), "11c mapping: every undecided state maps to None and only those")
    return results

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    selftest_rows = run_selftest(verbose=False)
    print(f"selftest: {len(selftest_rows)} checks, {sum(not r['ok'] for r in selftest_rows)} failure(s)")
    texts = load_texts()
    folder = load_folder()
    items = all_items()
    p1, r1 = b157_1(texts, items, folder)
    p2, r2, table = b157_2(texts)
    p3, r3 = b157_3(texts, table)
    p4, r4 = b157_4(texts)
    p5, r5 = b157_5(texts)
    p6, r6 = b157_6(texts)

    print(f"B157-1 items {len(r1['items'])}, per grade {r1['per_grade']}, files "
          + ", ".join(f"{f['file']} ({f['items']} items, sha {f['sha256_equal']})" for f in r1["files"]))
    print("B157-2 class x position:")
    for c in CLASSES:
        print(f"   {c:8s} " + "  ".join(f"{p} {table[(c, p)]:>9s}" for p in POSITIONS))
    for p, d in r2["per_position"].items():
        print(f"   {p}: {d['distinct']} values, partition {d['partition']}")
    print(f"   classes changing value across positions {r2['classes_changing_value_across_positions']}; "
          f"fork {r2['fork_121_AL_1020']}")
    for name, cr in [("executed", r3["executed"])] + sorted(r3["alternatives"].items()):
        print(f"B157-3 [{name}] " + "; ".join(
            f"{c}: {r['state']} " + ",".join(f"{x['type']}={x['value']}" for x in r["cells"])
            for c, r in cr["rows"].items()) + f" => {cr['overall']}; no card {cr['types_with_no_card']}, "
            f"two cards {cr['types_with_two_cards']}, Cassel {[x['agrees'] for x in cr['cassel']]}")
    print("B157-3 timeline: " + "; ".join(f"{t['date']} {t['event']}" for t in r3["timeline"]))
    print(f"B157-4 {r4['groups']}, distinct {r4['distinct_ranges']}")
    print(f"B157-5 {r5['per_path']}, premium {r5['premium_per_mark']} ({r5['premium_over_market']} of market)")
    print(f"B157-6 {r6['state']}, {r6['days_request_to_deciding_office']} days, steps "
          + "; ".join(f"{s['date']} {s['kind']}" for s in r6["steps"]))

    ex = r3["executed"]
    to = r3["alternatives"]["executed+text_only"]
    crit = [
        {"name": "B157-1", "kind": "bookkeeping", "passed": p1,
         "detail": f"{len(r1['items'])} items, per grade {r1['per_grade']}; "
                   f"{sum(1 for r in r1['items'] if r['stored'])} from stored files, every quote found: "
                   f"{all(r['quote_found'] for r in r1['items'] if r['stored'])}; "
                   f"{sum(1 for r in r1['items'] if not r['stored'])} from pages read and not stored. Files: "
                   + "; ".join(f"{f['file']} {f['items']} items, SHA-256 equal {f['sha256_equal']}" for f in r1["files"])
                   + ". Not opened: " + "; ".join(w for w, _s in NOT_OPENED) + "."},
        {"name": "B157-2", "kind": "own_reading", "passed": p2,
         "detail": f"The arrêté writes one rate, {r2['rates_in_arrete']}, in articles 3, 9 and 11. Distinct values "
                   "per position (unwritten counted): "
                   + ", ".join(f"{p} {d['distinct']}" for p, d in r2["per_position"].items())
                   + f". The three positions draw {r2['distinct_partitions']} different partitions: "
                   + "; ".join(f"{p} {d['partition']}" for p, d in r2["per_position"].items())
                   + f". Classes whose value changes with the position: {r2['classes_changing_value_across_positions']}. "
                   f"If the execution file 121 AL 1020 writes 0.70 for the last class at cash, the cash count is "
                   f"{r2['fork_121_AL_1020']['cash_distinct']}; the file was not opened."},
        {"name": "B157-3", "kind": "own_reading", "passed": p3,
         "detail": "Cash position, cards as executed, exchange classes as executed: "
                   + "; ".join(f"{c} {r['state']} (" + ", ".join(f"{x['type']}={x['value']}" for x in r["cells"]) + ")"
                               for c, r in ex["rows"].items())
                   + f" => {ex['overall']}. With the arrêté alone the class of p3 and p4 is not settled and card b is "
                   f"{to['rows']['b']['state']}. Read as Le Temps prints class b, type p3 has no card and p4 has two; "
                   "the Cassel file (Anna Cassel, Strasbourg-born of Palatinate parents: D; her children by an "
                   "Alsatian father: B) agrees with the rule as executed and not with the printed wording. "
                   f"The class was declared on {TIMELINE[1][0]}, before the card arrêté of {TIMELINE[2][0]}."},
        {"name": "B157-4", "kind": "own_reading", "passed": p4,
         "detail": f"Travel ranges, both transcriptions agree: {r4['groups']}; {r4['distinct_ranges']} distinct, "
                   f"nested {' < '.join(RANGE_ORDER)}; no motor vehicles for any class."},
        {"name": "B157-5", "kind": "own_reading", "passed": p5,
         "detail": "Loop: an eligible holder exchanges an ineligible holder's marks. Per path: "
                   + "; ".join(f"{p} {s}" for p, s in r5["per_path"].items())
                   + ". Articles on other paths: "
                   + "; ".join(f"art. {r['article']} {r['state']} ({r['path']})" for r in r5["rows"] if not r["on_proxy_loop"])
                   + f". Not written: {', '.join(NOT_WRITTEN_IN_ARRETE)}. Premium kept by the loop "
                   f"{r5['premium_per_mark']} franc per mark, {r5['premium_over_market']} of the market price."},
        {"name": "B157-6", "kind": "own_reading", "passed": p6,
         "detail": f"Changing a card: {r6['state']}. " + "; ".join(f"{s['date'] or 'undated'} {s['step']}" for s in r6["steps"])
                   + f". {r6['days_request_to_deciding_office']} days from the request to the deciding office; "
                   "the sheet carries no decision. Stated cost of the D card: no work."},
    ]
    record = {
        "stage": "B157",
        "title": "Alsace and Lorraine 1918: the mark exchange and the identity cards, two partitions of one population",
        "config": {
            "files": FILES,
            "normalisation": "NFKC; typographic apostrophes and hyphens to ASCII; whitespace collapsed; OCR errors kept",
            "card_rule": "executed (b: one parent not of French origin; children of two immigrant parents: d)",
            "exchange_class_definition": "executed (Alsaciens-Lorrains: A and B holders; Weil 1921)",
            "market_price_not_counted": MARKET_PRICE,
            "fork": "/".join(FORK_121_AL_1020),
        },
        "criteria": crit,
        "mapping_11c": [{"criterion": m[0], "state": m[1], "verdict": m[2]} for m in MAPPING],
        "selftest": selftest_rows,
        "B157_1": r1, "B157_2": r2, "B157_3": r3, "B157_4": r4, "B157_5": r5, "B157_6": r6,
        "classes": CLASS_NAMES,
    }
    text = json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if not a.no_write:
        sys.path.insert(0, str(ROOT.parent))
        from safe_write import create, rewrite
        if RECORD.exists():
            rewrite(RECORD, "B157_record", lambda _t: text, session=SESSION)
        else:
            create(RECORD, "B157_record", text, session=SESSION)
        print(f"wrote {RECORD.name}")
    bad = [c["name"] for c in crit if c["passed"] is False]
    print("criteria:", {c["name"]: c["passed"] for c in crit})
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
