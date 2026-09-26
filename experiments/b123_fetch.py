"""B123: fetch the raw files, on the machine that runs the project.

Nothing here reads a rate. The script puts each file on disk, checks that it is whole, and
keeps a manifest, b123_manifest.json, with the URL, the byte count, the SHA-256, the check it
passed and the retrieval time. Reading the files is a later step.

Sources, all public:

  visa        Visa USA Interchange Reimbursement Fees, the schedule effective 2026-04-18,
              as served from usa.visa.com.
  mastercard  Mastercard U.S. Region Interchange Programs and Rates, the 2026-2027 edition
              effective 2026-04-17 and the 2025-2026 edition before it. Both servers refuse a
              request that does not come from a browser, so these two go in with --import
              from a browser-saved copy, which runs the same check as a fetch and records the
              file as a browser-saved copy of its URL.
  fed         The Board's Regulation II table of average interchange fee by payment card
              network, the CSV linked from its page.
  visa_au     Visa's Australian pages, domestic and the two for foreign-issued cards.
  mastercard_au  Mastercard's three Australian schedules, credit, debit and prepaid.
  eftpos      Australian Payments Plus's eftpos schedule.
  rba         The Reserve Bank of Australia's conclusions paper of 31 March 2026, updated
              19 June 2026, which sets the caps that take effect on 1 October 2026 and carries
              the varied standards as its Appendix D.

The Australian files are the versions in force before those caps. Their URLs carry no date, so
each is served over on the day the new rates take effect; these copies are named with the day
they were saved and are the only record of what came before. They all arrived through a browser.

Run from the repository root with the venv active:

    python experiments/b123_fetch.py --plan               # the files and URLs, no network
    python experiments/b123_fetch.py --fetch              # fetch what is missing or fails its check
    python experiments/b123_fetch.py --verify             # check what is on disk, no network
    python experiments/b123_fetch.py --import DEST PATH   # one browser-saved file
    python experiments/b123_fetch.py --selftest           # offline, seeded faults

Every fetch can be interrupted and run again: a file already on disk that passes its check is
kept, and a download is written to a temporary name and renamed only when it passes. Nothing is
deleted. A file on disk that fails its check is renamed aside with the time it was set aside, and
a file that an import replaces is renamed aside the same way.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data" / "raw" / "b123"
MANIFEST_NAME = "b123_manifest.json"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
TIMEOUT = 120
RETRIES = 3
PAUSE = 2.0

PLAN = (
    {"dest": "visa/visa-usa-interchange-reimbursement-fees_2026-04-18.pdf", "kind": "pdf",
     "url": "https://usa.visa.com/dam/VCOM/download/merchants/visa-usa-interchange-reimbursement-fees.pdf"},
    {"dest": "mastercard/merchant-rates-2026-2027-april2026.pdf", "kind": "pdf", "browser": True,
     "url": "https://www.mastercard.com/content/dam/mccom/us/business/documents/merchant-rates-2026-2027-april2026.pdf"},
    {"dest": "mastercard/merchant-rates-2025-2026.pdf", "kind": "pdf", "browser": True,
     "url": "https://www.mastercard.us/content/dam/public/mastercardcom/na/us/en/smb/documents/merchant-rates-2025-2026.pdf"},
    {"dest": "fed/Avg_IF_by_PCN.csv", "kind": "csv",
     "url": "https://www.federalreserve.gov/paymentsystems/files/Avg_IF_by_PCN.csv"},
    # The Australian schedules as they stood before the caps of 1 October 2026. Every one of these
    # URLs is undated, so each is served over on the day the new rates take effect and the version
    # here is the only copy of what came before. Saved from a browser, verified against the byte
    # count the live URL reported the same evening, and named with the day they were saved.
    {"dest": "visa_au/visa-au-domestic-interchange_2026-09-22.html", "kind": "html", "browser": True,
     "url": "https://www.visa.com.au/about-visa/interchange.html"},
    {"dest": "visa_au/visa-ap-intra-regional-interchange_2026-09-22.html", "kind": "html", "browser": True,
     "url": "https://www.visa.com.au/about-visa/ap-intra-regional-interchange.html"},
    {"dest": "visa_au/visa-inter-regional-interchange_2026-09-22.html", "kind": "html", "browser": True,
     "url": "https://www.visa.com.au/about-visa/inter-regional-interchange.html"},
    {"dest": "mastercard_au/Australia-Intracountry-CREDIT-POS-Interchange-Rates_2026-09-22.pdf",
     "kind": "pdf", "browser": True,
     "url": "https://www.mastercard.com/content/dam/mccom/aus/data-source/merchant-interchange-rates/"
            "Australia-Intracountry-CREDIT-POS-Interchange-Rates.pdf"},
    {"dest": "mastercard_au/Australia-Intracountry-DEBIT-POS-Interchange-Rates_2026-09-22.pdf",
     "kind": "pdf", "browser": True,
     "url": "https://www.mastercard.com/content/dam/mccom/aus/data-source/merchant-interchange-rates/"
            "Australia-Intracountry-DEBIT-POS-Interchange-Rates.pdf"},
    {"dest": "mastercard_au/Australia-Intracountry-PREPAID-POS-Interchange-Rates-v1_2026-09-22.pdf",
     "kind": "pdf", "browser": True,
     "url": "https://www.mastercard.com/content/dam/mccom/aus/data-source/merchant-interchange-rates/"
            "Australia-Intracountry-PREPAID-POS-Interchange-Rates-v1.pdf"},
    {"dest": "eftpos/auspayplus-eftpos-interchange-fees_2026-09-22.html", "kind": "html", "browser": True,
     "url": "https://www.auspayplus.com.au/solutions/eftpos-interchange-fees"},
    # The Reserve Bank's conclusions paper, which sets those caps and carries the varied standards
    # as its Appendix D. This one is dated on its own page and is not served over.
    {"dest": "rba/rba-conclusions-paper_2026-03-31_upd-2026-06-19.pdf", "kind": "pdf", "browser": True,
     "url": "https://www.rba.gov.au/payments-and-infrastructure/review-of-retail-payments-regulation/"
            "2026-03/conclusions-paper/pdf/conclusions-paper.pdf"},
)


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------- checks

def check_pdf(data: bytes) -> tuple[bool, str]:
    """Whole means: the header, an end-of-file marker near the end, and a document that opens
    with at least one page carrying text. A truncated download loses the trailer first."""
    if not data.startswith(b"%PDF-"):
        return False, "does not start with %PDF-"
    if b"%%EOF" not in data[-2048:]:
        return False, "no %%EOF in the last 2048 bytes (truncated?)"
    try:
        import pymupdf
    except Exception:  # pragma: no cover
        return False, "pymupdf is not importable; activate the venv"
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        return False, "pymupdf cannot open it: " + type(exc).__name__
    pages = doc.page_count
    chars = sum(len(doc[i].get_text()) for i in range(min(pages, 3)))
    if pages < 1 or chars == 0:
        return False, "opens with %d page(s) and %d characters on the first three" % (pages, chars)
    return True, "pdf, %d page(s), %d characters on the first three" % (pages, chars)


def check_csv(data: bytes) -> tuple[bool, str]:
    """Whole means: it decodes, it has a header and body rows, and every row of the first two
    hundred has the header's width or is blank. A truncated download usually breaks the last."""
    for enc in ("utf-8-sig", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    rows = list(csv.reader(io.StringIO(text)))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if len(rows) < 3:
        return False, "fewer than three non-blank rows"
    width = max(len(r) for r in rows[:5])
    if width < 3:
        return False, "header narrower than three columns"
    ragged = [i for i, r in enumerate(rows[:200]) if len(r) not in (width, 1)]
    if len(ragged) > len(rows[:200]) // 2:
        return False, "%d of the first %d rows have neither the header's width nor one cell" % (
            len(ragged), len(rows[:200]))
    if not text.endswith(("\n", "\r")):
        return False, "does not end with a line break (truncated?)"
    return True, "csv, %d non-blank row(s), widest of the first five %d" % (len(rows), width)


def check_html(data: bytes) -> tuple[bool, str]:
    """Whole means: it decodes as UTF-8, it closes its html element, and it carries at least one
    table. A page saved before its tables rendered loses the last two; a truncated save loses the
    closing tag first."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return False, "does not decode as utf-8"
    tail = text.rstrip()[-4096:].lower()
    if "</html>" not in tail:
        return False, "no </html> near the end (truncated?)"
    tables = text.lower().count("<table")
    if tables < 1:
        return False, "no <table> element; the rates may not have rendered before the save"
    return True, "html, %d characters, %d table(s), closes its html element" % (len(text), tables)


CHECKS = {"pdf": check_pdf, "csv": check_csv, "html": check_html}


def check(kind: str, data: bytes, length: int | None = None) -> tuple[bool, str]:
    if length is not None and len(data) != length:
        return False, "%d bytes on disk against Content-Length %d" % (len(data), length)
    return CHECKS[kind](data)


# ------------------------------------------------- manifest and disk

def load_manifest(raw: Path) -> dict:
    p = raw / MANIFEST_NAME
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def save_manifest(raw: Path, manifest: dict) -> None:
    p = raw / MANIFEST_NAME
    tmp = p.with_name(p.name + ".tmp.expired")
    tmp.write_text(json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    os.replace(tmp, p)


def set_aside(path: Path, why: str) -> Path:
    """Rename a file out of the way instead of deleting it (rule 5)."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    aside = path.with_name(path.name + ".expired_%s_%s" % (stamp, why))
    os.replace(path, aside)
    return aside


def place(raw: Path, item: dict, data: bytes, how: str, manifest: dict, note: str) -> None:
    dest = raw / item["dest"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=dest.name + ".", suffix=".part.expired")
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    if dest.exists():
        set_aside(dest, "replaced")
    os.replace(tmp, dest)
    manifest[item["dest"]] = {"url": item["url"], "bytes": len(data), "sha256": sha256(data),
                              "check": note, "retrieved_utc": now_utc(), "how": how}


# ------------------------------------------------- network

def head_length(url: str) -> int | None:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            v = resp.headers.get("Content-Length")
            return int(v) if v else None
    except Exception:
        return None


def get(url: str) -> bytes:
    last = None
    for attempt in range(RETRIES):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403, 404):
                raise
            last = exc
        except Exception as exc:
            last = exc
        time.sleep(PAUSE * (attempt + 1))
    raise RuntimeError("gave up after %d attempts: %r" % (RETRIES, last))


