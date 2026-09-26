"""Parse the B127 Sotheby's pages on disk into lot rows, and run the depth gate on counts only.

A sale page carries its first 48 lots as LotCard + BidState in the Apollo cache of __NEXT_DATA__;
a lot page carries one LotV2 + BidState and, in its auction, the list of every lot of the sale.
Both are read here. Stage-one pages that were fetched with ?page=N return the first 48 again
(the parameter is ignored by the site); rows are keyed by lotId, so they collapse.

Title grammar, read off the pages: "<colour> <leather> <model> <size> <hardware> Hardware, <year>",
with prefixes such as "Limited Edition" or "So Black". The fields are read by vocabulary, and any
title where the model is not found is printed, not guessed.

The depth gate (`D21`) prints counts only: sales, lots on the site, lots read, and per year the
mix of houses' models and sizes, with how many (model, size, leather, year) cells hold three
sold lots or more. No price is printed by --gate, so the choice of years for stage two cannot
lean on the readings.

Run from the repo root:
    python experiments/b127_parse.py --gate
    python experiments/b127_parse.py --selftest
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b127_fetch as F  # noqa: E402

OUT = F.ROOT / "data" / "b127" / "parsed"

MODELS = [  # longer names first, so "Kelly Pochette" wins over "Kelly"
    "Kelly Pochette", "Kelly Cut", "Kelly Danse", "Kelly Elan", "Kelly To Go", "Kelly Wallet", "Kelly Mini",
    "Mini Kelly", "Birkin", "Kelly", "Constance", "Evelyne", "Picotin", "Lindy", "Herbag", "Garden Party",
    "Bolide", "Jypsiere", "Roulis", "Verrou", "Geta", "In-the-Loop", "Halzan", "24/24", "Haut à Courroies",
    "HAC", "Classic Double Flap", "Classic Flap", "Classic Single Flap", "Double Flap", "Single Flap",
    "Mini Rectangular Flap", "Mini Square Flap", "Mini Rectangular", "Mini Square", "Boy", "2.55", "19 Flap", "22 Bag",
]
# words that may stand between a model and its size, and are not a colour or a leather
VARIANT_WORDS = (r"(?:Sellier|Retourn[ée]|Touch|Verso|Graphie|Relax|Fray|Cargo|Faubourg|Shadow|Cut|Shoulder|"
                 r"Ghillies|Picnic|Colormatic|Tricolor|Bicolor|Casaque|Ombre|So Black|Lakis|Club|HSS|Horseshoe)")
LEATHERS = [
    "Niloticus Crocodile", "Porosus Crocodile", "Himalaya", "Alligator", "Crocodile", "Ostrich", "Lizard",
    "Togo", "Epsom", "Clemence", "Clémence", "Swift", "Box", "Barenia", "Evercolor", "Chevre", "Chèvre",
    "Tadelakt", "Novillo", "Fjord", "Taurillon", "Veau", "Lambskin", "Caviar", "Vache", "Toile", "Canvas",
]
EXOTIC = {"Niloticus Crocodile", "Porosus Crocodile", "Himalaya", "Alligator", "Crocodile", "Ostrich", "Lizard"}
HARDWARE = ["Brushed Gold", "Brushed Palladium", "Rose Gold", "Permabrass", "Ruthenium", "Palladium", "Gold",
            "Silver", "Diamond"]


def parse_title(t: str) -> dict:
    out = {"model": None, "size": None, "leather": None, "hardware": None, "year": None}
    out["variant"] = None
    for mdl in MODELS:
        # up to two variant words may stand between the model and its size ("Kelly Sellier 32",
        # "Birkin Touch 25"); a first version read the size only right after the model and
        # missed 193 of 1,196 Birkin and Kelly sizes in 2021-2023
        m = re.search(r"\b" + re.escape(mdl) + r"\b((?:\s+" + VARIANT_WORDS + r"){0,2})(?:\s+(\d{2})(?:\s?cm)?\b)?", t)
        if m:
            out["model"], out["size"] = mdl, (int(m.group(2)) if m.group(2) else None)
            words = [w for w in re.findall(VARIANT_WORDS, m.group(1) or "") if not re.match(r"Sellier|Retourn", w)]
            out["variant"] = " ".join(words) or None
            break
    for lt in LEATHERS:
        if re.search(r"\b" + re.escape(lt) + r"\b", t):
            out["leather"] = lt
            break
    for hw in HARDWARE:
        if re.search(r"\b" + re.escape(hw) + r"\b(?= Hardware)", t):
            out["hardware"] = hw
            break
    # Kelly comes Sellier (stiff, outside stitching) or Retourné (soft, inside); Birkin has a
    # Sellier variant. The two carry different list prices, so they are two specifications.
    st = re.search(r"\b(Sellier|Retourn[ée])\b", t)
    out["style"] = ("Sellier" if st.group(1) == "Sellier" else "Retourne") if st else None
    y = re.search(r",\s*((?:19|20)\d{2})\s*$", t)
    if y:
        out["year"] = int(y.group(1))
    out["exotic"] = out["leather"] in EXOTIC
    return out


def amount(a) -> float | None:
    try:
        return float(a["amount"]) if a and a.get("amount") not in (None, "") else None
    except (TypeError, ValueError):
        return None


def rows_from(url: str, body: bytes) -> tuple[list[dict], dict | None]:
    """Lot rows on a page, and the sale header."""
    nd = F.next_data(body)
    cache = nd["props"]["pageProps"]["apolloCache"]
    auc = next((v for k, v in cache.items() if k.startswith("Auction:")), None)
    out = []
    for k, v in cache.items():
        if not (k.startswith("LotCard:") or k.startswith("LotV2:")):
            continue
        bs = cache.get((v.get("bidState") or {}).get("__ref", ""), {})
        sold = bs.get("sold") or {}
        price = amount(((sold.get("premiums") or {}).get("finalPriceV2")))
        # a sale page's LotCard carries its auction inline; a lot page's LotV2 points to it
        a = v.get("auction") or {}
        if "__ref" in a:
            a = cache.get(a["__ref"], {})
        cur = a.get("currency") or a.get("currencyV2") or (auc or {}).get("currencyV2")
        est = v.get("estimateV2") or {}
        wd = v.get("withdrawnState") or {}
        if "__ref" in wd:
            wd = cache.get(wd["__ref"], {})
        dates = a.get("dates") or {}
        title = (v.get("title") or "").strip()
        row = {"lot_id": v.get("lotId"), "title": title, "brand": v.get("creatorsDisplayTitle"),
               "lot_no": (v.get("lotNumber") or {}).get("lotDisplayNumber"),
               "sale": ((a.get("slug") or {}).get("year"), (a.get("slug") or {}).get("name")),
               "sale_no": a.get("sapSaleNumber") or v.get("sapAuctionSaleNumber"),
               "location": (a.get("locationV2") or {}).get("name"), "currency": cur,
               "closed": dates.get("startsToClose") or dates.get("closed") or bs.get("closingTime"),
               "withdrawn": wd.get("state") not in (None, "NotAffected"),
               # a lot whose bidding has not closed is neither sold nor unsold; a 2026 sale
               # still open on the fetch day read as 189 unsold before this was read
               "is_closed": bs.get("isClosed"),
               "is_sold": sold.get("isSold"), "result_visible": sold.get("__typename") == "ResultVisible",
               "price_with_premium": price, "bids": bs.get("numberOfBids"),
               "est_low": amount(est.get("lowEstimate")), "est_high": amount(est.get("highEstimate")),
               "page": url}
        row.update(parse_title(title))
        out.append(row)
    head = None
    if auc:
        conn = next((vv for kk, vv in auc.items() if kk.startswith("lotCardsConnection") and isinstance(vv, dict)), {})
        # the auction's own slug, not the URL's: two URLs can serve one sale
        # (2023 handbags-and-accessories-2 serves handbags-and-accessories-4)
        own = auc.get("slug") or {}
        key = ([own.get("year"), own.get("name")] if own.get("name")
               else url.split("/auction/")[1].split("?")[0].split("/")[:2])
        head = {"sale": key, "url": url, "total": conn.get("totalCount"),
                "title": auc.get("title"), "currency": auc.get("currencyV2"),
                "location": (auc.get("locationV2") or {}).get("name")}
    return out, head


def load_all() -> tuple[list[dict], list[dict]]:
    m = F.load_manifest()
    rows, heads = {}, {}
    for url, rec in sorted(m.items()):
        if rec.get("status") != 200 or "/buy/auction/" not in url:
            continue
        r, h = rows_from(url, (F.RAW / rec["file"]).read_bytes())
        for x in r:
            rows.setdefault(x["lot_id"], x)
        if h and "?" not in url and url.count("/") == 7:
            heads[tuple(h["sale"])] = h
    return list(rows.values()), list(heads.values())


def gate() -> int:
    rows, heads = load_all()
    by_year = collections.defaultdict(lambda: {"sales": 0, "site_lots": 0})
    for h in heads:
        y = int(h["sale"][0])
        by_year[y]["sales"] += 1
        by_year[y]["site_lots"] += h["total"] or 0
    print("year  sales  lots on site  lots read  sold  Birkin  Kelly  other Hermes  Chanel  other  exotic")
    for y in sorted(by_year):
        rs = [r for r in rows if r["sale"][0] and int(r["sale"][0]) == y]
        sold = [r for r in rs if r["is_sold"]]
        mdl = collections.Counter(r["model"] for r in sold)
        herm = [r for r in sold if (r["brand"] or "").startswith("Herm")]
        print(f"{y}  {by_year[y]['sales']:>5}  {by_year[y]['site_lots']:>12}  {len(rs):>9}  {len(sold):>4}"
              f"  {mdl['Birkin']:>6}  {mdl['Kelly']:>5}  {len(herm) - mdl['Birkin'] - mdl['Kelly']:>12}"
              f"  {sum(1 for r in sold if (r['brand'] or '').startswith('Chanel')):>6}"
              f"  {sum(1 for r in sold if not (r['brand'] or '').startswith(('Herm', 'Chanel'))):>5}"
              f"  {sum(r['exotic'] for r in sold):>6}")
    cells = collections.Counter((r["model"], r["size"], r["leather"], int(r["sale"][0])) for r in rows
                                if r["is_sold"] and r["model"] in ("Birkin", "Kelly") and r["size"] and r["leather"])
    print("\n(model, size, leather, sale year) cells with 3 or more sold lots, per year:")
    per = collections.Counter(k[3] for k, n in cells.items() if n >= 3)
    print("  ", dict(sorted(per.items())))
    unparsed = [r["title"] for r in rows if (r["brand"] or "").startswith("Herm") and not r["model"]]
    print(f"\nHermès titles with no model read: {len(unparsed)}")
    for t in unparsed[:15]:
        print("   ", t)
    print(f"\nsales: {len(heads)}; lots on the site {sum(h['total'] or 0 for h in heads)}; lots read {len(rows)}"
          f" (stage one reads at most 48 per sale)")
    return 0


def instrument(years: range) -> int:
    """B127-1 on the years given: per sale, lots on the site against rows read; result states;
    currency; how many Hermès and Chanel titles yield a model. Prices are not printed."""
    rows, heads = load_all()
    rows = [r for r in rows if r["sale"][0] and int(r["sale"][0]) in years]
    heads = [h for h in heads if int(h["sale"][0]) in years]
    print("sale  currency  lots on site  rows read  sold  unsold  open  withdrawn  hidden")
    short = 0
    for h in sorted(heads, key=lambda h: h["sale"]):
        rs = [r for r in rows if list(r["sale"]) == list(h["sale"])]
        st = collections.Counter("open" if r["is_closed"] is False else
                                 "hidden" if not r["result_visible"] else ("sold" if r["is_sold"] else "unsold") for r in rs)
        wd = sum(r["withdrawn"] for r in rs)
        flag = "" if len(rs) == (h["total"] or 0) else "  <-- rows != site total"
        short += bool(flag) and st["hidden"] == 0
        print(f"  {'/'.join(h['sale']):<52} {str(h['currency']):>4}  {h['total']:>5}  {len(rs):>5}  {st['sold']:>4}"
              f"  {st['unsold']:>5}  {st['open']:>4}  {wd:>5}  {st['hidden']:>5}{flag}")
    bags = [r for r in rows if (r["brand"] or "").startswith(("Herm", "Chanel"))]
    nomodel = [r for r in bags if not r["model"]]
    print(f"\nHermès and Chanel rows {len(bags)}; model read on {len(bags) - len(nomodel)}; not read {len(nomodel)}")
    print("  most common words in the unread titles:",
          collections.Counter(w for r in nomodel for w in re.findall(r"[A-Z][a-z]+", r["title"])).most_common(20))
    kb = [r for r in rows if r["model"] in ("Birkin", "Kelly")]
    print(f"Birkin/Kelly rows {len(kb)}; with size {sum(bool(r['size']) for r in kb)}; with leather "
          f"{sum(bool(r['leather']) for r in kb)}; with year stamp {sum(bool(r['year']) for r in kb)}; "
          f"Kelly with a style {sum(bool(r['style']) for r in kb if r['model'] == 'Kelly')} of {sum(r['model'] == 'Kelly' for r in kb)}")
    print(f"\nsales whose readable rows fall short of the site total: {short}")
    return 0


def selftest() -> int:
    t1 = parse_title("Gris Meyer Togo Birkin 25 Palladium Hardware, 2024")
    t2 = parse_title("Limited Edition Nata Swift In and Out Kelly 25 Retourné Palladium Hardware, 2021")
    t3 = parse_title("Shiny Noir Niloticus Crocodile Kelly Pochette Gold Hardware, 2019")
    t4 = parse_title("Black Caviar Medium Classic Double Flap Bag Gold Hardware, 2019")
    checks = [
        ("Birkin 25 Togo Palladium 2024", (t1["model"], t1["size"], t1["leather"], t1["hardware"], t1["year"]) == ("Birkin", 25, "Togo", "Palladium", 2024)),
        ("Kelly 25 Swift 2021 through a prefix", (t2["model"], t2["size"], t2["leather"], t2["year"]) == ("Kelly", 25, "Swift", 2021)),
        ("Kelly Pochette is not Kelly; Niloticus is exotic", t3["model"] == "Kelly Pochette" and t3["exotic"]),
        ("Chanel double flap, caviar", (t4["model"], t4["leather"]) == ("Classic Double Flap", "Caviar")),
        ("no year when the title carries none", parse_title("Black Togo Birkin 30")["year"] is None),
        ("Kelly style read: Retourné and Sellier", t2["style"] == "Retourne"
         and parse_title("Black Tadelakt Leather Sellier Kelly 28 Gold Hardware, 2020")["style"] == "Sellier"),
        ("no style word, no style", t1["style"] is None),
        ("size read through Sellier", parse_title("Noir Epsom Kelly Sellier 32 Gold Hardware, 2021")["size"] == 32),
        ("variant read and size kept",
         (lambda x: (x["variant"], x["size"]))(parse_title("Raisin Togo and Alligator Birkin Touch 25 Rose Gold Hardware, 2019")) == ("Touch", 25)),
        ("Chanel Jumbo Double Flap read",
         parse_title("Black Shiny Alligator Jumbo Double Flap Gold Hardware, 2016/17")["model"] == "Double Flap"),
        ("no size word, no size", parse_title("Black Togo Birkin Bag")["size"] is None),
    ]
    for n, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {n}")
    return 0 if all(ok for _, ok in checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--gate", action="store_true")
    g.add_argument("--instrument", action="store_true")
    g.add_argument("--selftest", action="store_true")
    ap.add_argument("--years", default="2021-2026")
    a = ap.parse_args()
    y0, y1 = (int(x) for x in a.years.split("-"))
    if a.instrument:
        return instrument(range(y0, y1 + 1))
    return selftest() if a.selftest else gate()


if __name__ == "__main__":
    sys.exit(main())
