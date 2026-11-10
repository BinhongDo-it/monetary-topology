"""B152: whether two app stores' published commission tables factor into a row part and a column part.

Apple (its European Union page and its Japan page) and Google (its Play Console help page, with the
June 2026 Android Developers Blog post and the two program pages) each publish a commission for a
row (a developer class) on a column (a position a transaction sits on). Apple's columns are payment
routes: in-app purchase through the store's own billing, an alternative payment processor inside
the app, and an external link out of the app. Google's columns are positions described by three
things at once: the product (auto-renewing subscription or other transaction), the install cohort
of the buyer (first install before or after the rollout date), and the billing route (Google Play
billing, alternative billing, external link). The rows are the store's: the standard rate against
the reduced rate (Apple; three programs and subscriptions after their first year), and the first
million dollars of annual earnings, the standard tier and the two program tiers (Google).

The station asks one question of each table. If the commission is a row term plus a column term in
some transform, every square on the table is zero in that transform. Two rivals are read:

    L   the level is additive: f(row, column) = A(row) + phi(column). Every level square is zero.
    M   a scalar potential on columns with a constant offset per row: log(1 + f), or
        -log(1 - f), splits into a row term plus a column term. Every log square is zero.

A square is decided exactly, in rationals: the level square is a sum of four printed percentages,
and a log square is zero if and only if a product of four rationals equals one (B123's
square_ratio and sign). Nothing is fitted and nothing has a tolerance.

**Three knobs this station declares, and every square is read across all of them (rule 11f).**

    transform     level, log(1 + f), -log(1 - f)
    add-on        Apple Japan prints a 5% payment processing fee on Apple In-App Purchase beside the
                  commission; Google prints a 5% billing fee on Google Play billing beside the
                  service fee. "with" reads the total the store collects; "without" strips the
                  printed add-on, which is the split rival L would make.
    Korea/India   Google's remaining-markets page sets the alternative-billing fee in South Korea and
                  India to the Google Play billing fee "reduced by 4%". The page prints no worked
                  example, so both readings are swept: four percentage points, or four per cent of
                  the fee.

A square that is non-zero on every setting is read; zero on every setting is zero; zero on some and
not on others is not read, because there the verdict moves on a knob.

**The floor.** Every rate is printed as a whole percentage, so one percentage point is the format's
tick. A number printed once is one input, and moving it moves every cell it sits in. A square's floor
in each transform is the largest change one tick in one input produces (level: additive; logs: the
tick-floor module's floor_of). A read square stands above its floor when, at the reference setting
(add-on included, Korea/India in points), its size exceeds its floor in all three transforms and in
both input layouts below.

**Two input layouts.** Google's help page prints "10% + 5% billing fee" in each cell, with the
first-million row as one cell spanning three columns; its blog post states the same numbers as two
rules (one 10% for the first million and every subscription, one 5% billing fee). Which numbers are
one input changes the floor, not the value, so the floor is taken in both and the smaller multiple
is the one reported.

Run:
    python experiments/b152_appstore_square.py --snapshot DIR   # copy saved pages in, write texts and manifest
    python experiments/b152_appstore_square.py --refresh-meta   # rewrite the transcription and version fields
    python experiments/b152_appstore_square.py
    python experiments/b152_appstore_square.py --selftest
    python experiments/b152_appstore_square.py --mutate         # break one piece at a time, rerun the self-test

A full run writes the self-test and the mutation run into the record, check by check.
"""

import argparse
import copy
import hashlib
import itertools
import json
import math
import pathlib
import re
import shutil
import sys
from fractions import Fraction as F
from html.parser import HTMLParser

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO.parent))

from b123_interchange_square import square_ratio, sign  # noqa: E402
from b122_b125_tick_floor import floor_of  # noqa: E402

RAW = REPO / "data" / "raw" / "b152"
MANIFEST = RAW / "b152_manifest.json"
TRANSCRIPTION = RAW / "b152_tables_transcribed.json"
SESSION = "T11_PAYMENT1"
ACCESSED = "2026-10-14"

TRANSFORMS = ("level", "log1p", "neglog1m")
ADDON = ("with", "without")
KRIN = ("points", "relative")
LAYOUTS = ("rule", "cell")
REF = {"addon": "with", "krin": "points"}
TICK = F(1)  # one percentage point

# ---------------------------------------------------------------- pages

PAGES = {
    "apple_eu": {
        "url": "https://developer.apple.com/support/alternative-payment-options-on-the-app-store-in-the-eu/",
        "version": "Effective October 1, 2026, the primary updates include:"},
    "apple_jp": {
        "url": "https://developer.apple.com/support/app-distribution-in-japan/",
        "version": None,
        "version_reason": "the page prints no version or effective date for its rate tables; the one dated sentence "
                          "on it ('By March 17, 2026, all current members of the Apple Developer Program will need "
                          "to agree to the latest update ...') is an agreement deadline. The rates' date is on the "
                          "announcement page (apple_jp_news: December 17, 2025)."},
    "apple_jp_news": {
        "url": "https://www.apple.com/newsroom/2025/12/apple-announces-changes-to-ios-in-japan/",
        "version": "December 17, 2025"},
    "apple_sbp": {
        "url": "https://developer.apple.com/app-store/small-business-program/",
        "version": None, "version_reason": "the page prints no version or effective date"},
    "google_help": {
        "url": "https://support.google.com/googleplay/android-developer/answer/112622?hl=en",
        "version": "(June 30, 2026 for the EEA, UK, and US; September 30, 2026 for Australia and Japan)"},
    "google_blog": {
        "url": "https://android-developers.googleblog.com/2026/06/play-expanded-billing.html",
        "version": "This starts on June 30, 2026, beginning with the United States, European Economic Area, "
                   "and United Kingdom."},
    "google_levelup": {
        "url": "https://play.google.com/console/about/levelup/",
        "version": None, "version_reason": "the page prints no version; its rate card prints no date"},
    "google_appsexp": {
        "url": "https://play.google.com/console/about/programs/appsexperience/",
        "version": "United States, United Kingdom, Japan, European Economic Area and Australia September 30, 2026"},
}

# ---------------------------------------------------------------- page text

_BLOCK = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "br", "section", "article",
          "table", "ul", "ol", "header", "footer", "dt", "dd", "caption", "figcaption", "blockquote"}
_SKIP = {"script", "style", "noscript", "svg", "template"}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self.skip += 1
        elif tag in ("td", "th"):
            a = dict(attrs)
            span = "".join(" %s=%s" % (k, a[k]) for k in ("colspan", "rowspan") if a.get(k))
            self.out.append(" | <" + tag + span + "> ")
        elif tag == "img":
            a = dict(attrs)
            src = a.get("src", "")
            if src.startswith("data:"):
                src = "data:..."
            self.out.append("\n[img src=%s alt=%s]\n" % (src, a.get("alt", "")))
        elif tag in _BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in _BLOCK:
            self.out.append("\n")

    def handle_data(self, d):
        if not self.skip:
            self.out.append(d)


def page_text(raw_bytes):
    """The saved page as text: one block per line, each table cell opened by a ' | <td> ' mark that
    carries its colspan and rowspan, script and style dropped."""
    p = _Text()
    p.feed(raw_bytes.decode("utf-8", errors="replace"))
    lines = [" ".join(l.split()) for l in "".join(p.out).split("\n")]
    keep = []
    for l in lines:
        if l or (keep and keep[-1]):
            keep.append(l)
    return "\n".join(keep).strip() + "\n"


_MARK = re.compile(r"\|\s*<t[dh][^>]*>")


def flat(text):
    """Cell marks removed and whitespace collapsed: the form quotes are matched against."""
    return " ".join(_MARK.sub(" ", text).split())


def pct_tokens(quote):
    return re.findall(r"(\d+(?:\.\d+)?)%", quote)


# ---------------------------------------------------------------- the transcription

# Every printed number the station uses: (page, quote as printed, which percentage in the quote).
# Quotes are matched against the page text with cell marks removed and whitespace collapsed.
Q_EU = {
    "iap_s": ("apple_eu", "26% Sales processed by Apple In-App Purchase.", 0),
    "iap_r": ("apple_eu", "15% Sales processed by Apple In-App Purchase from participants in the App Store Small "
                          "Business Program, Mini Apps Partner Program, or Video Partner Program, and sales of "
                          "auto-renewable subscriptions after their first year.", 0),
    "alt_s": ("apple_eu", "20% Sales processed via alternative payment processing within the app.", 0),
    "alt_r": ("apple_eu", "10% Sales processed via alternative payment processing within the app from participants "
                          "in the App Store Small Business Program, Mini Apps Partner Program, or Video Partner "
                          "Program; and sales of auto-renewable subscriptions after their first year.", 0),
    "lnk_s": ("apple_eu", "15% Out-of-app offers. 10% Out-of-app offers for relevant transactions", 0),
    "lnk_r": ("apple_eu", "10% Out-of-app offers for relevant transactions from participants in the App Store Small "
                          "Business Program, Mini Apps Partner Program, and Video Partner Program; and out-of-app "
                          "offers for relevant auto-renewable subscriptions after their first year", 0),
}
Q_JP = {
    "com_s": ("apple_jp", "21% Sale of digital goods or services (including using alternative payments within "
                          "apps). Excludes transactions from program participants or auto-renewable subscriptions "
                          "after their first year.", 0),
    "com_r": ("apple_jp", "10% Transactions from participants in the App Store Small Business Program, Mini Apps "
                          "Partner Program, and Video Partner Program.", 0),
    "com_r_sub": ("apple_jp", "10% Auto-renewable subscriptions after their first year. 21% Sale", 0),
    "proc": ("apple_jp", "Apple payment processing fee Rate Applies to 5% Payments processed by Apple In-App "
                         "Purchase.", 0),
    "lnk_s": ("apple_jp", "10% Out-of-app offers for relevant auto-renewable subscriptions after their first year. "
                          "15% Out-of-app offers.", 1),
    "lnk_r": ("apple_jp", "10% Out-of-app offers for relevant transactions from participants in the App Store "
                          "Small Business Program, Mini Apps Partner Program, and Video Partner Program.", 0),
    "lnk_r_sub": ("apple_jp", "10% Out-of-app offers for relevant auto-renewable subscriptions after their first "
                              "year.", 0),
}
# Japan prints its reduced class in two rows (programs; subscriptions after their first year), each at the same
# rate. The table uses one input per channel for the class; each second row's quote is checked against it, so a
# split of the class into two rates flips PAY1-1.
MERGED = {("apple_jp", "com_r_sub"): "com_r", ("apple_jp", "lnk_r_sub"): "lnk_r"}
G_FIRST = "First $1M (USD) of annual earnings 10% + 5% billing fee *"
G_STD = ("Standard 10% + 5% billing fee * 20% + 5% billing fee * 25% + 5% billing fee * OR; 20% for external "
         "web links")
