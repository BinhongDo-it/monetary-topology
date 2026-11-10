"""B123: whether a published interchange schedule factors into a fee-program part and a class part.

A card network prints, for each fee program (a merchant category, a way of taking the card) and
for each class of card, the share of the sale that the merchant's bank pays the cardholder's
bank. The schedule is a table with two indices. The station asks one question of it: does the
logarithm of the price split into a program term plus a class term. If it does, one scalar on
programs plus one factor per class reproduces the whole table, which is the separable rival and
covers every class-level markup or symmetric friction. If it does not, no such pair exists.

Two families of table are read apart, because who drew the class line differs:

  regulatory  exempt issuers against regulated issuers. The line is drawn by statute: an issuer
              with less than ten billion dollars of assets is exempt from the Regulation II cap
              (12 CFR 235.5), and the regulated column is that cap, 0.05 per cent plus 21 cents.
  product     the network's own card products (Visa Infinite, Signature, Traditional Rewards...).
              The network draws this line, so it is the weaker of the two (D30, second clause).

**Two networks, one test.** Visa prints ruled tables and pymupdf's table finder reads them.
Mastercard prints positioned text with no rules, so its rows are rebuilt from word positions: a
line with a rate in a class column opens a row, a line within CONT_GAP points below it with no
rate of its own continues that row (a second label line, a "(0.95 max)" line under the rates), and
anything further down ends the table on that page. Mastercard calls exempt issuers "Unregulated"
and prints the regulated purchase rate once, for every program, so its statutory tables pair each
exempt program with that one printed rate. The two schedules have two designers (D42), and each
network's counts are printed apart.

**The test is exact.** At a fixed ticket T every cell's fee is a rational number, so a square's
log sum is zero if and only if a product of four rationals equals one, which Fraction decides
with no tolerance. The logarithms and the CPD residuals are printed for reading and decide
nothing.

**Three knobs this station declares, and every square is read across all of them (rule 11f).**
The ticket T, the transform (log(1 + r), the design's, against -log(1 - r), the merchant's
gross-up factor), and whether the regulated cell carries the one-cent fraud adjustment. The
rival predicts a zero, so what a setting decides is zero or not. A square that is non-zero on
every setting where its four cells apply is read; one that is zero on every setting is zero; one
that is zero on some settings and not on others is not read, because there the verdict moves on
a knob. The second transform is defined only where every cell's fee is below the ticket, so a
setting where some cell's fee reaches the ticket is not a setting for that transform and is not
counted. Whether a read square also holds one sign throughout is printed beside it, and it
decides nothing: the rival never named a sign.

A read square need not hold one sign. On the statutory tables two programs' exempt rates, one
flat and one ad valorem, change places as the ticket grows, so their square changes sign without
ever being zero, and at every ticket it contradicts the rival's zero.

**What is left out, and why.** Rows whose name says Small Ticket or Large Ticket: their
eligibility threshold is set in the network's core rules, not printed in this schedule, and it is
not guessed. (A Large Ticket rate carries a fixed fee of $35 or more; read at a $10 ticket it is
a fee of 351% of the sale, which is not a transaction the program covers.) Rows whose
cell holds two rates at once (a merged cell): they are listed, not split. Incentive rows (a
negative adjustment, not a fee program). Rows printed with a ticket condition ("applies to
transactions >=$500") are read only at tickets that meet it. On Mastercard's schedule also refunds,
payment transactions and rebates, which are not fees on a sale; its Small Ticket threshold, where
printed, is $5 and below, under every ticket on the grid.

**What the earlier Mastercard edition is for.** Its regulated rows join the known answer (the cap
was the same in both years), and every table is compared with the current edition row by row and
printed. Unchanged cells reading alike is not a known answer: without the network's own notice of
what changed, "unchanged" has no source apart from the reader.

Run:
    python experiments/b123_interchange_square.py
    python experiments/b123_interchange_square.py --selftest
"""

import argparse
import copy
import csv
import io
import json
import math
import pathlib
import re
import sys
import tempfile
from fractions import Fraction as F

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

RAW = REPO / "data" / "raw" / "b123"
VISA_PDF = RAW / "visa" / "visa-usa-interchange-reimbursement-fees_2026-04-18.pdf"
MC_EDITIONS = {"2026-04-17": RAW / "mastercard" / "merchant-rates-2026-2027-april2026.pdf",
               "2025-04-11": RAW / "mastercard" / "merchant-rates-2025-2026.pdf"}
MC_CURRENT, MC_EARLIER = "2026-04-17", "2025-04-11"
FED_CSV = RAW / "fed" / "Avg_IF_by_PCN.csv"
MANIFEST = RAW / "b123_manifest.json"

TICKETS = [F(10), F(25), F(50), F(100), F(250), F(1000)]
TRANSFORMS = ("log1p", "neglog1m")
FRAUD = [F(0), F(1, 100)]
REF = {"ticket": F(100), "transform": "log1p", "fraud": F(0)}

# The statutory cap (12 CFR 235.3(b)), as the Board states it: no more than $0.21 plus 0.05 per
# cent of the transaction value, plus $0.01 for an issuer that meets the fraud-prevention
# standards (12 CFR 235.4).
CAP_PCT, CAP_FIXED, CAP_FRAUD = F(5, 10000), F(21, 100), F(1, 100)

# Visa tables: (name, zero-based page, table index on the page, family, class names).
# Class names are read off the header rows; the instrument criterion checks the header text
# carries the words below rather than trusting the list.
VISA_TABLES = [
    ("debit_card_present", 4, 0, "regulatory", ["exempt", "regulated"]),
    ("debit_card_not_present", 5, 0, "regulatory", ["exempt", "regulated"]),
    ("prepaid_card_present", 6, 0, "regulatory", ["exempt", "regulated"]),
    ("prepaid_card_not_present", 7, 0, "regulatory", ["exempt", "regulated"]),
    ("business_and_purchasing_prepaid", 18, 0, "regulatory",
     ["exempt business prepaid", "exempt purchasing prepaid", "regulated"]),
    ("corporate_prepaid", 18, 1, "regulatory", ["exempt", "regulated"]),
    ("business_debit", 20, 1, "regulatory", ["exempt", "regulated"]),
    ("consumer_credit_card_present_a", 8, 0, "product",
     ["infinite_spend_qualified", "infinite_spend_not_qualified", "signature_preferred",
      "signature", "traditional_rewards", "all_other"]),
    ("consumer_credit_card_present_b", 9, 0, "product",
     ["infinite_spend_qualified", "infinite_spend_not_qualified", "signature_preferred",
      "signature", "traditional_rewards", "all_other"]),
    ("consumer_credit_card_not_present", 10, 0, "product",
     ["infinite_spend_qualified", "infinite_spend_not_qualified", "signature_preferred",
      "signature", "traditional_rewards", "all_other"]),
    ("small_merchant_credit", 11, 0, "product",
     ["infinite_spend_qualified", "infinite_spend_not_qualified", "signature_preferred",
      "signature", "traditional_rewards", "all_other"]),
    ("business_credit_spend_tier", 20, 0, "product",
     ["tier_I", "tier_II", "tier_III", "tier_IV", "tier_V"]),
]
HEADER_WORDS = {"regulatory": ("Exempt", "Regulated"), "product": ()}
PRODUCT_HEADER_WORDS = {
    "consumer": ("Infinite", "Signature", "Traditional", "All Other"),
    "business_credit_spend_tier": ("Tier I", "Tier V"),
}

