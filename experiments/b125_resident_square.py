"""B125: the Spanish island resident discount, and whether its square closes.

Residents of the Canary and Balearic Islands, Ceuta and Melilla pay a discounted
fare on domestic scheduled flights to and from their territory. The share alpha
and its base are written in Ley 17/2012, additional provision 13, section Three:
alpha is 75% of the fare, and **from the fare are deducted the public charges of
letters d), e) and f) of article 68.2 of Ley 21/2003**, whether or not they were
passed on to the passenger. Those letters are the security charge, the passenger
charge and the charge for passengers with reduced mobility (PMR), all three set
per departure airport by the airport operator's tariff guide. (Real Decreto
1316/2001, article 2.4, names only two of them; the law names three and governs.)
A one-way ticket from departure airport r at airline fare f therefore costs

    non-resident   P(r)   = f + U_r
    resident       P_R(r) = f + U_r - alpha * f

where U_r is the three charges at r. The resident's factor on the price is

    k_R(r) = P_R(r) / P(r) = 1 - alpha * f / (f + U_r)

and the non-resident's is one.

**Two departure airports and two classes make a square**, and its sum in logs
is log k_R(r1) - log k_R(r2). It is zero exactly when U_r1 / f1 = U_r2 / f2.
At one airline fare on both segments
it is non-zero whenever the excluded charges differ; with two fares it closes
only on the one fare ratio that makes the excluded charges proportional to the
fares. That ratio is printed per square.

**Everything is a decimal the guide prints to the cent, so the arithmetic is
exact.** Fractions decide every zero; logarithms are printed for reading only.

**Two rivals, scored apart, as in B122.**

    bare        P(r, class) = phi(r)                    no class index
    separable   log P(r, class) = phi(r) + psi(class)    the class enters as one
                                                         proportion on every route

The separable rival is the one that carries weight: a 75% discount on the whole
ticket is exactly its form, and D30's third clause calls that one price. The
statute breaks it by excluding three airport-specific charges from the base.

Run:
    python experiments/b125_resident_square.py
    python experiments/b125_resident_square.py --selftest
"""

import argparse
import copy
import json
import math
import pathlib
import sys
from fractions import Fraction as F

# ---------------------------------------------------------------------------
# The statutory and tariff table. Every value carries the provision or the
# page that prints it (rule 25).
# ---------------------------------------------------------------------------

GUIDE = ("Aena, Guía de Tarifas, edición agosto 2026, "
         "data/raw/b125/aena/guia-tarifas-aena_2026-08.pdf")

LAW = {
    "base_rule": ("Ley 17/2012, disposición adicional décima tercera, apartado Tres (texto consolidado; "
                  "párrafo final añadido por la disposición final 16 de la Ley 8/2013): del importe de la "
                  "tarifa del servicio regular de transporte se deducirá el importe correspondiente a las "
                  "prestaciones patrimoniales públicas a que se refieren las letras d), e) y f) del "
                  "artículo 68.2 de la Ley 21/2003, con independencia de que hayan sido repercutidas o no "
                  "al pasajero"),
    "excluded_now": ("Ley 21/2003, art. 68.2 (redacción de la Ley 18/2014): d) inspección y control de "
                     "pasajeros y equipajes (the guide's 'Seguridad'); e) puesta a disposición a los "
                     "pasajeros de las instalaciones aeroportuarias no accesibles a los visitantes (the "
                     "guide's 'Pasajeros'); f) movilidad general de los pasajeros y asistencia a PMRs (the "
                     "guide's 'PMR'). The guide's section 2.2 definitions repeat letters d), e) and f) word "
                     "for word. Real Decreto 1316/2001 art. 2.4 names only the first two; the law governs"),
    "alpha_rule": ("Ley 17/2012, DA 13a, apartado Tres: 75 por ciento de la tarifa por cada trayecto directo, "
                   "y en los viajes interinsulares asimismo del 75 por ciento"),
    "class_edge": ("residence is certified per person against the municipal register and the ticket is "
                   "nominative, checked against identity at boarding; the crossing is the traveller's own "
                   "and nobody can make it for another (D30, fourth clause: a crossing only oneself can make)"),
    "same_object": ("resident and non-resident buy the same seat on the same flight under the same fare "
                    "conditions; the discount is applied to that fare (D49: the reading depends on route "
                    "and fare, and those are equal)"),
}

ALPHA = {
    "current": (F(75, 100), "75%: Ley 17/2012 DA 13a apartado Tres; raised from 50% under the authority of "
                            "Ley 6/2018 DA 147a by the Council of Ministers agreement of 2018-07-13 (BOE "
                            "2018-07-14) and Real Decreto 949/2018"),
    "before_2018": (F(50, 100), "50%: Ley 17/2012 DA 13a as enacted, for journeys to the rest of the national "
                                "territory; the RD 949/2018 preamble and the 2018-07-13 agreement both cite it"),
}