G_PROG = ("When participating in the Play Games Level Up or Apps Experience programs 10% + 5% billing fee * 15% "
          "+ 5% billing fee * 20% + 5% billing fee * OR; 15% for external web links")
G_TEN = ("Regardless of whether you use Google Play's billing system, alternative billing, or external web links, "
         "the service fee starts at 10% on your first $1M (USD) in annual earnings. This 10% service fee also "
         "applies to all auto-renewing subscriptions.")
G_BILL = "In the United States, United Kingdom, and the European Economic Area, the billing fee is set at 5%."
Q_GMAIN = {
    # rule layout: the blog's two rules are one input each
    "ten": ("google_blog", G_TEN, 0),
    "bill": ("google_blog", G_BILL, 0),
    # cell layout: each printed cell its own input; the first-million cell spans three columns
    "first": ("google_help", G_FIRST, 0), "bill_first": ("google_help", G_FIRST, 1),
    "first_lnk": ("google_blog", G_TEN, 0),
    "s_sub": ("google_help", G_STD, 0), "bill_s_sub": ("google_help", G_STD, 1),
    "s_new": ("google_help", G_STD, 2), "bill_s_new": ("google_help", G_STD, 3),
    "s_ex": ("google_help", G_STD, 4), "bill_s_ex": ("google_help", G_STD, 5),
    "s_lnk": ("google_help", G_STD, 6),
    "p_sub": ("google_help", G_PROG, 0), "bill_p_sub": ("google_help", G_PROG, 1),
    "p_new": ("google_help", G_PROG, 2), "bill_p_new": ("google_help", G_PROG, 3),
    "p_ex": ("google_help", G_PROG, 4), "bill_p_ex": ("google_help", G_PROG, 5),
    "p_lnk": ("google_help", G_PROG, 6),
}
G_TIER = ("Developers enrolled in the 15% service fee tier 15% for the first $1M (USD) revenue earned by the "
          "developer each year 30% for earnings in excess of $1M (USD) revenue earned by the developer each year")
Q_GROW = {
    "first": ("google_help", G_TIER, 1),
    "above": ("google_help", G_TIER, 2),
    "sub": ("google_help", "Subscriptions 15% for automatically renewing subscription products purchased by "
                           "subscribers, regardless of revenue earned by the developer each year", 0),
    "cut": ("google_help", "the service fee for such transactions using the Alternative Billing System is equal to "
                           "the service fee applicable for transactions via Google Play’s billing system reduced "
                           "by 4%.", 0),
}
QUOTES = {"apple_eu": Q_EU, "apple_jp": Q_JP, "google_main": Q_GMAIN, "google_row": Q_GROW}


def _cell(sum_, addon=(), cut=None):
    return {"sum": list(sum_), "addon": list(addon), "cut": cut}


def spec_tables():
    """Rows, columns, inputs (percentage points, as printed) and cells per table and input layout."""
    eu_in = {k: F(pct_tokens(q)[i]) for k, (p, q, i) in Q_EU.items()}
    eu = {"writer": "Apple", "where": "EU", "rows": ["standard", "reduced"], "cols": ["iap", "alt", "link"],
          "inputs": eu_in,
          "cells": {("standard", "iap"): _cell(["iap_s"]), ("standard", "alt"): _cell(["alt_s"]),
                    ("standard", "link"): _cell(["lnk_s"]), ("reduced", "iap"): _cell(["iap_r"]),
                    ("reduced", "alt"): _cell(["alt_r"]), ("reduced", "link"): _cell(["lnk_r"])}}
    jp_in = {k: F(pct_tokens(Q_JP[k][1])[Q_JP[k][2]]) for k in ("com_s", "com_r", "proc", "lnk_s", "lnk_r")}
    jp = {"writer": "Apple", "where": "Japan", "rows": ["standard", "reduced"], "cols": ["iap", "alt", "link"],
          "inputs": jp_in,
          "cells": {("standard", "iap"): _cell(["com_s"], ["proc"]), ("standard", "alt"): _cell(["com_s"]),
                    ("standard", "link"): _cell(["lnk_s"]), ("reduced", "iap"): _cell(["com_r"], ["proc"]),
                    ("reduced", "alt"): _cell(["com_r"]), ("reduced", "link"): _cell(["lnk_r"])}}
    val = {k: F(pct_tokens(q)[i]) for k, (p, q, i) in Q_GMAIN.items()}
    rows, cols = ["first1m", "standard", "program"], ["sub", "new", "exist", "exist_link"]
    rule_in = {k: val[k] for k in ("ten", "bill", "s_new", "s_ex", "s_lnk", "p_new", "p_ex", "p_lnk")}
    rule_cells = {}
    for c in ("sub", "new", "exist"):
        rule_cells[("first1m", c)] = _cell(["ten"], ["bill"])
    rule_cells[("first1m", "exist_link")] = _cell(["ten"])
    for r, p in (("standard", "s"), ("program", "p")):
        rule_cells[(r, "sub")] = _cell(["ten"], ["bill"])
        rule_cells[(r, "new")] = _cell([p + "_new"], ["bill"])
        rule_cells[(r, "exist")] = _cell([p + "_ex"], ["bill"])
        rule_cells[(r, "exist_link")] = _cell([p + "_lnk"])
    cell_in = {k: val[k] for k in Q_GMAIN if k not in ("ten", "bill")}
    cell_cells = {}
    for c in ("sub", "new", "exist"):
        cell_cells[("first1m", c)] = _cell(["first"], ["bill_first"])
    cell_cells[("first1m", "exist_link")] = _cell(["first_lnk"])
    for r, p in (("standard", "s"), ("program", "p")):
        cell_cells[(r, "sub")] = _cell([p + "_sub"], ["bill_" + p + "_sub"])
        cell_cells[(r, "new")] = _cell([p + "_new"], ["bill_" + p + "_new"])
        cell_cells[(r, "exist")] = _cell([p + "_ex"], ["bill_" + p + "_ex"])
        cell_cells[(r, "exist_link")] = _cell([p + "_lnk"])
    gm = {"writer": "Google", "where": "Australia, EEA, Japan, UK, US", "rows": rows, "cols": cols,
          "inputs": rule_in, "cells": rule_cells,
          "layout_cell": {"inputs": cell_in, "cells": cell_cells}}
    gr_in = {k: F(pct_tokens(q)[i]) for k, (p, q, i) in Q_GROW.items()}
    gr = {"writer": "Google", "where": "all remaining markets; Korea and India for the alternative-billing columns",
          "rows": ["first1m", "above"], "cols": ["other", "sub", "other_alt", "sub_alt"], "inputs": gr_in,
          "cells": {("first1m", "other"): _cell(["first"]), ("above", "other"): _cell(["above"]),
                    ("first1m", "sub"): _cell(["sub"]), ("above", "sub"): _cell(["sub"]),
                    ("first1m", "other_alt"): _cell(["first"], cut="cut"),
                    ("above", "other_alt"): _cell(["above"], cut="cut"),
                    ("first1m", "sub_alt"): _cell(["sub"], cut="cut"),
                    ("above", "sub_alt"): _cell(["sub"], cut="cut")}}
    return {"apple_eu": eu, "apple_jp": jp, "google_main": gm, "google_row": gr}


def layout_of(t, layout):
    if layout == "cell" and "layout_cell" in t:
        return dict(t, inputs=t["layout_cell"]["inputs"], cells=t["layout_cell"]["cells"])
    return t


# Printed but not read, and not printed at all. Neither enters any square.
MISSING = [
    {"table": "google_main", "row": "standard", "col": "new_link",
     "reason": "external web link rate on new installs: not printed; the link rate is printed only beside the "
               "existing-install cell"},
    {"table": "google_main", "row": "program", "col": "new_link", "reason": "as for the standard row"},
    {"table": "google_row", "row": "program", "col": "other",
     "reason": "the remaining-markets program row prints '15% or lower', a bound and not a rate"},
    {"table": "google_row", "row": "first1m", "col": "billing_fee",
     "reason": "no billing fee is printed for the remaining markets ('We'll announce billing fee details for "
               "other markets soon.')"},
    {"table": "apple_jp", "row": "standard", "col": "off_store",
     "reason": "Core Technology Commission 5% for distribution outside the App Store: one rate printed with no class "
               "split, and not a payment channel inside the App Store; left out by the design"},
    {"table": "apple_eu", "row": "standard", "col": "off_store",
     "reason": "the Core Technology Commission is not on the page read"},
    {"table": "apple_row", "row": "standard", "col": "iap",
     "reason": "Apple's rates outside the EU and Japan are not on the pages read"},
]

# Set by a printed rule from cells already in a table, and so not added as columns: adding them would
# count printed numbers twice. Neither enters any square; each is listed with the rule that sets it.
DERIVED = [
    {"table": "google_main", "row": "standard and program", "col": "alt_billing (sub, new, exist)",
     "quotes": [["google_blog", "For all other transactions, the rates in the table below applies:"],
                ["google_blog", "For transactions processed via alternative billing or external web links, the "
                                "billing fee does not apply."],
                ["google_levelup", "When qualified for Level Up 10% +billing fee, if applicable"],
                ["google_appsexp", "Standard, for annual earnings $1M+ (USD) 10% +billing fee, if applicable"]],
     "rule": "The post introduces the rate card with 'Regardless of whether you use Google Play's billing system, "
             "alternative billing, or external web links, the service fee starts at 10% ... For all other "
             "transactions, the rates in the table below applies' and states 'For transactions processed via "
             "alternative billing or external web links, the billing fee does not apply.' The program pages print "
             "the same card in text with each service fee marked '+billing fee, if applicable' and no separate "
             "alternative-billing column. So under alternative billing a row pays the card's service fee and no "
             "billing fee: the column is the Google Play billing column with the add-on stripped, which the add-on "
             "knob already reads (setting 'without').",
     "if_added": "its squares against the Google Play billing columns are level zeros made by the billing-fee rule "
                 "(the same 5 on every row) and non-zero in the logs; its squares against the other columns repeat "
                 "the existing level squares. No direction changes; counts would grow."},
]