RATE = re.compile(
    r"^\s*(?:(?P<pct>-?\d+(?:\.\d+)?)%)?\s*(?:\+\s*)?(?:\$(?P<fix>\d+(?:\.\d+)?))?\s*(?P<star>\*)?"
    r"\s*(?:\(\$(?P<cap>\d+(?:\.\d+)?)\s*Cap\))?\s*(?:\(min\.\s*\$(?P<mn>\d+(?:\.\d+)?)\))?\s*$",
    re.I)
MIN_TICKET = re.compile(r"applies to transactions\s*>=\s*\$(\d+)", re.I)
RATE_SHAPED = re.compile(r"\d%|\$\d")

# Mastercard tables: (name, pages, a phrase that opens the table on its first page, family, class
# names, words the header rows must carry). Family "cap" is read only for the known answer.
MC_TABLES = [
    ("mc_consumer_credit", [1, 2, 3], "Consumer Credit Rates", "product",
     ["core", "enhanced_value", "world", "world_high_value", "world_elite"],
     ("Core", "Enhanced", "World High", "World Elite")),
    ("mc_debit_prepaid", [4, 5], "Unregulated Consumer Debit and Prepaid Rates", "product",
     ["debit", "prepaid"], ("Unregulated", "Debit Rate", "Prepaid Rate")),
    ("mc_small_business_credit", [7], "Small Business Credit", "product",
     ["level_1_business_core", "level_2_business_world", "level_3_business_world_elite",
      "level_4", "level_5"], ("Business Core", "Business World", "Level 5")),
    ("mc_commercial_and_large_market", [8], "Large Market Credit", "product",
     ["commercial_debit", "commercial_prepaid", "large_market_credit"],
     ("Commercial Debit", "Commercial Prepaid", "Large Market Credit")),
    ("mc_regulated", [6], "Regulated Consumer/Commercial Debit and Prepaid Rates", "cap",
     ["debit", "prepaid"],
     ("Regulated Consumer/Commercial Debit", "Debit Rate", "Prepaid Rate", "Purchases with Cash-back")),
    ("mc_pin_debit", [11], "PIN Debit Rates", "cap", ["rate"], ("PIN Debit", "Rate")),
]
MC_STATUTORY_WORDS = ("Unregulated Consumer Debit", "Regulated Consumer/Commercial Debit")
MC_RATE = re.compile(r"^\s*(?P<pct>\d+(?:\.\d+)?)%\s*\+\s*(?P<fix>\d+(?:\.\d+)?)"
                     r"(?:\s*\((?P<cap>\d+(?:\.\d+)?)\s*max\))?\s*$", re.I)
RATE_START = re.compile(r"^(\d+(?:\.\d+)?%|N/A)$")
LINE_TOL = 2.0     # points: words whose centres sit this close in y are one printed line
CONT_GAP = 16.5    # points: a rate-free line this close below a row continues it (12.7 measured)
COL_PAD = 12.0     # points: a class column starts this far left of its first rate on the page


# ---------------------------------------------------------------- parsing

def parse_rate(text):
    """A cell as printed to (pct, fixed, cap, min, fraud_flag), or a reason it is not one rate."""
    s = (text or "").replace("\n", " ").strip()
    if not s:
        return None, "empty"
    if s.lower() == "na":
        return None, "na"
    m = RATE.match(s)
    if not m or (m.group("pct") is None and m.group("fix") is None):
        return None, "not a single rate: " + s
    pct = F(m.group("pct")) / 100 if m.group("pct") else F(0)
    if pct < 0:
        return None, "an adjustment, not a fee program: " + s
    return {"pct": pct, "fixed": F(m.group("fix")) if m.group("fix") else F(0),
            "cap": F(m.group("cap")) if m.group("cap") else None,
            "min": F(m.group("mn")) if m.group("mn") else None,
            "fraud": bool(m.group("star")), "printed": s}, None


def fee(rate, ticket, fraud):
    """The fee on a ticket, exact. Cap and minimum as printed; the fraud cent only where starred."""
    f = rate["pct"] * ticket + rate["fixed"]
    if rate["cap"] is not None:
        f = min(f, rate["cap"])
    if rate["min"] is not None:
        f = max(f, rate["min"])
    if rate["fraud"]:
        f += fraud
    return f


def read_tables(pdf_path, specs):
    """pymupdf's table finder on the named pages. Returns per table: header text, rows used with
    their parsed cells, and rows left out with the reason."""
    import pymupdf
    doc = pymupdf.open(pdf_path)
    out = {}
    for name, page, idx, family, classes in specs:
        tabs = doc[page].find_tables().tables
        rows = tabs[idx].extract() if idx < len(tabs) else []
        header_text, used, left = [], [], []
        for r in rows:
            cells = [(c or "").replace("\n", " ").strip() for c in r]
            label, body = cells[0], cells[1:1 + len(classes)]
            parsed = [parse_rate(c) for c in body]
            if not any(p for p, _ in parsed):
                # A row with nothing that looks like a rate is a header row. A row that carries
                # something rate-shaped and still parses to nothing is a data row left out.
                if any(RATE_SHAPED.search(c) for c in body):
                    reasons = [why for _, why in parsed if why not in ("empty",)]
                    left.append({"row": label, "why": "; ".join(sorted(set(reasons)))})
                else:
                    header_text.append(" ".join(cells))
                continue
            if "small ticket" in label.lower():
                left.append({"row": label, "why": "Small Ticket: eligibility threshold not printed "
                             "in this schedule"})
                continue
            if "large ticket" in label.lower():
                left.append({"row": label, "why": "Large Ticket: eligibility threshold not printed "
                             "in this schedule"})
                continue
            bad = [why for p, why in parsed if p is None and why not in ("na",)]
            if bad:
                left.append({"row": label, "why": "; ".join(bad)})
                continue
            mt = MIN_TICKET.search(label)
            used.append({"row": label, "min_ticket": F(mt.group(1)) if mt else F(0),
                         "cells": [p for p, _ in parsed]})
        out[name] = {"family": family, "classes": classes, "page": page + 1, "pages": [page + 1],
                     "network": "visa", "header": " ".join(header_text), "used": used, "left": left}
    return out


def parse_mc_rate(text):
    """A Mastercard cell as printed ("1.90% + 0.00 (0.95 max)", "N/A"), in the same shape as a
    Visa cell. Mastercard prints no fraud star; its fraud cent is a row of its own."""
    s = " ".join((text or "").split())
    if not s:
        return None, "empty"
    if s.upper() == "N/A":
        return None, "na"
    m = MC_RATE.match(s)
    if not m:
        return None, "not a single rate: " + s
    return {"pct": F(m.group("pct")) / 100, "fixed": F(m.group("fix")),
            "cap": F(m.group("cap")) if m.group("cap") else None, "min": None,
            "fraud": False, "printed": s}, None


