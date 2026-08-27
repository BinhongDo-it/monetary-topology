# -*- coding: utf-8 -*-
"""C3. Provincial admission cutoffs, probe only.

**The design, so the probe is aimed at something.** Provinces publish a
score-to-rank table each year, so a raw score converts to a within-province
percentile. That conversion is what makes this carrier work: it quotients out
any per-province monotone transformation, and "a point costs more effort in one
province" is exactly such a transformation. Whatever survives the conversion
cannot be explained by it.

**Who claims the scalar.** This matters, because a carrier with no claimant
tests nobody's assertion. Two institutions claim one here. The percentile
method is the officially recommended way to compare across years and across
institutions, which is a claim that rank is the transferable currency. And the
national tiering of universities asserts a single quality ordering that is
executable, because quotas and guidance are set against it.

**The criterion cannot be "is the interaction rank one".** Any real matrix has
full rank, so that reading is decided before the data arrives, the same way
comparing whole area sets across list types was decided by which schemes each
list annotates with. The reading that can come out either way is **rank
reversal between named universities across provinces, and whether a reversal
reproduces in the next year**. Consistent ordering everywhere means the scalar
is realised. Reversals that reproduce mean it is not. Reversals that do not
reproduce are noise and are counted as the third state.

**Two definitional hazards, both dated.** Provinces moved to the new regime in
five waves between 2017 and 2025, and after the move a university no longer has
one cutoff per province: it has one per subject group, so the quantity this
stage needs is undefined there. Batch mergers changed what a line is, at
different times in different provinces. Both push the clean panel earlier, and
both are the reason the first thing this file does is count how many
province-years are usable rather than how many rows exist.

**Probe only.** Nothing is swept until it is known whether the cutoffs and the
rank tables come from one aggregator or from thirty-one provincial sites,
because those two answers differ by an order of magnitude in cost and the
difference is settled by one run of this file.

    python data/fetch_gaokao.py --diagnose
"""
from __future__ import annotations

import argparse
import json
import collections
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "gaokao"

#: Politeness for university sites, which are small and not built for sweeps.
DELAY_PAGE = 1.0

#: A year page carries its table inline or hangs it off an attachment. Both
#: occur on one university: the 2016 page is markup and the 2009-2011 page is a
#: workbook. A sweep that only reads markup records the second as a year with
#: no data, so attachments are followed and their type is recorded.
ATTACHMENT = re.compile(r'href="([^"]+\.(?:xlsx?|pdf|docx?|csv))"', re.I)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

#: Candidates, ordered by how much they would collapse the cost if they answer.
#: The first three would make this one source; the last two are the fallback
#: shape, one provincial authority each, and are here to price that fallback
#: rather than to be used.
CANDIDATES = (
    ("aggregator json",
     "https://static-data.gaokao.cn/www/2.0/schoolprovinceindex/2023/1/1/2.json"),
    ("aggregator json alt",
     "https://static-data.gaokao.cn/www/2.0/school/1/pc_special_score.json"),
    ("aggregator site", "https://www.gaokao.cn/"),
    ("eol data portal", "https://gkcx.eol.cn/"),
    ("eol rank tables", "https://www.eol.cn/e_html/gk/gkfsd/index.shtml"),
    ("ministry platform", "https://gaokao.chsi.com.cn/"),
    ("province: Zhejiang", "https://www.zjzs.net/"),
    ("province: Jiangsu", "https://www.jseea.cn/"),
    ("province: Henan", "http://www.haeea.cn/"),
)


CHARSET = re.compile(rb'charset=["\']?([\w-]+)', re.I)


def decode_page(body: bytes) -> str:
    """Decode a page by what it declares rather than by assumption.

    **Both encodings are in play here.** The portal's archive from these years
    declares `gb2312` and the education site declares `utf-8`, so hardcoding
    either one silently destroys every Chinese string in half the corpus while
    leaving the markup intact. Every count over tags, rows and digits keeps
    working, and only the checks that read Chinese fail, which is to say the
    checks fail at the moment the diagnostics look cleanest.

    `gb18030` rather than `gb2312`: it is a superset, so a page that declares
    the narrower one still decodes, and a character outside it does not become a
    replacement.
    """
    m = CHARSET.search(body[:4000])
    declared = (m.group(1).decode("ascii", "replace").lower() if m else "")
    order = ([declared] if declared else []) + ["gb18030", "utf-8"]
    seen = set()
    for enc in order:
        enc = {"gb2312": "gb18030", "gbk": "gb18030"}.get(enc, enc)
        if enc in seen:
            continue
        seen.add(enc)
        try:
            text = body.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
        return text
    return body.decode("utf-8", "replace")


