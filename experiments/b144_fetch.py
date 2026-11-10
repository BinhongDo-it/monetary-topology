"""B144 arm B, retrieval: posted prices of one digital item in many account regions.

Fifteen public sources, no key, nothing bought. Every response is cached under
data/raw/b144/ and a cached file is never fetched again, so a run that stops resumes
where it stopped. A payload that does not validate is kept beside the cache with a
.partial suffix and reported; it is not read by anything.

  steam    store.steampowered.com/api/appdetails, filters=price_overview. The list price
           of a title for an account in country cc, in that region's currency.
           Titles: the paid titles of steamspy.com's catalogue pages, which carry the
           publisher of each. Regions: every ISO country code is asked once for eight
           reference titles; codes that return the same currency and the same eight
           prices are one zone, and one code per zone is asked for every title.
  gog      catalog.gog.com/v1/catalog by country. A second store selling many of the same
           titles. Probed and set aside: where the publisher, or a parity term of the
           larger store, keeps a title at one price on both, the second number is the
           first one again. The probes stay on disk; nothing reads them.
  icloud   support.apple.com/en-us/108047: one seller, five storage tiers, every
           country on one page.
  gamepass displaycatalog.mp.microsoft.com: one seller, three subscription tiers, one
           request per market, the same product ids everywhere.
  fx       open.er-api.com (166 currencies against the dollar) and the ECB daily
           reference rates (29), for the one reading that needs a market rate.
  law      eleven pages of statute and official rule on who may buy, hold, sell or rent a
           dwelling on what terms, in six jurisdictions; the list is LAW below.
  us       one country seen from inside, official: the BEA regional price parities by
           metropolitan area (apps.bea.gov/regional/zip/MARPP.zip) and the BLS quarterly
           census of employment and wages, annual averages by industry
           (data.bls.gov/cew/data/api/<year>/a/industry/<code>.csv).
  uk       one hour seen from both sides, official: the price quotes the Office for
           National Statistics collects for its consumer price indices, two months, with
           the glossary of their columns, and the Annual Survey of Hours and Earnings by
           four-digit occupation, for the country and by region, with the table that
           carries each region's own line. Each edition page names its own file; the page
           is read first and the file it names is fetched. Beside them, the government
           pages that state the rates the reading uses (value added tax, national
           insurance, income tax, the wage floor) and the statutory framework that says
           how many children one childminder may care for.

  oecd     the OECD's comparative indicators of the taxation of labour (marginal and
           average tax wedge by household type and earnings level, from 2022) and its
           table of VAT rates.
  cuts     statute and official description of what sovereigns write for services bought
           by households: credits to the buyer, exemptions, reduced rates, and separate
           classes of provider. The list is CUTS below.
  school   statute and official rule on what the right to a place in a public school is
           attached to: the title of a dwelling, an entry in a register, or living there.
           The list is SCHOOL below.
  eurostat the share of people in each tenure class whose housing costs exceed 40 percent of
           their disposable income (ilc_lvho07c), and mean and median income by tenure
           (ilc_di09), from the Union's survey of income and living conditions, since 2023.
  bls      consumer price index components for the United States city average and average
           hourly earnings of production and nonsupervisory employees, monthly, 1990 to 2025,
           from the public interface of the Bureau of Labor Statistics (api.bls.gov, version 1:
           ten years and twenty-five series a request, no key). The series are BLS_SERIES below.
  weights  the Statistics Bureau of Japan's table of weights of the 2020-base consumer price
           index, which prints the total with and without the imputed rent of owner-occupied
           housing; and its summary of the regional price difference index of 2025, with the
           index of every prefecture in ten groups.
  worldbank the World Bank's PPP conversion factors (GDP and private consumption) and official
           exchange rates for 2022, whose ratio is the price level the scalar conversion uses.

The cost of a request is measured, per source and per request size, before any number
of hours is quoted: the script times every request and prints the medians.

Run from the repo root:
    python experiments/b144_fetch.py                 everything that is not yet on disk
    python experiments/b144_fetch.py --only steam    one source
    python experiments/b144_fetch.py --plan          what is on disk and what is missing
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics as st
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b144"
MANIFEST = RAW / "b144_manifest.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research price reader"

ISO = ("AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS "
       "BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE "
       "EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM "
       "HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC "
       "LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA "
       "NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW "
       "SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO "
       "TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW").split()

STEAM_REF = [1245620, 292030, 413150, 367520, 105600, 1174180, 620, 1086940]   # eight titles, seven publishers
STEAM_PAGES = (0, 1)             # steamspy catalogue pages, 1,000 apps each, by owners
STEAM_TITLES = 1000              # paid titles kept, in the catalogue's order
STEAM_CHUNK = 100                # titles per price request
STEAM_SLEEP = 1.7                # seconds between store requests
SPY_SLEEP = 65.0                 # the catalogue endpoint answers once a minute
GOG_PAGES = 42                   # catalogue pages per zone, 48 products each, by sales
GOG_SLEEP = 0.8
GAMEPASS = ("CFQ7TTC0KHS0", "CFQ7TTC0K5DJ", "CFQ7TTC0KGQ8")   # Ultimate, Essential, PC
LAW = {
    "sg_absd.html": "https://www.iras.gov.sg/taxes/stamp-duty/for-property/buying-or-acquiring-property/"
                    "additional-buyer's-stamp-duty-(absd)",
    "cn_deedtax.html": "https://fgk.chinatax.gov.cn/zcfgk/c102416/c5235817/content.html",
    "cn_sh_xinhua.html": "https://www.news.cn/local/20250825/7a7b2ff6bec2494da7244605262d5581/c.html",
    "kr_lease_6_3.html": "https://korea.legal/wiki/%ec%a3%bc%ed%83%9d%ec%9e%84%eb%8c%80%ec%b0%a8%eb%b3%b4%ed%98%b8"
                         "%eb%b2%95-%ec%a0%9c6%ec%a1%b0%ec%9d%983/",
    "kr_lease_7.html": "https://korea.legal/wiki/%ec%a3%bc%ed%83%9d%ec%9e%84%eb%8c%80%ec%b0%a8%eb%b3%b4%ed%98%b8"
                       "%eb%b2%95-%ec%a0%9c7%ec%a1%b0/",
    "kr_localtax_13_2.html": "https://korea.legal/wiki/%ec%a7%80%eb%b0%a9%ec%84%b8%eb%b2%95-%ec%a0%9c13%ec%a1%b0"
                             "%ec%9d%982/",
    "us_1445.html": "https://www.law.cornell.edu/uscode/text/26/1445",
    "us_boe_pub29.pdf": "https://www.boe.ca.gov/proptaxes/pdf/pub29.pdf",
    "de_bgb_573.html": "https://www.gesetze-im-internet.de/bgb/__573.html",
    "de_bgb_558.html": "https://www.gesetze-im-internet.de/bgb/__558.html",
    "jp_shakuchi_28.xml": "https://laws.e-gov.go.jp/api/1/articles;lawNum=%E5%B9%B3%E6%88%90%E4%B8%89%E5%B9%B4"
                          "%E6%B3%95%E5%BE%8B%E7%AC%AC%E4%B9%9D%E5%8D%81%E5%8F%B7;article=28",
}
_ONS_Q = ("/economy/inflationandpriceindices/datasets/"
          "consumerpriceindicescpiandretailpricesindexrpiitemindicesandpricequotes")
_ONS_E = "/employmentandlabourmarket/peopleinwork/earningsandworkinghours/datasets"
UK = {"quotes_2025_04": _ONS_Q + "/pricequotesapril2025",       # the pay period of the earnings survey
      "quotes_2026_08": _ONS_Q + "/pricequotesaugust2026",      # the latest month on the page
      "glossary": _ONS_Q + "/glossaryfebruary2026",
      "glossary_2025": _ONS_Q + "/glossaryfebruary2025onwards",
      "ashe14": _ONS_E + "/occupation4digitsoc2010ashetable14/2025provisional",
      "ashe15": _ONS_E + "/regionbyoccupation4digitsoc2010ashetable15/2025provisional",
      "ashe3": _ONS_E + "/regionbyoccupation2digitsocashetable3/2025provisional",
      "segments_2025_04": _ONS_Q + "/consumptionsegmentindicesapril2025"}   # weights of every segment
UK_RULES = {"vat.html": "https://www.gov.uk/vat-rates",
            "employers_2025_26.html": "https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2025-to-2026",
            "income_tax.html": "https://www.gov.uk/income-tax-rates",
            "minimum_wage.html": "https://www.gov.uk/national-minimum-wage-rates",
            "eyfs.html": "https://www.gov.uk/government/publications/early-years-foundation-stage-framework--2"}
UK_RULES_PDF = ("eyfs_childminders.pdf", "eyfs.html", r"https://assets\.publishing\.service\.gov\.uk/[^\"' ]*"
                                                      r"EYFS_childminders[^\"' ]*\.pdf")
UK_SLEEP = 25.0                  # the host answers 429 to requests a second apart
OECD = {"tw_comp.csv": "https://sdmx.oecd.org/public/rest/data/OECD.CTP.TPS,DSD_TAX_WAGES_COMP@DF_TW_COMP,2.1/all"
                       "?startPeriod=2022&dimensionAtObservation=AllDimensions&format=csvfilewithlabels",
        "vat_rates.xlsx": "https://www.oecd.org/content/dam/oecd/en/topics/policy-sub-issues/"
                          "consumption-tax-trends/vat-gst-rates-ctt-trends.xlsx"}
CUTS = {
    "de_estg_35a.html": "https://www.gesetze-im-internet.de/estg/__35a.html",
    "fr_f12.html": "https://www.service-public.fr/particuliers/vosdroits/F12",
    "se_inkomstskattelag.html": "https://www.riksdagen.se/sv/dokument-och-lagar/dokument/"
                                "svensk-forfattningssamling/inkomstskattelag-19991229_sfs-1999-1229/",
    "uk_tax_free_childcare.html": "https://www.gov.uk/tax-free-childcare",
    "us_tc756.html": "https://www.irs.gov/taxtopics/tc756",
    "eu_vat_annex3.html": "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02006L0112-20250101",
    "sg_fdw_levy.html": "https://www.mom.gov.sg/passes-and-permits/work-permit-for-foreign-domestic-worker/"
                        "foreign-domestic-worker-levy/paying-levy",
    "hk_smw.html": "https://www.labour.gov.hk/eng/news/mwo.htm",
    "hk_smw_guideline.pdf": "https://www.labour.gov.hk/eng/public/SMW_Reference_Guidelines_Eng_34_5.pdf",
    "hk_maw_2025.html": "https://www.info.gov.hk/gia/general/202509/29/P2025092900318.htm",
}
US_YEARS = (2024, 2023)
US_INDUSTRIES = {"10": "total, all industries", "8121": "personal care services",
                 "7225": "restaurants and other eating places", "5617": "services to buildings and dwellings",
                 "2382": "building equipment contractors", "8111": "automotive repair and maintenance",
                 "6244": "child day care services", "8123": "drycleaning and laundry services",
                 "2361": "residential building construction", "4451": "grocery stores"}
SCHOOL = {
    "cn_compulsory_education_law.html": "https://www.gov.cn/guoqing/2021-10/29/content_5647617.htm",
    "sh_city_2026.pdf": "https://www.shanghai.gov.cn/cmsres/fb/fb01b236253b426e982864a3d3231f84/"
                        "8738e07f15cf925d5187c601d8ff5675.pdf",
    "sh_hongkou_2026.pdf": "https://www.shanghai.gov.cn/cmsres/5a/5af6240c44894a4b81205d2ea49c4729/"
                           "ead91a1f3f20c590ca2820376ead2f2b.pdf",
    "sh_huangpu_2026.pdf": "https://www.shanghai.gov.cn/cmsres/3b/3b623963d7cd46d2a5e1c94e010cd281/"
                           "800340cc5da3943c58b4b5806ebeb6af.pdf",
    "bj_huairou_2026.docx": "https://www.beijing.gov.cn/zhengce/zhengcefagui/202604/W020260430484104439820.docx",
    "jp_gakko_rei_1.xml": "https://laws.e-gov.go.jp/api/1/articles;lawNum=%E6%98%AD%E5%92%8C%E4%BA%8C%E5%8D%81"
                          "%E5%85%AB%E5%B9%B4%E6%94%BF%E4%BB%A4%E7%AC%AC%E4%B8%89%E7%99%BE%E5%9B%9B%E5%8D%81"
                          "%E5%8F%B7;article=1",
    "de_bayeug_42.html": "https://www.gesetze-bayern.de/Content/Document/BayEUG-42",
    "en_admissions_code_2021.pdf": "https://assets.publishing.service.gov.uk/media/60ebfeb08fa8f50c76838685/"
                                   "School_admissions_code_2021.pdf",
    "us_ny_edn_3202.html": "https://www.nysenate.gov/legislation/laws/EDN/3202",
    "sg_moe_distance.html": "https://www.moe.gov.sg/primary/p1-registration/distance",
}
EUROSTAT = {name: "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/" + name
            + "?format=SDMX-CSV&startPeriod=2023" for name in ("ilc_lvho07c", "ilc_di09")}
BLS_SERIES = {"CEU0500000008": "average hourly earnings, production and nonsupervisory, total private",
              "CUUR0000SA0": "all items", "CUUR0000SETA01": "new vehicles", "CUUR0000SAA": "apparel",
              "CUUR0000SERA01": "televisions", "CUUR0000SAF11": "food at home",
              "CUUR0000SEFV": "food away from home", "CUUR0000SEGD": "personal care services",
              "CUUR0000SEEB03": "day care and preschool", "CUUR0000SETD": "motor vehicle maintenance and repair",
              "CUUR0000SEHA": "rent of primary residence", "CUUR0000SEHC": "owners' equivalent rent of residences",
              "CUUR0000SEEB01": "college tuition and fees", "CUUR0000SEMD": "hospital and related services",
              "CUUR0000SEMC01": "physicians' services", "CUUR0000SEHG": "water and sewer and trash collection"}
BLS_WINDOWS = ((1990, 1999), (2000, 2009), (2010, 2019), (2020, 2025))
JP_WEIGHTS = "https://www.stat.go.jp/data/cpi/2020/kaisetsu/pdf/5-1.pdf"
JP_REGIONS = "https://www.stat.go.jp/data/kouri/kouzou/pdf/g_2025.pdf"   # regional price difference index, 2025
WORLDBANK = ("PA.NUS.PRVT.PP", "PA.NUS.PPP", "PA.NUS.FCRF")
BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
           "Chrome/126.0 Safari/537.36")
STOP_CODES = (403, 429)          # the host is telling us to slow down: stop, resume later


class Stop(Exception):
    pass


TIMES: dict[str, list[float]] = {}


def fetch(url: str, dest: Path, valid, kind: str, sleep: float, agent: str | None = None) -> bool:
    """One request into the cache. True if the file is on disk and valid afterwards."""
    if dest.exists():
        if valid(dest):
            return True
        n = sum(1 for _ in dest.parent.glob(dest.name + ".partial*"))
        os.replace(dest, dest.with_name(f"{dest.name}.partial{n}"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": agent or UA, "Accept-Language": "en-US,en;q=0.8"})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        if e.code in STOP_CODES:
            raise Stop(f"{kind}: HTTP {e.code} on {url[:90]}") from e
        print(f"  {kind}: HTTP {e.code} on {dest.name}, skipped")
        time.sleep(sleep)
        return False
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"  {kind}: {type(e).__name__} on {dest.name}, skipped")
        time.sleep(sleep)
        return False
    TIMES.setdefault(kind, []).append(time.perf_counter() - t0)
    tmp = dest.with_name(dest.name + ".writing")
    tmp.write_bytes(body)
    if valid(tmp):
        os.replace(tmp, dest)
        ok = True
    else:
        n = sum(1 for _ in dest.parent.glob(dest.name + ".partial*"))
        os.replace(tmp, dest.with_name(f"{dest.name}.partial{n}"))
        print(f"  {kind}: {dest.name} did not validate, kept as .partial{n}")
        ok = False
    time.sleep(sleep)
    return ok


def is_json(p: Path) -> bool:
    try:
        json.loads(p.read_text(encoding="utf-8"))
        return True
    except (ValueError, OSError):
        return False


def steam_valid(ids):
    want = {str(i) for i in ids}

    def check(p: Path) -> bool:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return False
        return isinstance(d, dict) and want <= set(d)
    return check


def spy_valid(p: Path) -> bool:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return False
    return isinstance(d, dict) and len(d) >= 900 and all("publisher" in v for v in list(d.values())[:20])


def gog_valid(p: Path) -> bool:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return False
    return isinstance(d, dict) and isinstance(d.get("products"), list) and "pages" in d


def steam_url(ids, cc):
    return ("https://store.steampowered.com/api/appdetails?appids=" + ",".join(str(i) for i in ids)
            + f"&cc={cc.lower()}&filters=price_overview")


def steam_cell(v):
    """(currency, list price) of one title in one response, or a word for why there is none."""
    if not isinstance(v, dict) or not v.get("success"):
        return "not sold here"
    d = v.get("data")
    if not isinstance(d, dict) or "price_overview" not in d:
        return "no price"
    po = d["price_overview"]
    return po["currency"], po["initial"] / 100.0


def steam_titles():
    """Paid titles of the catalogue pages, in the catalogue's order, with their publishers."""
    out = []
    for pg in STEAM_PAGES:
        p = RAW / f"steamspy_all_p{pg}.json"
        if not p.exists():
            return None
        for a in json.loads(p.read_text(encoding="utf-8")).values():
            try:
                paid = int(a.get("initialprice") or 0) > 0
            except ValueError:
                paid = False
            if paid and str(a.get("publisher") or "").strip():
                out.append({"appid": int(a["appid"]), "name": a["name"], "publisher": a["publisher"].strip(),
                            "developer": (a.get("developer") or "").strip(),
                            "us_list_cents": int(a["initialprice"])})
    return out[:STEAM_TITLES]