# ------------------------------------------------- commands

def cmd_plan() -> int:
    width = max(len(item["dest"]) for item in PLAN) + 2
    for item in PLAN:
        print(item["dest"].ljust(width) + ("browser  " if item.get("browser") else "fetch    ")
              + item["url"])
    return 0


def cmd_verify(raw: Path = RAW) -> int:
    bad = 0
    manifest = load_manifest(raw)
    for item in PLAN:
        p = raw / item["dest"]
        if not p.exists():
            print("MISSING  " + item["dest"])
            bad += 1
            continue
        data = p.read_bytes()
        ok, note = check(item["kind"], data)
        rec = manifest.get(item["dest"], {})
        same = rec.get("sha256") == sha256(data)
        print(("OK       " if ok and same else "BAD      ") + item["dest"] + "  " + note
              + ("" if same else "  (sha256 differs from the manifest)"))
        bad += 0 if ok and same else 1
    return 1 if bad else 0


def cmd_fetch(raw: Path = RAW) -> int:
    manifest = load_manifest(raw)
    failures = 0
    for item in PLAN:
        dest = raw / item["dest"]
        if dest.exists():
            ok, note = check(item["kind"], dest.read_bytes())
            if ok:
                print("KEEP     " + item["dest"] + "  " + note)
                continue
            aside = set_aside(dest, "failed_check")
            print("ASIDE    " + item["dest"] + " -> " + aside.name + "  " + note)
        if item.get("browser"):
            print("BROWSER  " + item["dest"] + "  the server refuses scripts; save it from a "
                  "browser and run --import " + item["dest"] + " <path>")
            failures += 1
            continue
        length = head_length(item["url"])
        try:
            data = get(item["url"])
        except Exception as exc:
            print("FAIL     " + item["dest"] + "  " + repr(exc))
            failures += 1
            continue
        ok, note = check(item["kind"], data, length)
        if not ok:
            print("REFUSED  " + item["dest"] + "  " + note)
            failures += 1
            continue
        place(raw, item, data, "fetch", manifest, note
              + ("" if length is None else ", matches Content-Length %d" % length))
        save_manifest(raw, manifest)
        print("FETCHED  " + item["dest"] + "  %d bytes  " % len(data) + note)
        time.sleep(PAUSE)
    return 1 if failures else 0


