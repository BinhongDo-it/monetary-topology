"""B154: fetch the statistical uniform price announcements of the ten federal milk marketing orders
other than Central (Order 32, fetched by b154_fetch.py).

Nothing here reads a price. Each file is put on disk under data/raw/b154/<part>/, checked whole, and
entered in data/raw/b154/b154_orders_manifest.json with its URL, byte count, SHA-256, the server's
Last-Modified header, the check it passed, the seconds the request took and the retrieval time.

Where the file names come from (each order's market administrator publishes its own archive):

  1001 Northeast          fmmone.com, Price_Announcements_Uniform.htm, monthly UPyyyymm[-rev].pdf
  1005 Appalachian        malouisville.com/hist_uniform_price, monthly "Uniform Price yyyy/unpr????.pdf"
  1006 Florida            fmmatlanta.com, Price_Announcements_Uniform.htm, FO6/: yearly 2021 to 2025, monthly 2026
  1007 Southeast          the same page, FO7/
  1030 Upper Midwest      fmma30.com/PPD.html, monthly PPD/yyyy/PPDmmyy.pdf
  1033 Mideast            fmmaclev.com, Price_Announcements_Uniform.htm, yearly Unifyyyy.pdf to 2021, monthly UPyyyymm.pdf
  1051 California         cafmmo.com/prices/statistical-uniform/, monthly "yyyymm Pool Price.pdf" (order from 2018-11)
  1124 Pacific Northwest  fmmaseattle.com uniform.html and uniformarchive.html: yearly ppd124yy.pdf (2000 to 2011),
                          yearly ppdyyyy.pdf (2012 to 2021), monthly ppdcomputation/ppdyyyymm.pdf (2022 on)
  1126 Southwest          dallasma.com; its listing is built by script, so the URL is written from the pattern
                          the office uses, file_map/producer_price/SOUTHWEST+FO+126/yyyy/26PDmmyy.PDF
  1131 Arizona            azfmmo.com/prices/uniform-price/, monthly "yyyymm   uniform.pdf"

The listing pages are fetched each run and kept under data/raw/b154/listings/. Months after 2026-09 are
listed on some pages before they are published and are left out.

Run from the repository root:

    python experiments/b154_fetch_orders.py --inventory            # listings only; counts per order
    python experiments/b154_fetch_orders.py --measure              # one file per order, earliest and latest
                                                                   # month (rule D38: size changes with the
                                                                   # year), then the estimate; refuses above 1 GB
    python experiments/b154_fetch_orders.py --fetch [--order 1001 ...] [--budget S]
    python experiments/b154_fetch_orders.py --verify               # no network
    python experiments/b154_fetch_orders.py --selftest             # offline, seeded faults

Second set (ruled 2026-10-29), its own manifest data/raw/b154/b154_census_rules_manifest.json:

    python experiments/b154_fetch_orders.py --extra                # Census place-by-county file and the
                                                                   # .51 text of 1005, 1006, 1007
    python experiments/b154_fetch_orders.py --extra-verify         # no network

  census/national_place_by_county2020.txt   www2.census.gov, codes2020 (2,736,928 bytes by HEAD)
  rules/cfr{2009,2020,2024}_100{5,6,7}_51.xml govinfo annual CFR print, title 7 vol. 9, as of January 1
  rules/ecfr_versions_100{5,6,7}_51.json    eCFR versioner: the amendment dates of each section
  rules/ecfr20250201_100{5,6,7}_51.xml      eCFR point-in-time text in force 2025-02-01 (the 2025-01-17 version)

A partial download is resumed with an HTTP Range request from the bytes already in its .part file; the
file is renamed into place only when its length equals the server's total and it passes its check (the
Census text: a header with the expected columns, every line the same number of fields, a final newline).

--fetch is refused until --measure has written an estimate at or under the cap. A fetch can be
interrupted and run again: a file on disk that passes its check and matches the manifest is kept; a
download goes to a .part file and is renamed into place only when its length equals the server's
Content-Length (when sent) and it passes its check. Nothing is deleted; a file that fails is renamed
aside with the reason. Nothing downloaded is executed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # safe_write.py sits one level above the repository
sys.path.insert(0, str(Path(__file__).resolve().parent))

import b154_fetch as base  # noqa: E402  check(), get(), sha256_bytes(), set_aside(), now_utc()

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data" / "raw" / "b154"
MANIFEST = "b154_orders_manifest.json"
EXTRA_MANIFEST = "b154_census_rules_manifest.json"
SESSION = "B154_1029b"
CAP_BYTES = 1_000_000_000
LAST = (2026, 9)
FIRST = (2000, 1)

LISTINGS = {
    1001: ["https://www.fmmone.com/Price_Announcements_Uniform.htm"],
    1005: ["https://www.malouisville.com/hist_uniform_price"],
    1006: ["https://www.fmmatlanta.com/Price_Announcements_Uniform.htm"],
    1007: ["https://www.fmmatlanta.com/Price_Announcements_Uniform.htm"],
    1030: ["https://www.fmma30.com/PPD.html"],
    1033: ["https://www.fmmaclev.com/Price_Announcements_Uniform.htm"],
    1051: ["https://www.cafmmo.com/prices/statistical-uniform/"],
    1124: ["https://fmmaseattle.com/uniform.html", "https://fmmaseattle.com/uniformarchive.html"],
    1126: [],
    1131: ["https://www.azfmmo.com/prices/uniform-price/"],
}
NAMES = {1001: "Northeast", 1005: "Appalachian", 1006: "Florida", 1007: "Southeast", 1030: "Upper Midwest",
         1033: "Mideast", 1051: "California", 1124: "Pacific Northwest", 1126: "Southwest", 1131: "Arizona"}
SW_URL = "https://www.dallasma.com/file_map/producer_price/SOUTHWEST+FO+126/{y}/26PD{m:02d}{yy:02d}.PDF"


def in_window(y, m=1):
    return FIRST <= (y, m) <= LAST


def item(order, unit, key, url, fname, listed=True):
    """unit is 'month' (key yyyymm) or 'year' (key yyyy, a yearly compilation)."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", fname).strip("_")
    return {"id": "%d_%s" % (order, key), "order": order, "unit": unit, "key": key, "kind": "pdf",
            "url": url, "dest": "%d/%s" % (order, safe.lower()), "must": None, "listed": listed}