def steam_zones():
    """Country codes grouped by what they return for the reference titles. None until all are on disk."""
    sig = {}
    for cc in ISO:
        p = RAW / "steam_zone" / f"{cc}.json"
        if not p.exists():
            return None
        d = json.loads(p.read_text(encoding="utf-8"))
        sig[cc] = tuple(json.dumps(steam_cell(d.get(str(i)))) for i in STEAM_REF)
    zones = {}
    for cc, s in sig.items():
        zones.setdefault(s, []).append(cc)
    return zones


def representative(members):
    """One code per zone: the United States for its own zone, else the first in alphabetical order."""
    return "US" if "US" in members else sorted(members)[0]


def do_steam():
    for i, pg in enumerate(STEAM_PAGES):
        fetch(f"https://steamspy.com/api.php?request=all&page={pg}", RAW / f"steamspy_all_p{pg}.json",
              spy_valid, "steamspy", SPY_SLEEP if i + 1 < len(STEAM_PAGES) else 1.0)
    for cc in ISO:
        fetch(steam_url(STEAM_REF, cc), RAW / "steam_zone" / f"{cc}.json", steam_valid(STEAM_REF),
              "steam, 8 titles", STEAM_SLEEP)
    titles, zones = steam_titles(), steam_zones()
    if titles is None or zones is None:
        print("steam: the catalogue pages or the zone probes are incomplete; run again")
        return
    reps = sorted(representative(m) for s, m in zones.items()
                  if any(c != '"not sold here"' and c != '"no price"' for c in s))
    print(f"steam: {len(titles)} paid titles, {len(zones)} distinct answers over {len(ISO)} codes, "
          f"{len(reps)} zones with a price")
    ids = [t["appid"] for t in titles]
    chunks = [ids[i:i + STEAM_CHUNK] for i in range(0, len(ids), STEAM_CHUNK)]
    for cc in reps:
        for k, ch in enumerate(chunks):
            fetch(steam_url(ch, cc), RAW / "steam_price" / f"{cc}_{k:03d}.json", steam_valid(ch),
                  f"steam, {STEAM_CHUNK} titles", STEAM_SLEEP)