# Each class line: the rule that puts a developer's transaction in it, and how it is assigned.
ASSIGNED_BY = ("eligibility", "revenue_tranche", "subscription_age", "program")
CLASS_LINES = [
    {"table": "apple_eu", "row": "reduced", "part": "Small Business Program", "assigned_by": "eligibility",
     "page": "apple_sbp", "quote": "Existing developers who made up to 1 million USD in proceeds in the prior "
                                   "calendar year for all their apps, as well as developers new to the App Store, "
                                   "can qualify for the program and the reduced commission."},
    {"table": "apple_eu", "row": "reduced", "part": "Mini Apps and Video Partner programs", "assigned_by": "program",
     "page": "apple_eu", "quote": "from participants in the App Store Small Business Program, Mini Apps Partner "
                                  "Program, or Video Partner Program"},
    {"table": "apple_eu", "row": "reduced", "part": "subscriptions after their first year",
     "assigned_by": "subscription_age", "page": "apple_eu",
     "quote": "and sales of auto-renewable subscriptions after their first year."},
    {"table": "apple_eu", "row": "standard", "part": "everyone else", "assigned_by": "eligibility",
     "page": "apple_sbp", "quote": "If a participating developer surpasses the 1 million USD threshold in the "
                                   "current calendar year, the standard commission rate will apply to future sales."},
    {"table": "apple_jp", "row": "reduced", "part": "Small Business, Mini Apps and Video Partner programs",
     "assigned_by": "program", "page": "apple_jp",
     "quote": "Transactions from participants in the App Store Small Business Program, Mini Apps Partner Program, "
              "and Video Partner Program."},
    {"table": "apple_jp", "row": "reduced", "part": "subscriptions after their first year",
     "assigned_by": "subscription_age", "page": "apple_jp",
     "quote": "Auto-renewable subscriptions after their first year."},
    {"table": "apple_jp", "row": "standard", "part": "everyone else", "assigned_by": "eligibility",
     "page": "apple_jp", "quote": "Excludes transactions from program participants or auto-renewable subscriptions "
                                  "after their first year."},
    {"table": "google_main", "row": "first1m", "part": "first million of annual earnings",
     "assigned_by": "revenue_tranche", "page": "google_help", "quote": "First $1M (USD) of annual earnings"},
    {"table": "google_main", "row": "standard", "part": "annual earnings above one million",
     "assigned_by": "revenue_tranche", "page": "google_appsexp", "quote": "Standard, for annual earnings $1M+ (USD)"},
    {"table": "google_main", "row": "program", "part": "Play Games Level Up",
     "assigned_by": "program", "page": "google_levelup",
     "quote": "games that implement all new Level Up guidelines will qualify for a lower service fee."},
    {"table": "google_main", "row": "program", "part": "Apps Experience",
     "assigned_by": "program", "page": "google_appsexp",
     "quote": "by meeting all the guidelines, your apps qualify for a new program rate card."},
    {"table": "google_row", "row": "first1m", "part": "first million, developers enrolled in the 15% tier",
     "assigned_by": "revenue_tranche", "page": "google_help",
     "condition": "the rows apply to developers enrolled in the 15% service fee tier; within it the tranche of "
                  "annual earnings assigns the row",
     "quote": "Developers enrolled in the 15% service fee tier 15% for the first $1M (USD) revenue earned by the "
              "developer each year"},
    {"table": "google_row", "row": "above", "part": "above one million, developers enrolled in the 15% tier",
     "assigned_by": "revenue_tranche", "page": "google_help",
     "condition": "as for the first-million row",
     "quote": G_TIER},
]

# What each column is. Apple's columns differ only in the payment route. Google's are positions:
# product x install cohort of the buyer x billing route ('any' where the page does not split it).
POSITIONS = {
    "apple_eu": {"iap": ("any", "any", "store billing"), "alt": ("any", "any", "alternative payment"),
                 "link": ("any", "any", "external link")},
    "apple_jp": {"iap": ("any", "any", "store billing"), "alt": ("any", "any", "alternative payment"),
                 "link": ("any", "any", "external link")},
    "google_main": {"sub": ("subscription", "any", "Play billing"), "new": ("other", "new install", "Play billing"),
                    "exist": ("other", "existing install", "Play billing"),
                    "exist_link": ("other", "existing install", "external link")},
    "google_row": {"other": ("other", "any", "Play billing"), "sub": ("subscription", "any", "Play billing"),
                   "other_alt": ("other", "any", "alternative billing (Korea, India)"),
                   "sub_alt": ("subscription", "any", "alternative billing (Korea, India)")},
}
PAIR_KINDS = ("route_only", "product_or_cohort", "mixed")


def pair_kind(table, c1, c2):
    """route_only: the two columns differ in the billing route alone; product_or_cohort: same route, different
    product or install cohort; mixed: both differ."""
    p1, p2 = POSITIONS[table][c1], POSITIONS[table][c2]
    route = p1[2] != p2[2]
    other = p1[:2] != p2[:2]
    return "mixed" if route and other else ("route_only" if route else "product_or_cohort")

# Rules the writer prints that combine numbers across cells (the known answers of PAY1-3).
PRINTED_RULES = [
    {"table": "apple_jp", "page": "apple_jp",
     "quote": "The total charge when using Apple In-App Purchase consists of two primary components—a commission "
              "and a separate payment processing fee"},
    {"table": "apple_jp", "page": "apple_jp", "quote": "(including using alternative payments within apps)"},
    {"table": "google_main", "page": "google_blog",
     "quote": "For transactions processed via alternative billing or external web links, the billing fee does not "
              "apply."},
    {"table": "google_main", "page": "google_blog", "quote": G_TEN},
    {"table": "google_row", "page": "google_help", "quote": Q_GROW["cut"][1]},
    {"table": "google_row", "page": "google_help", "quote": Q_GROW["sub"][1]},
    {"table": "basis", "page": "apple_eu", "quote": "App Store commission rates apply to the price paid by the "
                                                     "customer."},
    {"table": "basis", "page": "apple_jp", "quote": "These rates apply to the price paid by the customer."},
]

# The two program pages print the program rate card in text; it is read against the help page.
PROGRAM_CARDS = {
    "google_levelup": ("When qualified for Level Up 10% +billing fee, if applicable 15% +billing fee, if applicable "
                       "20% +billing fee, if applicable 15% external web link transactions"),
    "google_appsexp": ("When qualified for Apps Experience 10% +billing fee, if applicable 15% +billing fee, if "
                       "applicable 20% +billing fee, if applicable 15% external web link transactions"),
}
PROGRAM_CARD_STANDARD = ("Standard, for annual earnings $1M+ (USD) 10% +billing fee, if applicable 20% +billing fee, "
                         "if applicable 25% +billing fee, if applicable 20% external web link transactions")
PROGRAM_CARD_FIRST = ("First $1M (USD) of annual earnings 10% +billing fee, if applicable 10% +billing fee, if "
                      "applicable 10% +billing fee, if applicable")

# Class definitions on the two Apple pages, compared word for word (PAY1-5).
CLASS_DEFS = {
    "apple_eu": [Q_EU["iap_r"][1][4:], Q_EU["alt_r"][1][4:], Q_EU["lnk_r"][1][4:]],
    "apple_jp": [Q_JP["com_r"][1][4:], Q_JP["lnk_r_sub"][1][4:], Q_JP["lnk_r"][1][4:]],
}
CLASS_MEMBERS = ("Small Business Program", "Mini Apps Partner Program", "Video Partner Program",
                 "auto-renewable subscriptions after their first year")

# ---------------------------------------------------------------- PAY1-4: the registered reading

# Design section 3, square by square: read above the floor, read on the floor, zero, not read.
REGISTERED = {
    ("apple_eu", "standard", "reduced", "iap", "alt"): "read_on_floor",
    ("apple_eu", "standard", "reduced", "iap", "link"): "read_above",
    ("apple_eu", "standard", "reduced", "alt", "link"): "read_above",
    ("apple_jp", "standard", "reduced", "iap", "alt"): "unread",
    ("apple_jp", "standard", "reduced", "iap", "link"): "read_above",
    ("apple_jp", "standard", "reduced", "alt", "link"): "read_above",
    ("google_row", "first1m", "above", "other", "sub"): "read_above",
    ("google_row", "first1m", "above", "other", "other_alt"): "unread",
    ("google_row", "first1m", "above", "other", "sub_alt"): "read_above",
    ("google_row", "first1m", "above", "sub", "other_alt"): "read_above",
    ("google_row", "first1m", "above", "sub", "sub_alt"): "zero",
    ("google_row", "first1m", "above", "other_alt", "sub_alt"): "read_above",
}
for _r1, _r2, _unread in (("first1m", "standard", {("new", "exist_link")}),
                          ("first1m", "program", {("new", "exist_link")}),
                          ("standard", "program", {("new", "exist"), ("new", "exist_link"),
                                                   ("exist", "exist_link")})):
    for _c1, _c2 in itertools.combinations(["sub", "new", "exist", "exist_link"], 2):
        REGISTERED[("google_main", _r1, _r2, _c1, _c2)] = "unread" if (_c1, _c2) in _unread else "read_above"

MAPPING = [  # rule 11c: each state, what it is called, where it maps, what it counts toward
    {"state": "read_above", "called": "read, above the floor", "maps_to":
        "both rivals' point predictions fail on this square (written into detail)", "counts_in": "above_floor",
     "verdict": True},
    {"state": "read_on_floor", "called": "read, on the floor", "maps_to": "no verdict for either rival",
     "counts_in": "printed only", "verdict": None},
    {"state": "zero", "called": "zero", "maps_to": "two prices printed as one (D30 third clause, the constant is 1); "
                                                   "the rivals say zero too, grid A", "counts_in": "zero",
     "verdict": True},
    {"state": "unread", "called": "not read", "maps_to": "no joint verdict; each rival is then read in its own "
                                                         "units by RIVAL_MAPPING",
     "counts_in": "unread", "verdict": None},
]

# Each rival read in its own units (L: the level square on its 4 settings; M: each log square on its 4 settings).
# Both branches look at the rival's own quantity only: a rival fails where its own squares are non-zero on every
# one of its settings and above the floor on every one of them in both layouts; it holds where one of its own
# squares is zero on every one of its settings; anything else carries no verdict for it.
RIVAL_TRANSFORMS = {"L": ("level",), "M": ("log1p", "neglog1m")}
RIVAL_MAPPING = [
    {"outcome": "fails", "when": "L: the level square is non-zero on all 4 add-on x Korea/India settings and above "
                                 "its floor on each of them in both input layouts. M: both log squares are non-zero "
                                 "on all 4 settings and above their floors on each of them in both layouts",
     "verdict": False},
    {"outcome": "holds", "when": "L: the level square is zero on all 4 add-on x Korea/India settings. M: one log "
                                 "square is zero on all 4 settings", "verdict": True},
    {"outcome": "no_verdict", "when": "otherwise (on the floor, or the rival's own square moves between zero and "
                                      "non-zero on a knob, or non-zero but not above the floor)",
     "verdict": None},
]


def rival_scoring(s):
    """L and M on one square, by RIVAL_MAPPING, each in its own units."""
    out = {}
    for rv, trs in RIVAL_TRANSFORMS.items():
        own = [(tr, a, k) for tr in trs for a in ADDON for k in KRIN]
        if all(s["settings"][x] != 0 for x in own) and all(s["mult_set"][(a, k)][tr] > 1 for tr, a, k in own):
            out[rv] = "fails"
        elif any(all(s["settings"][(tr, a, k)] == 0 for a in ADDON for k in KRIN) for tr in trs):
            out[rv] = "holds"
        else:
            out[rv] = "no_verdict"
    return out

# ---------------------------------------------------------------- the object