def hrefs(html_text):
    return [html_unescape(h) for h in re.findall(r'href="([^"]+)"', html_text, flags=re.I)]


def html_unescape(s):
    return s.replace("&amp;", "&")


def strip_session(u):
    return re.sub(r";jsessionid=[0-9A-Fa-f]+", "", u)


# ---------------------------------------------------------------- per-order name parsers

def items_1001(pages):
    out, seen = [], set()
    for page_url, txt in pages:
        for h in hrefs(txt):
            m = re.search(r"Statistical_Uniform/(?:Past_Years/)?UP(\d{4})(\d{2})(-rev)?\.pdf$", h, flags=re.I)
            if not m:
                continue
            y, mo, rev = int(m.group(1)), int(m.group(2)), m.group(3)
            if not in_window(y, mo):
                continue
            key = "%04d%02d%s" % (y, mo, "rev" if rev else "")
            if key in seen:
                continue
            seen.add(key)
            u = urllib.parse.urljoin(page_url, h)
            out.append(item(1001, "month", key, u, "UP%04d%02d%s.pdf" % (y, mo, "-rev" if rev else "")))
    return out


def month_from_app(folder_year, a, b):
    yy = folder_year % 100
    if a == yy and 1 <= b <= 12:
        return b
    if b == yy and 1 <= a <= 12:
        return a
    return None


def items_1005(pages):
    out, seen = [], set()
    for page_url, txt in pages:
        for h in hrefs(txt):
            m = re.search(r"Uniform Price (\d{4})/unpr(\d\d)(\d\d)\.pdf$", urllib.parse.unquote(h), flags=re.I)
            if not m:
                continue
            y = int(m.group(1))
            mo = month_from_app(y, int(m.group(2)), int(m.group(3)))
            if mo is None or not in_window(y, mo):
                continue
            key = "%04d%02d" % (y, mo)
            if key in seen:
                continue
            seen.add(key)
            u = urllib.parse.urljoin(page_url, urllib.parse.quote(urllib.parse.unquote(h)))
            out.append(item(1005, "month", key, u, "unpr_%s.pdf" % key))
    return out


def items_atl(order, pages):
    fo = "FO6" if order == 1006 else "FO7"
    out, seen = [], set()
    for page_url, txt in pages:
        for h in hrefs(txt):
            hu = urllib.parse.unquote(h)
            if ("/%s/" % fo) not in hu:
                continue
            m = re.search(r"/(\d\d)(\d{4})uprice\.pdf$", hu, flags=re.I)
            if m:
                y, mo = int(m.group(2)), int(m.group(1))
                unit, key = "month", "%04d%02d" % (y, mo)
            else:
                m = re.search(r"(\d{4})\s*uprice\.pdf$|uprice(\d{4})\.pdf$", hu, flags=re.I)
                if not m:
                    continue
                y, mo = int(m.group(1) or m.group(2)), 1
                unit, key = "year", "%04d" % y
            if not in_window(y, mo) or key in seen:
                continue
            seen.add(key)
            u = urllib.parse.urljoin(page_url, urllib.parse.quote(hu))
            out.append(item(order, unit, key, u, "uprice_%s.pdf" % key))
    return out


def items_1030(pages):
    out, seen = [], set()
    for page_url, txt in pages:
        for h in hrefs(txt):
            m = re.search(r"PPD/(\d{4})/PPD(\d\d)(\d\d)\.pdf$", h, flags=re.I)
            if not m:
                continue
            y, mo = int(m.group(1)), int(m.group(2))
            if int(m.group(3)) != y % 100 or not in_window(y, mo):
                continue
            key = "%04d%02d" % (y, mo)
            if key in seen:
                continue
            seen.add(key)
            out.append(item(1030, "month", key, urllib.parse.urljoin(page_url, h), "PPD_%s.pdf" % key))
    return out