def gog_url(cc, page, cur=None):
    u = (f"https://catalog.gog.com/v1/catalog?limit=48&order=desc:bestselling&productType=in:game"
         f"&page={page}&countryCode={cc}&locale=en-US")
    return u + (f"&currencyCode={cur}" if cur else "")


def gog_sig(p: Path):
    d = json.loads(p.read_text(encoding="utf-8"))
    cells = {}
    for pr in d["products"]:
        m = (pr.get("price") or {}).get("baseMoney") or {}
        cells[str(pr["id"])] = (m.get("currency"), m.get("amount"))
    return cells


GOG_COMMON = 5        # products two codes must share before they can be called one zone
GOG_AGREE = 0.9       # share of the shared products that must carry the same price


def gog_zones():
    """Codes grouped into zones: same currency, and the same price on the products they share.

    Page 1 is each country's own best sellers, so no product is on every page. Two codes are
    therefore compared on what they have in common, and a code joins the first zone whose
    reference prices it agrees with; the zone's reference then grows by that code's products.
    """
    pages = {}
    for cc in ISO:
        p = RAW / "gog_zone" / f"{cc}.json"
        if not p.exists():
            return None
        pages[cc] = gog_sig(p)
    zones = []
    for cc in ISO:
        cells = {i: c for i, c in pages[cc].items() if c[0] and c[1] is not None}
        if not cells:
            continue
        curs = {}
        for c in cells.values():
            curs[c[0]] = curs.get(c[0], 0) + 1
        cur = max(curs, key=curs.get)
        home = None
        for z in zones:
            if z["currency"] != cur:
                continue
            common = set(cells) & set(z["cells"])
            if len(common) >= GOG_COMMON and                     sum(cells[i] == z["cells"][i] for i in common) >= GOG_AGREE * len(common):
                home = z
                break
        if home is None:
            zones.append({"currency": cur, "members": [cc], "cells": dict(cells)})
        else:
            home["members"].append(cc)
            for i, c in cells.items():
                home["cells"].setdefault(i, c)
    return {k: z["members"] for k, z in enumerate(zones)}, {k: z["currency"] for k, z in enumerate(zones)}