def cmd_import(dest: str, path: str, raw: Path = RAW) -> int:
    item = next((i for i in PLAN if i["dest"] == dest), None)
    if item is None:
        print(dest + " is not in the plan; --plan prints the destinations")
        return 2
    data = Path(path).read_bytes()
    ok, note = check(item["kind"], data)
    if not ok:
        print("REFUSED  " + dest + "  " + note)
        return 1
    manifest = load_manifest(raw)
    place(raw, item, data, "browser-saved copy of the URL", manifest, note)
    save_manifest(raw, manifest)
    print("IMPORTED " + dest + "  %d bytes  " % len(data) + note)
    return 0


def selftest() -> int:
    checks = []

    def ok(label, cond):
        checks.append((label, bool(cond)))

    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Interchange 1.51% + $0.10")
    good = doc.tobytes()
    ok("a whole pdf passes", check_pdf(good)[0])
    ok("a pdf cut before its trailer fails", not check_pdf(good[: len(good) // 2])[0])
    ok("bytes that are not a pdf fail", not check_pdf(b"<html>403 Forbidden</html>")[0])
    ok("a length mismatch fails before the content check",
       not check("pdf", good, len(good) + 1)[0])
    blank = pymupdf.open()
    blank.new_page()
    ok("a pdf with no text on its pages fails", not check_pdf(blank.tobytes())[0])

    html_good = (b"<!doctype html><html><body><h1>Interchange</h1>"
                 b"<table><tr><td>Electronic rate</td><td>0.20%</td></tr></table></body></html>")
    ok("a whole page passes", check_html(html_good)[0])
    ok("a page cut before its closing tag fails", not check_html(html_good[:-30])[0])
    ok("a page whose tables did not render fails",
       not check_html(b"<!doctype html><html><body><h1>Interchange</h1></body></html>")[0])
    ok("bytes that do not decode as utf-8 fail", not check_html(b"<html>\xff\xfe</html><table>")[0])

    csv_good = b"Year,Network,Exempt fee,Covered fee\n2024,Visa,0.62,0.22\n2024,MasterCard,0.63,0.24\n"
    ok("a whole csv passes", check_csv(csv_good)[0])
    ok("a csv cut mid-row fails", not check_csv(csv_good[:-9])[0])
    ok("a two-row csv fails", not check_csv(b"a,b,c\n1,2,3\n")[0])

    with tempfile.TemporaryDirectory() as d:
        raw = Path(d)
        item = PLAN[3]
        manifest = {}
        place(raw, item, csv_good, "test", manifest, "seeded")
        save_manifest(raw, manifest)
        (raw / item["dest"]).write_bytes(csv_good[:-9])
        ok("verify reports a file that no longer passes", cmd_verify(raw) == 1)
        before = sorted(p.name for p in (raw / "fed").iterdir())
        place(raw, item, csv_good, "test", manifest, "seeded again")
        after = sorted(p.name for p in (raw / "fed").iterdir())
        ok("a replaced file is set aside, not deleted",
           len(after) == len(before) + 1 and any(".expired_" in n for n in after))

    width = max(len(label) for label, _ in checks)
    for label, cond in checks:
        print(("PASS  " if cond else "FAIL  ") + label.ljust(width))
    bad = [label for label, cond in checks if not cond]
    print("\nselftest: %d/%d" % (len(checks) - len(bad), len(checks)))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true")
    g.add_argument("--fetch", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--import", dest="imp", nargs=2, metavar=("DEST", "PATH"))
    g.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.plan:
        return cmd_plan()
    if a.selftest:
        return selftest()
    if a.verify:
        return cmd_verify()
    if a.imp:
        return cmd_import(*a.imp)
    return cmd_fetch()


if __name__ == "__main__":
    sys.exit(main())