def items_1033(pages):
    out, seen = [], set()
    for page_url, txt in pages:
        for h in hrefs(txt):
            m = re.search(r"Statistical_Uniform/UP(\d{4})(\d{2})\.pdf$", h, flags=re.I)
            if m:
                y, mo = int(m.group(1)), int(m.group(2))
                unit, key = "month", "%04d%02d" % (y, mo)
            else:
                m = re.search(r"Past_Years/Unif(\d{4})\.pdf$", h, flags=re.I)
                if not m:
                    continue
                y, mo = int(m.group(1)), 1
                unit, key = "year", "%04d" % y
            if not in_window(y, mo) or key in seen:
                continue
            seen.add(key)
            out.append(item(1033, unit, key, urllib.parse.urljoin(page_url, h), "%s_%s.pdf" % (unit, key)))
    return out


def items_download_file(order, pages, folder, pat):
    out, seen = [], set()
    for page_url, txt in pages:
        for h in hrefs(txt):
            if "folderMap=%s" % folder not in h:
                continue
            m = re.search(r"fileName=([^&]+)", h)
            if not m:
                continue
            fn = urllib.parse.unquote_plus(m.group(1))
            mm = re.fullmatch(pat, fn)
            if not mm:
                continue
            y, mo = int(mm.group(1)), int(mm.group(2))
            if not in_window(y, mo):
                continue
            key = "%04d%02d" % (y, mo)
            if key in seen:
                continue
            seen.add(key)
            u = strip_session(urllib.parse.urljoin(page_url, h))
            out.append(item(order, "month", key, u, "%s.pdf" % key))
    return out


def items_1124(pages):
    out, seen = [], set()
    for page_url, txt in pages:
        for h in hrefs(txt):
            hh = h.replace("\\", "/")
            m = re.search(r"prices/ppdcomputation/ppd124(\d\d)\.pdf$", hh, flags=re.I)
            if m:
                unit, y, mo = "year", 2000 + int(m.group(1)), 1
                key = "%04d" % y
            else:
                m = re.search(r"prices/ppdcomputation/ppd(\d{4})(\d\d)\.pdf$", hh, flags=re.I)
                if m:
                    unit, y, mo = "month", int(m.group(1)), int(m.group(2))
                    key = "%04d%02d" % (y, mo)
                else:
                    m = re.search(r"prices/ppdcomputation/ppd(\d{4})\.pdf$", hh, flags=re.I)
                    if not m:
                        continue
                    unit, y, mo = "year", int(m.group(1)), 1
                    key = "%04d" % y
            if not in_window(y, mo) or key in seen:
                continue
            seen.add(key)
            out.append(item(1124, unit, key, urllib.parse.urljoin(page_url, hh), "ppd_%s.pdf" % key))
    return out


def items_1126():
    out = []
    y, m = FIRST
    while (y, m) <= LAST:
        key = "%04d%02d" % (y, m)
        out.append(item(1126, "month", key, SW_URL.format(y=y, m=m, yy=y % 100), "26PD_%s.pdf" % key,
                        listed=False))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def items_for_order(order, pages):
    if order == 1001:
        return items_1001(pages)
    if order == 1005:
        return items_1005(pages)
    if order in (1006, 1007):
        return items_atl(order, pages)
    if order == 1030:
        return items_1030(pages)
    if order == 1033:
        return items_1033(pages)
    if order == 1051:
        return items_download_file(1051, pages, "prices.statistical-uniform", r"(\d{4})/(?:\d{4})(\d\d) Pool Price\.pdf")
    if order == 1124:
        return items_1124(pages)
    if order == 1126:
        return items_1126()
    if order == 1131:
        return items_download_file(1131, pages, "prices.uniform-price", r"(\d{4})/(?:\d{4})(\d\d)\s+uniform\.pdf")
    raise ValueError(order)


# ---------------------------------------------------------------- manifest

def load_manifest(raw=RAW):
    p = raw / MANIFEST
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_manifest(manifest, raw=RAW, use_safe_write=True):
    raw.mkdir(parents=True, exist_ok=True)
    p = raw / MANIFEST
    text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if not use_safe_write:
        p.write_text(text, encoding="utf-8", newline="\n")
        return
    from safe_write import create, rewrite
    if p.exists():
        rewrite(p, "B154 orders manifest", lambda _t: text, session=SESSION)
    else:
        create(p, "B154 orders manifest", text, session=SESSION)


def fetch_listings(orders, manifest, raw=RAW):
    pages = {}
    cache = {}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    (raw / "listings").mkdir(parents=True, exist_ok=True)
    for o in orders:
        pages[o] = []
        for u in LISTINGS[o]:
            if u not in cache:
                body, hdr, secs = base.get(u)
                name = "%s_%s.html" % (re.sub(r"[^A-Za-z0-9]+", "_", u.split("//", 1)[1]).strip("_"), stamp)
                p = raw / "listings" / name
                if not p.exists():
                    p.write_bytes(body)
                manifest.setdefault("_listings", {})[name] = {"url": u, "bytes": len(body),
                                                              "sha256": base.sha256_bytes(body),
                                                              "retrieved_utc": base.now_utc(), "seconds": round(secs, 3)}
                cache[u] = body.decode("utf-8", errors="replace")
            pages[o].append((u, cache[u]))
    return pages