def do_gog():
    for cc in ISO:
        fetch(gog_url(cc, 1), RAW / "gog_zone" / f"{cc}.json", gog_valid, "gog, page 1", GOG_SLEEP)
    got = gog_zones()
    if got is None:
        print("gog: the zone probes are incomplete; run again")
        return
    zones, currency = got
    reps = sorted(representative(m) for m in zones.values())
    print(f"gog: {len(zones)} zones over {sum(len(m) for m in zones.values())} codes, "
          f"{len(set(currency.values()))} currencies")
    for cc in reps:
        for page in range(1, GOG_PAGES + 1):
            fetch(gog_url(cc, page), RAW / "gog_price" / f"{cc}_{page:03d}.json", gog_valid,
                  "gog, 48 products", GOG_SLEEP)


def do_icloud():
    fetch("https://support.apple.com/en-us/108047", RAW / "icloud_108047.html",
          lambda p: p.stat().st_size > 50_000 and b"iCloud" in p.read_bytes(), "icloud", 1.0)


def gamepass_valid(p: Path) -> bool:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return False
    return isinstance(d, dict) and isinstance(d.get("Products"), list)


def do_gamepass():
    for cc in ISO:
        url = ("https://displaycatalog.mp.microsoft.com/v7.0/products?bigIds=" + ",".join(GAMEPASS)
               + f"&market={cc}&languages=en-us&fieldsTemplate=browse&MS-CV=DGU1mcuYo0WMMp+F.1")
        fetch(url, RAW / "gamepass" / f"{cc}.json", gamepass_valid, "gamepass, 3 products", 0.4)