# The share by period and by kind of journey, as the statutes write it. The
# 2026 tariff guide is not paired with an earlier period's alpha; what is
# printed per period is the part of the square alpha writes alone, between an
# inter-island segment and a segment to the rest of the national territory,
# with the airport charges set aside: log(1 - alpha_inter) - log(1 - alpha_pen).
ALPHA_PERIODS = [
    {"from": "2013-01-01", "alpha_peninsula": F(1, 2), "alpha_inter_island": F(1, 2),
     "source": "Ley 17/2012 (BOE 2012-12-28), DA 13a apartado Tres as enacted: 50 por ciento, "
               "trayectos con el resto del territorio nacional así como en los viajes interinsulares. "
               "For Canary residents the provision was annulled by STC 164/2014 (BOE 2014-10-29), the "
               "nullity deferred one year, and re-enacted by Ley 40/2015, DF 10 (in force 2015-10-03, "
               "DF 18.3), with its first paragraphs taking effect from 2013-01-01, so the share runs "
               "unbroken; the re-enacted text drops the ministerial power to cap the subsidised fare"},
    {"from": "2017-06-29", "alpha_peninsula": F(1, 2), "alpha_inter_island": F(3, 4),
     "source": "Ley 3/2017 (BOE 2017-06-28, in force the next day, DF 35a), DA 128a rewriting DA 13a "
               "apartado Tres: 50 por ciento por cada trayecto directo, y en los viajes interinsulares "
               "será del 75 por ciento"},
    {"from": "2018-07-16", "alpha_peninsula": F(3, 4), "alpha_inter_island": F(3, 4),
     "source": "Ley 6/2018 DA 147a; Council of Ministers agreement of 2018-07-13 (BOE 2018-07-14, a "
               "Saturday; tickets issued from 09:00 on the day of publication if it is a working day, "
               "so from Monday 2018-07-16, the date the press reports); Real Decreto 949/2018"},
]


def alpha_only_square(period):
    """Inter-island against peninsula, charges set aside: exact product form."""
    return (1 - period["alpha_inter_island"]) / (1 - period["alpha_peninsula"])


# Departure cells. U = passenger + security + PMR at the departure airport.
# Section 2.2.1 applies to EEE flights, which include domestic flights from the
# Peninsula; 2.2.2 to flights between the islands, Ceuta or Melilla and the
# Peninsula (charged at the island end); 2.2.3 to inter-island flights.
P221 = GUIDE + ", p. 18, table 2.2.1, E.E.E. column; PMR 0,87 and Seguridad 3,99 for every airport"
P222 = GUIDE + ", p. 18, table 2.2.2; PMR 0,74 and Seguridad 3,39 for every airport"
P223 = GUIDE + ", p. 19, table 2.2.3; PMR 0,26 and Seguridad 0,60 for every airport"
WINTER = (GUIDE + ", p. 18: from November to March the passenger and security amounts at Palma de "
          "Mallorca, Menorca, Ibiza and Son Bonet carry a 20% reduction")

CELLS = [
    {"cell": "MAD dep, peninsula to islands", "section": "2.2.1", "passenger": "14.06",
     "security": "3.99", "pmr": "0.87", "source": P221 + "; Adolfo Suárez Madrid-Barajas 14,06"},
    {"cell": "BCN dep, peninsula to islands", "section": "2.2.1", "passenger": "13.09",
     "security": "3.99", "pmr": "0.87", "source": P221 + "; Barcelona-El Prat 13,09"},
    {"cell": "AGP dep, peninsula to islands", "section": "2.2.1", "passenger": "5.85",
     "security": "3.99", "pmr": "0.87", "source": P221 + "; Málaga-Costa del Sol row 5,85"},
    {"cell": "SVQ dep, peninsula to islands", "section": "2.2.1", "passenger": "4.98",
     "security": "3.99", "pmr": "0.87", "source": P221 + "; Sevilla row 4,98"},
    {"cell": "SDR dep, peninsula to islands", "section": "2.2.1", "passenger": "3.57",
     "security": "3.99", "pmr": "0.87", "source": P221 + "; Santander row 3,57"},
    {"cell": "VLL dep, peninsula to islands", "section": "2.2.1", "passenger": "2.33",
     "security": "3.99", "pmr": "0.87", "source": P221 + "; Valladolid row 2,33"},
    {"cell": "PMI dep to peninsula, Apr-Oct", "section": "2.2.2", "passenger": "4.97",
     "security": "3.39", "pmr": "0.74", "source": P222 + "; Palma de Mallorca 4,97"},
    {"cell": "PMI dep to peninsula, Nov-Mar", "section": "2.2.2", "passenger": "4.97",
     "security": "3.39", "pmr": "0.74", "winter": True,
     "source": P222 + "; Palma de Mallorca 4,97; " + WINTER},
    {"cell": "LPA dep to peninsula", "section": "2.2.2", "passenger": "4.97",
     "security": "3.39", "pmr": "0.74", "source": P222 + "; Gran Canaria 4,97"},
    {"cell": "IBZ dep to peninsula, Apr-Oct", "section": "2.2.2", "passenger": "4.23",
     "security": "3.39", "pmr": "0.74", "source": P222 + "; Ibiza 4,23"},
    {"cell": "IBZ dep to peninsula, Nov-Mar", "section": "2.2.2", "passenger": "4.23",
     "security": "3.39", "pmr": "0.74", "winter": True,
     "source": P222 + "; Ibiza 4,23; " + WINTER},
    {"cell": "ACE dep to peninsula", "section": "2.2.2", "passenger": "4.23",
     "security": "3.39", "pmr": "0.74", "source": P222 + "; César Manrique-Lanzarote 4,23"},
    {"cell": "SPC dep to peninsula", "section": "2.2.2", "passenger": "3.03",
     "security": "3.39", "pmr": "0.74", "source": P222 + "; La Palma 3,03"},
    {"cell": "MLN dep to peninsula", "section": "2.2.2", "passenger": "1.98",
     "security": "3.39", "pmr": "0.74", "source": P222 + "; Melilla 1,98"},
    {"cell": "PMI dep inter-island, Apr-Oct", "section": "2.2.3", "passenger": "1.76",
     "security": "0.60", "pmr": "0.26", "source": P223 + "; Palma de Mallorca 1,76"},
    {"cell": "PMI dep inter-island, Nov-Mar", "section": "2.2.3", "passenger": "1.76",
     "security": "0.60", "pmr": "0.26", "winter": True,
     "source": P223 + "; Palma de Mallorca 1,76; " + WINTER},
    {"cell": "LPA dep inter-island", "section": "2.2.3", "passenger": "1.76",
     "security": "0.60", "pmr": "0.26", "source": P223 + "; Gran Canaria 1,76"},
    {"cell": "IBZ dep inter-island, Apr-Oct", "section": "2.2.3", "passenger": "1.49",
     "security": "0.60", "pmr": "0.26", "source": P223 + "; Ibiza 1,49"},
    {"cell": "IBZ dep inter-island, Nov-Mar", "section": "2.2.3", "passenger": "1.49",
     "security": "0.60", "pmr": "0.26", "winter": True,
     "source": P223 + "; Ibiza 1,49; " + WINTER},
    {"cell": "TFN dep inter-island", "section": "2.2.3", "passenger": "1.49",
     "security": "0.60", "pmr": "0.26", "source": P223 + "; Tenerife Norte 1,49"},
    {"cell": "SPC dep inter-island", "section": "2.2.3", "passenger": "1.07",
     "security": "0.60", "pmr": "0.26", "source": P223 + "; La Palma 1,07"},
    {"cell": "VDE dep inter-island", "section": "2.2.3", "passenger": "0.70",
     "security": "0.60", "pmr": "0.26", "source": P223 + "; Hierro 0,70"},
]

