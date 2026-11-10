"""B144, a first look at one whole basket inside one country. Prints, writes nothing.

Every item the Office for National Statistics prices by local collection, April 2025: how far
its posted price is one number for the country, and how far it moves with the region. Per item:

  mode      share of valid quotes that carry the commonest price exactly
  between   share of the variance of log price that lies between regions
  london    log of the London median over the median of the other regions
  slope     slope of the regional median log price on the region's median hourly pay

Items the office prices centrally (rents, utilities, fares, cars, tuition, insurance) are not in
this file, so the look covers the locally collected part of the basket and carries no weights.

Run from the repo root:
    python experiments/b144_basket_first_look.py
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict

import numpy as np

from b144_two_prices_of_an_hour import RAW, REGIONS, line, one_file, raw_records, region_lines, sheet

MIN_QUOTES = 60        # an item is looked at when it has this many valid quotes
MIN_REGION = 3         # and a region enters its regional numbers with this many
GROUPS = {"21": "food at home", "22": "restaurants, cafes, takeaways", "31": "alcohol", "32": "tobacco",
          "41": "housing repairs and materials", "43": "furniture, appliances, household goods",
          "44": "household services", "51": "clothing and footwear", "52": "personal goods and services",
          "61": "motoring", "62": "fares and travel", "63": "leisure goods", "64": "leisure services"}


def main() -> int:
    header, rows = raw_records(one_file(RAW / "quotes_2025_04"))
    c = {name: header.index(name) for name in ("ITEM_ID", "ITEM_DESC", "VALIDITY", "PRICE", "REGION", "SHOP_TYPE")}
    items = defaultdict(list)
    for r in rows:
        price = float(r[c["PRICE"]] or 0)
        if str(r[c["VALIDITY"]]).strip().lower() == "true" and price > 0:
            items[(str(r[c["ITEM_ID"]]), str(r[c["ITEM_DESC"]]).strip())].append(
                (price, int(float(r[c["REGION"]] or 0)), int(float(r[c["SHOP_TYPE"]] or 0))))
    pay = region_lines(sheet(one_file(RAW / "ashe3"), "Table 3.6a"))
    level = {rc: math.log(pay[name]["median"]) for rc, (_t, name) in REGIONS.items()}
    out = []
    for (iid, desc), q in items.items():
        if len(q) < MIN_QUOTES:
            continue
        p = np.log([x[0] for x in q])
        reg = np.array([x[1] for x in q])
        mode = Counter(round(x[0], 2) for x in q).most_common(1)[0][1] / len(q)
        cells = {rc: p[reg == rc] for rc in REGIONS if (reg == rc).sum() >= MIN_REGION}
        if len(cells) < 8 or p.var() == 0:
            between = london = slope = math.nan if p.var() else 0.0
        else:
            grand = np.concatenate(list(cells.values()))
            between = sum(len(v) * (v.mean() - grand.mean()) ** 2 for v in cells.values()) / (
                len(grand) * grand.var())
            rest = np.concatenate([v for rc, v in cells.items() if rc != 2])
            london = float(np.median(cells[2]) - np.median(rest)) if 2 in cells else math.nan
            slope = line([level[rc] for rc in cells], [float(np.median(v)) for v in cells.values()])
        out.append({"id": iid, "desc": desc, "n": len(q), "mode": mode, "between": between, "london": london,
                    "slope": slope, "multiple": float(np.mean([x[2] == 1 for x in q]))})
    print(f"{len(items)} items in the file, {len(out)} with {MIN_QUOTES} or more valid quotes")
    bands = Counter("half or more at one price" if o["mode"] >= 0.5 else
                    ("a fifth to a half" if o["mode"] >= 0.2 else "under a fifth") for o in out)
    print("share of quotes at the commonest price:", dict(bands))
    print(f"\n{'group':40} {'items':>5} {'mode':>6} {'between':>8} {'london':>7} {'slope':>6} {'chains':>6}")
    by = defaultdict(list)
    for o in out:
        by[GROUPS.get(o["id"][:2], "other " + o["id"][:2])].append(o)
    for g, v in sorted(by.items(), key=lambda kv: np.nanmedian([o["slope"] for o in kv[1]])):
        med = lambda k: float(np.nanmedian([o[k] for o in v]))            # noqa: E731
        print(f"{g:40} {len(v):5d} {med('mode'):6.2f} {med('between'):8.3f} {med('london'):+7.3f} "
              f"{med('slope'):+6.2f} {med('multiple'):6.2f}")
    ok = [o for o in out if math.isfinite(o["slope"])]
    for title, pick in (("follow the region most", sorted(ok, key=lambda o: -o["slope"])[:14]),
                        ("one number for the country", sorted(out, key=lambda o: -o["mode"])[:14])):
        print(f"\n{title}:")
        for o in pick:
            print(f"  {o['desc'][:34]:34} n {o['n']:4d} mode {o['mode']:.2f} between {o['between']:.3f} "
                  f"london {o['london']:+.3f} slope {o['slope']:+.2f}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