def do_law():
    for name, url in LAW.items():
        fetch(url, RAW / "law" / name, lambda p: p.stat().st_size > 1_000, "law", 1.5)


def uk_file_valid(p: Path) -> bool:
    head = p.read_bytes()[:4]
    if p.name.split(".partial")[0].split(".writing")[0].endswith((".zip", ".xlsx", ".xlsm")):
        return head[:2] == b"PK" and p.stat().st_size > 10_000
    return p.stat().st_size > 10_000 and b"<html" not in p.read_bytes()[:400].lower()


def do_uk():
    for slug, path in UK.items():
        page = RAW / "uk" / f"{slug}.edition.json"
        if not fetch("https://www.ons.gov.uk" + path + "/data", page,
                     lambda q: is_json(q) and b"downloads" in q.read_bytes(), "ons page", UK_SLEEP):
            continue
        names = [d.get("file") for d in json.loads(page.read_text(encoding="utf-8")).get("downloads", [])]
        for name in filter(None, names):
            fetch("https://www.ons.gov.uk/file?uri=" + path + "/" + urllib.parse.quote(name),
                  RAW / "uk" / slug / name, uk_file_valid, "ons file", UK_SLEEP)
    for name, url in UK_RULES.items():
        fetch(url, RAW / "uk_rules" / name, lambda q: q.stat().st_size > 20_000, "gov.uk", 2.0)
    name, page, pattern = UK_RULES_PDF
    if (RAW / "uk_rules" / page).exists():
        links = sorted(set(re.findall(pattern, (RAW / "uk_rules" / page).read_text(encoding="utf-8",
                                                                                 errors="replace"))))
        if links:
            fetch(links[0], RAW / "uk_rules" / name,
                  lambda q: q.read_bytes()[:4] == b"%PDF" and q.stat().st_size > 50_000, "gov.uk", 2.0)


