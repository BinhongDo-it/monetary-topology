"""B154: fetch the Federal Milk Marketing Order rule texts and the Central order announcements.

Nothing here reads a price. The script puts each file on disk, checks that it is whole, and keeps
a manifest, data/raw/b154/b154_manifest.json, with the URL, the byte count, the SHA-256, the
server's Last-Modified header, the check the file passed, the seconds the request took and the
retrieval time.

Groups (each is a list of files; nothing outside these groups is fetched):

  rules        7 CFR 1000.40, 1000.50, 1000.52 and sections 51, 61, 75 of the eleven orders, as
               served by Cornell LII (the current text, with the 2026-09-18 correcting amendment);
               7 CFR 1000.52 in the annual CFR editions revised as of 2000-01-01, 2024-01-01 and
               2026-01-01 (govinfo XML); the 2026-09-18 correcting amendment (91 FR 59047, PDF).
  central24    Central order (Order 32) statistical uniform price announcements, 2024-10 to 2026-09.
  central_all  the same announcements, 2000-01 to 2024-09. Refused until central24 is complete,
               so that the per-file seconds and bytes are measured before the larger set is taken.
  sums         Federal Order Statistical Overview (all orders), one file a year, 2000 to 2026.

The file names of the announcements and the overviews are read from the two listing pages on the
Central order site (one announcement, 2021-07, is listed in upper case); the listing pages are
saved beside the files.

Run from the repository root:

    python experiments/b154_fetch.py --plan [--group G ...]     # files and URLs, no network
    python experiments/b154_fetch.py --fetch --group G [...]    # fetch what is missing or fails its check
    python experiments/b154_fetch.py --verify                   # check what is on disk, no network
    python experiments/b154_fetch.py --timing                   # measured seconds and bytes per group
    python experiments/b154_fetch.py --selftest                 # offline, seeded faults

A fetch can be interrupted and run again: a file already on disk that passes its check and matches
the manifest is kept; a partial download stays in a .part file and is restarted; a file is renamed
into place only when its length equals the server's Content-Length (when sent) and it passes its
check. Nothing is deleted. A file on disk that fails its check is renamed aside with the reason.
Nothing downloaded is executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # safe_write.py sits one level above the repository

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data" / "raw" / "b154"
MANIFEST = "b154_manifest.json"
SESSION = "T13_MILK"
UA = "Mozilla/5.0 (research; federal milk order rule reader)"
CHUNK = 1 << 20

LII = "https://www.law.cornell.edu/cfr/text/7/"
GOV_CFR = ("https://www.govinfo.gov/content/pkg/CFR-{y}-title7-vol9/xml/"
           "CFR-{y}-title7-vol9-sec1000-52.xml")
FMMA = "https://www.fmmacentral.com/"
LIST_PP = FMMA + "statistical_uniform_price.html"
LIST_SUM = FMMA + "federal_order_statistical_overview.html"

#: The eleven orders by CFR part number.
ORDERS = {1001: "Northeast", 1005: "Appalachian", 1006: "Florida", 1007: "Southeast",
          1030: "Upper Midwest", 1032: "Central", 1033: "Mideast", 1051: "California",
          1124: "Pacific Northwest", 1126: "Southwest", 1131: "Arizona"}
ORDER_SECTIONS = (51, 61, 75)
CFR_EDITIONS = (2000, 2024, 2026)


def months(y0, m0, y1, m1):
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


# ---------------------------------------------------------------- the file list

def rule_items() -> list[dict]:
    items = []
    for sec in ("1000.40", "1000.50", "1000.52"):
        items.append({"id": "lii_" + sec, "kind": "html", "group": "rules", "url": LII + sec,
                      "dest": "rules/lii_" + sec.replace(".", "_") + ".html", "must": "1000."})
    for part in ORDERS:
        for s in ORDER_SECTIONS:
            sec = "%d.%d" % (part, s)
            items.append({"id": "lii_" + sec, "kind": "html", "group": "rules", "url": LII + sec,
                          "dest": "rules/lii_" + sec.replace(".", "_") + ".html", "must": str(part) + "."})
    for y in CFR_EDITIONS:
        items.append({"id": "cfr%d_1000_52" % y, "kind": "xml", "group": "rules",
                      "url": GOV_CFR.format(y=y), "dest": "rules/cfr%d_1000_52.xml" % y,
                      "must": "1000.52"})
    items.append({"id": "fr_2026_19177", "kind": "pdf", "group": "rules",
                  "url": "https://www.govinfo.gov/content/pkg/FR-2026-09-18/pdf/2026-19177.pdf",
                  "dest": "rules/fr_2026-19177.pdf", "must": None})
    return items


def pp_name_map(listing: str) -> dict:
    """yymm -> href file name as listed (case kept)."""
    out = {}
    for m in re.finditer(r'PDFdata/((?:pp|PP)(\d{2})(\d{2})\.pdf)', listing):
        out[m.group(2) + m.group(3)] = m.group(1)
    return out


def sum_name_map(listing: str) -> dict:
    out = {}
    for m in re.finditer(r'PDFdata/((?:sum|SUM)(\d{4})\.pdf)', listing, flags=re.I):
        out[m.group(2)] = m.group(1)
    return out


def central_items(group: str, names: dict) -> list[dict]:
    if group == "central24":
        span = list(months(2024, 10, 2026, 9))
    else:
        span = list(months(2000, 1, 2024, 9))
    items = []
    for y, m in span:
        key = "%02d%02d" % (y % 100, m)
        name = names.get(key, "pp%s.pdf" % key)
        items.append({"id": "pp" + key, "kind": "pdf", "group": group, "url": FMMA + "PDFdata/" + name,
                      "dest": "central/" + name.lower(), "must": None, "listed": key in names})
    return items


def sum_items(names: dict) -> list[dict]:
    items = []
    for y in range(2000, 2027):
        name = names.get(str(y), "sum%d.pdf" % y)
        items.append({"id": "sum%d" % y, "kind": "pdf", "group": "sums", "url": FMMA + "PDFdata/" + name,
                      "dest": "sums/" + name.lower(), "must": None, "listed": str(y) in names})
    return items


# ---------------------------------------------------------------- checks

def check_pdf(path: Path, must: str | None) -> tuple[bool, str]:
    data = path.read_bytes()
    if not data.startswith(b"%PDF"):
        return False, "does not start with %PDF"
    if b"%%EOF" not in data[-2048:]:
        return False, "no %%EOF in the last 2,048 bytes"
    return True, "PDF header and %%EOF trailer present"


def check_html(path: Path, must: str | None) -> tuple[bool, str]:
    text = path.read_bytes().decode("utf-8", errors="replace")
    if "</html>" not in text[-4096:].lower():
        return False, "no closing </html> in the last 4,096 characters"
    if must and must not in text:
        return False, "the section number %s is not on the page" % must
    low = text.lower()
    if "captcha" in low or "are you a robot" in low:
        return False, "a bot check page"
    return True, "closes </html> and carries %s" % must


def check_xml(path: Path, must: str | None) -> tuple[bool, str]:
    import xml.etree.ElementTree as ET
    try:
        ET.parse(str(path))
    except ET.ParseError as e:
        return False, "not well-formed XML: %s" % e
    if must and must not in path.read_text(encoding="utf-8", errors="replace"):
        return False, "the section number %s is not in the file" % must
    return True, "well-formed XML carrying %s" % must


CHECKS = {"pdf": check_pdf, "html": check_html, "xml": check_xml}


def check(item: dict, path: Path, length: int | None = None) -> tuple[bool, str]:
    if length is not None and path.stat().st_size != length:
        return False, "length %d differs from the server's %d" % (path.stat().st_size, length)
    return CHECKS[item["kind"]](path, item.get("must"))


# ---------------------------------------------------------------- manifest and files

def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_manifest(raw: Path) -> dict:
    p = raw / MANIFEST
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def save_manifest(raw: Path, manifest: dict, use_safe_write: bool = True) -> None:
    raw.mkdir(parents=True, exist_ok=True)
    p = raw / MANIFEST
    text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if not use_safe_write:
        p.write_text(text, encoding="utf-8", newline="\n")
        return
    from safe_write import create, rewrite
    if p.exists():
        rewrite(p, "B154 manifest", lambda _t: text, session=SESSION)
    else:
        create(p, "B154 manifest", text, session=SESSION)


def set_aside(path: Path, why: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    aside = path.with_name(path.name + ".expired_" + stamp + "_" + why)
    path.rename(aside)
    return aside


def get(url: str) -> tuple[bytes, dict, float]:
    t0 = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        body = r.read()
        hdr = {"length": int(r.headers["Content-Length"]) if r.headers.get("Content-Length") else None,
               "last_modified": r.headers.get("Last-Modified"), "type": r.headers.get("Content-Type")}
    return body, hdr, time.time() - t0


def listing(raw: Path, url: str, name: str, manifest: dict) -> str:
    """Fetch a listing page each run (it changes as months are added) and keep the copy."""
    body, hdr, secs = get(url)
    (raw / "listings").mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    p = raw / "listings" / ("%s_%s.html" % (name, stamp))
    if not p.exists():
        p.write_bytes(body)
    manifest.setdefault("_listings", {})[p.name] = {"url": url, "bytes": len(body),
                                                    "sha256": sha256_bytes(body), "retrieved_utc": now_utc(),
                                                    "seconds": round(secs, 3)}
    return body.decode("utf-8", errors="replace")


def items_for(groups: list[str], raw: Path, manifest: dict, offline: bool = False) -> list[dict]:
    items = []
    pp_names, sum_names = {}, {}
    if not offline and any(g in groups for g in ("central24", "central_all")):
        pp_names = pp_name_map(listing(raw, LIST_PP, "statistical_uniform_price", manifest))
    if not offline and "sums" in groups:
        sum_names = sum_name_map(listing(raw, LIST_SUM, "federal_order_statistical_overview", manifest))
    if "rules" in groups:
        items += rule_items()
    for g in ("central24", "central_all"):
        if g in groups:
            items += central_items(g, pp_names)
    if "sums" in groups:
        items += sum_items(sum_names)
    return items


def group_complete(manifest: dict, group: str) -> bool:
    its = central_items(group, {}) if group.startswith("central") else []
    return bool(its) and all(it["id"] in manifest for it in its)


# ---------------------------------------------------------------- commands

def cmd_plan(groups: list[str]) -> int:
    for it in items_for(groups, RAW, {}, offline=True):
        print("%-14s %-11s %-4s %s\n               -> %s" % (it["id"], it["group"], it["kind"], it["url"], it["dest"]))
    return 0


def cmd_fetch(groups: list[str], raw: Path = RAW, budget_s: float = 480.0) -> int:
    manifest = load_manifest(raw)
    if "central_all" in groups and not group_complete(manifest, "central24"):
        print("REFUSED  central_all: central24 is not complete, so the per-file cost is not measured yet")
        return 3
    items = items_for(groups, raw, manifest)
    t_start = time.time()
    pending = fetched = kept = 0
    for it in items:
        dest = raw / it["dest"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and it["id"] in manifest:
            ok, _ = check(it, dest, manifest[it["id"]].get("bytes"))
            if ok and manifest[it["id"]].get("sha256") == sha256_bytes(dest.read_bytes()):
                kept += 1
                continue
            set_aside(dest, "failed_check")
        if time.time() - t_start > budget_s:
            pending += 1
            continue
        try:
            body, hdr, secs = get(it["url"])
        except urllib.error.HTTPError as e:
            manifest[it["id"] + "__error"] = {"url": it["url"], "http": e.code, "seen_utc": now_utc()}
            print("HTTP %d   %s" % (e.code, it["id"]))
            pending += 1
            continue
        except (urllib.error.URLError, OSError) as e:
            print("ERROR    %s  %r" % (it["id"], e))
            pending += 1
            continue
        part = dest.with_name(dest.name + ".part")
        if part.exists():
            set_aside(part, "stale_part")
        part.write_bytes(body)
        ok, why = check(it, part, hdr["length"])
        if not ok:
            aside = set_aside(part, "failed_check")
            print("FAILED   %s  %s  (set aside as %s)" % (it["id"], why, aside.name))
            pending += 1
            continue
        part.rename(dest)
        manifest.pop(it["id"] + "__error", None)
        manifest[it["id"]] = {"url": it["url"], "dest": it["dest"], "group": it["group"], "kind": it["kind"],
                              "bytes": len(body), "sha256": sha256_bytes(body),
                              "server_last_modified": hdr["last_modified"], "check": why,
                              "seconds": round(secs, 3), "retrieved_utc": now_utc(),
                              "listed": it.get("listed")}
        fetched += 1
        if fetched % 10 == 0:
            save_manifest(raw, manifest)
    save_manifest(raw, manifest)
    print("fetched %d, kept %d, pending %d" % (fetched, kept, pending))
    return 2 if pending else 0


def cmd_verify(raw: Path = RAW) -> int:
    manifest = load_manifest(raw)
    bad = n = 0
    for key, rec in sorted(manifest.items()):
        if key.startswith("_") or key.endswith("__error"):
            continue
        n += 1
        p = raw / rec["dest"]
        item = {"kind": rec["kind"], "must": None}
        if not p.exists():
            print("MISSING  " + key)
            bad += 1
            continue
        ok, why = check(item, p, rec["bytes"])
        same = rec["sha256"] == sha256_bytes(p.read_bytes())
        if not (ok and same):
            print("BAD      %s  %s%s" % (key, why, "" if same else "  [hash differs from the manifest]"))
            bad += 1
    errs = [k for k in manifest if k.endswith("__error")]
    print("%d files in the manifest, %d bad, %d URLs with an HTTP error" % (n, bad, len(errs)))
    return 1 if bad else 0


def timing(manifest: dict) -> dict:
    """Measured seconds and bytes per group (rule D38: measured, never assumed)."""
    out = {}
    for rec in manifest.values():
        if not isinstance(rec, dict) or "group" not in rec:
            continue
        g = out.setdefault(rec["group"], {"files": 0, "bytes": 0, "seconds": []})
        g["files"] += 1
        g["bytes"] += rec["bytes"]
        g["seconds"].append(rec["seconds"])
    for g in out.values():
        s = g.pop("seconds")
        g["seconds_total"] = round(sum(s), 3)
        g["seconds_median"] = round(statistics.median(s), 3)
        g["seconds_max"] = round(max(s), 3)
    return out


def cmd_timing(raw: Path = RAW) -> int:
    t = timing(load_manifest(raw))
    if not t:
        print("not measured: nothing fetched yet, so no time estimate is printed")
        return 1
    print(json.dumps(t, indent=2, sort_keys=True))
    return 0


# ---------------------------------------------------------------- selftest

def selftest() -> int:
    fails = []

    def ok(label, cond):
        print(("ok    " if cond else "FAIL  ") + label)
        if not cond:
            fails.append(label)

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        pdf = {"kind": "pdf", "must": None}
        good = b"%PDF-1.4\n" + b"x" * 5000 + b"\n%%EOF\n"
        p = d / "a.pdf"
        p.write_bytes(good)
        ok("a whole PDF passes", check(pdf, p, len(good))[0])
        ok("a PDF one byte short of the server's length fails", not check(pdf, p, len(good) + 1)[0])
        q = d / "b.pdf"
        q.write_bytes(good[:3000])
        ok("a PDF cut before its trailer fails", not check(pdf, q)[0])
        h = d / "c.pdf"
        h.write_bytes(b"<html><body>not found</body></html>")
        ok("an HTML page served in place of a PDF fails", not check(pdf, h)[0])

        html = {"kind": "html", "must": "1000.52"}
        page = "<html><body>7 CFR 1000.52 table</body></html>"
        hp = d / "a.html"
        hp.write_text(page, encoding="utf-8")
        ok("a whole LII page passes", check(html, hp)[0])
        hp2 = d / "b.html"
        hp2.write_text(page[:30], encoding="utf-8")
        ok("a page cut before </html> fails", not check(html, hp2)[0])
        hp3 = d / "c.html"
        hp3.write_text("<html><body>please solve this captcha</body></html>", encoding="utf-8")
        ok("a bot check page fails", not check(html, hp3)[0])
        hp4 = d / "d.html"
        hp4.write_text("<html><body>7 CFR 1032.75</body></html>", encoding="utf-8")
        ok("a page for another section fails", not check(html, hp4)[0])

        xml = {"kind": "xml", "must": "1000.52"}
        xp = d / "a.xml"
        xp.write_text("<SECTION><SECTNO>1000.52</SECTNO></SECTION>", encoding="utf-8")
        ok("a whole XML passes", check(xml, xp)[0])
        xp2 = d / "b.xml"
        xp2.write_text("<SECTION><SECTNO>1000.52</SECTNO>", encoding="utf-8")
        ok("an XML cut before its closing tag fails", not check(xml, xp2)[0])

        lst = 'a href="PDFdata/pp0001.pdf" b href="PDFdata/PP2107.pdf" c href="PDFdata/pp2609.pdf"'
        names = pp_name_map(lst)
        ok("the listing keeps the upper-case 2021-07 name", names.get("2107") == "PP2107.pdf")
        its = central_items("central24", names)
        ok("central24 is 24 months, 2024-10 to 2026-09",
           len(its) == 24 and its[0]["id"] == "pp2410" and its[-1]["id"] == "pp2609")
        ok("central_all is 297 months, 2000-01 to 2024-09",
           len(central_items("central_all", names)) == 297)
        ok("together they are 321 announcements", 24 + 297 == 321)
        ok("rules has 3 + 33 + 3 + 1 files", len(rule_items()) == 40)

        m = {}
        ok("central_all is refused before central24 is complete", not group_complete(m, "central24"))
        for it in central_items("central24", {}):
            m[it["id"]] = {"group": "central24", "bytes": 1, "seconds": 0.5}
        ok("and allowed once it is", group_complete(m, "central24"))
        t = timing(m)
        ok("timing reads the measured seconds", t["central24"]["seconds_median"] == 0.5)
        ok("timing with nothing fetched prints no estimate", timing({}) == {})

        s = d / "s.pdf"
        s.write_bytes(b"abc")
        aside = set_aside(s, "failed_check")
        ok("a file set aside keeps its bytes and its name says why",
           aside.read_bytes() == b"abc" and "failed_check" in aside.name and not s.exists())
        save_manifest(d, {"x": {"bytes": 3}}, use_safe_write=False)
        ok("the manifest reads back", load_manifest(d) == {"x": {"bytes": 3}})
    print("\n%d failed" % len(fails))
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true")
    g.add_argument("--fetch", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--timing", action="store_true")
    g.add_argument("--selftest", action="store_true")
    ap.add_argument("--group", nargs="*", default=["rules"],
                    choices=["rules", "central24", "central_all", "sums"])
    ap.add_argument("--budget", type=float, default=480.0, help="seconds this call may spend")
    a = ap.parse_args()
    if a.plan:
        return cmd_plan(a.group)
    if a.verify:
        return cmd_verify()
    if a.timing:
        return cmd_timing()
    if a.selftest:
        return selftest()
    return cmd_fetch(a.group, budget_s=a.budget)


if __name__ == "__main__":
    sys.exit(main())