WINTER_FACTOR = F(80, 100)

# The airline fare is not known and does not need to be: the square is printed
# on a grid of fares held equal on both segments, and the one fare ratio that
# would close each square is printed beside it.
FARE_GRID = [F(40), F(80), F(150), F(300)]


# ---------------------------------------------------------------------------
# The Canary Islands public service obligation routes: the one place where the
# fare itself is published. The declaration (Council of Ministers agreement of
# 2006-06-02, BOE-A-2006-13558, annex, section II) defines the reference fare as
# "la tarifa mas baja sin condiciones", the lowest fare without conditions, which
# is the wording Real Decreto 1316/2001 uses for the basic fare ("la tarifa
# plenamente flexible mas baja"); that correspondence is a reading of the two
# texts, not a sentence in either. The same annex defines the air fare as
# including taxes except the infrastructure and security charges, which are
# itemised apart; the reduced-mobility charge dates from 2008 and is read as
# excluded too (the law deducts all three from the subsidised base).
# ---------------------------------------------------------------------------

OSP_SOURCE = ("Orden TRM/789/2026 (BOE-A-2026-16658, aplicable desde 2026-08-01), apartado primero: "
              "tarifa de referencia por trayecto")
OSP_FLEX_SOURCE = ("Orden TRM/1175/2024 (BOE-A-2024-22062, aplicable desde 2024-10-27), apartado quinto: "
                   "la tarifa flexible no supere el treinta por ciento de la tarifa de referencia")
OSP_FLEX = F(130, 100)

# How article 2.5 is administered: Real Decreto 1316/2001, annex IV (consolidated text), the
# basic-fares file "contendrá aquellas necesarias para la comprobación de los topes máximos de
# subvención aplicable a cada cupón facturado", and an airline with no basic fares files its
# highest fares instead. So the cap is per coupon, at alpha times the registered basic fare,
# whatever the product is called. On the Canary Islands routes the registered basic fare is read
# as the reference fare (the lowest fare without conditions); the airlines' own filings are not
# public, so that step is a reading of the two definitions.
CAP_RULE = ("Real Decreto 1316/2001, anexo IV, fichero de tarifas básicas: necesarias para la comprobación "
            "de los topes máximos de subvención aplicable a cada cupón facturado")

# Inter-island departure charges, guide section 2.2.3 (page 19): passenger by airport group,
# security 0,60 and PMR 0,26 for every airport. No winter reduction on these airports.
P223_PASSENGER = {"LPA": "1.76", "TFS": "1.76", "TFN": "1.49", "FUE": "1.49", "ACE": "1.49",
                  "SPC": "1.07", "VDE": "0.70", "GMZ": "0.70",
                  "PMI": "1.76", "IBZ": "1.49", "MAH": "1.49"}

# Social fares: a second class axis, age, written into both declarations. The statutes fix a
# minimum discount off the reference fare; airlines may give more, so the value is a floor and
# the object read here is that floor. The resident subsidy is taken on the fare charged, after
# the social discount (annex IV: the fare charged is the fare applied after any commercial
# discount, the resident one excepted).
SOCIAL = {
    "baleares": {"discount": F(20, 100), "residents_only": True,
                 "source": ("Orden FOM/1085/2008 (BOE-A-2008-6924), apartado 2.3 c), unchanged by "
                            "Orden TRM/1406/2024 and Orden TRM/395/2025: tarifas sociales con un descuento "
                            "mínimo del 20% respecto de la tarifa de referencia para jóvenes menores de "
                            "veinticuatro años y personas que hayan cumplido los sesenta y cinco años, "
                            "categorías de pasajeros residentes en las Islas Baleares")},
    "canarias": {"discount": F(10, 100), "residents_only": False,
                 "source": ("Acuerdo del Consejo de Ministros de 2006-06-02 (BOE-A-2006-13558), anexo, "
                            "apartado 2.3 c), unchanged by the 2011 agreement (BOE-A-2011-18917), Orden "
                            "TMA/830/2022 and Orden TRM/1175/2024: tarifas sociales para jóvenes menores de "
                            "veintidós años y personas que hayan cumplido los sesenta y cinco años, descuentos "
                            "no inferiores al diez por ciento de la tarifa de referencia; no limited to residents")},
}

BALEARES_SOURCE = ("Orden TRM/395/2025 (BOE-A-2025-8367, aplicable desde 2025-04-27), apartado primero: "
                   "tarifa de referencia en los trayectos de ida")