def probe(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://www.gaokao.cn/",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as fh:
            return fh.status, fh.read(), ""
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()[:400], (exc.reason or "")[:40]
    except Exception as exc:                                  # noqa: BLE001
        return 0, b"", str(exc)[:70]


def describe(blob: bytes) -> str:
    if not blob:
        return "(empty)"
    head = blob[:200]
    try:
        doc = json.loads(blob.decode("utf-8"))
    except Exception:                                         # noqa: BLE001
        text = head.decode("utf-8", "replace").replace("\n", " ")
        return "%d B, not json, starts %r" % (len(blob), text[:90])
    if isinstance(doc, dict):
        return "%d B, json dict, keys %s" % (len(blob), sorted(doc)[:8])
    return "%d B, json list of %d" % (len(blob), len(doc))


INDEX = "https://www.eol.cn/e_html/gk/gkfsd/index.shtml"
ARTICLE = re.compile(r'href="(https://gaokao\.eol\.cn/[a-z_]+/dongtai/\d{6}/t\d{8}_\d+\.shtml)"'
                     r'[^>]*>([^<]{2,60})</a>')


def sample() -> int:
    """Fetch the index, then two of the articles it links, and report the form.

    **The form is the whole question.** A rank table published as an HTML table
    costs a parser; the same table published as an image or a downloadable
    workbook costs an order of magnitude more and changes whether this carrier
    is worth opening at all. Guessing which it is from the index page is not
    possible, and it is one request to find out.
    """
    status, blob, note = probe(INDEX)
    if status != 200:
        print("index %s %s" % (status, note))
        return 1
    html = blob.decode("utf-8", "replace")
    links = ARTICLE.findall(html)
    print("index             %d bytes, %d article links" % (len(blob), len(links)))

    provinces = {}
    for url, label in links:
        prov = url.split("gaokao.eol.cn/")[1].split("/")[0]
        provinces.setdefault(prov, []).append((url, label.strip()))
    print("provinces linked  %d: %s" % (len(provinces), ", ".join(sorted(provinces))))

    OUT.mkdir(parents=True, exist_ok=True)
    for prov in sorted(provinces)[:2]:
        url, label = provinces[prov][0]
        st, body, nt = probe(url)
        print("\n%-16s %s\n  %s" % (prov, label[:58], url))
        if st != 200:
            print("  %s %s" % (st, nt))
            continue
        page = body.decode("utf-8", "replace")
        dest = OUT / ("_article_%s.html" % prov)
        dest.write_bytes(body)
        tables = re.findall(r"<table", page, re.I)
        rows = re.findall(r"<tr", page, re.I)
        imgs = re.findall(r'<img[^>]+src="([^"]+)"', page, re.I)
        atts = re.findall(r'href="([^"]+\.(?:xlsx?|pdf|docx?))"', page, re.I)
        # A rank table row is a score with a count beside it.
        numeric = re.findall(r"<td[^>]*>\s*(\d{2,6})\s*</td>", page)
        print("  %d bytes, %d <table>, %d <tr>, %d <img>, %d attachment(s)"
              % (len(body), len(tables), len(rows), len(imgs), len(atts)))
        print("  numeric cells: %d" % len(numeric))
        if numeric[:12]:
            print("  first numeric cells: %s" % " ".join(numeric[:12]))
        for a in atts[:3]:
            print("  attachment: %s" % a[:100])
        verdict = ("HTML table, parseable" if len(rows) > 50 and len(numeric) > 100
                   else "attachment, needs a second fetch" if atts
                   else "image or script-rendered, expensive"
                   if len(imgs) > 2 else "unclear, read the file on disk")
        print("  --> %s" % verdict)
        print("  wrote %s" % dest)
        time.sleep(0.5)

    print("\n--- what is still open ---")
    print("This index carries rank tables only. The other half of the panel is a "
          "cutoff per university per province per year, which is a different "
          "source and is not priced by this run.")
    return 0


#: Provincial authorities that answered a plain request. Only their front pages
#: are named. Deeper paths are found by following links from those pages rather
#: than guessed, because a guessed path that happens to answer is how a probe
#: reports a source it has not actually found.
BUREAUS = (
    ("Jiangsu", "https://www.jseea.cn/"),
    ("Henan", "http://www.haeea.cn/"),
    ("Shandong", "http://www.sdzk.cn/"),
    ("Hebei", "http://www.hebeea.edu.cn/"),
    ("Hunan", "https://jyt.hunan.gov.cn/"),
)

WANT = re.compile(r"投档|录取分数|分数线|一分一段|分数段|位次|投档线")
LINK = re.compile(r'<a[^>]+href="([^"#]+)"[^>]*>([^<]{2,60})</a>', re.I)


def form_of(body: bytes, page: str) -> str:
    """Say what shape a page's payload is in, from the page rather than a guess."""
    rows = len(re.findall(r"<tr", page, re.I))
    cells = len(re.findall(r"<td[^>]*>\s*[\d.]{1,7}\s*</td>", page))
    atts = re.findall(r'href="([^"]+\.(?:xlsx?|pdf|docx?|csv))"', page, re.I)
    cms_imgs = re.findall(r'(W0\d{16,}\.(?:png|jpe?g))', page)
    bits = ["%d B" % len(body), "%d <tr>" % rows, "%d numeric <td>" % cells,
            "%d attachment" % len(atts), "%d CMS image" % len(cms_imgs)]
    if rows > 40 and cells > 80:
        verdict = "HTML TABLE, parseable"
    elif atts:
        verdict = "ATTACHMENT: %s" % atts[0][:80]
    elif cms_imgs:
        verdict = "CMS IMAGE, needs OCR"
    else:
        verdict = "neither, read the file"
    return "  ".join(bits) + "\n      --> " + verdict


def cutoffs() -> int:
    """Price the other half of the panel: a cutoff, ideally with its rank.

    The rank tables on the aggregator are published as images, and the quantity
    this stage needs from them is a rank. **But many authorities print the rank
    directly beside the cutoff**, because the rank method is the officially
    recommended one, so the table that carries cutoffs may already carry the
    coordinate and make the rank tables unnecessary. That is what this checks,
    and it checks it by following links off front pages rather than by guessing
    deep paths.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    for name, home in BUREAUS:
        st, blob, note = probe(home, timeout=15)
        print("\n%-10s %-38s %s" % (name, home, st if st else note))
        if st != 200 or not blob:
            continue
        page = blob.decode("utf-8", "replace")
        found = [(u, x.strip()) for u, x in LINK.findall(page) if WANT.search(x)]
        print("  relevant links on the front page: %d" % len(found))
        for u, x in found[:4]:
            print("    %-30s %s" % (x[:30], u[:74]))
        if not found:
            continue
        href, label = found[0]
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = home.rstrip("/") + href
        elif not href.startswith("http"):
            href = home.rstrip("/") + "/" + href.lstrip("./")
        st2, body2, note2 = probe(href, timeout=15)
        print("  follow: %s\n    %s" % (label[:56], href[:100]))
        if st2 != 200 or not body2:
            print("    %s %s" % (st2, note2))
            continue
        inner = body2.decode("utf-8", "replace")
        print("    " + form_of(body2, inner))
        dest = OUT / ("_cutoff_%s.html" % name)
        dest.write_bytes(body2)
        print("      wrote %s" % dest)
        time.sleep(0.6)

    print("\n--- the question this run answers ---")
    print("Does a table that carries a cutoff also carry the rank beside it. If "
          "it does, the image-published rank tables are not needed and this "
          "carrier costs one parser per source rather than an OCR pipeline "
          "whose errors land on the exact column the design depends on.")
    return 0


#: Channel indexes on the aggregator. `gkfsd` is the rank-table channel already
#: probed; the others are guesses at sibling channels and are here to be tried
#: and reported, not to be swept. A channel that answers is then read for the
#: years its links actually cover, which is the question this run exists for.
CHANNELS = (
    ("rank tables", "https://www.eol.cn/e_html/gk/gkfsd/index.shtml"),
    ("score lines", "https://www.eol.cn/e_html/gk/fsx/index.shtml"),
    ("admission lines", "https://www.eol.cn/e_html/gk/lqfsx/index.shtml"),
    ("province channel", "https://gaokao.eol.cn/he_nan/"),
    ("province dongtai", "https://gaokao.eol.cn/he_nan/dongtai/"),
)

DATED = re.compile(r'href="(https?://gaokao\.eol\.cn/[a-z_]+/[a-z_]+/(\d{4})(\d{2})/[^"]+\.shtml)"'
                   r'[^>]*>([^<]{2,70})</a>')


def history() -> int:
    """Can the pre-reform years be reached, and in what form.

    The design needs one cutoff per university per province per year, in the
    era when a university had exactly one, and it needs no rank and no
    normalisation because the criterion compares orderings inside a province.
    So the only open question is whether tables from roughly 2013 to 2016 are
    still served, and whether they are markup, attachments or images.

    Nothing here is guessed past the channel index. A channel that answers is
    read for the years its own links carry.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    hits = []
    for label, url in CHANNELS:
        st, blob, note = probe(url, timeout=18)
        if st != 200 or not blob:
            print("  %-18s %s %s" % (label, st or "", note))
            continue
        page = blob.decode("utf-8", "replace")
        dated = DATED.findall(page)
        years = collections.Counter(y for _u, y, _m, _x in dated)
        print("  %-18s %6d B  %3d dated links  years %s"
              % (label, len(blob), len(dated),
                 dict(sorted(years.items())) or "none"))
        hits.extend(dated)
        time.sleep(0.4)

    if not hits:
        print("\n  No dated article links found on any channel index. The "
              "archive is not reachable by walking these pages.")
        return 1

    years = collections.Counter(y for _u, y, _m, _x in hits)
    old = sorted([h for h in hits if h[1] < "2018"], key=lambda h: h[1])
    print("\n  year coverage across every channel: %s" % dict(sorted(years.items())))
    print("  links dated before 2018: %d" % len(old))

    for url, y, m, label in old[:2]:
        st, body, note = probe(url, timeout=18)
        print("\n  %s-%s  %s\n    %s" % (y, m, label[:56], url[:100]))
        if st != 200 or not body:
            print("    %s %s" % (st, note))
            continue
        page = body.decode("utf-8", "replace")
        print("    " + form_of(body, page))
        dest = OUT / ("_hist_%s%s.html" % (y, m))
        dest.write_bytes(body)
        print("      wrote %s" % dest)
        time.sleep(0.6)

    print("\n--- what this decides ---")
    print("Pre-reform years reachable and in markup: this carrier is one parser "
          "and a bounded fetch. Reachable but as attachments: add one extraction "
          "step, still bounded. Not reachable: the archive has to come from the "
          "provincial authorities one at a time, and two of the five tried "
          "already refused a plain connection, which prices that route.")
    return 0


#: Universities whose own admissions site serves the archive to a plain
#: request. Verified one at a time and added as they are; a university whose
#: index renders client-side is not listed, because a placeholder here would be
#: swept and recorded as a university with no history.
#:
#: `index` is the page listing one link per year. `slug` names the directory.
UNIVERSITIES = (
    {"slug": "tsinghua", "name": "Tsinghua University",
     "index": "https://www.join-tsinghua.edu.cn/xxgk/lnlqfsx.htm",
     "verified": "2026-08-27, archive reaches 2009, 31 provinces as text"},
)

#: The window where a university has exactly one cutoff per province per track.
#: Later years are excluded because the subject-group reform makes the quantity
#: undefined, and that exclusion is the reason this stage looks backwards at
#: all rather than a convenience.
PRE_REFORM = range(2009, 2017)

#: The year is read from the anchor's `title` attribute, not its text. The
#: text is wrapped in nested `div` elements on this template, so any pattern
#: that walks the anchor's characters stops at the first tag and matches
#: nothing, which is what the first version of this did.
#:
#: One href can carry several years: the 2011-2013 page is one document
#: covering three, so the mapping is year to url and not url to year.
YEARLINK = re.compile(r'<a\b[^>]*href="([^"#]+)"[^>]*title="([^"]*)"', re.I)


def universities() -> int:
    """Pull each listed university's year pages, raw, for a parser to be
    written against.

    The parser is not written here on purpose. Three carriers in this project
    have now had a parser written against a description of a payload and
    returned zero rows while every transport check passed, so the raw pages are
    kept and the parser is written against them.
    """
    print("handshake         none needed; these are plain public pages")
    for uni in UNIVERSITIES:
        root = OUT / "univ" / uni["slug"]
        root.mkdir(parents=True, exist_ok=True)
        print("\n%s\n  index %s" % (uni["name"], uni["index"]))
        st, blob, note = probe(uni["index"], timeout=25)
        if st != 200 or not blob:
            print("  %s %s" % (st, note))
            continue
        (root / "_index.html").write_bytes(blob)
        page = blob.decode("utf-8", "replace")
        found = {}
        for href, title in YEARLINK.findall(page):
            years = [int(y) for y in re.findall(r"20[0-2]\d", title)]
            years = [y for y in years if y in PRE_REFORM]
            if not years:
                continue
            url = urllib.parse.urljoin(uni["index"], href)
            # A title naming a range covers every year between its endpoints.
            span = range(min(years), max(years) + 1) if len(years) > 1 else years
            for y in span:
                if y in PRE_REFORM:
                    found.setdefault(y, (url, title))
        print("  pre-reform years linked: %s" % (sorted(found) or "none"))
        if not found:
            print("  The index answered but no year in %d-%d was linked from it. "
                  "Read _index.html before changing the pattern: a loosened "
                  "regex that starts matching is how a sweep records the wrong "
                  "pages." % (PRE_REFORM[0], PRE_REFORM[-1]))
            continue

        seen_urls = {}
        for y in sorted(found):
            url, title = found[y]
            if url in seen_urls:
                print("    %d  covered by the %s page" % (y, seen_urls[url]))
                continue
            dest = root / ("%d.html" % y)
            if dest.exists():
                seen_urls[url] = y
                have_att = list(root.glob("%d.[xpdc]*" % y))
                print("    %d  have%s" % (y, "" if have_att else
                                          "  (page only, attachments not checked)"))
                continue
            st, body, note = probe(url, timeout=25)
            if st != 200 or not body:
                print("    %d  %s %s" % (y, st, note))
                time.sleep(DELAY_PAGE)
                continue
            dest.write_bytes(body)
            seen_urls[url] = y
            page = body.decode("utf-8", "replace")
            rows = len(re.findall(r"<tr", page, re.I))
            cells = len(re.findall(r"<td[^>]*>\s*\d{2,3}(?:\.\d)?\s*</td>", page))
            provinces = len(re.findall(
                "北京|天津|河北|山西|内蒙古|辽宁|吉林|黑龙江|上海|江苏|浙江|安徽|"
                "福建|江西|山东|河南|湖北|湖南|广东|广西|海南|重庆|四川|贵州|云南|"
                "西藏|陕西|甘肃|青海|宁夏|新疆", page))
            atts = [urllib.parse.urljoin(url, a) for a in ATTACHMENT.findall(page)]
            print("    %d  %7d B  %3d <tr>  %3d score cells  %3d province mentions  %s"
                  % (y, len(body), rows, cells, provinces, title[:26]))
            time.sleep(DELAY_PAGE)

            for a in atts:
                ext = a.rsplit(".", 1)[-1].lower()
                adest = root / ("%d.%s" % (y, ext))
                if adest.exists():
                    print("        attachment .%s  have" % ext)
                    continue
                ast_, abody, anote = probe(a, timeout=40)
                if ast_ != 200 or not abody:
                    print("        attachment .%s  %s %s" % (ext, ast_, anote))
                    time.sleep(DELAY_PAGE)
                    continue
                adest.write_bytes(abody)
                print("        attachment %7d B  -> %s" % (len(abody), adest.name))
                time.sleep(DELAY_PAGE)

    print("\n--- next ---")
    print("Raw pages are on disk. The parser is written against them, not "
          "against this description of them, and only then is the university "
          "list extended.")
    return 0


PROVINCES = ("北京 天津 河北 山西 内蒙古 辽宁 吉林 黑龙江 上海 江苏 浙江 安徽 福建 "
             "江西 山东 河南 湖北 湖南 广东 广西 海南 重庆 四川 贵州 云南 西藏 陕西 "
             "甘肃 青海 宁夏 新疆").split()

ROW = re.compile(r"(" + "|".join(PROVINCES) + r")\s*[：:]\s*(.{0,90}?)(?=<br|</p|<p|$)", re.S)

#: A track label immediately followed by a number. The immediacy is what keeps
#: the other admission channels out: a line reads
#: `安徽：理科689分；文科675分；理科定向683分`, and the third figure is a
#: directed-placement cutoff rather than the general one. `理科定向683` does not
#: match because `定向` sits between the label and the digits.
SCORE = re.compile(r"(理科|文科|理工|文史)\s*(\d{3})\s*分")

MARK = re.compile(r"【([^】]+)】")


def year_sections(html: str) -> list[tuple[str, str]]:
    """Split a year page into its bracketed sections.

    The head is dropped first. On the 2015 page the section title also appears
    inside a `meta` description, so a scan of the whole document finds the title
    twice and the first hit carries no data.
    """
    body = html.split("<body", 1)[-1]
    marks = [(m.start(), m.group(1)) for m in MARK.finditer(body)]
    return [(name, body[pos:(marks[i + 1][0] if i + 1 < len(marks) else len(body))])
            for i, (pos, name) in enumerate(marks)]


def parse_year(html: str) -> tuple[list[str], dict]:
    """Institution cutoffs for the general first-batch channel, by province.

    **Only the general channel.** A page also carries an early batch, a poverty
    or national special plan, and military and directed places, each with its
    own and lower cutoffs. Those are separate admission channels rather than
    variants of the same number, and mixing them would put different quantities
    in one column.

    The section title is matched on `一批` and `录取分数线` rather than on a
    fixed string: the same university titles it `一批录取分数线` in 2014 and
    2015 and `一批统招录取分数线` in 2016.
    """
    picked = [(n, s) for n, s in year_sections(html)
              if "一批" in n and "录取分数线" in n and "专项" not in n]
    rows: dict[str, dict[str, int]] = {}
    for _name, seg in picked:
        for prov, tail in ROW.findall(seg):
            for track, score in SCORE.findall(tail):
                key = "science" if track in ("理科", "理工") else "arts"
                rows.setdefault(prov, {})[key] = int(score)
    return [n for n, _ in picked], rows


def parse() -> int:
    """Reduce the saved year pages to one tidy table.

    **Only the pages, not the workbooks.** Some years hang their figures off an
    `.xlsx` instead, and that workbook is a different quantity: it is by major,
    highest, lowest and mean, rather than one institution cutoff per province.
    A minimum over majors is close to an institution's lowest admitted score,
    which is not the same object as the cutoff at which files are released, so
    those years are left out rather than folded in.
    """
    # At data/ root rather than under data/raw/, which `.gitignore` excludes.
    # The raw pages are not redistributed and the table is the small derived
    # object a reader needs, so it is the one that ships.
    out = ROOT / "data" / "gaokao_cutoffs.csv"
    lines = ["university,province,year,track,batch,cutoff"]
    total = 0
    for uni in UNIVERSITIES:
        root = OUT / "univ" / uni["slug"]
        for f in sorted(root.glob("[12][0-9][0-9][0-9].html")):
            year = int(f.stem)
            names, rows = parse_year(f.read_bytes().decode("utf-8", "replace"))
            if not rows:
                print("  %-12s %d  no first-batch section; titles present: %s"
                      % (uni["slug"], year, [n for n, _ in year_sections(
                          f.read_bytes().decode("utf-8", "replace"))]))
                continue
            n = 0
            for prov, tracks in sorted(rows.items()):
                for key, score in sorted(tracks.items()):
                    lines.append("%s,%s,%d,%s,first,%d"
                                 % (uni["slug"], prov, year, key, score))
                    n += 1
            total += n
            both = sum(1 for v in rows.values() if len(v) == 2)
            print("  %-12s %d  %2d provinces, %2d with both tracks, %3d rows  [%s]"
                  % (uni["slug"], year, len(rows), both, n, ", ".join(names)))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\nwrote %s  %d rows" % (out, total))
    print("Workbook years are not in this table; see the note in `parse`.")
    return 0


#: The provincial authorities, by the host their announcements sat on. The list
#: is for a Wayback lookup and not for fetching them live: the pages this stage
#: needs were published between 2014 and 2016 and are largely gone from the
#: live sites, and two of five sampled would not accept a plain connection
#: anyway.
BUREAU_HOSTS = (
    ("Beijing", "bjeea.cn"), ("Tianjin", "zhaokao.net"), ("Hebei", "hebeea.edu.cn"),
    ("Shanxi", "sxkszx.cn"), ("Nei Menggu", "nm.zsks.cn"), ("Liaoning", "lnzsks.com"),
    ("Jilin", "jleea.edu.cn"), ("Heilongjiang", "lzk.hl.cn"), ("Shanghai", "shmeea.edu.cn"),
    ("Jiangsu", "jseea.cn"), ("Zhejiang", "zjzs.net"), ("Anhui", "ahzsks.cn"),
    ("Fujian", "eeafj.cn"), ("Jiangxi", "jxeea.cn"), ("Shandong", "sdzk.cn"),
    ("Henan", "haeea.cn"), ("Hubei", "hbea.edu.cn"), ("Hunan", "hneao.edu.cn"),
    ("Guangdong", "eeagd.edu.cn"), ("Guangxi", "gxeea.cn"), ("Hainan", "ea.hainan.gov.cn"),
    ("Chongqing", "cqksy.cn"), ("Sichuan", "sceea.cn"), ("Guizhou", "eaagz.org.cn"),
    ("Yunnan", "ynzs.cn"), ("Xizang", "zsks.edu.cn"), ("Shaanxi", "sneea.cn"),
    ("Gansu", "ganseea.cn"), ("Qinghai", "qhjyks.com"), ("Ningxia", "nxjyks.cn"),
    ("Xinjiang", "xjzk.gov.cn"),
)

CDX = ("https://web.archive.org/cdx/search/cdx?url={host}%2F*&output=json"
       "&from={lo}&to={hi}&filter=statuscode:200&collapse=urlkey&limit=8000"
       "&fl=timestamp,original")

#: A path that is likely to be a cutoff announcement. Deliberately broad: this
#: mode reports candidates for a human to look at rather than deciding, and a
#: narrow pattern here would hide the pages whose URL says nothing.
LOOKSLIKE = re.compile(r"投档|分数|录取|fenshu|toudang|luqu|lqx|fsx|score|batch", re.I)


def wayback(lo: int = 2014, hi: int = 2017) -> int:
    """Ask the Wayback index which provincial pages from the window survive.

    **This mode exists because the archive is unreachable from the environments
    the rest of this file was written in**, on three separate paths, so the
    question of whether the 2014 to 2016 announcements were captured cannot be
    answered there. It is answerable from any machine with ordinary internet
    access, and one run settles whether the provincial route is open after all.

    Writes one index per province so that a later pass can fetch specific
    snapshots without repeating the search.
    """
    root = OUT / "wayback"
    root.mkdir(parents=True, exist_ok=True)
    grand = 0
    for name, host in BUREAU_HOSTS:
        dest = root / ("%s.json" % host.replace(".", "_"))
        if dest.exists():
            rows = json.loads(dest.read_text(encoding="utf-8"))
        else:
            url = CDX.format(host=urllib.parse.quote(host), lo=lo, hi=hi)
            st, blob, note = probe(url, timeout=45)
            if st != 200 or not blob:
                print("  %-13s %-22s %s %s" % (name, host, st or "", note))
                time.sleep(DELAY_PAGE)
                continue
            try:
                rows = json.loads(blob.decode("utf-8", "replace") or "[]")
            except json.JSONDecodeError:
                print("  %-13s %-22s index did not parse as json" % (name, host))
                time.sleep(DELAY_PAGE)
                continue
            rows = rows[1:] if rows else []
            dest.write_text(json.dumps(rows), encoding="utf-8", newline="\n")
            time.sleep(DELAY_PAGE)

        hits = [r for r in rows if len(r) > 1 and LOOKSLIKE.search(r[1])]
        grand += len(hits)
        print("  %-13s %-22s %5d captures, %4d look like cutoff pages"
              % (name, host, len(rows), len(hits)))
        for r in hits[:2]:
            print("        %s  %s" % (r[0], r[1][:84]))

    print("\n%d candidate pages across %d provinces." % (grand, len(BUREAU_HOSTS)))
    print("Indexes are on disk under %s, one per host, so a later pass fetches "
          "snapshots without searching again." % root)
    print("\nA province with captures but no candidates is not the same as one "
          "with no captures: the first says the crawler was there and the "
          "pattern did not match, and the second says it was not. Both are in "
          "the counts above and neither is inferred from the other.")
    return 0


SOURCES = ROOT / "data" / "gaokao_sources.json"

#: The words a provincial parallel-volunteer filing table for the first
#: undergraduate batch uses for its own quantity. A page that never says any of
#: them is reporting something else, whatever its title claims.
FILING = ("投档", "投档线", "投档最低分", "投档分数线", "平行投档")

#: Batches that are not the one this stage reads. Their presence does not
#: disqualify a page, since one article often carries several, but it is
#: reported so that a parser is written knowing they are there.
OTHER_BATCH = ("提前批", "本科二批", "二本", "第二批", "征集志愿", "专项", "定向", "国防")


def check() -> int:
    """Fetch every unverified candidate and report it against the criteria.

    **A candidate list is a list of things to check.** These were gathered by a
    search pass run elsewhere, and an article identifier is exactly the kind of
    string that reads as real whether or not it is, so none of them is treated
    as a source until it has answered and been looked at. The raw pages are kept
    so the parser is written against documents.

    `verified` is set only on the mechanical criteria: the page answers, it
    carries a table, the table is long enough to be a whole province rather than
    a summary of a few institutions, and the page uses the word for the quantity.
    Everything softer is printed rather than decided here.
    """
    doc = json.loads(SOURCES.read_text(encoding="utf-8"))
    root = OUT / "provincial"
    root.mkdir(parents=True, exist_ok=True)
    todo = [x for x in doc["pages"] if not x.get("verified")]
    print("%d candidates to check, %d already verified\n"
          % (len(todo), len(doc["pages"]) - len(todo)))
    print("  %-6s %-5s %-4s %6s %5s %5s %6s  %s"
          % ("prov", "year", "src", "bytes", "tbl", "rows", "3-digit", "verdict"))

    passed = failed = 0
    for row in todo:
        tag = "eol" if "eol.cn" in row["url"] else "sina"
        # The track belongs in the name. Without it a province-year's second
        # url reuses the first one's file, and every statistic it prints is the
        # first page's, which is indistinguishable from a real reading.
        dest = root / ("%s_%d_%s_%s.html"
                       % (row["province"], row["year"], row.get("track", "both"), tag))
        if dest.exists():
            body = dest.read_bytes()
            st = 200
        else:
            st, body, note = probe(row["url"], timeout=30)
            if st == 200 and body:
                dest.write_bytes(body)
            time.sleep(DELAY_PAGE)
        if st != 200 or not body:
            print("  %-6s %-5d %-4s  %s" % (row["province"], row["year"], tag,
                                            "NO  http %s" % st))
            failed += 1
            continue

        page = decode_page(body)
        tables = len(re.findall(r"<table", page, re.I))
        rows_n = len(re.findall(r"<tr", page, re.I))
        numeric = len(re.findall(r"<td[^>]*>\s*\d{3}(?:\.\d)?\s*</td>", page))
        says = [w for w in FILING if w in page]
        others = [w for w in OTHER_BATCH if w in page]
        first = ("本科一批" in page or "第一批" in page or "一本" in page)
        prov_named = row["province"] in page

        ok = (tables >= 1 and rows_n >= 100 and bool(says) and prov_named)
        row["verified"] = ok
        row["check"] = {"bytes": len(body), "tables": tables, "rows": rows_n,
                        "three_digit_cells": numeric, "filing_words": says,
                        "other_batches": others, "says_first_batch": first,
                        "province_named": prov_named}
        passed += ok
        failed += (not ok)
        why = ""
        if not ok:
            why = " (" + ", ".join(
                w for w, bad in (("no table", tables < 1), ("short", rows_n < 100),
                                 ("no filing word", not says),
                                 ("province absent", not prov_named)) if bad) + ")"
        print("  %-6s %-5d %-4s %6d %5d %5d %6d  %s%s"
              % (row["province"], row["year"], tag, len(body), tables, rows_n,
                 numeric, "YES" if ok else "NO", why))

    SOURCES.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8", newline="\n")
    print("\n%d verified, %d not. Pages are under %s." % (passed, failed, root))
    import collections
    byy = collections.defaultdict(set)
    for x in doc["pages"]:
        if x.get("verified"):
            byy[x["year"]].add(x["province"])
    provs = set().union(*byy.values()) if byy else set()
    twice = [p_ for p_ in provs if sum(1 for y in byy if p_ in byy[y]) >= 2]
    print("Verified coverage: " + ", ".join("%d: %d provinces" % (y, len(byy[y]))
                                            for y in sorted(byy)))
    print("Provinces verified in two or more years: %d  <- the criterion needs "
          "this above about fifteen" % len(twice))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagnose", action="store_true")
    ap.add_argument("--sample", action="store_true",
                    help="fetch the index and two articles, report the form")
    ap.add_argument("--cutoffs", action="store_true",
                    help="follow provincial front pages to a cutoff table")
    ap.add_argument("--history", action="store_true",
                    help="how far back the aggregator archive reaches")
    ap.add_argument("--universities", action="store_true",
                    help="pull the listed universities' own year pages")
    ap.add_argument("--parse", action="store_true",
                    help="reduce the saved year pages to one table")
    ap.add_argument("--wayback", action="store_true",
                    help="ask the Wayback index for the 2014-2016 announcements")
    ap.add_argument("--check", action="store_true",
                    help="fetch every unverified candidate and judge it")
    args = ap.parse_args()
    if args.sample:
        return sample()
    if args.cutoffs:
        return cutoffs()
    if args.history:
        return history()
    if args.universities:
        return universities()
    if args.parse:
        return parse()
    if args.wayback:
        return wayback()
    if args.check:
        return check()
    if not args.diagnose:
        return ap.error("this file is a probe. Pass --diagnose, --sample, --cutoffs, --history, --universities, --parse, --wayback or --check.")

    OUT.mkdir(parents=True, exist_ok=True)
    answered = []
    for label, url in CANDIDATES:
        status, blob, note = probe(url)
        print("  %-3s %-20s %s" % (status, label, describe(blob)))
        if note:
            print("      %s" % note)
        if status == 200 and blob:
            answered.append(label)
            dest = OUT / ("_probe_%s.bin" % label.replace(" ", "_").replace(":", ""))
            dest.write_bytes(blob[:400000])
            print("      wrote %s" % dest)
        time.sleep(0.4)

    print("\n--- what this decides ---")
    agg = [a for a in answered if a.startswith("aggregator") or a.startswith("eol")]
    if agg:
        print("An aggregator answered (%s). If it carries both the cutoffs and "
              "the rank tables, this carrier costs about what the last one did, "
              "and the next step is one sweep against one source." % ", ".join(agg))
    else:
        print("No aggregator answered. The fallback is one authority per "
              "province, thirty-one formats, and that is an order of magnitude "
              "more than anything in this repository so far. **Price it before "
              "starting it**: the panel needs a rank table and a cutoff table "
              "per province per year, and a wave of regime changes between 2017 "
              "and 2025 means the usable years differ by province.")
    print("\nPayloads that answered are on disk for the parser to be written "
          "against rather than guessed at.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