def cell_value(t, key, addon, krin, inputs=None):
    """A cell in percentage points under a setting."""
    inp = t["inputs"] if inputs is None else inputs
    c = t["cells"][key]
    base = sum((inp[k] for k in c["sum"]), F(0))
    if addon == "with":
        base += sum((inp[k] for k in c["addon"]), F(0))
    if c["cut"] is not None:
        base = base - inp[c["cut"]] if krin == "points" else base * (1 - inp[c["cut"]] / 100)
    return base


def level_square(t, r1, r2, c1, c2, addon, krin, inputs=None):
    v = lambda r, c: cell_value(t, (r, c), addon, krin, inputs)
    return v(r1, c1) + v(r2, c2) - v(r1, c2) - v(r2, c1)


def prod_square(t, r1, r2, c1, c2, tr, addon, krin, inputs=None):
    v = lambda r, c: cell_value(t, (r, c), addon, krin, inputs) / 100
    return square_ratio(v(r1, c1), v(r2, c2), v(r1, c2), v(r2, c1), tr)


def square_sign(t, r1, r2, c1, c2, tr, addon, krin, inputs=None):
    if tr == "level":
        lv = level_square(t, r1, r2, c1, c2, addon, krin, inputs)
        return 0 if lv == 0 else (1 if lv > 0 else -1)
    return sign(prod_square(t, r1, r2, c1, c2, tr, addon, krin, inputs))


def floors(t, r1, r2, c1, c2, addon, krin, transforms=TRANSFORMS):
    """Size and floor of a square in each transform: level in points, logs as |log|."""
    out = {}
    if "level" in transforms:
        base = level_square(t, r1, r2, c1, c2, addon, krin)
        worst = F(0)
        for k in t["inputs"]:
            for s in (1, -1):
                m = dict(t["inputs"])
                m[k] = t["inputs"][k] + s * TICK
                worst = max(worst, abs(level_square(t, r1, r2, c1, c2, addon, krin, m) - base))
        out["level"] = (abs(float(base)), float(worst))
    for tr in ("log1p", "neglog1m"):
        if tr not in transforms:
            continue
        g, fl = floor_of(lambda d: prod_square(t, r1, r2, c1, c2, tr, addon, krin, d), dict(t["inputs"]),
                         {k: TICK for k in t["inputs"]})
        out[tr] = (abs(g), fl)
    return out


def multiple(size, fl):
    if fl > 0:
        return size / fl
    return math.inf if size > 0 else 0.0


def state_of(signs):
    if all(s == 0 for s in signs):
        return "zero"
    if all(s != 0 for s in signs):
        return "read"
    return "unread"


def squares_of(name, t, transforms=TRANSFORMS):
    out = []
    for r1, r2 in itertools.combinations(t["rows"], 2):
        for c1, c2 in itertools.combinations(t["cols"], 2):
            settings = {}
            for tr in transforms:
                for ad in ADDON:
                    for kr in KRIN:
                        settings[(tr, ad, kr)] = square_sign(t, r1, r2, c1, c2, tr, ad, kr)
            st = state_of(list(settings.values()))
            level = {(ad, kr): level_square(t, r1, r2, c1, c2, ad, kr) for ad in ADDON for kr in KRIN}
            mult = {}
            for lay in LAYOUTS:
                tl = layout_of(t, lay)
                fl = floors(tl, r1, r2, c1, c2, REF["addon"], REF["krin"], transforms)
                mult[lay] = {tr: (fl[tr][0], fl[tr][1], multiple(*fl[tr])) for tr in fl}
            worst = {tr: min(mult[lay][tr][2] for lay in LAYOUTS) for tr in transforms}
            # The floor on each add-on x Korea/India setting, smaller of the two layouts: read by each rival in
            # its own units (rival_scoring). The joint state below stays on the reference setting.
            mult_set = {}
            for ad in ADDON:
                for kr in KRIN:
                    per = {tr: [] for tr in transforms}
                    for lay in LAYOUTS:
                        fl_s = floors(layout_of(t, lay), r1, r2, c1, c2, ad, kr, transforms)
                        for tr in transforms:
                            per[tr].append(multiple(*fl_s[tr]))
                    mult_set[(ad, kr)] = {tr: min(v) for tr, v in per.items()}
            above = st == "read" and all(worst[tr] > 1 for tr in transforms)
            full = st if st != "read" else ("read_above" if above else "read_on_floor")
            ref_signs = [settings[(tr, REF["addon"], REF["krin"])] for tr in transforms]
            out.append({"table": name, "r1": r1, "r2": r2, "c1": c1, "c2": c2, "state": full,
                        "settings": settings, "level": level, "mult": mult, "worst": worst, "mult_set": mult_set,
                        "ref_signs": ref_signs,
                        "sign_stable": st == "read" and len({s for s in settings.values()}) == 1})
    return out


def class_jurisdiction(tables, addon="with"):
    """Apple's standard-minus-reduced difference in the EU against Japan, per channel (PAY1-5). The add-on knob
    does not act here: the EU page prints no separate processing fee, so stripping Japan's alone would compare
    different objects. Japan's stripped square is printed beside it."""
    eu, jp = tables["apple_eu"], tables["apple_jp"]
    out = []
    for ch in eu["cols"]:
        cells = {}
        inputs = {}
        for where, t in (("EU", eu), ("Japan", jp)):
            for r in t["rows"]:
                c = t["cells"][(r, ch)]
                ids = [where + ":" + k for k in c["sum"] + (c["addon"] if addon == "with" else [])]
                for k in c["sum"] + c["addon"]:
                    inputs[where + ":" + k] = t["inputs"][k]
                cells[(r, where)] = _cell(ids)
        ct = {"rows": ["standard", "reduced"], "cols": ["EU", "Japan"], "inputs": inputs, "cells": cells}
        signs = [square_sign(ct, "standard", "reduced", "EU", "Japan", tr, "with", "points") for tr in TRANSFORMS]
        st = state_of(signs)
        fl = floors(ct, "standard", "reduced", "EU", "Japan", "with", "points")
        worst = {tr: multiple(*fl[tr]) for tr in TRANSFORMS}
        if st == "read":
            st = "read_above" if all(worst[tr] > 1 for tr in TRANSFORMS) else "read_on_floor"
        strip = None
        if jp["cells"][("standard", ch)]["addon"]:
            sct = copy.deepcopy(ct)
            for r in ("standard", "reduced"):
                sct["cells"][(r, "Japan")] = _cell(["Japan:" + k for k in jp["cells"][(r, ch)]["sum"]])
            strip = {"level": float(level_square(sct, "standard", "reduced", "EU", "Japan", "with", "points")),
                     "signs": [square_sign(sct, "standard", "reduced", "EU", "Japan", tr, "with", "points")
                               for tr in TRANSFORMS]}
        out.append({"channel": ch, "state": st, "signs": signs,
                    "level": float(level_square(ct, "standard", "reduced", "EU", "Japan", "with", "points")),
                    "floors": {tr: (fl[tr][0], fl[tr][1]) for tr in TRANSFORMS}, "worst": worst,
                    "japan_addon_stripped": strip})
    return out


def _rank(vectors):
    """Exact rank over the rationals."""
    m = [list(map(F, v)) for v in vectors]
    rank, col = 0, 0
    ncol = len(m[0]) if m else 0
    while rank < len(m) and col < ncol:
        piv = next((i for i in range(rank, len(m)) if m[i][col] != 0), None)
        if piv is None:
            col += 1
            continue
        m[rank], m[piv] = m[piv], m[rank]
        for i in range(len(m)):
            if i != rank and m[i][col] != 0:
                f = m[i][col] / m[rank][col]
                m[i] = [a - f * b for a, b in zip(m[i], m[rank])]
        rank += 1
        col += 1
    return rank


def independent_squares(tables, squares=None):
    """D22: independent squares from the positions, not the cells. Within each table (r - 1)(c - 1); Apple's two
    jurisdictions also as one 2 x 6 table (the class-by-jurisdiction squares of PAY1-5 included). With squares
    given, the rank of the squares read above the floor in each table."""
    within = {name: (len(t["rows"]) - 1) * (len(t["cols"]) - 1)
              for name, t in tables.items() if name in ("apple_eu", "apple_jp", "google_main", "google_row")}
    out = {"within_tables": dict(within, total=sum(within.values()))}
    apple_joint = len(tables["apple_eu"]["cols"]) + len(tables["apple_jp"]["cols"]) - 1
    out["with_apple_jurisdictions"] = {"apple_both_jurisdictions": apple_joint,
                                       "google_main": within["google_main"], "google_row": within["google_row"],
                                       "total": apple_joint + within["google_main"] + within["google_row"]}
    if squares is not None:
        def rank_where(pred):
            ranks = {}
            for name in within:
                t = tables[name]
                vecs = []
                for s in squares:
                    if s["table"] != name or not pred(s):
                        continue
                    v = [0] * (len(t["rows"]) * len(t["cols"]))
                    ix = lambda r, c: t["rows"].index(r) * len(t["cols"]) + t["cols"].index(c)
                    v[ix(s["r1"], s["c1"])] += 1
                    v[ix(s["r2"], s["c2"])] += 1
                    v[ix(s["r1"], s["c2"])] -= 1
                    v[ix(s["r2"], s["c1"])] -= 1
                    vecs.append(v)
                ranks[name] = _rank(vecs) if vecs else 0
            return dict(ranks, total=sum(ranks.values()))
        out["rank_of_read_above"] = rank_where(lambda s: s["state"] == "read_above")
        if all("rivals" in s for s in squares):
            out["rank_by_rival_outcome"] = {
                "%s_%s" % (rv, o["outcome"]): rank_where(lambda s, rv=rv, o=o: s["rivals"][rv] == o["outcome"])
                for rv in RIVAL_TRANSFORMS for o in RIVAL_MAPPING}
    return out


# ---------------------------------------------------------------- checks on the transcription


def load_texts(raw=RAW):
    texts = {}
    for pid in PAGES:
        p = raw / (pid + ".txt")
        texts[pid] = flat(p.read_text(encoding="utf-8")) if p.exists() else None
    return texts


def check_quotes(texts, quotes=QUOTES, tables=None):
    """PAY1-1: every input's quote is on its saved page as printed, and the percentage it points at is the
    value the table uses."""
    tables = tables or spec_tables()
    bad, rows = [], []
    for tname, qs in quotes.items():
        t = tables[tname]
        used = dict(t["inputs"])
        if "layout_cell" in t:
            used.update(t["layout_cell"]["inputs"])
        for k, (pid, q, idx) in sorted(qs.items()):
            on_page = texts.get(pid) is not None and q in texts[pid]
            toks = pct_tokens(q)
            printed = toks[idx] if idx < len(toks) else None
            merged = MERGED.get((tname, k))
            v = used.get(merged if merged else k)
            agrees = v is not None and printed is not None and F(printed) == v
            rows.append({"table": tname, "input": k, "page": pid, "quote": q, "token": idx, "printed": printed,
                         "value": None if v is None else str(v), "merged_into": merged, "on_page": on_page,
                         "agrees": agrees})
            if not (on_page and agrees):
                bad.append((tname, k, "quote not on page" if not on_page else
                            ("no value to check against" if v is None else "value differs from print")))
    for m in MISSING:
        t = tables.get(m["table"])
        if t and (m["row"], m["col"]) in t["cells"]:
            bad.append((m["table"], m["row"] + "/" + m["col"], "a missing cell sits in the table"))
    for d in DERIVED:
        for pid, q in d["quotes"]:
            if texts.get(pid) is None or q not in texts[pid]:
                bad.append((d["table"], d["col"], "derived-column rule not on page: " + q[:40]))
    return bad, rows