def do_oecd():
    fetch(OECD["tw_comp.csv"], RAW / "oecd" / "tw_comp.csv",
          lambda q: q.stat().st_size > 500_000 and b"REF_AREA" in q.read_bytes()[:3000], "oecd", 3.0)
    fetch(OECD["vat_rates.xlsx"], RAW / "oecd" / "vat_rates.xlsx",
          lambda q: q.read_bytes()[:2] == b"PK" and q.stat().st_size > 10_000, "oecd", 3.0)


def do_cuts():
    for name, url in CUTS.items():
        fetch(url, RAW / "law_labour" / name, lambda q: q.stat().st_size > 2_000, "cuts", 2.0,
              agent=BROWSER if "eur-lex" in url else None)        # that host answers a plain agent with nothing


def do_school():
    for name, url in SCHOOL.items():
        fetch(url, RAW / "law_school" / name, lambda q: q.stat().st_size > 2_000, "school", 2.0, agent=BROWSER)


def do_eurostat():
    for name, url in EUROSTAT.items():
        fetch(url, RAW / "eurostat" / f"{name}.csv",
              lambda q: q.read_bytes()[:8] == b"DATAFLOW" and q.stat().st_size > 5_000, "eurostat", 2.0)


def do_bls():
    for start, end in BLS_WINDOWS:
        dest = RAW / "bls" / f"cpi_{start}_{end}.json"
        if dest.exists() and b"REQUEST_SUCCEEDED" in dest.read_bytes():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps({"seriesid": list(BLS_SERIES), "startyear": str(start), "endyear": str(end)}).encode()
        req = urllib.request.Request("https://api.bls.gov/publicAPI/v1/timeseries/data/", data=body,
                                     headers={"Content-Type": "application/json", "User-Agent": UA})
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
        TIMES.setdefault("bls", []).append(time.perf_counter() - t0)
        if b"REQUEST_SUCCEEDED" not in raw:
            n = sum(1 for _ in dest.parent.glob(dest.name + ".partial*"))
            dest.with_name(f"{dest.name}.partial{n}").write_bytes(raw)
            print(f"  bls: {dest.name} did not succeed, kept as .partial{n}")
        else:
            dest.write_bytes(raw)
        time.sleep(3.0)