BALEARES_ROUTES = [("PMI", "IBZ", "113"), ("PMI", "MAH", "113"), ("MAH", "IBZ", "155")]

OSP_ROUTES = [
    ("LPA", "TFN", "90"), ("LPA", "TFS", "90"), ("LPA", "FUE", "97"), ("LPA", "VDE", "133"),
    ("LPA", "ACE", "108"), ("LPA", "SPC", "114"), ("TFN", "FUE", "128"), ("TFN", "VDE", "96"),
    ("TFN", "ACE", "132"), ("TFN", "SPC", "92"), ("SPC", "ACE", "136"), ("LPA", "GMZ", "112"),
    ("TFN", "GMZ", "84"),
]


def osp_cells(routes=OSP_ROUTES, source=None):
    """One cell per route and direction: the departure airport's charges and the route's fare."""
    out = []
    for a, b, fare in routes:
        for dep, arr in ((a, b), (b, a)):
            out.append({"cell": dep + "-" + arr, "section": "2.2.3",
                        "passenger": P223_PASSENGER[dep], "security": "0.60", "pmr": "0.26",
                        "fare": fare,
                        "source": P223 + "; " + (source or OSP_SOURCE) + ", " + a + "-" + b + " " + fare})
    return out


def osp_route_squares(cells, alpha, kfn=None):
    """Squares between route-directions, each at its own published reference fare."""
    kfn = factor if kfn is None else kfn
    out = []
    for x in range(len(cells)):
        for y in range(x + 1, len(cells)):
            c1, c2 = cells[x], cells[y]
            f1, f2 = F(c1["fare"]), F(c2["fare"])
            q = kfn(c1, f1, alpha, excluded) / kfn(c2, f2, alpha, excluded)
            equal_share = excluded(c1) / f1 == excluded(c2) / f2
            out.append({"cells": [c1["cell"], c2["cell"]], "log": logf(q), "zero": q == 1,
                        "zero_iff_equal_share": (q == 1) == equal_share})
    return out


def social_class_square(c, alpha, rule, charges=True):
    """Four classes on one route-direction, age (young, adult) by residence (resident, not), at
    the statutory minimum social discount. Product form: one iff the class square vanishes."""
    r = F(c["fare"])
    u = excluded(c) if charges else F(0)
    d = rule["discount"]
    young_res = (1 - alpha) * (1 - d) * r + u
    adult_res = (1 - alpha) * r + u
    adult_non = r + u
    young_non = adult_non if rule["residents_only"] else (1 - d) * r + u
    return (young_res * adult_non) / (young_non * adult_res)


def social_cells():
    return {"baleares": osp_cells(BALEARES_ROUTES, BALEARES_SOURCE), "canarias": osp_cells()}


def osp_product_square(c, alpha, capped, flex=OSP_FLEX):
    """Reference fare against the flexible fare at its cap, resident against non-resident, one
    route-direction. capped: article 2.5 read as covering the flexible fare, so the subsidised
    base stops at the reference fare; otherwise the base is the whole flexible fare."""
    r, u = F(c["fare"]), excluded(c)
    flex = r * flex
    base_flex = r if capped else flex
    k_ref = (r + u - alpha * r) / (r + u)
    k_flex = (flex + u - alpha * base_flex) / (flex + u)
    return k_flex / k_ref


# ---------------------------------------------------------------------------
# The object
# ---------------------------------------------------------------------------

def excluded(c):
    """U: letters d), e) and f), deducted from the base. The winter reduction is
    printed for the passenger and security amounts only, so PMR is not reduced."""
    ps = F(c["passenger"]) + F(c["security"])
    return (ps * WINTER_FACTOR if c.get("winter") else ps) + F(c["pmr"])


def included(c, f):
    """The base the discount applies to: the airline fare, all three charges out."""
    return f


def factor(c, f, alpha, exclude=excluded):
    """k_R: the resident's price over the non-resident's, exact."""
    inc, u = included(c, f), exclude(c)
    return (inc + u - alpha * inc) / (inc + u)


def closed_form(c1, c2, f, alpha):
    """The square in product form written out, on a path that shares no helper."""
    def u(c):
        s = F(c["passenger"]) + F(c["security"])
        return (s * F(4, 5) if c.get("winter") else s) + F(c["pmr"])
    num = ((1 - alpha) * f + u(c1)) * (f + u(c2))
    den = ((1 - alpha) * f + u(c2)) * (f + u(c1))
    return num / den


def logf(q):
    """A printed logarithm, fixed format (derived-file rule 5). Never decides."""
    return "%.6f" % math.log(q)


def fracs(q):
    return "%d/%d" % (q.numerator, q.denominator)


def build(cells, alpha, exclude=excluded, grid=FARE_GRID, kfn=factor):
    squares = []
    for x in range(len(cells)):
        for y in range(x + 1, len(cells)):
            c1, c2 = cells[x], cells[y]
            u1, u2 = exclude(c1), exclude(c2)
            per_fare = []
            for f in grid:
                q = kfn(c1, f, alpha, exclude) / kfn(c2, f, alpha, exclude)
                q2 = closed_form(c1, c2, f, alpha)
                explained = (q == 1) == (u1 / included(c1, f) == u2 / included(c2, f))
                per_fare.append({"fare": fracs(f), "ratio": fracs(q), "log": logf(q),
                                 "zero": q == 1, "two_paths_agree": q == q2,
                                 "zero_iff_equal_share": explained})
            closing = None if u1 == 0 else u2 / u1
            squares.append({
                "cells": [c1["cell"], c2["cell"]],
                "excluded": [fracs(u1), fracs(u2)],
                "closing_ratio_fare_2_over_1": None if closing is None else "%.4f" % float(closing),
                "per_fare": per_fare})
    gaps = [{"cell": c["cell"], "fare": fracs(f),
             "resident_over_nonresident": "%.6f" % float(factor(c, f, alpha, exclude)),
             "zero": factor(c, f, alpha, exclude) == 1}
            for c in cells for f in grid]
    return {"squares": squares, "class_gaps": gaps,
            "independent_squares": len(cells) - 1,
            "nonzero_squares": sum(1 for s in squares for p in s["per_fare"] if not p["zero"]),
            "square_fare_cells": sum(len(s["per_fare"]) for s in squares)}