def check_program_cards(texts):
    """The two program pages print the program rate card in text; it is read against the help page's row."""
    out = []
    for pid, q in list(PROGRAM_CARDS.items()) + [("google_appsexp", PROGRAM_CARD_STANDARD),
                                                 ("google_levelup", PROGRAM_CARD_FIRST)]:
        on = texts.get(pid) is not None and q in texts[pid]
        out.append({"page": pid, "quote": q, "on_page": on, "percentages": pct_tokens(q)})
    help_prog = [t for i, t in enumerate(pct_tokens(G_PROG)) if i in (0, 2, 4, 6)]
    help_std = [t for i, t in enumerate(pct_tokens(G_STD)) if i in (0, 2, 4, 6)]
    agree = (all(o["on_page"] for o in out)
             and out[0]["percentages"] == help_prog and out[1]["percentages"] == help_prog
             and out[2]["percentages"] == help_std and out[3]["percentages"] == ["10", "10", "10"])
    return agree, out


def check_class_lines(texts, lines=CLASS_LINES):
    bad = []
    for c in lines:
        ok = (c.get("quote") and texts.get(c["page"]) is not None and c["quote"] in texts[c["page"]]
              and c.get("assigned_by") in ASSIGNED_BY)
        if not ok:
            bad.append((c["table"], c["row"], c["part"]))
    covered = {(c["table"], c["row"]) for c in lines}
    tables = spec_tables()
    for name, t in tables.items():
        for r in t["rows"]:
            if (name, r) not in covered:
                bad.append((name, r, "no class rule"))
    return bad


def layouts_disagree(tables):
    """Every cell of a table printed in two input layouts has the same value in both, on every add-on x
    Korea/India setting. Returns the cells where the two layouts differ (an empty list is agreement)."""
    out = []
    for name, t in sorted(tables.items()):
        if "layout_cell" not in t:
            continue
        tc = layout_of(t, "cell")
        for key in sorted(t["cells"]):
            for ad in ADDON:
                for kr in KRIN:
                    a, b = cell_value(t, key, ad, kr), cell_value(tc, key, ad, kr)
                    if a != b:
                        out.append((name, key, ad, kr, str(a), str(b)))
    return out


def known_answers(tables):
    """PAY1-3: where the writer prints a rule that combines numbers, the level square is zero by arithmetic.
    Google's two rules (b and c) are checked on the help page's cell-by-cell layout, where each printed cell is
    its own input, so they ask whether the numbers printed cell by cell obey the rules the post states; on the
    post's own rule layout they would hold by construction."""
    jp, gr = tables["apple_jp"], tables["google_row"]
    gm = layout_of(tables["google_main"], "cell")
    res = {}
    res["a_apple_japan_iap_vs_alt"] = all(
        level_square(jp, "standard", "reduced", "iap", "alt", ad, "points") == 0 for ad in ADDON)
    same = True
    for r1, r2 in itertools.combinations(gm["rows"], 2):
        for c1, c2 in itertools.combinations(gm["cols"], 2):
            if level_square(gm, r1, r2, c1, c2, "with", "points") != level_square(gm, r1, r2, c1, c2, "without",
                                                                                  "points"):
                same = False
    res["b_google_billing_fee_leaves_level_squares"] = same
    res["c_google_first_million_row_flat"] = len(
        {cell_value(gm, ("first1m", c), "without", "points") for c in gm["cols"]}) == 1
    res["d_korea_india_alt_vs_play_billing_level_zero"] = (
        level_square(gr, "first1m", "above", "other", "other_alt", "with", "points") == 0)
    res["e_subscription_vs_subscription_alt_zero"] = all(
        square_sign(gr, "first1m", "above", "sub", "sub_alt", tr, "with", kr) == 0
        for tr in TRANSFORMS for kr in KRIN)
    return res


# ---------------------------------------------------------------- criteria


def _crit(name, kind, verdict, detail, extra=None):
    c = {"name": name, "kind": kind, "detail": detail, "passed": None if verdict is None else bool(verdict)}
    if verdict is None:
        c["void"] = True
    if extra:
        c.update(extra)
    return c


RIVALS = {
    "rival_premise": "L (level): the commission is a price of the position the transaction sits on (its product, "
                     "the buyer's install cohort, its billing route) plus a term for the developer class; one term "
                     "per column and one per row. M (log): a scalar potential on positions, with a constant offset "
                     "per class.",
    "rival_entailment": "L: f(row, column) = A(row) + phi(column), so every level square is zero. "
                        "M: log(1 + f), or -log(1 - f), is a row term plus a column term, so every log square is zero.",
    "rival_shape": "point prediction (exactly zero)",
}


def build(tables=None, texts=None):
    tables = tables or spec_tables()
    texts = load_texts() if texts is None else texts
    sq = []
    for name in ("apple_eu", "apple_jp", "google_main", "google_row"):
        sq.extend(squares_of(name, tables[name]))
    for s in sq:
        s["pair_kind"] = pair_kind(s["table"], s["c1"], s["c2"]) if s["table"] in POSITIONS else None
        s["rivals"] = rival_scoring(s)
    cj = class_jurisdiction(tables)
    return {"tables": tables, "texts": texts, "squares": sq, "class_jurisdiction": cj,
            "known": known_answers(tables), "d22": independent_squares(tables, sq)}


def rival_counts(sq):
    return {rv: {o["outcome"]: sum(1 for s in sq if s["rivals"][rv] == o["outcome"]) for o in RIVAL_MAPPING}
            for rv in ("L", "M")}


def pair_counts(sq, state="read_above"):
    return {k: sum(1 for s in sq if s["state"] == state and s["pair_kind"] == k) for k in PAIR_KINDS}


def counts(sq):
    out = {}
    for s in sq:
        d = out.setdefault(s["table"], {"read_above": 0, "read_on_floor": 0, "zero": 0, "unread": 0})
        d[s["state"]] += 1
    tot = {k: sum(d[k] for d in out.values()) for k in ("read_above", "read_on_floor", "zero", "unread")}
    out["total"] = tot
    return out


def criteria(rep, manifest=None, quotes=QUOTES, class_lines=CLASS_LINES, class_defs=CLASS_DEFS):
    crits = []
    texts, tables, sq = rep["texts"], rep["tables"], rep["squares"]

    bad, qrows = check_quotes(texts, quotes, tables)
    cards_ok, cards = check_program_cards(texts)
    n_merged = sum(1 for r in qrows if r["merged_into"])
    n_good = sum(1 for r in qrows if r["on_page"] and r["agrees"])
    ldiff = layouts_disagree(tables)
    n_lcells = sum(len(t["cells"]) for t in tables.values() if "layout_cell" in t)
    crits.append(_crit(
        "PAY1-1", "instrument", not bad and cards_ok and not ldiff,
        "Every printed number the station uses is quoted from its saved page as printed, and the percentage the "
        "quote points at equals the value in the table: %d quotes agree of %d (%d inputs over both input layouts, "
        "and %d second class-row quotes on the Japan page, each checked against the input of the class row it "
        "merges into). %d cells are listed missing with a reason and none of them sits in any table; %d column set "
        "by a printed rule from cells already read is listed apart with the rule quoted on its pages. The two "
        "program pages print the program rate card in text and it agrees with the help page's rows (program "
        "10/15/20/15, standard 10/20/25/20, first million 10/10/10): %s. Google's help page (cell by cell) and its "
        "post (two rules) give the same value in each of the %d cells on all four add-on x Korea/India settings: "
        "%s. Failures: %s."
        % (n_good, len(qrows), len(qrows) - n_merged, n_merged, len(MISSING), len(DERIVED),
           "yes" if cards_ok else "no", n_lcells, "yes" if not ldiff else "no, " + str(ldiff), bad or "none")))

    cbad = check_class_lines(texts, class_lines)
    crits.append(_crit(
        "PAY1-2", "premise", not cbad,
        "Every class line carries a quoted rule from a saved page and how the rule assigns it (%s); none of them "
        "lets a developer pick the class on one transaction: %d class lines, failures %s."
        % ("/".join(ASSIGNED_BY), len(class_lines), cbad or "none")))

    known = rep["known"]
    crits.append(_crit(
        "PAY1-3", "known_answer", all(known.values()),
        "Where the writer prints a rule that combines numbers, the result is fixed by arithmetic (a, d and e are "
        "squares; b and c are the post's two rules checked against the help page's cell-by-cell numbers): "
        + "; ".join("%s %s" % (k, "holds" if v else "FAILS") for k, v in sorted(known.items())) + "."))

    have = {(s["table"], s["r1"], s["r2"], s["c1"], s["c2"]): s["state"] for s in sq}
    diff = sorted(k for k in set(have) | set(REGISTERED) if have.get(k) != REGISTERED.get(k))
    cnt = counts(sq)
    every = all(s["state"] in ("read_above", "read_on_floor", "zero", "unread") for s in sq)
    summed = sum(cnt["total"].values()) == len(sq)
    above = [s for s in sq if s["state"] == "read_above"]
    min_mult = min(min(s["worst"].values()) for s in above) if above else None
    rc = rival_counts(sq)
    pk = pair_counts(sq)
    d22 = rep["d22"]
    rr = d22["rank_by_rival_outcome"]
    crits.append(_crit(
        "PAY1-4", "own_reading", every and summed and not diff,
        "Exact squares across 3 transforms x 2 add-on settings x 2 Korea/India readings: %d squares; read above the "
        "floor %d, read on the floor %d, zero %d, not read %d. Every square has one state and the four counts add to "
        "the total. Square by square the states equal the registered table (%d squares): %s. Smallest multiple over "
        "the floor among the squares read above it, worst of three transforms and two input layouts: %s. The squares "
        "read above the floor by the two columns they compare: billing route only %d, product or install cohort on "
        "one route %d, both %d. Independent squares within the tables %d (with Apple's two jurisdictions as one "
        "table %d); the squares read above the floor span %d of the %d. Each rival in its own units, squares "
        "(independent squares they span): L fails on %d (%d), holds on %d (%d), no verdict on %d; M fails on %d "
        "(%d), holds on %d (%d), no verdict on %d. %s %s %s"
        % (len(sq), cnt["total"]["read_above"], cnt["total"]["read_on_floor"], cnt["total"]["zero"],
           cnt["total"]["unread"], len(REGISTERED), "differences " + str(diff) if diff else "no difference",
           "%.2f" % min_mult if min_mult is not None else "none",
           pk["route_only"], pk["product_or_cohort"], pk["mixed"],
           d22["within_tables"]["total"], d22["with_apple_jurisdictions"]["total"],
           d22["rank_of_read_above"]["total"], d22["within_tables"]["total"],
           rc["L"]["fails"], rr["L_fails"]["total"], rc["L"]["holds"], rr["L_holds"]["total"],
           rc["L"]["no_verdict"],
           rc["M"]["fails"], rr["M_fails"]["total"], rc["M"]["holds"], rr["M_holds"]["total"],
           rc["M"]["no_verdict"],
           RIVALS["rival_premise"], RIVALS["rival_entailment"], RIVALS["rival_shape"]),
        extra=dict(RIVALS)))

    cj = rep["class_jurisdiction"]
    eu_def, jp_def = class_defs.get("apple_eu", []), class_defs.get("apple_jp", [])
    defs_on_page = (bool(eu_def) and bool(jp_def)
                    and all(texts.get("apple_eu") and d in texts["apple_eu"] for d in eu_def)
                    and all(texts.get("apple_jp") and d in texts["apple_jp"] for d in jp_def))
    members = {where: [m for m in CLASS_MEMBERS if any(m in d for d in defs)]
               for where, defs in (("apple_eu", eu_def), ("apple_jp", jp_def))}
    verbatim = sorted(eu_def) == sorted(jp_def)
    crits.append(_crit(
        "PAY1-5", "own_reading", defs_on_page and len(cj) == 3 and all(c["state"] for c in cj),
        "Apple's reduced class, EU against Japan: both pages' definitions are on the saved pages (%s); word for word "
        "the same: %s; the same four members on both (%s / %s). Class by jurisdiction squares, add-on included "
        "(printed, not judged): %s. With Japan's processing fee stripped the in-app purchase square is %s."
        % ("yes" if defs_on_page else "no", "yes" if verbatim else "no", len(members["apple_eu"]),
           len(members["apple_jp"]),
           "; ".join("%s %s (level %+.0f)" % (c["channel"], c["state"], c["level"]) for c in cj),
           next(("level %+.0f, signs %s" % (c["japan_addon_stripped"]["level"], c["japan_addon_stripped"]["signs"])
                 for c in cj if c["japan_addon_stripped"]), "n/a"))))

    man = manifest if manifest is not None else (json.loads(MANIFEST.read_text(encoding="utf-8"))
                                                 if MANIFEST.exists() else {})
    pages = man.get("pages", {})
    missing_fields = []
    for pid in PAGES:
        e = pages.get(pid)
        if not e:
            missing_fields.append((pid, "no entry"))
            continue
        for f in ("url", "accessed", "sha256_html", "sha256_text"):
            if not e.get(f):
                missing_fields.append((pid, f))
        if not e.get("version") and not e.get("version_reason"):
            missing_fields.append((pid, "version"))
    crits.append(_crit(
        "PAY1-6", "bookkeeping", not missing_fields and all(m.get("reason") for m in MISSING)
        and all(d.get("rule") for d in DERIVED),
        "Each of %d pages carries its address, access date, version or effective-date sentence (or why there is "
        "none) and the sha256 of the saved page and its text; %d missing cells carry a reason; %d derived column "
        "carries its rule. Gaps: %s."
        % (len(PAGES), len(MISSING), len(DERIVED), missing_fields or "none")))
    return crits