def do_weights():
    fetch(JP_WEIGHTS, RAW / "weights" / "jp_cpi_2020_weights.pdf",
          lambda q: q.read_bytes()[:4] == b"%PDF" and q.stat().st_size > 50_000, "weights", 2.0)
    fetch(JP_REGIONS, RAW / "weights" / "jp_regional_price_index_2025.pdf",
          lambda q: q.read_bytes()[:4] == b"%PDF" and q.stat().st_size > 50_000, "weights", 2.0)


def do_worldbank():
    for ind in WORLDBANK:
        fetch(f"https://api.worldbank.org/v2/country/all/indicator/{ind}?date=2022&format=json&per_page=20000&source=2",
              RAW / "worldbank" / f"{ind}_2022.json", lambda q: is_json(q) and q.stat().st_size > 20_000, "worldbank", 2.0)


def do_us():
    fetch("https://apps.bea.gov/regional/zip/MARPP.zip", RAW / "us" / "MARPP.zip",
          lambda p: p.read_bytes()[:2] == b"PK" and p.stat().st_size > 50_000, "bea", 1.0)
    for year in US_YEARS:
        for code in US_INDUSTRIES:
            fetch(f"https://data.bls.gov/cew/data/api/{year}/a/industry/{code}.csv",
                  RAW / "us" / f"qcew_{year}_{code}.csv",
                  lambda p: p.read_bytes()[:12] == b'"area_fips",' and p.stat().st_size > 20_000, "qcew", 1.0)