def all_items(orders, manifest, offline_pages=None):
    pages = offline_pages if offline_pages is not None else fetch_listings(orders, manifest)
    out = {}
    for o in orders:
        out[o] = sorted(items_for_order(o, pages.get(o, [])), key=lambda it: it["key"])
    return out


# ---------------------------------------------------------------- one file

def fetch_one(it, manifest, raw=RAW):
    dest = raw / it["dest"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and it["id"] in manifest:
        ok, _ = base.check(it, dest, manifest[it["id"]].get("bytes"))
        if ok and manifest[it["id"]].get("sha256") == base.sha256_bytes(dest.read_bytes()):
            return "kept"
        base.set_aside(dest, "failed_check")
    try:
        body, hdr, secs = base.get(it["url"])
    except urllib.error.HTTPError as e:
        manifest[it["id"] + "__error"] = {"url": it["url"], "http": e.code, "seen_utc": base.now_utc(),
                                          "order": it["order"], "key": it["key"], "unit": it["unit"]}
        return "http %d" % e.code
    except (urllib.error.URLError, OSError) as e:
        return "error %r" % (e,)
    part = dest.with_name(dest.name + ".part")
    if part.exists():
        base.set_aside(part, "stale_part")
    part.write_bytes(body)
    ok, why = base.check(it, part, hdr["length"])
    if not ok:
        base.set_aside(part, "failed_check")
        manifest[it["id"] + "__error"] = {"url": it["url"], "check": why, "seen_utc": base.now_utc(),
                                          "order": it["order"], "key": it["key"], "unit": it["unit"]}
        return "failed: " + why
    part.rename(dest)
    manifest.pop(it["id"] + "__error", None)
    manifest[it["id"]] = {"url": it["url"], "dest": it["dest"], "order": it["order"], "unit": it["unit"],
                          "key": it["key"], "kind": "pdf", "bytes": len(body), "sha256": base.sha256_bytes(body),
                          "server_last_modified": hdr["last_modified"], "check": why, "seconds": round(secs, 3),
                          "retrieved_utc": base.now_utc(), "listed": it["listed"]}
    return "fetched"


# ---------------------------------------------------------------- estimate (D38)

def estimate(inv, manifest):
    """Per order: listed count x measured bytes and seconds of the files fetched so far. Both the mean and
    the larger measured file are used; the cap is checked against the larger one."""
    rows, tot_mean, tot_max, tot_s = {}, 0, 0, 0.0
    for o, its in inv.items():
        got = [manifest[it["id"]] for it in its if it["id"] in manifest]
        if not got:
            rows[str(o)] = {"listed": len(its), "measured": 0, "estimate": "not measured"}
            tot_max = None
            continue
        b = [g["bytes"] for g in got]
        s = [g["seconds"] for g in got]
        mean_b, max_b, mean_s = sum(b) / len(b), max(b), sum(s) / len(s)
        rows[str(o)] = {"listed": len(its), "measured": len(got), "measured_bytes": b, "measured_seconds": s,
                        "est_bytes_mean": int(mean_b * len(its)), "est_bytes_upper": int(max_b * len(its)),
                        "est_seconds": round(mean_s * len(its), 1)}
        tot_mean += rows[str(o)]["est_bytes_mean"]
        if tot_max is not None:
            tot_max += rows[str(o)]["est_bytes_upper"]
        tot_s += rows[str(o)]["est_seconds"]
    return {"orders": rows, "total_bytes_mean": tot_mean, "total_bytes_upper": tot_max,
            "total_seconds": round(tot_s, 1), "cap_bytes": CAP_BYTES,
            "within_cap": tot_max is not None and tot_max <= CAP_BYTES}


# ---------------------------------------------------------------- second set: Census places, .51(b) text

CENSUS_URL = "https://www2.census.gov/geo/docs/reference/codes2020/national_place_by_county2020.txt"
CENSUS_HEADER = "STATE|STATEFP|COUNTYFP|COUNTYNAME|PLACEFP|PLACENS|PLACENAME|TYPE|CLASSFP|FUNCSTAT"
GOVINFO = "https://www.govinfo.gov/content/pkg/CFR-{y}-title7-vol9/xml/CFR-{y}-title7-vol9-sec{o}-51.xml"
ECFR_VERSIONS = "https://www.ecfr.gov/api/versioner/v1/versions/title-7.json?section={o}.51"
ECFR_FULL = "https://www.ecfr.gov/api/versioner/v1/full/{d}/title-7.xml?section={o}.51"


def extra_items():
    its = [{"id": "census_place_by_county2020", "kind": "pipe", "must": CENSUS_HEADER, "url": CENSUS_URL,
            "dest": "census/national_place_by_county2020.txt", "gzip": False}]
    for o in (1005, 1006, 1007):
        for y in (2009, 2020, 2024):
            its.append({"id": "cfr%d_%d_51" % (y, o), "kind": "xml", "must": "%d.51" % o,
                        "url": GOVINFO.format(y=y, o=o), "dest": "rules/cfr%d_%d_51.xml" % (y, o), "gzip": False})
        its.append({"id": "ecfr_versions_%d_51" % o, "kind": "json", "must": "content_versions",
                    "url": ECFR_VERSIONS.format(o=o), "dest": "rules/ecfr_versions_%d_51.json" % o, "gzip": True})
        its.append({"id": "ecfr20250201_%d_51" % o, "kind": "xml", "must": "%d.51" % o,
                    "url": ECFR_FULL.format(d="2025-02-01", o=o), "dest": "rules/ecfr20250201_%d_51.xml" % o,
                    "gzip": True})
    return its


def check_pipe(path, must):
    """A pipe-delimited text: the header given, every line with the header's field count, a final newline.
    A file cut short ends mid-line, so its last line has fewer fields or no newline."""
    data = path.read_bytes()
    if not data.endswith(b"\n"):
        return False, "no final newline"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        return False, "not UTF-8: %s" % e
    lines = text.rstrip("\n").split("\n")
    head = lines[0].lstrip("﻿").rstrip("\r")
    if head != must:
        return False, "header %r is not %r" % (head[:80], must)
    k = head.count("|")
    bad = [i for i, ln in enumerate(lines) if ln.rstrip("\r").count("|") != k]
    if bad:
        return False, "%d lines with another field count, first at line %d" % (len(bad), bad[0] + 1)
    return True, "header as expected, %d data lines of %d fields, final newline" % (len(lines) - 1, k + 1)


def check_json(path, must):
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        return False, "not JSON: %s" % e
    if must and must not in d:
        return False, "no key %s" % must
    return True, "JSON with key %s" % must


def check_extra(it, path, length=None):
    if length is not None and path.stat().st_size != length:
        return False, "length %d differs from the server's %d" % (path.stat().st_size, length)
    if it["kind"] == "pipe":
        return check_pipe(path, it["must"])
    if it["kind"] == "json":
        return check_json(path, it["must"])
    return base.check({"kind": it["kind"], "must": it["must"]}, path)


def total_from(status, headers, have):
    """The full length of the resource: from Content-Range on a 206, from Content-Length on a 200."""
    cr = headers.get("Content-Range")
    if status == 206 and cr:
        m = re.match(r"bytes (\d+)-(\d+)/(\d+)", cr)
        if m and int(m.group(1)) == have:
            return int(m.group(3)), True
        return None, False
    cl = headers.get("Content-Length")
    return (int(cl) if cl else None), False


def get_resumable(url, part, gz=False):
    """Download into part, resuming from its current length with a Range request (no Range for a
    compressed eCFR response, which the server must send gzipped). Returns (total or None, last_modified,
    seconds, compressed_length)."""
    import gzip
    import urllib.request
    t0 = time.time()
    have = part.stat().st_size if (part.exists() and not gz) else 0
    hdrs = {"User-Agent": base.UA}
    if gz:
        hdrs["Accept-Encoding"] = "gzip"
    elif have:
        hdrs["Range"] = "bytes=%d-" % have
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=120) as r:
        status = r.status
        body = r.read()
        total, appended = total_from(status, r.headers, have)
        lm = r.headers.get("Last-Modified")
        enc = r.headers.get("Content-Encoding")
    comp_len = len(body)
    if gz and enc == "gzip":
        if total is not None and total != comp_len:
            raise OSError("compressed body %d bytes, header %d" % (comp_len, total))
        body = gzip.decompress(body)
        total = len(body)
    if appended:
        with open(part, "ab") as f:
            f.write(body)
    else:
        part.write_bytes(body)
    return total, lm, time.time() - t0, comp_len