# ---------------------------------------------------------------- snapshot


def transcription():
    """What the station reads from the pages, as written beside them in raw/b152."""
    return {"quotes": {t: {k: {"page": p, "quote": q, "token": i, "merged_into": MERGED.get((t, k))}
                           for k, (p, q, i) in qs.items()} for t, qs in QUOTES.items()},
            "missing": MISSING, "derived": DERIVED, "class_lines": CLASS_LINES, "positions":
                {t: {c: list(v) for c, v in cs.items()} for t, cs in POSITIONS.items()},
            "printed_rules": PRINTED_RULES}


def snapshot(src_dir):
    """Copy saved pages into data/raw/b152, write their texts, the transcription and the manifest."""
    import safe_write  # noqa: E402
    RAW.mkdir(parents=True, exist_ok=True)
    pages = {}
    for pid, meta in PAGES.items():
        src = pathlib.Path(src_dir) / (pid + ".html")
        dst = RAW / (pid + ".html")
        if not dst.exists():
            shutil.copyfile(src, dst)
        raw = dst.read_bytes()
        text = page_text(raw)
        tp = RAW / (pid + ".txt")
        if not tp.exists():
            safe_write.create(tp, "B152 page text " + pid, text, session=SESSION)
        tb = tp.read_bytes()
        pages[pid] = {"url": meta["url"], "accessed": ACCESSED, "html": dst.name, "text": tp.name,
                      "bytes_html": len(raw), "bytes_text": len(tb),
                      "sha256_html": hashlib.sha256(raw).hexdigest(), "sha256_text": hashlib.sha256(tb).hexdigest(),
                      "version": meta.get("version"), "version_reason": meta.get("version_reason"),
                      "how": "page saved as served (HTML) on the access date; text derived by page_text()"}
    man = {"station": "B152", "pages": pages}
    if not MANIFEST.exists():
        safe_write.create(MANIFEST, "B152 manifest", json.dumps(man, indent=2, sort_keys=True) + "\n",
                          session=SESSION)
    tr = transcription()
    if not TRANSCRIPTION.exists():
        safe_write.create(TRANSCRIPTION, "B152 transcription", json.dumps(tr, indent=2, sort_keys=True,
                                                                          ensure_ascii=False) + "\n",
                          session=SESSION)
    return man