# ---------------------------------------------------------------------------
# Criteria. Each flag is computed from the object (rule 11f).
# ---------------------------------------------------------------------------

def _crit(name, kind, verdict, detail, extra=None):
    crit = {"name": name, "kind": kind, "detail": detail,
            "passed": None if verdict is None else bool(verdict)}
    if verdict is None:
        crit["void"] = True
    if extra:
        crit.update(extra)
    return crit


def criteria(report, cells, law, alpha, osp_sq=None, prod_sq=None, social=None):
    crits = []
    sq = [p for s in report["squares"] for p in s["per_fare"]]

    unsourced = [c["cell"] for c in cells if not str(c.get("source", "")).strip()]
    disagree = [s["cells"][0] + " / " + s["cells"][1] for s in report["squares"]
                if not all(p["two_paths_agree"] for p in s["per_fare"])]
    crits.append(_crit(
        "B125-S1", "instrument", not unsourced and not disagree and bool(cells),
        "every departure cell carries the page and row of the tariff guide it is read from, "
        "and every square is computed twice, as a ratio of the two resident factors and from "
        "the written-out product, which share no helper. Unsourced cells: "
        + (", ".join(unsourced) if unsourced else "none") + ". Squares where the two paths "
        "differ: " + (", ".join(disagree[:5]) if disagree else "none") + " of "
        + str(len(report["squares"])) + ". The guide prints every charge to the cent, a fixed "
        "published format, so the arithmetic is exact and a zero is decided without a tolerance."))

    missing = [k for k in ("base_rule", "alpha_rule", "class_edge", "same_object")
               if not str(law.get(k, "")).strip()]
    crits.append(_crit(
        "B125-S2", "premise", not missing,
        "the statute writes one share alpha per class (resident, non-resident) and a base that "
        "leaves out three charges the airport operator writes per departure airport; the two classes "
        "buy the same seat under the same fare; the class edge is a crossing only the traveller "
        "can make. Missing on record: " + (", ".join(missing) if missing else "none") + "."))

    zeros = [p for p in sq if p["zero"]]
    unexplained = [p for p in sq if not p["zero_iff_equal_share"]]
    nonzero = len(sq) - len(zeros)
    logs = sorted({p["log"] for p in sq if not p["zero"]}, key=lambda s: abs(float(s)))
    crits.append(_crit(
        "B125-S3", "own_reading", nonzero > 0 and not unexplained,
        "the registered reading is that the deduction of letters d), e) and f) alone makes the "
        "resident factor depend on the departure airport, so a square at one airline fare is non-zero "
        "exactly when the excluded share U / f differs between the two cells. Read at alpha = " + fracs(alpha) + ": "
        + str(nonzero) + " of " + str(len(sq)) + " (square, fare) cells non-zero; "
        + str(len(zeros)) + " zero, and every zero falls where the excluded shares are equal "
        "(unexplained: " + str(len(unexplained)) + "). Smallest and largest non-zero log: "
        + (logs[0] + ", " + logs[-1] if logs else "none") + "."))

    gaps = report["class_gaps"]
    nz_gaps = [g for g in gaps if not g["zero"]]
    crits.append(_crit(
        "B125-S4", "rival", len(nz_gaps) > 0,
        "the bare scalar field puts one price on one seat whoever buys it. Read: "
        + str(len(nz_gaps)) + " of " + str(len(gaps)) + " (cell, fare) class gaps differ from one.",
        {"rival_premise": "P(r, class) = phi(r): one seat on one segment has one price",
         "rival_entailment": "phi carries no class index, so a resident and a non-resident pay "
                             "the same on every segment",
         "rival_shape": "point prediction of zero",
         "grid": "B"}))

    crits.append(_crit(
        "B125-S5", "rival", nonzero > 0,
        "the separable rival lets the class enter as one proportion on every segment, which is "
        "what a 75% discount on the whole ticket would be, and it makes every square exactly one. "
        "Read: " + str(nonzero) + " of " + str(len(sq)) + " (square, fare) cells differ from one. "
        "With two different fares on the two segments a square closes only when the fares "
        "stand in the ratio of the excluded charges; that ratio is printed per square "
        "(closing_ratio_fare_2_over_1), and the rival needs every airline to price every "
        "pair of segments on it on every date.",
        {"rival_premise": "log P(r, class) = phi(r) + psi(class): the class changes the price by "
                          "one proportion on every segment",
         "rival_entailment": "the resident factor is exp(psi(R) - psi(N)) on every segment, so the "
                             "ratio of that factor across two segments, which is the square, is one",
         "rival_shape": "point prediction of zero",
         "grid": "B"}))

    osp = osp_route_squares(osp_cells(), alpha) if osp_sq is None else osp_sq
    osp_nz = sum(1 for q in osp if not q["zero"])
    osp_bad = sum(1 for q in osp if not q["zero_iff_equal_share"])
    crits.append(_crit(
        "B125-S7", "own_reading", osp_nz > 0 and osp_bad == 0,
        "on the Canary Islands public service obligation routes the fare is published, so the "
        "square is read at the state's own reference fare instead of on a grid: 13 routes, both "
        "directions, each at its reference fare with the departure airport's inter-island "
        "charges. Read at alpha = " + fracs(alpha) + ": " + str(osp_nz) + " of " + str(len(osp))
        + " squares non-zero; zeros the excluded share U / f does not explain: " + str(osp_bad) + "."))

    prod = ([osp_product_square(c, alpha, True) for c in osp_cells()] if prod_sq is None else prod_sq)
    prod_nz = sum(1 for q in prod if q != 1)
    free = [osp_product_square(c, alpha, False) for c in osp_cells()]
    binds = sum(1 for q, g in zip(prod, free) if q != g)
    crits.append(_crit(
        "B125-S8", "own_reading", bool(prod) and prod_nz == len(prod) and binds == len(prod),
        "article 2.5 as administered (annex IV: the basic-fares file serves to check the maximum "
        "subsidy on each coupon), so a flexible fare above the basic fare is subsidised only up to "
        "alpha times the basic fare. On the Canary Islands routes, with the basic fare read as the "
        "reference fare and the flexible fare at its 130% ceiling, the square of reference against "
        "flexible fare, resident against non-resident, is non-zero on " + str(prod_nz) + " of "
        + str(len(prod)) + " route-directions, and the cap binds (the square differs from the "
        "uncapped one) on " + str(binds) + "; with no airport charges it is "
        "(1 + m - alpha)/((1 + m)(1 - alpha)), written by the cap alone. The separable rival, one "
        "class proportion on every product, predicts one."))

    soc = social if social is not None else SOCIAL
    sc = social_cells()
    sq_on = {k: [social_class_square(c, alpha, soc[k]) for c in sc[k]] for k in sc}
    sq_off = {k: [social_class_square(c, alpha, soc[k], charges=False) for c in sc[k]] for k in sc}
    all_on = [q for k in sq_on for q in sq_on[k]]
    nz_on = sum(1 for q in all_on if q != 1)
    crits.append(_crit(
        "B125-S9", "rival", bool(all_on) and nz_on == len(all_on),
        "the separable rival on the class side: at one route-direction the price of four classes, "
        "age (young, adult) by residence, is a route term plus an age term plus a residence term in "
        "logs, so their class square is zero. Read at the published reference fares and the "
        "statutory minimum social discounts (Balearic Islands 20% for residents only, Canary Islands "
        "10% for everyone in the age bands): " + str(nz_on) + " of " + str(len(all_on))
        + " route-directions non-zero (Balearic Islands " + str(len(sq_on["baleares"]))
        + ", Canary Islands " + str(len(sq_on["canarias"])) + ").",
        {"rival_premise": "log P(route, age, residence) = phi(route) + psi(age) + chi(residence)",
         "rival_entailment": "the ratio young over adult is the same for residents and non-residents, "
                             "so the class square at every route-direction is one",
         "rival_shape": "point prediction of zero",
         "grid": "B"}))
    bal_off_nz = all(q != 1 for q in sq_off["baleares"])
    can_off_zero = all(q == 1 for q in sq_off["canarias"])
    crits.append(_crit(
        "B125-S10", "own_reading", bool(sq_off["baleares"]) and bal_off_nz and can_off_zero,
        "the two archipelagos write the age axis differently, and the class square shows it. With the "
        "airport charges set to zero the Balearic square is still non-zero on every route-direction "
        "(" + str(sum(1 for q in sq_off["baleares"] if q != 1)) + " of " + str(len(sq_off["baleares"]))
        + "; log " + logf(sq_off["baleares"][0]) + " = log 0.8, because the age discount is written for "
        "residents only), while the Canary square is exactly one on every one ("
        + str(sum(1 for q in sq_off["canarias"] if q == 1)) + " of " + str(len(sq_off["canarias"]))
        + ": two class-only discounts that multiply). There it opens only through the airport charges, "
        "which neither discount touches."))

    need = [c["cell"] + ":" + k for c in cells for k in ("section", "passenger", "security", "pmr")
            if not str(c.get(k, "")).strip()]
    crits.append(_crit(
        "B125-S6", "bookkeeping", not need and bool(cells),
        "each cell's tariff section, passenger, security and PMR amounts are printed into the "
        "record beside the provisions and the fare grid. Missing: "
        + (", ".join(need) if need else "none") + "; cells: " + str(len(cells)) + "."))
    return crits