def mc_lines(page):
    """The page's words grouped into printed lines, top to bottom; each word as (x0, text)."""
    words = sorted(page.get_text("words"), key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    lines = []
    for w in words:
        yc = (w[1] + w[3]) / 2
        if lines and yc - lines[-1]["y"] <= LINE_TOL:
            lines[-1]["words"].append((w[0], w[4]))
        else:
            lines.append({"y": yc, "words": [(w[0], w[4])]})
    for ln in lines:
        ln["words"].sort()
        ln["text"] = " ".join(t for _, t in ln["words"])
    return lines


def mc_left_out(label, family):
    """Rows of a Mastercard table that are not a fee on a sale, or not readable on the grid."""
    if family not in ("product", "regulatory"):
        return None
    low = label.lower()
    if "refund" in low:
        return "a refund, not a fee on a sale"
    if "payment transaction" in low or "paymenttransaction" in low:
        return "a payment to the card, not a sale"
    if low.startswith("rebate"):
        return "a rebate, not a sale"
    if "small ticket" in low:
        return ("Small Ticket: its ticket threshold is not printed for this row, or is printed as "
                "$5 and below, under every ticket on the declared grid")
    if "large ticket" in low:
        return "Large Ticket: its ticket threshold is not printed in this schedule"
    return None


def read_mc_tables(pdf_path, specs, edition, cont_gap=CONT_GAP, col_pad=COL_PAD):
    """Rows rebuilt from word positions. On each page the class columns start COL_PAD points left
    of the rates on the first line that carries one rate per class; words left of the first column
    are the label. A line with a rate in a column opens a row; a rate-free line within cont_gap
    points below continues it; any other line before the first row is header, and after it ends
    the table on that page."""
    import pymupdf
    doc = pymupdf.open(pdf_path)
    out = {}
    for name, pages, opener, family, classes, words in specs:
        ncls = len(classes)
        header, rows = [], []
        for n, pno in enumerate(pages):
            lines = mc_lines(doc[pno - 1])
            if n == 0:
                start = next((i for i, ln in enumerate(lines) if opener in ln["text"]), None)
                if start is None:
                    break
                lines = lines[start:]
            first = next((ln for ln in lines
                          if sum(1 for _, t in ln["words"] if RATE_START.match(t)) == ncls), None)
            if first is None:
                continue
            edges = [x - col_pad for x, t in first["words"] if RATE_START.match(t)]
            current, last_y = None, None
            for ln in lines:
                label = [t for x, t in ln["words"] if x < edges[0]]
                cols = [[] for _ in range(ncls)]
                for x, t in ln["words"]:
                    if x >= edges[0]:
                        cols[max(i for i, e in enumerate(edges) if e <= x)].append(t)
                if any(RATE_START.match(t) for c in cols for t in c):
                    current = {"label": label, "cells": cols, "page": pno}
                    rows.append(current)
                    last_y = ln["y"]
                elif current is None:
                    header.append(ln["text"])
                elif ln["y"] - last_y <= cont_gap:
                    current["label"] += label
                    for k in range(ncls):
                        current["cells"][k] += cols[k]
                    last_y = ln["y"]
                else:
                    break
        used, left, unparsed = [], [], []
        for r in rows:
            label = " ".join(r["label"])
            parsed = [parse_mc_rate(" ".join(c)) for c in r["cells"]]
            # Mastercard prints every class cell as one rate or N/A, so anything else, kept or left
            # out, is a word the reader put in the wrong place.
            unparsed += [(label, " ".join(c) or "(empty)") for (p, w), c in zip(parsed, r["cells"])
                         if p is None and w != "na"]
            why = mc_left_out(label, family)
            if why is None:
                bad = [w for p, w in parsed if p is None and w not in ("na", "empty")]
                if bad or not any(p for p, _ in parsed):
                    why = "; ".join(bad) or "no rate in any class"
            if why:
                left.append({"row": label, "why": why})
                continue
            used.append({"row": label, "min_ticket": F(0), "page": r["page"],
                         "cells": [p for p, _ in parsed]})
        out[name] = {"family": family, "classes": classes, "page": pages[0], "pages": list(pages),
                     "network": "mastercard", "edition": edition, "header": " ".join(header),
                     "header_words": words, "used": used, "left": left, "unparsed": unparsed}
    return out


def mc_statutory(mc):
    """Mastercard prints one regulated purchase rate for every program (the page headed
    'Purchases, Purchases with Cash-back and Unique') and the unregulated issuers' rates program by
    program. Each statutory table pairs an unregulated column with that one printed rate, starred
    for the fraud cent as Visa stars it; the known answer checks the printed fraud row is the base
    rate plus exactly that cent. Derived, so its regulated cells are not counted twice there."""
    reg, src = mc.get("mc_regulated"), mc.get("mc_debit_prepaid")
    if not reg or not src:
        return {}
    base = next((u for u in reg["used"] if u["row"] == "Regulated POS Debit"), None)
    if base is None:
        return {}
    out = {}
    for k, cls in enumerate(src["classes"]):
        if base["cells"][k] is None:
            continue
        rcell = dict(base["cells"][k], fraud=True)
        out["mc_%s_statutory" % cls] = {
            "family": "regulatory", "classes": ["exempt", "regulated"], "network": "mastercard",
            "edition": src["edition"], "page": src["page"], "pages": src["pages"] + reg["pages"],
            "derived": True, "header": src["header"] + " " + reg["header"],
            "header_words": MC_STATUTORY_WORDS,
            "used": [{"row": u["row"], "min_ticket": u["min_ticket"], "page": u["page"],
                      "cells": [u["cells"][k], rcell]} for u in src["used"]],
            "left": list(src["left"])}
    return out


def load_all(cont_gap=CONT_GAP, col_pad=COL_PAD):
    """Every table the station reads: Visa's, Mastercard's current edition with its statutory
    tables, and the earlier edition's regulated rows for the known answer. Also returns both
    Mastercard editions whole, for the row-by-row comparison."""
    tables = read_tables(VISA_PDF, VISA_TABLES)
    editions = {}
    for ed, path in MC_EDITIONS.items():
        if path.exists():
            editions[ed] = read_mc_tables(path, MC_TABLES, ed, cont_gap, col_pad)
    if MC_CURRENT in editions:
        tables.update(editions[MC_CURRENT])
        tables.update(mc_statutory(editions[MC_CURRENT]))
    if MC_EARLIER in editions:
        for n, t in editions[MC_EARLIER].items():
            if t["family"] == "cap":
                tables["mc_earlier_" + n[3:]] = t
    return tables, editions


def edition_diff(new, old):
    """Row by row, table by table, the two Mastercard editions. Labels are compared with spaces and
    footnote marks taken out. Printed, decides nothing: a schedule may change between editions."""
    def norm(s):
        return re.sub(r"[\s\d]+", "", s)
    out = {}
    for n in new:
        if n not in old:
            out[n] = "absent from the earlier edition"
            continue
        a, b = new[n]["used"], old[n]["used"]
        if len(a) != len(b):
            out[n] = {"rows_now": len(a), "rows_before": len(b)}
            continue
        cells = [(u["row"], new[n]["classes"][k], None if c is None else c["printed"],
                  None if d is None else d["printed"])
                 for u, v in zip(a, b) for k, (c, d) in enumerate(zip(u["cells"], v["cells"]))
                 if (None if c is None else c["printed"]) != (None if d is None else d["printed"])]
        out[n] = {"rows": len(a), "cells_changed": cells,
                  "labels_differing": [(u["row"], v["row"]) for u, v in zip(a, b)
                                       if norm(u["row"]) != norm(v["row"])],
                  "left_out_now": len(new[n]["left"]), "left_out_before": len(old[n]["left"])}
    return out


# ---------------------------------------------------------------- the object

def ratio_one_minus(r):
    return 1 - r


def square_ratio(ra, rb, rc, rd, transform):
    """Product form of the square on cells (i,a), (j,b), (i,b), (j,a): one iff the log sum is zero,
    and above one iff the square is positive in that transform. The second transform is
    -log(1 - r), so its product is taken the other way up to keep the sign the square's own."""
    if transform == "log1p":
        return ((1 + ra) * (1 + rb)) / ((1 + rc) * (1 + rd))
    return ((1 - rc) * (1 - rd)) / ((1 - ra) * (1 - rb))


def sign(q):
    return 0 if q == 1 else (1 if q > 1 else -1)


def squares_of(table):
    """Every 2x2 square with four present cells, read across the declared knobs."""
    used, ncls = table["used"], len(table["classes"])
    results = []
    for i in range(len(used)):
        for j in range(i + 1, len(used)):
            for a in range(ncls):
                for b in range(a + 1, ncls):
                    ci, cj = used[i]["cells"], used[j]["cells"]
                    if None in (ci[a], ci[b], cj[a], cj[b]):
                        continue
                    lo = max(used[i]["min_ticket"], used[j]["min_ticket"])
                    signs, ref = [], None
                    for t in TICKETS:
                        if t < lo:
                            continue
                        for tr in TRANSFORMS:
                            for fr in FRAUD:
                                r = [fee(c, t, fr) / t for c in (ci[a], cj[b], ci[b], cj[a])]
                                if tr == "neglog1m" and any(x >= 1 for x in r):
                                    # -log(1 - r) has no real value there: not a setting.
                                    continue
                                q = square_ratio(r[0], r[1], r[2], r[3], tr)
                                signs.append(sign(q))
                                if t == REF["ticket"] and tr == REF["transform"] and fr == REF["fraud"]:
                                    ref = q
                    if not signs:
                        continue
                    # The rival's prediction is a zero, so what a setting decides is zero or not.
                    # Read: non-zero on every setting. Zero: zero on every setting. Unread: zero on
                    # some settings and not on others, which is the verdict moving on a knob (11f).
                    # Whether the sign also holds is printed beside it; the rival never named one.
                    if all(s == 0 for s in signs):
                        state = "zero"
                    elif all(s != 0 for s in signs):
                        state = "read"
                    else:
                        state = "unread"
                    stable = state == "read" and len(set(signs)) == 1
                    results.append({"rows": [used[i]["row"], used[j]["row"]],
                                    "classes": [table["classes"][a], table["classes"][b]],
                                    "state": state, "sign_stable": stable,
                                    "sign": signs[0] if stable else 0,
                                    "settings": len(signs),
                                    "ref_log": None if ref is None else "%.6f" % math.log(ref)})
    return results


def cpd_residual(table):
    """B81's CPD fit on log(1 + r) at the reference ticket: rows are programs, columns classes.
    Imported rather than rewritten. Printed, never used to decide anything."""
    import numpy as np
    from b81_cpd import cpd_fit
    used, ncls = table["used"], len(table["classes"])
    t, fr = REF["ticket"], REF["fraud"]
    rows = [u for u in used if u["min_ticket"] <= t]
    if len(rows) < 2:
        return None
    y = np.zeros((len(rows), ncls))
    mask = np.zeros((len(rows), ncls), dtype=bool)
    for i, u in enumerate(rows):
        for a, c in enumerate(u["cells"]):
            if c is not None:
                y[i, a] = math.log(1 + float(fee(c, t, fr) / t))
                mask[i, a] = True
    coef, fitted, rhs, obs, X = cpd_fit(y, mask)
    resid = rhs - fitted
    return {"cells": int(mask.sum()), "max_abs_residual": "%.6f" % float(np.max(np.abs(resid))),
            "rms_residual": "%.6f" % float(np.sqrt(np.mean(resid ** 2)))}


# ---------------------------------------------------------------- the Fed table

def money(s):
    s = (s or "").strip().replace("$", "").replace(",", "")
    try:
        return F(s)
    except (ValueError, ZeroDivisionError):
        return None


def fed_rows(path=FED_CSV):
    """(year, network, covered average ticket, covered average fee) for every filled cell pair."""
    text = path.read_bytes().decode("utf-8-sig", errors="replace")
    rows = [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]
    years = rows[1]
    out = []
    for r in rows[4:]:
        net = r[0].strip()
        if not net or net.lower().startswith(("note", "source", "1", "2", "3")):
            continue
        for k in range(1, len(r), 14):
            if k + 9 >= len(r):
                break
            year = years[k].strip()
            tkt, fe = money(r[k + 7]), money(r[k + 8])
            if year.isdigit() and tkt is not None and fe is not None:
                out.append((int(year), net, tkt, fe))
    return out


def fed_tickets(path=FED_CSV):
    """(year, network, exempt average ticket, covered average ticket), printed beside the known
    answer: the two classes of issuer have different average tickets, which is why the Board's
    averages cannot carry a square. Same column layout as fed_rows, read two columns further."""
    text = path.read_bytes().decode("utf-8-sig", errors="replace")
    rows = [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]
    years = rows[1]
    out = []
    for r in rows[4:]:
        net = r[0].strip()
        if not net or net.lower().startswith(("note", "source", "1", "2", "3")):
            continue
        for k in range(1, len(r), 14):
            if k + 9 >= len(r):
                break
            year = years[k].strip()
            ex, cov = money(r[k + 2]), money(r[k + 7])
            if year.isdigit() and ex is not None and cov is not None:
                out.append([int(year), net, "%.2f" % float(ex), "%.2f" % float(cov)])
    return out


# ---------------------------------------------------------------- criteria

def _crit(name, kind, verdict, detail, extra=None):
    c = {"name": name, "kind": kind, "detail": detail,
         "passed": None if verdict is None else bool(verdict)}
    if verdict is None:
        c["void"] = True
    if extra:
        c.update(extra)
    return c


def build(tables, fed):
    report = {}
    for name, t in tables.items():
        if t["family"] == "cap":
            report[name] = {"family": "cap", "network": t["network"], "edition": t.get("edition"),
                            "pages": t["pages"], "classes": t["classes"],
                            "rows_used": [u["row"] for u in t["used"]],
                            "rows_left_out": t["left"]}
            continue
        sq = squares_of(t)
        states = {s: sum(1 for x in sq if x["state"] == s) for s in ("read", "zero", "unread")}
        report[name] = {
            "family": t["family"], "network": t["network"], "edition": t.get("edition"),
            "derived": bool(t.get("derived")), "page": t["page"], "pages": t["pages"],
            "classes": t["classes"],
            "rows_used": [u["row"] for u in t["used"]],
            "rows_left_out": t["left"],
            "independent_squares_if_complete": max(0, (len(t["used"]) - 1) * (len(t["classes"]) - 1)),
            "squares": states,
            "read_sign_stable": sum(1 for x in sq if x["state"] == "read" and x["sign_stable"]),
            "read_positive": sum(1 for x in sq if x["state"] == "read" and x["sign"] > 0),
            "read_negative": sum(1 for x in sq if x["state"] == "read" and x["sign"] < 0),
            "examples_read": [x for x in sq if x["state"] == "read"][:6],
            "examples_unread": [x for x in sq if x["state"] == "unread"][:4],
            "cpd": cpd_residual(t),
        }
    report["_fed"] = {"rows": len(fed),
                      "average_tickets_exempt_covered": fed_tickets() if fed else []}
    return report


def criteria(tables, report, fed, parsed_ok_cells):
    crits = []

    # B123-1 instrument: headers carry the words the class list claims; hand-checked cells parse.
    header_miss = []
    for name, t in tables.items():
        miss = [w for w in header_words_of(name, t) if w.lower() not in t["header"].lower()]
        if miss:
            header_miss.append(name + ":" + "/".join(miss))
    ok_cells, n_cells = parsed_ok_cells
    mc = [t for t in tables.values() if t["network"] == "mastercard" and not t.get("derived")]
    mc_rows = sum(len(t["used"]) + len(t["left"]) for t in mc)
    unparsed = [lab + " -> " + txt for t in mc for lab, txt in t.get("unparsed", [])]
    crits.append(_crit(
        "B123-1", "instrument",
        not header_miss and ok_cells == n_cells and n_cells > 0 and not unparsed,
        "the class names each table is read under are found in that table's own header rows, and "
        "hand-checked cells parse to their printed terms: four on the Visa schedule and seven on "
        "Mastercard's, where rows are rebuilt from word positions (a continued label, a cap printed "
        "on the line under the rates, a class column past the label, a printed N/A read as "
        "absent). Header words missing: "
        + (", ".join(header_miss) if header_miss else "none") + ". Hand-checked cells: "
        + str(ok_cells) + " of " + str(n_cells) + " match. Mastercard rows rebuilt: "
        + str(mc_rows) + "; cells in them that are neither one rate nor N/A, which Mastercard "
        "never prints and a misplaced word would make: " + str(len(unparsed))
        + ("" if not unparsed else " (" + "; ".join(unparsed[:4]) + ")") + "."))

    # B123-2 premise: every regulatory table has exactly one regulated column; every class column
    # names an attribute of the card or its issuer, not of the merchant.
    reg_bad = [n for n, t in tables.items() if t["family"] == "regulatory"
               and sum(1 for c in t["classes"] if c.startswith("regulated")) != 1]
    crits.append(_crit(
        "B123-2", "premise", not reg_bad and bool(tables),
        "the class index is the card's or its issuer's: in the regulatory tables exactly one "
        "column is the regulated issuer's and the rest are exempt issuers', a line 12 CFR 235.5 "
        "draws at ten billion dollars of issuer assets, which the merchant can neither see nor "
        "choose; in the product tables the columns are card products. Tables breaking the "
        "one-regulated-column shape: " + (", ".join(reg_bad) if reg_bad else "none") + "."))

    # B123-3 known answer, two parts. One: every regulated cell is the statutory cap as printed.
    # Visa stars the cap in every row; Mastercard prints it as rows of its own, the fraud cent as a
    # separate row, in both editions. Derived tables copy one printed cell and are not counted.
    reg_cells = [(n, u["row"], c) for n, t in tables.items()
                 if t["family"] == "regulatory" and not t.get("derived")
                 for u in t["used"] for k, c in enumerate(u["cells"])
                 if t["classes"][k].startswith("regulated") and c is not None]
    off = [n + ":" + r for n, r, c in reg_cells
           if not (c["pct"] == CAP_PCT and c["fixed"] == CAP_FIXED and c["fraud"]
                   and c["cap"] is None and c["min"] is None)]
    cap_cells = [(n, u["row"], c) for n, t in tables.items() if t["family"] == "cap"
                 for u in t["used"] if is_regulated_row(u["row"])
                 for c in u["cells"] if c is not None]
    off += [n + ":" + r for n, r, c in cap_cells
            if not (c["pct"] == CAP_PCT and c["cap"] is None and c["min"] is None
                    and c["fixed"] == CAP_FIXED + (CAP_FRAUD if "fraud" in r.lower() else 0))]
    n_visa = len(reg_cells)
    reg_cells = reg_cells + cap_cells
    # Two: the Board's covered averages sit under the cap at the covered average ticket. The cap is
    # linear in the ticket, so the average of capped fees is at most the cap at the average ticket;
    # the table prints to the cent, so half a cent is the format's floor (D24).
    over = [(y, n, str(t), str(f)) for y, n, t, f in fed
            if f > CAP_FIXED + CAP_FRAUD + CAP_PCT * t + F(1, 200)]
    ok = (not off) and bool(reg_cells) and (not over) and bool(fed)
    crits.append(_crit(
        "B123-3", "known_answer", ok if (reg_cells and fed) else None,
        ("two answers known before the schedule is read. First, every regulated cell must be the "
         "cap 12 CFR 235.3 sets, 0.05 per cent plus $0.21, and one cent more where the fraud "
         "adjustment of 12 CFR 235.4 applies (Visa stars it, Mastercard prints it as its own row): "
         + str(len(reg_cells) - len(off)) + " of " + str(len(reg_cells)) + " cells are ("
         + str(n_visa) + " on Visa's schedule, " + str(len(cap_cells)) + " on Mastercard's two "
         "editions)" + ("" if not off else "; not: " + ", ".join(off[:6])) + ". Second, the Board's covered "
         "average fee must not exceed $0.22 + 0.05% of the covered average ticket, plus half a "
         "cent for the printed rounding: " + str(len(fed) - len(over)) + " of " + str(len(fed))
         + " network-years hold" + ("" if not over else "; exceeded: " + str(over[:4])) + ".")
        if (reg_cells and fed) else
        "void: the regulated cells or the Board's table are not on disk to be read back."))

    # B123-4 own reading: squares by state across both families.
    def tally(fam, net=None):
        names = [n for n, t in tables.items()
                 if t["family"] == fam and (net is None or t["network"] == net)]
        out = {s: sum(report[n]["squares"][s] for n in names) for s in ("read", "zero", "unread")}
        out["stable"] = sum(report[n]["read_sign_stable"] for n in names)
        return out

    def by_net(fam):
        parts = []
        for net in ("visa", "mastercard"):
            c = tally(fam, net)
            if c["read"] + c["zero"] + c["unread"]:
                parts.append("%s %d read (%d holding one sign), %d zero, %d unread"
                             % (net.capitalize(), c["read"], c["stable"], c["zero"], c["unread"]))
        return "; ".join(parts) if parts else "no squares"
    reg, prod = tally("regulatory"), tally("product")
    crits.append(_crit(
        "B123-4", "own_reading", reg["read"] + prod["read"] > 0,
        "the registered reading: the printed schedule does not factor, so squares with four "
        "present cells are non-zero on every declared setting. Regulatory tables: " + by_net("regulatory")
        + ". Product tables: " + by_net("product") + ". A square is read where it is non-zero on "
        "every setting its cells apply to, out of " + str(len(TICKETS)) + " tickets, two "
        "transforms and the fraud cent; whether its sign also holds is printed and decides nothing."))

    rival = {"rival_premise": "log price(program, class) = phi(program) + psi(class): one scalar "
                              "on programs and one factor per class",
             "rival_entailment": "the ratio of two classes' prices is the same on every program, "
                                 "so every square's log sum is zero, on every ticket and in "
                                 "either transform",
             "rival_shape": "point prediction of zero",
             "grid": "B"}
    crits.append(_crit(
        "B123-5", "rival", prod["read"] > 0 if (prod["read"] + prod["zero"] + prod["unread"]) else None,
        "separable rival on the networks' own card products. It covers any class markup the same "
        "on every program. Read: " + str(prod["read"]) + " squares non-zero on every setting, "
        + str(prod["stable"]) + " of them holding one sign throughout; " + str(prod["zero"])
        + " exactly zero on every setting (pairs of products a network prices identically on both "
        "programs). By network: " + by_net("product") + ". A criterion of this kind passes when "
        "the rival is wrong.", dict(rival)))
    crits.append(_crit(
        "B123-6", "rival", reg["read"] > 0 if (reg["read"] + reg["zero"] + reg["unread"]) else None,
        "separable rival on the statutory line, exempt against regulated issuers. The regulated "
        "column is one cap on every program (Visa prints it in every row, Mastercard once for all "
        "purchases) and the exempt column varies by program, so the class ratio moves with the "
        "program. Read: " + str(reg["read"]) + " squares non-zero on every setting, "
        + str(reg["stable"]) + " of them holding one sign throughout; " + str(reg["zero"])
        + " zero, " + str(reg["unread"]) + " unread. By network: " + by_net("regulatory") + ".",
        dict(rival)))

    # B123-7 bookkeeping: source file hash, schedule date, tables and every row left out.
    unmatched = manifest_misses(sources_read(tables))
    left = sum(len(t["left"]) for t in tables.values() if not t.get("derived"))
    crits.append(_crit(
        "B123-7", "bookkeeping", not unmatched and bool(tables),
        "every file read is in the fetch manifest with the SHA-256 of the bytes on disk, and every "
        "table's pages, class list, rows used and rows left out (with the reason) are printed "
        "into the record. Files read: " + str(len(sources_read(tables))) + "; not matching the "
        "manifest: " + (", ".join(unmatched) if unmatched else "none") + ". Rows left out: "
        + str(left) + "."))
    return crits


def header_words_of(name, t):
    if "header_words" in t:
        return t["header_words"]
    if t["family"] == "product":
        return PRODUCT_HEADER_WORDS["business_credit_spend_tier" if name.startswith("business")
                                    else "consumer"]
    return HEADER_WORDS[t["family"]]


def is_regulated_row(label):
    low = label.lower()
    return "regulated" in low and "unregulated" not in low


def sources_read(tables):
    files = [VISA_PDF, FED_CSV]
    files += [p for ed, p in MC_EDITIONS.items()
              if any(t.get("edition") == ed for t in tables.values())]
    return files


def manifest_misses(files):
    import hashlib
    man = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    out = []
    for p in files:
        key = p.relative_to(RAW).as_posix()
        rec = man.get(key)
        if not p.exists() or not rec or rec.get("sha256") != hashlib.sha256(p.read_bytes()).hexdigest():
            out.append(key)
    return out


def hand_checks(tables):
    """Cells read by eye off the printed schedules, as the instrument's known answers: four on
    Visa's, and seven on Mastercard's chosen where rebuilding rows from word positions can go
    wrong, one of them a printed N/A that must read as absent. Returns (matching, checked)."""
    want = [
        ("debit_card_present", "CPS/Retail, Debit", 0, (F(80, 10000), F(15, 100), None, None)),
        ("debit_card_present", "CPS/Supermarket, Debit", 0, (F(0), F(30, 100), None, None)),
        ("consumer_credit_card_present_a", "Fuel", 4, (F(115, 10000), F(25, 100), F(110, 100), None)),
        ("consumer_credit_card_present_b", "Restaurant 2", 4, (F(210, 10000), F(0), None, F(4, 100))),
    ]
    if MC_EDITIONS[MC_CURRENT].exists():
        want += [
            # a label on two lines
            ("mc_consumer_credit", "Convenience Purchases Base", 0, (F(165, 10000), F(4, 100), None, None)),
            # a cap printed on the line under the rates
            ("mc_consumer_credit", "Petroleum Base", 4, (F(200, 10000), F(0), F(95, 100), None)),
            # a cap inside the cell, and a label on two lines
            ("mc_debit_prepaid", "Emerging Markets (Education", 0, (F(65, 10000), F(15, 100), F(2), None)),
            # the last of five columns on a page whose labels start further left
            ("mc_small_business_credit", "Utilities", 4, (F(0), F(150, 100), None, None)),
            # a row with two classes printed N/A
            ("mc_commercial_and_large_market", "Data Rate III", 2, (F(190, 10000), F(10, 100), None, None)),
            # the fraud adjustment as a row of its own, label on two lines
            ("mc_regulated", "Regulated POS Debit with Fraud Adjustment", 1, (F(5, 10000), F(22, 100), None, None)),
            # a printed N/A is an absent cell, not a zero rate
            ("mc_commercial_and_large_market", "Data Rate III", 0, None),
        ]
    ok = 0
    for name, row, k, terms in want:
        found = [u for u in tables.get(name, {}).get("used", []) if u["row"].startswith(row)]
        c = found[0]["cells"][k] if found else "row missing"
        if terms is None:
            ok += c is None
        else:
            ok += isinstance(c, dict) and (c["pct"], c["fixed"], c["cap"], c["min"]) == terms
    return ok, len(want)


def config_block():
    return {"tickets": [str(t) for t in TICKETS], "transforms": list(TRANSFORMS),
            "fraud_cent": [str(f) for f in FRAUD], "reference": {k: str(v) for k, v in REF.items()},
            "schedules": ["Visa USA Interchange Reimbursement Fees, effective 18 April 2026",
                          "Mastercard 2026-2027 U.S. Region Interchange Programs and Rates, "
                          "effective 17 April 2026",
                          "Mastercard 2025-2026 U.S. Region Interchange Programs and Rates, "
                          "effective 11 April 2025 (regulated rows and the edition comparison)"],
            "tables": [n for n, *_ in VISA_TABLES] + [n for n, *_ in MC_TABLES],
            "mastercard_reader": {"line_tolerance_pt": LINE_TOL, "continuation_gap_pt": CONT_GAP,
                                  "column_pad_pt": COL_PAD},
            "left_out_by_rule": ["Small Ticket rows", "Large Ticket rows", "merged cells",
                                 "incentive rows",
                                 "refunds", "payment transactions", "rebates"]}


def serial(tables):
    out = {}
    for n, t in tables.items():
        out[n] = {"family": t["family"], "network": t["network"], "edition": t.get("edition"),
                  "derived": bool(t.get("derived")), "pages": t["pages"], "classes": t["classes"],
                  "rows": [{"row": u["row"], "min_ticket": str(u["min_ticket"]),
                            "cells": [None if c is None else c["printed"] for c in u["cells"]]}
                           for u in t["used"]],
                  "left_out": t["left"]}
    return out


# ---------------------------------------------------------------- self-test (11f)

def verdicts(tables, fed):
    report = build(tables, fed)
    return {c["name"]: c["passed"] for c in criteria(tables, report, fed, hand_checks(tables))}


def selftest():
    global MANIFEST
    checks = []

    def ok(label, cond):
        checks.append((label, bool(cond)))

    tables, editions = load_all()
    fed = fed_rows()
    base = verdicts(tables, fed)
    ok("every criterion holds on the schedules as printed", all(v is True for v in base.values()))

    # Mastercard: the reader, then the known answer and the bookkeeping on its files.
    thin, _ = load_all(cont_gap=5.0)
    ok("rows rebuilt with no room for a continuation line flip the instrument",
       verdicts(thin, fed)["B123-1"] is False)
    wide, _ = load_all(col_pad=40.0)
    ok("class columns started too far left flip the instrument", verdicts(wide, fed)["B123-1"] is False)
    ok("a label continued below its rates joins its own row",
       any(x["row"].startswith("Payment Transaction (Gaming Payments")
           for x in tables["mc_consumer_credit"]["left"]))
    ok("no Mastercard row carries a footnote or a title",
       not any(re.search(r"Applies to|following|Qualifying|Proprietary|Note:", u["row"])
               for t in tables.values() if t["network"] == "mastercard"
               for u in t["used"] + t["left"]))
    def seeded(label, plant, crit):
        """Plant a fault and require the criterion to flip. A seed that cannot be planted is
        reported as a failure of its own, not a crash that hides the rest of the report."""
        t = copy.deepcopy(tables)
        try:
            plant(t)
        except (KeyError, IndexError, StopIteration) as exc:
            ok(label + " (seed not planted: " + type(exc).__name__ + ")", False)
            return
        ok(label, verdicts(t, fed)[crit] is False)

    def off_cap(t):
        t["mc_regulated"]["used"][0]["cells"][0]["pct"] = F(6, 10000)

    def fraud_cent(t):
        next(u for u in t["mc_earlier_regulated"]["used"] if "Fraud" in u["row"])["cells"][1]["fixed"] = F(23, 100)

    def misplaced(t):
        t["mc_consumer_credit"]["unparsed"].append(("seeded row", "1.95% + 0.10 2.10%"))
    seeded("a Mastercard regulated row off the cap flips the known answer", off_cap, "B123-3")
    seeded("the earlier edition's fraud row a cent off flips the known answer", fraud_cent, "B123-3")
    seeded("a Mastercard cell holding a misplaced word flips the instrument", misplaced, "B123-1")
    real = MANIFEST
    with tempfile.TemporaryDirectory() as d:
        fake = pathlib.Path(d) / "manifest.json"
        man = json.loads(real.read_text(encoding="utf-8"))
        key = MC_EDITIONS[MC_EARLIER].relative_to(RAW).as_posix()
        man[key] = dict(man[key], sha256="0" * 64)
        fake.write_text(json.dumps(man), encoding="utf-8")
        MANIFEST = fake
        try:
            flipped = verdicts(tables, fed)["B123-7"] is False
        finally:
            MANIFEST = real
    ok("an edition whose bytes do not match the manifest flips the bookkeeping", flipped)

    # A separable product table must flip B123-5: class factor times program factor, exactly.
    t = copy.deepcopy(tables)
    for n, tab in t.items():
        if tab["family"] != "product":
            continue
        for i, u in enumerate(tab["used"]):
            for k in range(len(u["cells"])):
                u["cells"][k] = {"pct": F(0), "fixed": F(0), "cap": None, "min": None,
                                 "fraud": False, "printed": "seeded"}
                # (1 + r) = (1 + p_i)(1 + q_k) with a fixed-free rate so the ticket drops out
                p, q = F(i + 1, 100), F(k + 1, 1000)
                u["cells"][k]["pct"] = (1 + p) * (1 + q) - 1
            u["min_ticket"] = F(0)
    v = verdicts(t, fed)
    ok("a product table that factors exactly flips the product rival", v["B123-5"] is False)

    t = copy.deepcopy(tables)
    t["debit_card_present"]["used"][0]["cells"][1]["pct"] = F(6, 10000)
    ok("a regulated cell off the statutory cap flips the known answer", verdicts(t, fed)["B123-3"] is False)

    fed_bad = list(fed)
    y, n, tk, f = fed_bad[0]
    fed_bad[0] = (y, n, tk, f + F(10, 100))
    ok("a covered average above the cap flips the known answer", verdicts(tables, fed_bad)["B123-3"] is False)

    t = copy.deepcopy(tables)
    t["debit_card_present"]["header"] = "Card Present Fee Program"
    ok("a header without the class words flips the instrument", verdicts(t, fed)["B123-1"] is False)

    t = copy.deepcopy(tables)
    t["debit_card_present"]["classes"] = ["exempt", "exempt too"]
    ok("a regulatory table with no regulated column flips the premise", verdicts(t, fed)["B123-2"] is False)

    # A square whose sign moves with the ticket must be counted unread, not read.
    one = {"family": "product", "classes": ["a", "b"], "page": 0, "header": "", "left": [],
           "used": [
               {"row": "p", "min_ticket": F(0), "cells": [
                   {"pct": F(1, 100), "fixed": F(10, 100), "cap": None, "min": None, "fraud": False, "printed": ""},
                   {"pct": F(2, 100), "fixed": F(0), "cap": None, "min": None, "fraud": False, "printed": ""}]},
               {"row": "q", "min_ticket": F(0), "cells": [
                   {"pct": F(2, 100), "fixed": F(0), "cap": None, "min": None, "fraud": False, "printed": ""},
                   {"pct": F(2, 100), "fixed": F(0), "cap": None, "min": None, "fraud": False, "printed": ""}]}]}
    sq = squares_of(one)
    ok("a square that is zero on one ticket and not on others is left unread",
       len(sq) == 1 and sq[0]["state"] == "unread")

    # -log(1 - r) is defined only below r = 1. A $35 fixed fee reaches the ticket at $10 and
    # $25, so on those two tickets the second transform has no setting: 6 tickets x 2 fraud
    # values for log(1 + r), 4 x 2 for -log(1 - r).
    big = copy.deepcopy(one)
    big["used"][0]["cells"][0] = {"pct": F(1, 100), "fixed": F(35), "cap": None, "min": None,
                                  "fraud": False, "printed": ""}
    sq = squares_of(big)
    ok("a fee at or above the ticket is not a setting of the second transform",
       len(sq) == 1 and sq[0]["settings"] == 20)

    ok("no Large Ticket row is read, and each is listed with its reason",
       not any("large ticket" in u["row"].lower() for t in tables.values() for u in t["used"])
       and any("Large Ticket" in x["why"] for t in tables.values() for x in t["left"]))

    # A square that changes sign across tickets but is never zero refutes a zero on every
    # setting: it is read, and it is marked as not holding one sign.
    two = copy.deepcopy(one)
    # 1% + $0.15 crosses the 2% column at a $15 ticket, between the $10 and $25 grid points, so
    # the sign turns over and no grid point sits on the crossing.
    two["used"][0]["cells"][0] = {"pct": F(1, 100), "fixed": F(15, 100), "cap": None, "min": None,
                                  "fraud": False, "printed": ""}
    sq = squares_of(two)
    ok("a square that flips sign but is never zero is read and marked unstable",
       len(sq) == 1 and sq[0]["state"] == "read" and not sq[0]["sign_stable"])

    # Every exempt program priced the same: the statutory line then factors and B123-6 must fail.
    t = copy.deepcopy(tables)
    for n, tab in t.items():
        if tab["family"] != "regulatory":
            continue
        for u in tab["used"]:
            for k, cl in enumerate(tab["classes"]):
                if not cl.startswith("regulated"):
                    u["cells"][k] = {"pct": F(1, 100), "fixed": F(10, 100), "cap": None,
                                     "min": None, "fraud": False, "printed": "seeded"}
            u["min_ticket"] = F(0)
    ok("exempt programs all priced alike flip the statutory rival", verdicts(t, fed)["B123-6"] is False)

    # Both families factoring at once is the only thing that should flip the own reading.
    for n, tab in t.items():
        if tab["family"] != "product":
            continue
        for i, u in enumerate(tab["used"]):
            for k in range(len(u["cells"])):
                u["cells"][k] = {"pct": (1 + F(i + 1, 100)) * (1 + F(k + 1, 1000)) - 1, "fixed": F(0),
                                 "cap": None, "min": None, "fraud": False, "printed": "seeded"}
            u["min_ticket"] = F(0)
    ok("every table factoring flips the own reading", verdicts(t, fed)["B123-4"] is False)

    # The printed cap must bind where it should: fuel dispensers, debit, 0.80% + $0.15 capped at
    # $0.95. Uncapped at a $250 ticket that is $2.15.
    afd = next(u for u in tables["debit_card_present"]["used"]
               if u["row"].startswith("CPS/Automated Fuel Dispenser"))["cells"][0]
    ok("the printed cap binds on a large ticket", fee(afd, F(250), F(0)) == F(95, 100))

    # On a statutory square the regulated column cancels and what is left is one exempt rate
    # against another; both transforms rise with the rate, so they must agree on the sign.
    rows = tables["debit_card_present"]["used"]
    ret = next(u for u in rows if u["row"].startswith("CPS/Retail, Debit"))["cells"]
    sup = next(u for u in rows if u["row"].startswith("CPS/Supermarket, Debit"))["cells"]
    agree = True
    for t in TICKETS:
        r = [fee(c, t, F(0)) / t for c in (ret[0], sup[1], ret[1], sup[0])]
        agree &= sign(square_ratio(*r, "log1p")) == sign(square_ratio(*r, "neglog1m"))
    ok("both transforms give a statutory square the same sign", agree)
    ok("the printed cap is slack on a small ticket", fee(afd, F(10), F(0)) == F(23, 100))

    ok("a merged cell is refused, not split", parse_rate("0.65% + $0.15 ($2.00 Cap) 0.65% + $0.15 ($0.65 Cap)")[0] is None)
    ok("an incentive row is refused", parse_rate("-0.05%")[0] is None)
    ok("the statutory cap parses with its star", parse_rate("0.05% + $0.21*")[0]["fraud"] is True)
    ok("a minimum parses", parse_rate("2.20% (min. $0.04)")[0]["min"] == F(4, 100))

    width = max(len(label) for label, _ in checks)
    for label, cond in checks:
        print(("PASS  " if cond else "FAIL  ") + label.ljust(width))
    bad = [label for label, cond in checks if not cond]
    print("\nselftest: %d/%d" % (len(checks) - len(bad), len(checks)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default="results/b123_interchange_square.json")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    tables, editions = load_all()
    fed = fed_rows()
    report = build(tables, fed)
    crits = criteria(tables, report, fed, hand_checks(tables))

    for n, r in report.items():
        if n.startswith("_"):
            continue
        if r["family"] == "cap":
            print("== %-34s %-10s %-10s rows %2d  left %d  (known answer only)"
                  % (n, "cap", r["network"], len(r["rows_used"]), len(r["rows_left_out"])))
            continue
        print("== %-34s %-10s %-10s p%-3d rows %2d  left %2d  squares read %4d (+%d/-%d) zero %4d unread %4d  cpd %s"
              % (n, r["family"], r["network"], r["page"], len(r["rows_used"]), len(r["rows_left_out"]),
                 r["squares"]["read"], r["read_positive"], r["read_negative"], r["squares"]["zero"],
                 r["squares"]["unread"], (r["cpd"] or {}).get("max_abs_residual")))

    # The earlier Mastercard edition, whole: row by row against the current one, and its squares.
    comparison = None
    if MC_CURRENT in editions and MC_EARLIER in editions:
        diff = edition_diff(editions[MC_CURRENT], editions[MC_EARLIER])
        earlier = dict(editions[MC_EARLIER])
        earlier.update(mc_statutory(editions[MC_EARLIER]))
        rep_e = build({k: v for k, v in earlier.items() if v["family"] != "cap"}, fed)
        comparison = {"current": MC_CURRENT, "earlier": MC_EARLIER, "rows": diff,
                      "earlier_squares": {k: v["squares"] for k, v in rep_e.items()
                                          if not k.startswith("_")}}
        print("")
        for n, d in diff.items():
            if isinstance(d, dict) and "cells_changed" in d:
                print("   %s vs %s  %-34s rows %2d  cells changed %d  labels differing %d"
                      % (MC_CURRENT, MC_EARLIER, n, d["rows"], len(d["cells_changed"]),
                         len(d["labels_differing"])))
            else:
                print("   %s vs %s  %-34s %s" % (MC_CURRENT, MC_EARLIER, n, d))
    print("")
    failed = []
    for c in crits:
        mark = "VOID   " if c["passed"] is None else ("PASS   " if c["passed"] else "FAILED[" + c["kind"] + "]: ")
        if c["passed"] is False:
            failed.append(c["name"])
        print(mark + c["name"] + "  " + c["detail"])

    record = {"stage": "B123", "config": config_block(), "criteria": crits, "report": report,
              "tables": serial(tables), "mastercard_editions": comparison}
    out = REPO / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print("\nwrote " + str(out.relative_to(REPO)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