def load_extra(raw=RAW):
    p = raw / EXTRA_MANIFEST
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_extra(manifest, raw=RAW, use_safe_write=True):
    p = raw / EXTRA_MANIFEST
    text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if not use_safe_write:
        p.write_text(text, encoding="utf-8", newline="\n")
        return
    from safe_write import create, rewrite
    if p.exists():
        rewrite(p, "B154 census and rules manifest", lambda _t: text, session=SESSION)
    else:
        create(p, "B154 census and rules manifest", text, session=SESSION)


def cmd_extra(raw=RAW, tries=3):
    manifest = load_extra(raw)
    res = {}
    for it in extra_items():
        dest = raw / it["dest"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and it["id"] in manifest:
            ok, _ = check_extra(it, dest, manifest[it["id"]]["bytes"])
            if ok and manifest[it["id"]]["sha256"] == base.sha256_bytes(dest.read_bytes()):
                res[it["id"]] = "kept"
                continue
            base.set_aside(dest, "failed_check")
        part = dest.with_name(dest.name + ".part")
        r = None
        for k in range(tries):
            try:
                total, lm, secs, comp = get_resumable(it["url"], part, it["gzip"])
            except urllib.error.HTTPError as e:
                r = "http %d" % e.code
                manifest[it["id"] + "__error"] = {"url": it["url"], "http": e.code, "seen_utc": base.now_utc()}
                if e.code in (429, 503):
                    time.sleep(5 * (k + 1))
                    continue
                break
            except (urllib.error.URLError, OSError) as e:
                r = "error %r" % (e,)
                time.sleep(3 * (k + 1))
                continue
            ok, why = check_extra(it, part, total)
            if not ok:
                if total is not None and part.stat().st_size < total:
                    r = "short: %s" % why          # kept as .part; the next try resumes from it
                    continue
                base.set_aside(part, "failed_check")
                r = "failed: " + why
                manifest[it["id"] + "__error"] = {"url": it["url"], "check": why, "seen_utc": base.now_utc()}
                break
            part.rename(dest)
            body = dest.read_bytes()
            manifest.pop(it["id"] + "__error", None)
            manifest[it["id"]] = {"url": it["url"], "dest": it["dest"], "kind": it["kind"], "bytes": len(body),
                                  "sha256": base.sha256_bytes(body), "server_last_modified": lm, "check": why,
                                  "seconds": round(secs, 3), "bytes_on_the_wire": comp,
                                  "retrieved_utc": base.now_utc()}
            r = "fetched"
            break
        res[it["id"]] = r
        print("%-28s %s" % (it["id"], r))
    save_extra(manifest, raw)
    bad = [k for k, v in res.items() if v not in ("kept", "fetched")]
    print("results %s" % json.dumps(res, sort_keys=True))
    return 2 if bad else 0


def cmd_extra_verify(raw=RAW):
    manifest = load_extra(raw)
    bad = 0
    its = {it["id"]: it for it in extra_items()}
    for k, rec in sorted(manifest.items()):
        if k.startswith("_") or k.endswith("__error"):
            continue
        p = raw / rec["dest"]
        ok, why = check_extra(its[k], p, rec["bytes"]) if p.exists() else (False, "missing")
        same = p.exists() and rec["sha256"] == base.sha256_bytes(p.read_bytes())
        print("%-5s %-28s %s%s" % ("ok" if ok and same else "BAD", k, why, "" if same else " [hash differs]"))
        bad += 0 if (ok and same) else 1
    missing = sorted(set(its) - set(manifest))
    print("%d bad; not in the manifest: %s" % (bad, missing))
    return 1 if (bad or missing) else 0


# ---------------------------------------------------------------- commands

ORDERS = sorted(NAMES)


def cmd_inventory(orders):
    manifest = load_manifest()
    inv = all_items(orders, manifest)
    save_manifest(manifest)
    for o in orders:
        its = inv[o]
        units = {u: [it["key"] for it in its if it["unit"] == u] for u in ("month", "year")}
        print("%d %-18s months %3d (%s .. %s)  years %2d (%s .. %s)" % (
            o, NAMES[o], len(units["month"]), units["month"][0] if units["month"] else "-",
            units["month"][-1] if units["month"] else "-", len(units["year"]),
            units["year"][0] if units["year"] else "-", units["year"][-1] if units["year"] else "-"))
    return 0


def cmd_measure(orders):
    manifest = load_manifest()
    inv = all_items(orders, manifest)
    for o in orders:
        its = inv[o]
        picks = [its[0], its[-1]] if len(its) > 1 else its
        for it in picks:
            r = fetch_one(it, manifest)
            print("%-14s %s" % (it["id"], r))
    est = estimate(inv, manifest)
    manifest["_estimate"] = {"utc": base.now_utc(), **est}
    save_manifest(manifest)
    print(json.dumps(est, indent=1, sort_keys=True))
    if not est["within_cap"]:
        print("STOP  the upper estimate is above %d bytes or an order is not measured; nothing more is fetched"
              % CAP_BYTES)
        return 4
    print("estimate within the cap: upper %d bytes, central %d bytes, %.0f seconds"
          % (est["total_bytes_upper"], est["total_bytes_mean"], est["total_seconds"]))
    return 0


def cmd_fetch(orders, budget_s):
    manifest = load_manifest()
    est = manifest.get("_estimate")
    if not est or not est.get("within_cap"):
        print("REFUSED  no measured estimate within the cap; run --measure first")
        return 3
    inv = all_items(orders, manifest)
    t0 = time.time()
    counts, pending = {}, 0
    n = 0
    for o in orders:
        for it in inv[o]:
            if time.time() - t0 > budget_s:
                pending += 1
                continue
            if (it["id"] + "__error") in manifest and "http" in manifest[it["id"] + "__error"] \
                    and manifest[it["id"] + "__error"]["http"] == 404 and it["id"] not in manifest:
                r = "http 404 (seen before, not retried)"
            else:
                r = fetch_one(it, manifest)
            counts[r.split(":")[0]] = counts.get(r.split(":")[0], 0) + 1
            if r.startswith(("error", "failed")):
                print("%-16s %s" % (it["id"], r))
                pending += 1
            n += 1
            if n % 25 == 0:
                save_manifest(manifest)
    save_manifest(manifest)
    print("results %s; pending %d" % (json.dumps(counts, sort_keys=True), pending))
    return 2 if pending else 0


def cmd_verify(raw=RAW):
    manifest = load_manifest(raw)
    bad = n = 0
    per = {}
    for key, rec in sorted(manifest.items()):
        if key.startswith("_") or key.endswith("__error"):
            continue
        n += 1
        p = raw / rec["dest"]
        if not p.exists():
            print("MISSING  " + key)
            bad += 1
            continue
        ok, why = base.check({"kind": "pdf", "must": None}, p, rec["bytes"])
        same = rec["sha256"] == base.sha256_bytes(p.read_bytes())
        if not (ok and same):
            print("BAD      %s  %s%s" % (key, why, "" if same else "  [hash differs from the manifest]"))
            bad += 1
        d = per.setdefault(str(rec["order"]), {"files": 0, "bytes": 0})
        d["files"] += 1
        d["bytes"] += rec["bytes"]
    errs = sorted(k for k in manifest if k.endswith("__error"))
    print(json.dumps(per, sort_keys=True))
    print("%d files in the manifest, %d bad, %d with an error (%s)" % (n, bad, len(errs), ", ".join(errs[:20])))
    return 1 if bad else 0


# ---------------------------------------------------------------- selftest

def selftest():
    fails = []

    def ok(label, cond):
        print(("ok    " if cond else "FAIL  ") + label)
        if not cond:
            fails.append(label)

    ne = ('<a href="../Price_Announcements/Statistical_Uniform/Past_Years/UP200001.pdf">'
          '<a href="../Price_Announcements/Statistical_Uniform/Past_Years/UP2000.pdf">'
          '<a href="../Price_Announcements/Statistical_Uniform/Past_Years/UP202403-rev.pdf">'
          '<a href="../Price_Announcements/Statistical_Uniform/UP202610.pdf">')
    its = items_1001([("https://www.fmmone.com/Price_Announcements_Uniform.htm", ne)])
    ok("Northeast: a month, a revision, no yearly compilation, nothing after 2026-09",
       [i["key"] for i in its] == ["200001", "202403rev"])
    ok("Northeast: the relative link resolves to the site root",
       its[0]["url"] == "https://www.fmmone.com/Price_Announcements/Statistical_Uniform/Past_Years/UP200001.pdf")
    ok("Appalachian: yymm in early folders", month_from_app(2005, 5, 1) == 1)
    ok("Appalachian: mmyy in later folders", month_from_app(2026, 9, 26) == 9)
    ok("Appalachian: a name that fits neither is dropped", month_from_app(2010, 13, 40) is None)
    app = '<a href="/linkeddocs/unfprc/Uniform Price 2026/unpr0926.pdf"><a href="/linkeddocs/unfprc/Uniform Price 2026/unpr1226.pdf">'
    its = items_1005([("https://www.malouisville.com/hist_uniform_price", app)])
    ok("Appalachian: the space in the folder is quoted and December 2026 is left out",
       len(its) == 1 and "Uniform%20Price%202026" in its[0]["url"])
    atl = ('<a href="PriceAnnouncements/UniformPrice/FO6/092026uprice.pdf"><a href="PriceAnnouncements/UniformPrice/FO6/2021%20Uprice.pdf">'
           '<a href="PriceAnnouncements/UniformPrice/FO6/uprice2024.pdf"><a href="PriceAnnouncements/UniformPrice/FO7/2022uprice.pdf">')
    f6 = items_atl(1006, [("https://www.fmmatlanta.com/Price_Announcements_Uniform.htm", atl)])
    ok("Florida: one month and two yearly files, none of Southeast's",
       sorted((i["unit"], i["key"]) for i in f6) == [("month", "202609"), ("year", "2021"), ("year", "2024")])
    ca = ('<a href="/download-file/;jsessionid=ABC123?s=true&amp;folderMap=prices.statistical-uniform&amp;'
          'fileName=2026%2f202609+Pool+Price.pdf&amp;ia=inline">')
    c = items_download_file(1051, [("https://www.cafmmo.com/prices/statistical-uniform/", ca)],
                            "prices.statistical-uniform", r"(\d{4})/(?:\d{4})(\d\d) Pool Price\.pdf")
    ok("California: the session id is dropped and the month read", len(c) == 1 and "jsessionid" not in c[0]["url"]
       and c[0]["key"] == "202609")
    pnw = ('<a href="prices/ppdcomputation/ppd12405.pdf"><a href="prices/ppdcomputation/ppd2015.pdf">'
           '<a href="prices/ppdcomputation/ppd202609.pdf"><a href="prices/ppdcomputation/up202609.pdf">')
    p = items_1124([("https://fmmaseattle.com/uniform.html", pnw)])
    ok("Pacific Northwest: two yearly files and one month, no Arizona file",
       sorted((i["unit"], i["key"]) for i in p) == [("month", "202609"), ("year", "2005"), ("year", "2015")])
    sw = items_1126()
    ok("Southwest: 321 months written from the pattern",
       len(sw) == 321 and sw[-1]["url"].endswith("/2026/26PD0926.PDF") and sw[0]["url"].endswith("/2000/26PD0100.PDF"))
    inv = {1001: [item(1001, "month", "200001", "u", "a.pdf"), item(1001, "month", "200002", "u", "b.pdf")]}
    e = estimate(inv, {})
    ok("no measured file prints no estimate and is not within the cap", not e["within_cap"])
    m = {"1001_200001": {"bytes": 600_000_000, "seconds": 1.0}}
    e = estimate(inv, m)
    ok("an upper estimate above 1 GB is refused", not e["within_cap"] and e["total_bytes_upper"] == 1_200_000_000)
    m = {"1001_200001": {"bytes": 100, "seconds": 1.0}}
    ok("a small one is allowed", estimate(inv, m)["within_cap"])
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        good = b"%PDF-1.4\n" + b"x" * 5000 + b"\n%%EOF\n"
        it = item(1001, "month", "200001", "u", "a.pdf")
        (d / "1001").mkdir()
        (d / it["dest"]).write_bytes(good[:3000])
        manifest = {it["id"]: {"bytes": len(good), "sha256": base.sha256_bytes(good)}}
        okc, _ = base.check(it, d / it["dest"], manifest[it["id"]]["bytes"])
        ok("a truncated file on disk fails its check against the manifest", not okc)
        (d / it["dest"]).write_bytes(good)
        okc, _ = base.check(it, d / it["dest"], manifest[it["id"]]["bytes"])
        ok("the whole file passes", okc and base.sha256_bytes((d / it["dest"]).read_bytes()) == manifest[it["id"]]["sha256"])
        (d / it["dest"]).write_bytes(good.replace(b"xxxx", b"yyyy", 1))
        ok("a corrupted file of the right length differs in hash",
           base.sha256_bytes((d / it["dest"]).read_bytes()) != manifest[it["id"]]["sha256"])
        save_manifest({"_estimate": {"within_cap": False}}, raw=d, use_safe_write=False)
        ok("the manifest reads back", load_manifest(d)["_estimate"]["within_cap"] is False)
        # second set: the Census text and the JSON checks, and the Range bookkeeping
        cit = extra_items()[0]
        full = (CENSUS_HEADER + "\n" + "AL|01|001|Autauga County|03220|02405439|Autaugaville town|INCORPORATED PLACE|C1|A\n"
                + "AL|01|001|Autauga County|62328|02404536|Prattville city|INCORPORATED PLACE|C1|A\n").encode()
        (d / "census").mkdir()
        cp = d / cit["dest"]
        cp.write_bytes(full)
        ok("a whole Census text passes its check", check_extra(cit, cp, len(full))[0])
        cp.write_bytes(full[:-30])
        ok("a Census text cut mid-line fails its check", not check_extra(cit, cp)[0])
        cp.write_bytes(full[:-30] + b"\n")
        ok("a Census text cut mid-line fails even with a newline added (field count)", not check_extra(cit, cp)[0])
        cp.write_bytes(full.replace(b"STATE|", b"STATX|", 1))
        ok("a Census text with another header fails", not check_extra(cit, cp)[0])
        jit = [i for i in extra_items() if i["kind"] == "json"][0]
        jp = d / "v.json"
        jp.write_text('{"content_versions": []', encoding="utf-8")
        ok("a cut JSON fails its check", not check_extra(jit, jp)[0])
        jp.write_text('{"content_versions": []}', encoding="utf-8")
        ok("a whole JSON passes", check_extra(jit, jp)[0])
        ok("a 206 whose range starts where the part ends gives the total and appends",
           total_from(206, {"Content-Range": "bytes 1000-2735999/2736928"}, 1000) == (2736928, True))
        ok("a 206 starting elsewhere is not appended", total_from(206, {"Content-Range": "bytes 0-9/2736928"}, 1000)
           == (None, False))
        ok("a 200 is written fresh with its Content-Length", total_from(200, {"Content-Length": "2736928"}, 1000)
           == (2736928, False))
    print("\n%d failed" % len(fails))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    for f in ("inventory", "measure", "fetch", "verify", "selftest", "extra", "extra-verify"):
        g.add_argument("--" + f, action="store_true")
    ap.add_argument("--order", nargs="*", type=int, default=ORDERS, choices=ORDERS)
    ap.add_argument("--budget", type=float, default=480.0)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.extra:
        return cmd_extra()
    if a.extra_verify:
        return cmd_extra_verify()
    if a.inventory:
        return cmd_inventory(a.order)
    if a.measure:
        return cmd_measure(a.order)
    if a.verify:
        return cmd_verify()
    return cmd_fetch(a.order, a.budget)


if __name__ == "__main__":
    sys.exit(main())