def do_fx():
    fetch("https://open.er-api.com/v6/latest/USD", RAW / "fx_open_er_api.json",
          lambda p: is_json(p) and "rates" in json.loads(p.read_text(encoding="utf-8")), "fx", 1.0)
    fetch("https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml", RAW / "fx_ecb.xml",
          lambda p: b"currency=" in p.read_bytes(), "fx", 1.0)


def plan() -> dict:
    def count(sub, pat="*.json"):
        d = RAW / sub
        return len(list(d.glob(pat))) if d.exists() else 0
    out = {"steamspy pages": sum((RAW / f"steamspy_all_p{pg}.json").exists() for pg in STEAM_PAGES),
           "steam zone probes": count("steam_zone"), "steam price files": count("steam_price"),
           "gog zone probes": count("gog_zone"), "gog price files": count("gog_price"),
           "gamepass markets": count("gamepass"), "us files": count("us", "*"),
           "law pages": count("law", "*"),
           "uk files": len([q for q in (RAW / "uk").rglob("*") if q.is_file() and ".partial" not in q.name
                            and not q.name.endswith(".edition.json")]) if (RAW / "uk").exists() else 0,
           "uk rule pages": count("uk_rules", "*"),
           "oecd files": count("oecd", "*"), "labour law pages": count("law_labour", "*"),
           "school law pages": count("law_school", "*"), "eurostat files": count("eurostat", "*.csv"), "bls files": count("bls"), "weight files": count("weights", "*"), "world bank files": count("worldbank"),
           "icloud page": int((RAW / "icloud_108047.html").exists()),
           "fx files": int((RAW / "fx_open_er_api.json").exists()) + int((RAW / "fx_ecb.xml").exists()),
           "partial files kept": len(list(RAW.rglob("*.partial*"))) if RAW.exists() else 0}
    return out


def write_manifest():
    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    files = sorted(p for p in RAW.rglob("*") if p.is_file() and p != MANIFEST and ".partial" not in p.name
                   and not p.name.endswith(".writing"))
    first = old.get("first_fetch_utc") or time.strftime("%Y-%m-%d", time.gmtime())
    man = {"first_fetch_utc": first, "last_fetch_utc": time.strftime("%Y-%m-%d", time.gmtime()),
           "files": len(files), "bytes": sum(p.stat().st_size for p in files), "on_disk": plan(),
           "settings": {"steam_reference_titles": STEAM_REF, "steamspy_pages": list(STEAM_PAGES),
                        "steam_titles": STEAM_TITLES, "steam_chunk": STEAM_CHUNK, "gog_pages": GOG_PAGES},
           "seconds_per_request": {**old.get("seconds_per_request", {}),
                                   **{k: {"n": len(v), "median": round(st.median(v), 3), "max": round(max(v), 3)}
                                      for k, v in TIMES.items() if v}}}
    MANIFEST.write_text(json.dumps(man, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=("steam", "gog", "icloud", "gamepass", "fx", "us", "law", "uk", "oecd",
                                       "cuts", "school", "eurostat", "bls", "weights", "worldbank"))
    ap.add_argument("--plan", action="store_true")
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    if a.plan:
        for k, v in plan().items():
            print(f"{k:22} {v}")
        return 0
    jobs = {"fx": do_fx, "icloud": do_icloud, "gamepass": do_gamepass, "us": do_us, "law": do_law,
            "uk": do_uk, "oecd": do_oecd, "cuts": do_cuts, "school": do_school, "eurostat": do_eurostat, "bls": do_bls, "weights": do_weights, "worldbank": do_worldbank, "steam": do_steam,
            "gog": do_gog}
    stopped = False
    for name, job in jobs.items():
        if (a.only and a.only != name) or (name == "gog" and a.only != "gog"):
            continue                       # the second store is fetched only when asked for by name
        try:
            job()
        except Stop as e:
            print(f"STOPPED, the host asked for it: {e}. Everything fetched so far is cached; run again later.")
            stopped = True
            break
    write_manifest()
    for k, v in TIMES.items():
        print(f"measured, {k}: {len(v)} requests, median {st.median(v):.2f} s, max {max(v):.2f} s")
    for k, v in plan().items():
        print(f"{k:22} {v}")
    return 1 if stopped else 0


if __name__ == "__main__":
    sys.exit(main())