def refresh_meta():
    """Rewrite the transcription from the module, and the version fields in the manifest from PAGES. The
    saved pages, their texts and their hashes are not touched."""
    import safe_write  # noqa: E402
    text = json.dumps(transcription(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    safe_write.rewrite(TRANSCRIPTION, "B152 transcription", lambda _old: text, session=SESSION)

    def fix(old):
        man = json.loads(old)
        for pid, meta in PAGES.items():
            e = man["pages"][pid]
            e["version"] = meta.get("version")
            e["version_reason"] = meta.get("version_reason")
        return json.dumps(man, indent=2, sort_keys=True) + "\n"
    safe_write.rewrite(MANIFEST, "B152 manifest version fields", fix, session=SESSION)


# ---------------------------------------------------------------- selftest


def selftest():
    checks = selftest_checks()
    width = max(len(l) for l, _ in checks)
    for l, c in checks:
        print(("PASS  " if c else "FAIL  ") + l.ljust(width))
    bad = [l for l, c in checks if not c]
    print("\nselftest: %d/%d" % (len(checks) - len(bad), len(checks)))
    return 1 if bad else 0


def selftest_checks():
    checks = []

    def ok(label, cond):
        checks.append((label, bool(cond)))

    texts = load_texts()
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rep = build(texts=texts)
    base = {c["name"]: c["passed"] for c in criteria(rep, man)}
    ok("every criterion holds on the saved pages", all(base.values()))

    # Known answer fixture: an additive table reads zero in level, a rank-one table zero in log(1 + f).
    add = {"rows": ["a", "b"], "cols": ["x", "y", "z"], "inputs": {"A": F(5), "B": F(12), "x": F(3), "y": F(9),
                                                                   "z": F(1)},
           "cells": {(r, c): _cell([r.upper(), c]) for r in "ab" for c in "xyz"}}
    add["cells"] = {(r, c): _cell(["A" if r == "a" else "B", c]) for r in ("a", "b") for c in ("x", "y", "z")}
    sq_add = squares_of("fixture", add)
    ok("fixture: an additive table is zero in level on every square",
       all(s["settings"][("level", "with", "points")] == 0 for s in sq_add))
    ok("fixture: and non-zero in log(1 + f), so every square is not read",
       all(s["state"] == "unread" for s in sq_add))
    # A square that the add-on alone decides: flat rows, and a printed add-on on one cell only.
    knob = {"rows": ["a", "b"], "cols": ["x", "y"], "inputs": {"A": F(10), "B": F(20), "k": F(5)},
            "cells": {("a", "x"): _cell(["A"], ["k"]), ("a", "y"): _cell(["A"]),
                      ("b", "x"): _cell(["B"]), ("b", "y"): _cell(["B"])}}
    sk = squares_of("fixture", knob)[0]
    ok("fixture: a square non-zero with the add-on and zero without it is not read", sk["state"] == "unread")

    # PAY1-1: a missing cell filled with zero; a value moved while its quote stays.
    t1 = spec_tables()
    t1["google_main"]["cells"][("standard", "new_link")] = _cell(["s_lnk"])
    t1["google_main"]["inputs"]["s_lnk"] = F(20)
    bad, _ = check_quotes(texts, QUOTES, t1)
    ok("PAY1-1 flips when a missing cell is put in a table", bad)
    t2 = spec_tables()
    t2["apple_eu"]["inputs"]["iap_s"] = F(27)
    bad, _ = check_quotes(texts, QUOTES, t2)
    ok("PAY1-1 flips when a value moves by a point and its quote does not", bad)
    q3 = copy.deepcopy(QUOTES)
    q3["apple_jp"]["com_r_sub"] = (q3["apple_jp"]["com_r_sub"][0], q3["apple_jp"]["com_r_sub"][1], 1)
    bad, _ = check_quotes(texts, q3)
    ok("PAY1-1 flips when Japan's second reduced-class row points at a rate other than the class's (21%)", bad)
    saved = copy.deepcopy(DERIVED)
    DERIVED[0]["quotes"] = DERIVED[0]["quotes"] + [["google_blog", "alternative billing pays 7%"]]
    bad, _ = check_quotes(texts)
    DERIVED[:] = saved
    ok("PAY1-1 flips when a derived column's rule is not on its page", bad)

    # PAY1-2: one class line's quote erased.
    lines = copy.deepcopy(CLASS_LINES)
    lines[0]["quote"] = ""
    ok("PAY1-2 flips when a class line's rule is erased",
       {c["name"]: c["passed"] for c in criteria(rep, man, class_lines=lines)}["PAY1-2"] is False)

    # PAY1-3: Japan's processing fee raised for the standard class only; billing fee on the program row only.
    t3 = spec_tables()
    t3["apple_jp"]["inputs"]["proc6"] = F(6)
    t3["apple_jp"]["cells"][("standard", "iap")] = _cell(["com_s"], ["proc6"])
    ok("PAY1-3 flips when Japan's processing fee is 6 for the standard class only",
       not known_answers(t3)["a_apple_japan_iap_vs_alt"])
    t4 = spec_tables()
    for r in ("first1m", "standard"):
        for c in ("sub", "new", "exist"):
            t4["google_main"]["cells"][(r, c)]["addon"] = []
            t4["google_main"]["layout_cell"]["cells"][(r, c)]["addon"] = []
    ok("PAY1-3 flips when the billing fee is added on the program row only",
       not known_answers(t4)["b_google_billing_fee_leaves_level_squares"])
    # PAY1-3 b and c are read on the help page's cell-by-cell numbers: a help-page cell printing a 6% billing fee,
    # or a first-million cell printing 12%, must flip them, and must also break the two layouts' agreement.
    t4b = spec_tables()
    t4b["google_main"]["layout_cell"]["inputs"]["bill_s_ex"] = F(6)
    ok("PAY1-3 b flips when the help page prints a 6% billing fee in one cell",
       not known_answers(t4b)["b_google_billing_fee_leaves_level_squares"])
    ok("PAY1-1 layout agreement flips when the help page prints a 6% billing fee in one cell",
       bool(layouts_disagree(t4b)))
    t4c = spec_tables()
    t4c["google_main"]["layout_cell"]["inputs"]["first"] = F(12)
    ok("PAY1-3 c flips when the help page prints 12% for the first million",
       not known_answers(t4c)["c_google_first_million_row_flat"])
    ok("PAY1-1 layout agreement flips when the help page prints 12% for the first million",
       bool(layouts_disagree(t4c)) and not layouts_disagree(spec_tables()))

    # PAY1-4: a program cell moved a point; an additive table; a rank-one table.
    t5 = spec_tables()
    t5["google_main"]["inputs"]["p_new"] = F(16)
    t5["google_main"]["layout_cell"]["inputs"]["p_new"] = F(16)
    v5 = {c["name"]: c["passed"] for c in criteria(build(t5, texts), man)}
    ok("PAY1-4 flips when a program-row non-subscription cell moves one point", v5["PAY1-4"] is False)
    t6 = spec_tables()
    g = t6["google_main"]
    A = {"first1m": F(0), "standard": F(10), "program": F(5)}
    phi = {"sub": F(10), "new": F(12), "exist": F(17), "exist_link": F(8)}
    g["inputs"] = {**{"A_" + r: v for r, v in A.items()}, **{"P_" + c: v for c, v in phi.items()}}
    g["cells"] = {(r, c): _cell(["A_" + r, "P_" + c]) for r in g["rows"] for c in g["cols"]}
    g["layout_cell"] = {"inputs": g["inputs"], "cells": g["cells"]}
    sq6 = squares_of("google_main", g)
    ok("PAY1-4 on a level-additive table: every level square is zero",
       all(s["settings"][("level", a, k)] == 0 for s in sq6 for a in ADDON for k in KRIN))
    v6 = {c["name"]: c["passed"] for c in criteria(build(t6, texts), man)}
    ok("PAY1-4 flips on a level-additive table", v6["PAY1-4"] is False)
    t7 = spec_tables()
    g = t7["google_main"]
    # 1 + f = a(row) * b(col): f in points = 100 * (a * b - 1)
    a = {"first1m": F(11, 10), "standard": F(6, 5), "program": F(23, 20)}
    b = {"sub": F(1), "new": F(21, 20), "exist": F(11, 10), "exist_link": F(1)}
    g["inputs"] = {"c_%s_%s" % (r, c): 100 * (a[r] * b[c] - 1) for r in g["rows"] for c in g["cols"]}
    g["cells"] = {(r, c): _cell(["c_%s_%s" % (r, c)]) for r in g["rows"] for c in g["cols"]}
    g["layout_cell"] = {"inputs": g["inputs"], "cells": g["cells"]}
    sq7 = squares_of("google_main", g)
    ok("PAY1-4 on a rank-one table: every log(1 + f) square is zero",
       all(s["settings"][("log1p", a_, k)] == 0 for s in sq7 for a_ in ADDON for k in KRIN))
    v7 = {c["name"]: c["passed"] for c in criteria(build(t7, texts), man)}
    ok("PAY1-4 flips on a rank-one table", v7["PAY1-4"] is False)

    # PAY1-5: Japan's class definition erased.
    defs = copy.deepcopy(CLASS_DEFS)
    defs["apple_jp"] = []
    ok("PAY1-5 flips when Japan's class definition is erased",
       {c["name"]: c["passed"] for c in criteria(rep, man, class_defs=defs)}["PAY1-5"] is False)

    # PAY1-6: one page's access date deleted from a copy of the manifest.
    m2 = copy.deepcopy(man)
    m2["pages"]["apple_jp"]["accessed"] = ""
    ok("PAY1-6 flips when one page's access date is deleted",
       {c["name"]: c["passed"] for c in criteria(rep, m2)}["PAY1-6"] is False)

    # 11c: the mapping prints every state and the not-read states carry no verdict.
    ok("11c: four states mapped, read-on-floor and not-read carry no verdict",
       {m["state"] for m in MAPPING} == {"read_above", "read_on_floor", "zero", "unread"}
       and all(m["verdict"] is None for m in MAPPING if m["state"] in ("read_on_floor", "unread")))
    # 11c per rival: every square read above the floor fails both rivals; on the floor no rival has a verdict.
    ok("11c per rival: both rivals fail on every square read above the floor, no verdict on the floor",
       all(s["rivals"][rv] == "fails" for s in rep["squares"] if s["state"] == "read_above" for rv in "LM")
       and all(s["rivals"][rv] == "no_verdict" for s in rep["squares"] if s["state"] == "read_on_floor"
               for rv in "LM"))
    # A square non-zero and above the floor in one rival's units only: that rival fails, the other does not.
    dm = [s for s in rep["squares"] if s["table"] == "google_row" and (s["c1"], s["c2"]) == ("other", "other_alt")][0]
    ok("rival M fails where only its own units are non-zero above the floor (Korea/India other against other-alt)",
       dm["state"] == "unread" and dm["rivals"]["M"] == "fails")
    # Non-zero in the logs but below the floor: M has no verdict (Google's five equal-number squares).
    eq5 = [s for s in rep["squares"] if s["table"] == "google_main" and s["state"] == "unread"]
    ok("rival M has no verdict on the five equal-number squares (logs below the floor or zero without the fee)",
       len(eq5) == 5 and all(s["rivals"]["M"] == "no_verdict" and s["rivals"]["L"] == "holds" for s in eq5))
    # A square whose level moves between zero and non-zero on the Korea/India knob carries no verdict for L.
    d = [s for s in rep["squares"] if s["table"] == "google_row" and (s["c1"], s["c2"]) == ("other", "other_alt")][0]
    ok("rival L on Korea/India other against other-alt: no verdict (zero in points, not in share)",
       d["rivals"]["L"] == "no_verdict")
    # Pair kinds: Apple's columns differ in route only; Google's subscription against other is product, not route.
    ok("pair kinds: Apple in-app against link is route only; Google subscription against new installs is not",
       pair_kind("apple_eu", "iap", "link") == "route_only"
       and pair_kind("google_main", "sub", "new") == "product_or_cohort"
       and pair_kind("google_main", "new", "exist_link") == "mixed")
    # D22 rank: a single read square in a 2 x 3 table spans one of two.
    ok("D22 rank: exact rank of square vectors", _rank([[1, -1, 0, -1, 1, 0], [2, -2, 0, -2, 2, 0]]) == 1
       and _rank([[1, -1, 0, -1, 1, 0], [0, 1, -1, 0, -1, 1]]) == 2)

    # The shared-input floor: Japan's 21 printed once makes the level floor of in-app against alternative zero.
    jp = spec_tables()["apple_jp"]
    fl = floors(jp, "standard", "reduced", "iap", "alt", "with", "points")
    ok("Japan in-app against alternative: level floor is zero (21 and 5 are printed once)", fl["level"][1] == 0)

    # Coverage: every square read on all twelve settings, every floor measured in all three transforms.
    ok("every square carries a sign on 3 transforms x 2 add-on x 2 Korea/India settings",
       all(set(s["settings"]) == {(tr, a_, k) for tr in ("level", "log1p", "neglog1m") for a_ in ADDON
                                  for k in KRIN} for s in rep["squares"]))
    ok("every square read above the floor has a non-zero floor in all three transforms and both layouts",
       all(set(s["mult"][lay]) == {"level", "log1p", "neglog1m"} and all(v[1] > 0 for v in s["mult"][lay].values())
           for s in rep["squares"] if s["state"] == "read_above" for lay in LAYOUTS))
    # Hand value: Apple EU in-app against link is 26 + 10 - 15 - 15 = 6 points; one tick moves it by one point.
    eu = [s for s in rep["squares"] if s["table"] == "apple_eu" and s["c1"] == "iap" and s["c2"] == "link"][0]
    ok("Apple EU in-app against link: level 6, floor 1", eu["mult"]["rule"]["level"][:2] == (6.0, 1.0))
    return checks


# ---------------------------------------------------------------- mutation run (rule 11f, third clause)
#
# Each mutation breaks one piece of the implementation by replacing a module-level name, runs the self-test
# with its output suppressed, and restores the name. A mutation is caught when the self-test reports a failed
# check or stops on an exception.


def _mutations():
    g = globals()
    orig = {k: g[k] for k in ("squares_of", "floors", "spec_tables", "square_sign", "check_quotes",
                              "known_answers", "rival_scoring", "layouts_disagree")}

    def drop_transform(name, t, transforms=TRANSFORMS):
        return orig["squares_of"](name, t, ("level", "log1p"))

    def level_floor_zero(*a, **k):
        out = orig["floors"](*a, **k)
        if "level" in out:
            out["level"] = (out["level"][0], 0.0)
        return out

    def log_floor_zero(*a, **k):
        out = orig["floors"](*a, **k)
        for tr in ("log1p", "neglog1m"):
            if tr in out:
                out[tr] = (out[tr][0], 0.0)
        return out

    def split_japan_21():
        t = orig["spec_tables"]()
        jp = t["apple_jp"]
        jp["inputs"]["com_s_alt"] = jp["inputs"]["com_s"]
        jp["inputs"]["com_r_alt"] = jp["inputs"]["com_r"]
        jp["cells"][("standard", "alt")] = _cell(["com_s_alt"])
        jp["cells"][("reduced", "alt")] = _cell(["com_r_alt"])
        return t

    def reference_only_sign(t, r1, r2, c1, c2, tr, addon, krin, inputs=None):
        return orig["square_sign"](t, r1, r2, c1, c2, tr, REF["addon"], REF["krin"], inputs)

    def skip_quotes(*a, **k):
        _, rows = orig["check_quotes"](*a, **k)
        return [], rows

    def merged_unchecked(texts, quotes=QUOTES, tables=None):
        bad, rows = orig["check_quotes"](texts, quotes, tables)
        merged = {k for (_t, k) in MERGED}
        return [b for b in bad if b[1] not in merged], rows

    def answers_hardwired(tables):
        return {k: True for k in orig["known_answers"](spec_tables())}

    def answers_on_rule_layout(tables):
        gm = tables["google_main"]
        return orig["known_answers"](dict(tables, google_main=dict(gm, layout_cell={"inputs": gm["inputs"],
                                                                                      "cells": gm["cells"]})))

    def floor_rival_fails(s):
        out = orig["rival_scoring"](s)
        return {rv: "fails" if s["state"] == "read_on_floor" else v for rv, v in out.items()}

    def holds_reference_only(s):
        out = orig["rival_scoring"](s)
        for rv, trs in RIVAL_TRANSFORMS.items():
            if out[rv] != "fails" and any(s["settings"][(tr, REF["addon"], REF["krin"])] == 0 for tr in trs):
                out[rv] = "holds"
        return out

    def fails_by_joint_state(s):
        out = orig["rival_scoring"](s)
        return {rv: ("fails" if s["state"] == "read_above" else ("no_verdict" if v == "fails" else v))
                for rv, v in out.items()}

    unread_verdict = copy.deepcopy(MAPPING)
    for m in unread_verdict:
        if m["state"] == "unread":
            m["verdict"] = True

    return [
        ("a transform dropped", {"squares_of": drop_transform}),
        ("the level floor set to zero", {"floors": level_floor_zero}),
        ("the log floors set to zero", {"floors": log_floor_zero}),
        ("Japan's 21% split into two inputs", {"spec_tables": split_japan_21}),
        ("the state read on the reference setting only", {"square_sign": reference_only_sign}),
        ("the not-read state mapped to a verdict", {"MAPPING": unread_verdict}),
        ("the quote check skipped", {"check_quotes": skip_quotes}),
        ("the known answers written as constants", {"known_answers": answers_hardwired}),
        ("the merged class rows left unchecked", {"check_quotes": merged_unchecked}),
        ("a rival scored as failing on the floor", {"rival_scoring": floor_rival_fails}),
        ("a rival's hold read on the reference setting only", {"rival_scoring": holds_reference_only}),
        ("a rival's failure read from the joint state only", {"rival_scoring": fails_by_joint_state}),
        ("Google's two rules checked on the rule layout", {"known_answers": answers_on_rule_layout}),
        ("the two layouts' agreement written as a constant", {"layouts_disagree": lambda tables: []}),
    ]


def mutation_run():
    import contextlib
    import io
    g = globals()
    saved_derived = copy.deepcopy(DERIVED)
    out = []
    for label, patch in _mutations():
        keep = {k: g[k] for k in patch}
        g.update(patch)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                checks = selftest_checks()
            failed = [l for l, c in checks if not c]
            out.append({"mutation": label, "caught": bool(failed),
                        "how": "self-test check failed: %s" % failed[0] if failed else "not caught"})
        except Exception as e:  # noqa: BLE001
            out.append({"mutation": label, "caught": True, "how": "self-test stopped: %s" % type(e).__name__})
        finally:
            g.update(keep)
            DERIVED[:] = copy.deepcopy(saved_derived)
    return out


# ---------------------------------------------------------------- record


def fmt(x):
    if x == math.inf:
        return "inf"
    return "%.6f" % x


def record(rep, crits, checks=None, mutations=None):
    sq_out = []
    for s in rep["squares"]:
        sq_out.append({
            "table": s["table"], "rows": [s["r1"], s["r2"]], "cols": [s["c1"], s["c2"]], "state": s["state"],
            "level_pp": {"%s,%s" % k: str(v) for k, v in s["level"].items()},
            "signs": {"%s,%s,%s" % k: v for k, v in s["settings"].items()},
            "sign_stable_when_read": s["sign_stable"],
            "floor_at_reference": {lay: {tr: {"size": fmt(v[0]), "floor": fmt(v[1]), "multiple": fmt(v[2])}
                                         for tr, v in s["mult"][lay].items()} for lay in LAYOUTS},
            "worst_multiple": {tr: fmt(v) for tr, v in s["worst"].items()},
            "registered": REGISTERED.get((s["table"], s["r1"], s["r2"], s["c1"], s["c2"])),
            "pair_kind": s["pair_kind"],
            "multiple_by_setting": {"%s,%s" % k: {tr: fmt(v) for tr, v in d.items()}
                                    for k, d in s["mult_set"].items()},
            "rivals": s["rivals"]})
    tables_out = {}
    for name, t in rep["tables"].items():
        cells = {"%s|%s" % k: {"sum": c["sum"], "addon": c["addon"], "cut": c["cut"],
                               "with_pp": str(cell_value(t, k, "with", "points")),
                               "without_pp": str(cell_value(t, k, "without", "points")),
                               "relative_pp": str(cell_value(t, k, "with", "relative"))}
                 for k, c in t["cells"].items()}
        inputs_cell = t["layout_cell"]["inputs"] if "layout_cell" in t else t["inputs"]
        tables_out[name] = {"writer": t["writer"], "where": t["where"], "rows": t["rows"], "cols": t["cols"],
                            "inputs_rule_layout": {k: str(v) for k, v in t["inputs"].items()},
                            "inputs_cell_layout": {k: str(v) for k, v in inputs_cell.items()},
                            "cells": cells}
    _, qrows = check_quotes(rep["texts"], QUOTES, rep["tables"])
    _, cards = check_program_cards(rep["texts"])
    cj = [{"channel": c["channel"], "state": c["state"], "level_pp": "%+.0f" % c["level"], "signs": c["signs"],
           "floors": {tr: {"size": fmt(v[0]), "floor": fmt(v[1])} for tr, v in c["floors"].items()},
           "worst_multiple": {tr: fmt(v) for tr, v in c["worst"].items()},
           "japan_addon_stripped": c["japan_addon_stripped"] and {
               "level_pp": "%+.0f" % c["japan_addon_stripped"]["level"],
               "signs": c["japan_addon_stripped"]["signs"]}} for c in rep["class_jurisdiction"]]
    man = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    return {
        "stage": "B152",
        "config": {
            "transforms": list(TRANSFORMS), "addon": list(ADDON), "korea_india": list(KRIN),
            "input_layouts": list(LAYOUTS), "reference": REF, "tick": "1 percentage point",
            "pages": {pid: {"url": e["url"], "accessed": e["accessed"], "version": e.get("version"),
                            "version_reason": e.get("version_reason")} for pid, e in man.get("pages", {}).items()},
            "printed_once": {
                "apple_jp": "21% covers in-app purchase and alternative payment; 5% processing fee covers both "
                            "classes' in-app cells",
                "google_main rule layout": "one 10% for the first-million row and every subscription cell; one 5% "
                                           "billing fee for nine cells (the blog post's two rules)",
                "google_main cell layout": "the first-million 10% + 5% cell spans three columns; every other "
                                           "printed cell is its own input; the first-million link cell is the blog "
                                           "post's 10%",
                "google_row": "15% for subscriptions printed once for both rows; 4% reduction printed once"},
            "addon_scope": "the add-on knob acts within one table; PAY1-5 compares totals"},
        "criteria": crits,
        "mapping_11c": MAPPING,
        "rival_mapping_11c": RIVAL_MAPPING,
        "rivals": RIVALS,
        "rival_counts": rival_counts(rep["squares"]),
        "pair_kinds_read_above": pair_counts(rep["squares"]),
        "positions": {t: {c: list(v) for c, v in cs.items()} for t, cs in POSITIONS.items()},
        "derived": DERIVED,
        "tables": tables_out,
        "quotes": qrows,
        "program_cards": cards,
        "missing": MISSING,
        "class_lines": CLASS_LINES,
        "printed_rules": PRINTED_RULES,
        "squares": sq_out,
        "counts": counts(rep["squares"]),
        "class_jurisdiction": cj,
        "class_definitions": CLASS_DEFS,
        "known_answers": rep["known"],
        "independent_squares_d22": rep["d22"],
        "layout_disagreements": [list(map(str, d)) for d in layouts_disagree(rep["tables"])],
        "selftest": None if checks is None else [{"check": l, "passed": c} for l, c in checks],
        "mutations": mutations,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--snapshot", default=None)
    ap.add_argument("--refresh-meta", action="store_true")
    ap.add_argument("--mutate", action="store_true")
    ap.add_argument("--out", default=str(REPO / "results" / "b152_appstore_square.json"))
    a = ap.parse_args()
    if a.snapshot:
        man = snapshot(a.snapshot)
        for pid, e in sorted(man["pages"].items()):
            print(pid.ljust(16), e["bytes_html"], e["bytes_text"], e["sha256_html"][:16])
        return 0
    if a.refresh_meta:
        refresh_meta()
        return 0
    if a.selftest:
        return selftest()
    if a.mutate:
        res = mutation_run()
        for r in res:
            print(("CAUGHT  " if r["caught"] else "MISSED  ") + r["mutation"].ljust(52) + r["how"])
        print("\nmutations caught: %d/%d" % (sum(r["caught"] for r in res), len(res)))
        return 0 if all(r["caught"] for r in res) else 1
    rep = build()
    for s in rep["squares"]:
        print("%-12s %-9s %-9s %-11s %-11s %-14s level %-5s worst %s" % (
            s["table"], s["r1"], s["r2"], s["c1"], s["c2"], s["state"], s["level"][("with", "points")],
            " ".join("%s=%s" % (tr, fmt(v)[:6]) for tr, v in s["worst"].items())))
    print(counts(rep["squares"])["total"], rep["d22"])
    for c in rep["class_jurisdiction"]:
        print("class x jurisdiction", c["channel"], c["state"], c["level"], c["signs"],
              {k: fmt(v)[:6] for k, v in c["worst"].items()})
    for m in MAPPING:
        print("11c  %-14s %-22s -> %s  (verdict %s)" % (m["state"], m["called"], m["maps_to"], m["verdict"]))
    assert all(m["verdict"] is None for m in MAPPING if m["state"] in ("read_on_floor", "unread"))
    crits = criteria(rep)
    failed = []
    for c in crits:
        print(("PASS   " if c["passed"] else ("VOID   " if c["passed"] is None else "FAILED[" + c["kind"] + "]: "))
              + c["name"] + "  " + c["detail"][:400])
        if c["passed"] is False:
            failed.append(c["name"])
    # The self-test and the mutation run go into the record, check by check (design, full-print item 8).
    checks = selftest_checks()
    muts = mutation_run()
    print("selftest %d/%d, mutations caught %d/%d" % (sum(c for _, c in checks), len(checks),
                                                       sum(m["caught"] for m in muts), len(muts)))
    if not all(c for _, c in checks) or not all(m["caught"] for m in muts):
        failed.append("selftest or mutation run")
    rec = record(rep, crits, checks, muts)
    text = json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    out = pathlib.Path(a.out)
    import safe_write  # noqa: E402
    if out.exists():
        safe_write.rewrite(out, "B152 record", lambda _old: text, session=SESSION)
    else:
        safe_write.create(out, "B152 record", text, session=SESSION)
    print("wrote " + str(out))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