def config_block():
    """What this run chose (rule 18d)."""
    return {
        "alpha_scored": fracs(ALPHA["current"][0]),
        "alpha_printed": {k: fracs(v[0]) for k, v in sorted(ALPHA.items())},
        "fare_grid_eur": [fracs(f) for f in FARE_GRID],
        "cells": len(CELLS),
        "winter_factor": fracs(WINTER_FACTOR),
        "one_way_departure_charges_only": True,
        "excluded_letters": "Ley 21/2003 art. 68.2 d), e), f): security, passenger, PMR",
        "not_modelled": ["article 2.5 cap on higher-class fares (needs the registered basic fare)",
                         "the 40% reduction for connecting passengers",
                         "taxes on the fare, which sit in the base and are the same share on "
                         "every segment of one tax territory"],
        "arithmetic": "fractions.Fraction, exact; logarithms printed only",
    }


def verdicts(cells=CELLS, law=LAW, alpha=ALPHA["current"][0], exclude=excluded, kfn=factor):
    report = build(cells, alpha, exclude, kfn=kfn)
    return {c["name"]: c["passed"] for c in criteria(report, cells, law, alpha)}


def selftest():
    checks = []

    def ok(label, cond):
        checks.append((label, bool(cond)))

    base = verdicts()
    ok("every criterion holds on the statutory table", all(v is True for v in base.values()))

    # 11f: every flag must flip on an input built to make it false.
    c = copy.deepcopy(CELLS)
    c[0]["source"] = ""
    ok("an unsourced cell flips S1", verdicts(cells=c)["B125-S1"] is False)

    ok("a builder that forgets the winter reduction flips S1",
       verdicts(exclude=lambda c: F(c["passenger"]) + F(c["security"]))["B125-S1"] is False)

    law = dict(LAW)
    law["class_edge"] = ""
    ok("a missing class edge flips S2", verdicts(law=law)["B125-S2"] is False)

    c = copy.deepcopy(CELLS)
    for x in c:
        x["passenger"], x["security"], x["pmr"] = "5.00", "3.00", "0.50"
        x.pop("winter", None)
    v = verdicts(cells=c)
    ok("equal charges everywhere flip S3 and the separable rival, keep the bare one refuted",
       v["B125-S3"] is False and v["B125-S5"] is False and v["B125-S4"] is True)

    v = verdicts(exclude=lambda c: F(0))
    ok("a discount on the whole ticket (nothing excluded) closes every square",
       v["B125-S5"] is False and v["B125-S4"] is True)

    v = verdicts(alpha=F(0))
    ok("no discount flips both rivals", v["B125-S4"] is False and v["B125-S5"] is False)

    c = copy.deepcopy(CELLS)
    c[3]["section"] = ""
    ok("a cell with no tariff section on record flips S6", verdicts(cells=c)["B125-S6"] is False)

    # A zero the statute does not explain. A factor that puts PMR back into the
    # base (the article 2.4 reading the law overrides), on a pair built so that
    # its square closes at 40 euro while the statutory shares U / f differ.
    pair = [{"cell": "X", "section": "t", "passenger": "4.00", "security": "0.00", "pmr": "0.00",
             "source": "fixture"},
            {"cell": "Y", "section": "t", "passenger": "5.00", "security": "3.00", "pmr": "40.00",
             "source": "fixture"}]

    def pmr_in_base(c, f, a, ex=excluded):
        m = F(c["pmr"])
        ps = ex(c) - m
        return (f + m + ps - a * (f + m)) / (f + m + ps)
    ok("a factor whose zeros the statute does not explain flips S3",
       verdicts(cells=CELLS + pair, kfn=pmr_in_base)["B125-S3"] is False
       and "unexplained: 0)" not in criteria(build(CELLS + pair, F(3, 4), kfn=pmr_in_base),
                                             CELLS + pair, LAW, F(3, 4))[2]["detail"])

    # The OSP reading must fail when the fares are drawn in proportion to the excluded charges:
    # every route then carries the same share U / f and every square closes.
    prop = [dict(c, fare=str(excluded(c) * 40)) for c in osp_cells()]
    ok("reference fares in proportion to the charges close every OSP square and flip S7",
       {c["name"]: c["passed"] for c in criteria(build(CELLS, F(3, 4)), CELLS, LAW, F(3, 4),
                osp_sq=osp_route_squares(prop, F(3, 4)))}["B125-S7"] is False)
    flat = [osp_product_square(c, F(3, 4), True, flex=F(1)) for c in osp_cells()]
    ok("a flexible fare equal to the reference fare closes the product square and flips S8",
       {c["name"]: c["passed"] for c in criteria(build(CELLS, F(3, 4)), CELLS, LAW, F(3, 4),
                                                 prod_sq=flat)}["B125-S8"] is False)
    open_bal = {k: dict(v) for k, v in SOCIAL.items()}
    open_bal["baleares"]["residents_only"] = False
    ok("a Balearic social fare opened to non-residents closes its square at zero charges and flips S10",
       {c["name"]: c["passed"] for c in criteria(build(CELLS, F(3, 4)), CELLS, LAW, F(3, 4),
                                                 social=open_bal)}["B125-S10"] is False)
    no_disc = {k: dict(v, discount=F(0)) for k, v in SOCIAL.items()}
    ok("no social discount closes every class square and flips S9",
       {c["name"]: c["passed"] for c in criteria(build(CELLS, F(3, 4)), CELLS, LAW, F(3, 4),
                                                 social=no_disc)}["B125-S9"] is False)
    ok("hand value: the Balearic class square at zero charges is 1 - d",
       social_class_square({"fare": "113", "passenger": "0", "security": "0", "pmr": "0"}, F(3, 4),
                           SOCIAL["baleares"]) == F(4, 5))
    ok("the capped product square is (1 + m - alpha)/((1 + m)(1 - alpha)) with no charges",
       osp_product_square({"fare": "100", "passenger": "0", "security": "0", "pmr": "0"},
                          F(3, 4), True) == (OSP_FLEX - F(3, 4)) / (OSP_FLEX * F(1, 4)))

    # A hand value: Madrid departure against Palma inter-island departure, f = 100, alpha = 3/4.
    mad, pmi = CELLS[0], CELLS[14]
    hand = ((F(1, 4) * 100 + F("18.92")) / F("118.92")) / \
           ((F(1, 4) * 100 + F("2.62")) / F("102.62"))
    ok("the alpha-only square is one before mid-2017 and after mid-2018, and one half between",
       [alpha_only_square(pr) for pr in ALPHA_PERIODS] == [F(1), F(1, 2), F(1)])

    ok("the square matches a hand value, MAD vs PMI inter-island at 100 euro",
       closed_form(mad, pmi, F(100), F(3, 4)) == hand)

    width = max(len(label) for label, _ in checks)
    for label, cond in checks:
        print(("PASS  " if cond else "FAIL  ") + label.ljust(width))
    bad = [label for label, cond in checks if not cond]
    print("")
    print("selftest: %d/%d" % (len(checks) - len(bad), len(checks)))
    return 1 if bad else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--out", default="results/b125_resident_square.json")
    args = parser.parse_args()
    if args.selftest:
        return selftest()

    alpha = ALPHA["current"][0]
    report = build(CELLS, alpha)
    crits = criteria(report, CELLS, LAW, alpha)

    print("Resident factor k_R by departure cell (alpha = 3/4), fares " +
          ", ".join(fracs(f) for f in FARE_GRID) + " euro:")
    for c in CELLS:
        ks = ["%.4f" % float(factor(c, f, alpha)) for f in FARE_GRID]
        print("   " + c["cell"].ljust(34) + " U " + ("%.3f" % float(excluded(c))).rjust(7)
              + "   " + "  ".join(ks))
    print("")
    print("Squares against Madrid departure, at 80 euro, log (alpha 3/4 | alpha 1/2):")
    for c in CELLS[1:]:
        q75 = factor(CELLS[0], F(80), alpha) / factor(c, F(80), alpha)
        q50 = factor(CELLS[0], F(80), F(1, 2)) / factor(c, F(80), F(1, 2))
        print("   " + c["cell"].ljust(34) + " " + logf(q75).rjust(10) + " | " + logf(q50).rjust(10)
              + "   closing ratio " + "%.4f" % float(excluded(c) / excluded(CELLS[0])))
    print("")

    failed = []
    for cr in crits:
        if cr["passed"] is None:
            mark = "VOID   "
        elif cr["passed"]:
            mark = "PASS   "
        else:
            mark = "FAILED[" + cr["kind"] + "]: "
            failed.append(cr["name"])
        print(mark + cr["name"] + "  " + cr["detail"])

    print("")
    print("Alpha by period, inter-island against peninsula, charges set aside:")
    periods = []
    for pr in ALPHA_PERIODS:
        q = alpha_only_square(pr)
        print("   from " + pr["from"] + "   peninsula " + fracs(pr["alpha_peninsula"])
              + "   inter-island " + fracs(pr["alpha_inter_island"]) + "   square " + fracs(q)
              + "   log " + logf(q))
        periods.append({"from": pr["from"], "alpha_peninsula": fracs(pr["alpha_peninsula"]),
                        "alpha_inter_island": fracs(pr["alpha_inter_island"]),
                        "alpha_only_square": fracs(q), "log": logf(q), "source": pr["source"]})

    print("")
    ocells = osp_cells()
    osq = osp_route_squares(ocells, alpha)
    print("Canary Islands OSP routes at their published reference fares (alpha 3/4):")
    for c in ocells:
        print("   " + c["cell"].ljust(8) + " fare " + c["fare"].rjust(4) + "   U " + ("%.2f" % float(excluded(c)))
              + "   k_R " + "%.4f" % float(factor(c, F(c["fare"]), alpha)))
    logs = sorted((abs(float(q["log"])), q["log"], q["cells"]) for q in osq if not q["zero"])
    print("   squares non-zero " + str(sum(1 for q in osq if not q["zero"])) + " of " + str(len(osq))
          + "; smallest " + logs[0][1] + " " + "/".join(logs[0][2]) + "; largest " + logs[-1][1] + " "
          + "/".join(logs[-1][2]))
    product = []
    for c in ocells:
        qc, qn = osp_product_square(c, alpha, True), osp_product_square(c, alpha, False)
        product.append({"cell": c["cell"], "capped_log": logf(qc), "uncapped_log": logf(qn)})
    cl = sorted(float(x["capped_log"]) for x in product)
    ul = sorted(float(x["uncapped_log"]) for x in product)
    print("   product square, reference against flexible at 130%, resident against non-resident:")
    print("     article 2.5 read as capping the flexible fare: log %.4f to %.4f" % (cl[0], cl[-1]))
    print("     not capping it (printed for comparison only):    log %.4f to %.4f" % (ul[0], ul[-1]))
    print("   class square, age by residence, at the statutory minimum social discount:")
    sc = social_cells()
    social_record = {}
    for k in sorted(sc):
        on = [social_class_square(c, alpha, SOCIAL[k]) for c in sc[k]]
        off = [social_class_square(c, alpha, SOCIAL[k], charges=False) for c in sc[k]]
        lo = sorted(float(logf(q)) for q in on)
        print("     %-9s with charges log %.6f to %.6f; with no charges %s" % (
            k, lo[0], lo[-1], ", ".join(sorted({logf(q) for q in off}))))
        social_record[k] = {"rule": {"discount": fracs(SOCIAL[k]["discount"]),
                                     "residents_only": SOCIAL[k]["residents_only"],
                                     "source": SOCIAL[k]["source"]},
                            "cells": [{"cell": c["cell"], "fare": c["fare"], "log_with_charges": logf(a),
                                       "log_no_charges": logf(b)} for c, a, b in zip(sc[k], on, off)]}
    osp_record = {"source": OSP_SOURCE, "social_fares": social_record, "flex_source": OSP_FLEX_SOURCE, "flex_cap": fracs(OSP_FLEX),
                  "cells": ocells, "route_squares": osq, "product_squares": product,
                  "reading_of_article_2_5": ("settled by annex IV: a per-coupon cap at alpha times the "
                                             "registered basic fare; the basic fare read as the reference "
                                             "fare on these routes. The uncapped figures are printed for "
                                             "comparison and decide nothing"),
                  "cap_rule": CAP_RULE}

    dose = {}
    for key, (a, note) in sorted(ALPHA.items()):
        r = build(CELLS, a)
        dose[key] = {"alpha": fracs(a), "note": note,
                     "nonzero_squares": r["nonzero_squares"],
                     "square_fare_cells": r["square_fare_cells"]}
    record = {"stage": "B125", "config": config_block(), "criteria": crits,
              "report": report, "alpha_dose": dose, "alpha_periods": periods, "osp_canarias": osp_record,
              "law": LAW, "cells": CELLS}
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("")
    print("wrote " + str(out))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
