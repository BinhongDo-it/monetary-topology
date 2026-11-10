"""B147: fetch the hospital machine-readable files, on the machine that runs the project.

Nothing here reads a price. The script puts each file on disk, checks that it is whole, and keeps
a manifest, data/raw/b147/b147_manifest.json, with the URL, the byte count, the SHA-256, the
server's Last-Modified header, the check the file passed and the retrieval time. These addresses
carry no version and each hospital overwrites its file in place at least once a year, so the hash
and the retrieval time are the only record of which edition was read.

Sources, each a hospital's own site (the address is the mrf-url line of the cms-hpt.txt at the
root of that site, which is saved beside the file) or the CMS template repository:

  garfield   Garfield County Health Center, Jordan, Montana. Every payer column is a percentage
             of billed charges, so the file is the zero calibration.
  mh_tmc     Memorial Hermann - Texas Medical Center, Houston, one campus of a 19-location system.
  ohsu       Oregon Health and Science University, Portland, a teaching hospital (a zip).
  deaconess  Deaconess Regional Medical Center, Bozeman, Montana (JSON).
  cvmc       Central Vermont Medical Center, Berlin, Vermont, a community hospital.
  cheshire   Cheshire Medical Center, Keene, New Hampshire (a zip).
  dict_csv   CMS data dictionary for the CSV template.
  dict_json  CMS data dictionary for the JSON template.
  uihc       University of Iowa Health Care Medical Center, Iowa City, Iowa (main campus).
  uihc_dt    University of Iowa Health Care Medical Center Downtown, Iowa City, Iowa.
  asp_*      CMS Medicare Part B drug payment limit files, one per quarter (reference tables,
             not hospital files; they sit under data/raw/b147/cms_asp/).

The two Iowa files are 1,597,353,362 and 1,583,312,047 bytes (HEAD on 2026-10-13 and 2026-10-14).
They were left on the server in the first round by the 300 MB rule and fetched on 2026-10-14; each
carries its own byte ceiling (max_bytes), every other item keeps the 300 MB rule.

  clfs_*     CMS Clinical Laboratory Fee Schedule files, one per quarter (reference tables, under
             data/raw/b147/clfs/). Their links on cms.gov go through a page that asks the reader to
             accept the AMA CPT licence; that licence was accepted by hand in a browser on 2026-10-29,
             after which the page hands the browser the zip at its own address with
             ?agree=yes&next=Accept. This script fetches that address; it accepts nothing itself.

Run from the repository root:

    python experiments/b147_fetch.py --plan       # the files and URLs, no network
    python experiments/b147_fetch.py --fetch      # fetch what is missing or fails its check
    python experiments/b147_fetch.py --verify     # check what is on disk, no network
    python experiments/b147_fetch.py --selftest   # offline, seeded faults

A fetch can be interrupted and run again: bytes already received stay in a .part file and the
next run asks the server for the rest with a Range header; a file is renamed into place only when
its length equals the server's Content-Length and it passes its check. Nothing is deleted. A file
on disk that fails its check is renamed aside with the time it was set aside. Nothing downloaded
is executed, and archives are opened only to test their checksums and list their members.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data" / "raw" / "b147"
MANIFEST = "b147_manifest.json"
UA = "Mozilla/5.0 (research; hospital price transparency file reader)"
MAX_BYTES = 300 * 1024 * 1024
CHUNK = 1 << 20
MD = ".md"      # the two dictionary files keep the names they have at the source

MH = ("https://memorialhermann.org/-/media/memorial-hermann/org/files/patients-and-visitors/"
      "cms-standard-hospital-charges/")
ITEMS = [
    {"id": "garfield", "kind": "csv", "dest": "garfield/816001366_garfield-county-health-center_standardcharges.csv",
     "url": "https://garfieldcountymt.gov/wp-content/uploads/2026/01/"
            "816001366_garfield-county-health-center_standardcharges.csv",
     "index": None, "who": "Garfield County Health Center, Jordan, Montana"},
    {"id": "mh_tmc", "kind": "csv", "dest": "mh_tmc/741152597_memorial-hermann-texas-medical-center_standardcharges.csv",
     "url": MH + "741152597_memorial-hermann-texas-medical-center_standardcharges.ashx",
     "index": "https://memorialhermann.org/cms-hpt.txt", "who": "Memorial Hermann - Texas Medical Center, Houston, Texas"},
    {"id": "ohsu", "kind": "zip", "dest": "ohsu/931176109_Oregon-Health-and-Science-University_standardcharges.zip",
     "url": "https://www.ohsu.edu/sites/default/files/custom/"
            "931176109_Oregon-Health-and-Science-University_standardcharges.zip",
     "index": "https://www.ohsu.edu/cms-hpt.txt", "who": "Oregon Health and Science University, Portland, Oregon"},
    {"id": "deaconess", "kind": "json", "dest": "deaconess/474717998_deaconess-regional-medical-center_standardcharges.json",
     "url": "https://bozemanhealth.org/wp-content/uploads/2025/01/01/"
            "474717998_deaconess-regional-medical-center_standardcharges.json",
     "index": "https://www.bozemanhealth.org/cms-hpt.txt", "who": "Deaconess Regional Medical Center, Bozeman, Montana"},
    {"id": "cvmc", "kind": "csv", "dest": "cvmc/222547186_central-vermont-medical-center-inc_standardcharges.csv",
     "url": "https://www.uvmhealth.org/sites/default/files/"
            "222547186_central-vermont-medical-center-inc_standardcharges.csv",
     "index": "https://www.uvmhealth.org/cms-hpt.txt", "who": "Central Vermont Medical Center, Berlin, Vermont"},
    {"id": "cheshire", "kind": "zip", "dest": "cheshire/02-0354549_Cheshire-Medical-Center_standardcharges.zip",
     "url": "https://www.cheshiremed.org/02-0354549_Cheshire%20Medical%20Center_standardcharges.zip",
     "index": "https://www.cheshiremed.org/cms-hpt.txt", "who": "Cheshire Medical Center, Keene, New Hampshire"},
    {"id": "dict_csv", "kind": "text", "dest": "cms_dictionary/CSV_README" + MD,
     "url": "https://raw.githubusercontent.com/CMSgov/hospital-price-transparency/master/documentation/CSV/README.md",
     "index": None, "who": "CMS, data dictionary of the CSV template"},
    {"id": "dict_json", "kind": "text", "dest": "cms_dictionary/JSON_README" + MD,
     "url": "https://raw.githubusercontent.com/CMSgov/hospital-price-transparency/master/documentation/JSON/README.md",
     "index": None, "who": "CMS, data dictionary of the JSON template"},
]

UIOWA = "https://www.healthcare.uiowa.edu/marcom/uihc/billing/"
ITEMS += [
    {"id": "uihc", "kind": "csv", "dest": "uihc/426004813-1376544320_state-university-of-iowa_standardcharges.csv",
     "url": UIOWA + "426004813-1376544320_state-university-of-iowa_standardcharges.csv",
     "index": "https://uihc.org/cms-hpt.txt", "max_bytes": 1_700_000_000,
     "who": "University of Iowa Health Care Medical Center, Iowa City, Iowa"},
    {"id": "uihc_dt", "kind": "csv", "dest": "uihc_dt/426004813-1699541870_state-university-of-iowa_standardcharges.csv",
     "url": UIOWA + "426004813-1699541870_state-university-of-iowa_standardcharges.csv",
     "index": "https://uihc.org/cms-hpt.txt", "max_bytes": 1_700_000_000,
     "who": "University of Iowa Health Care Medical Center Downtown, Iowa City, Iowa"},
]

CMS_ZIP = "https://www.cms.gov/files/zip/"
#: Medicare Part B drug payment limits, one file per quarter. Reference tables, kind "reference".
ASP_FILES = {
    "asp_2026q1": "january-2026-medicare-part-b-payment-limit-files.zip",
    "asp_2026q2": "april-2026-medicare-part-b-payment-limit-files-final-file.zip",
    "asp_2026q3": "july-2026-medicare-part-b-payment-limit-files.zip",
    "asp_2026q4": "october-2026-medicare-part-b-payment-limit-files-final.zip",
    "asp_2024q4": "october-2024-asp-pricing-file.zip",
    # the four 2025 quarters, added 2026-10-14 so the quarter knob reaches the quarter before each file's date
    "asp_2025q1": "january-2025-asp-pricing-file-03/11/25-final-file.zip",
    "asp_2025q2": "april-2025-asp-pricing-file.zip",
    "asp_2025q3": "july-2025-asp-pricing-file.zip",
    "asp_2025q4": "october-2025-asp-pricing-final-file.zip",
}
ITEMS += [{"id": k, "kind": "reference", "dest": "cms_asp/" + v.replace("/", "_"), "url": CMS_ZIP + v, "index": None,
           "who": "CMS, Medicare Part B drug payment limits, " + k[4:8] + " quarter " + k[-1]}
          for k, v in ASP_FILES.items()]
#: Clinical Laboratory Fee Schedule, one file per quarter, the same quarters as the payment limit files
#: (CMS names the 2025 third quarter's file 25CLABQ3V2). Reference tables, kind "reference".
CLFS_FILES = {"clfs_2024q4": "24clabq4", "clfs_2025q1": "25clabq1", "clfs_2025q2": "25clabq2",
              "clfs_2025q3": "25clabq3v2", "clfs_2025q4": "25clabq4", "clfs_2026q1": "26clabq1",
              "clfs_2026q2": "26clabq2", "clfs_2026q3": "26clabq3", "clfs_2026q4": "26clabq4"}
ITEMS += [{"id": k, "kind": "reference", "dest": "clfs/" + v + ".zip",
           "url": CMS_ZIP + v + ".zip?agree=yes&next=Accept", "index": None,
           "who": "CMS, Clinical Laboratory Fee Schedule, " + k[5:9] + " quarter " + k[-1]}
          for k, v in CLFS_FILES.items()]

#: Seen on the server in the first round and left there under the 300 MB rule (HEAD on
#: 2026-10-13). Both were fetched on 2026-10-14 under their own byte ceiling; the list stays
#: because it is what the first round decided, and the reading script prints it.
NOT_FETCHED = [
    {"who": "University of Iowa Health Care Medical Center, Iowa City, Iowa",
     "url": "https://www.healthcare.uiowa.edu/marcom/uihc/billing/"
            "426004813-1376544320_state-university-of-iowa_standardcharges.csv",
     "bytes": 1597353362, "why": "over 300 MB in the first round; fetched 2026-10-14 as uihc", "fetched_as": "uihc"},
    {"who": "University of Iowa Health Care Medical Center Downtown, Iowa City, Iowa",
     "url": "https://www.healthcare.uiowa.edu/marcom/uihc/billing/"
            "426004813-1699541870_state-university-of-iowa_standardcharges.csv",
     "bytes": 1583312047, "why": "over 300 MB in the first round; fetched 2026-10-14 as uihc_dt", "fetched_as": "uihc_dt"},
]


def limit_of(it: dict) -> int:
    """The byte ceiling of one item: its own max_bytes when it has one, the 300 MB rule otherwise."""
    return int(it.get("max_bytes", MAX_BYTES))

def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------- checks

def check_csv(path: Path) -> tuple[bool, str]:
    """A hospital CSV: header rows present, and the file ends on a line end or on a full row."""
    size = path.stat().st_size
    if size < 200:
        return False, "shorter than 200 bytes"
    with open(path, "rb") as f:
        head = f.read(200000)
        f.seek(max(0, size - 200000))
        tail = f.read()
    text = head.decode("utf-8-sig", errors="replace")
    low = text.lower()
    if "hospital_name" not in low:
        return False, "no hospital_name header in the first 200,000 bytes"
    if "standard_charge" not in low:
        return False, "no standard_charge column in the first 200,000 bytes"
    if b"<html" in head[:2000].lower():
        return False, "an HTML page, not a CSV"
    # the last complete line and the line before it should carry the same number of quote marks parity
    lines = tail.decode("utf-8", errors="replace").splitlines()
    if len(lines) < 3:
        return False, "fewer than three lines in the last 200,000 bytes"
    last = lines[-1]
    if last.count('"') % 2:
        return False, "the last line ends inside a quoted field"
    return True, "header present, last line closes its quotes"


def check_zip(path: Path) -> tuple[bool, str]:
    try:
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
            if bad is not None:
                return False, "checksum fails on member " + bad
            names = [i.filename + " (" + str(i.file_size) + " bytes)" for i in z.infolist()]
    except (zipfile.BadZipFile, OSError) as e:
        return False, "not a readable zip: " + str(e)
    if not names:
        return False, "empty archive"
    return True, "every member passes its checksum: " + "; ".join(names)


def check_json(path: Path) -> tuple[bool, str]:
    """Cheap wholeness check; the reader parses the file in full and fails loudly if it cannot."""
    size = path.stat().st_size
    with open(path, "rb") as f:
        head = f.read(4096).lstrip(b"\xef\xbb\xbf \r\n\t")
        f.seek(max(0, size - 4096))
        tail = f.read().rstrip()
    if not head.startswith(b"{"):
        return False, "does not open with an object"
    if not tail.endswith(b"}"):
        return False, "does not close its outer object"
    return True, "opens and closes one object"


def check_text(path: Path) -> tuple[bool, str]:
    data = path.read_bytes()
    if len(data) < 2000:
        return False, "shorter than 2,000 bytes"
    if b"standard_charge" not in data:
        return False, "does not mention standard_charge"
    return True, "mentions standard_charge"


def check_reference(path: Path) -> tuple[bool, str]:
    """A CMS payment-limit zip: every member passes its checksum and some member's header names HCPCS."""
    ok, why = check_zip(path)
    if not ok:
        return ok, why
    try:
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                low = info.filename.lower()
                if not (low.endswith(".csv") or low.endswith(".txt")):
                    continue
                with z.open(info) as f:
                    head = f.read(20000).decode("latin-1", errors="replace")
                if "hcpcs" in head.lower():
                    return True, "zip whole; member " + info.filename + " carries an HCPCS header"
    except (zipfile.BadZipFile, OSError) as e:
        return False, "not a readable zip: " + str(e)
    return False, "no CSV or text member with an HCPCS header"


CHECKS = {"csv": check_csv, "zip": check_zip, "json": check_json, "text": check_text,
          "reference": check_reference}


def check(kind: str, path: Path, length: int | None = None) -> tuple[bool, str]:
    if length is not None and path.stat().st_size != length:
        return False, "length %d differs from the server's %d" % (path.stat().st_size, length)
    return CHECKS[kind](path)


# ---------------------------------------------------------------- manifest

def load_manifest(raw: Path) -> dict:
    p = raw / MANIFEST
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def save_manifest(raw: Path, manifest: dict) -> None:
    raw.mkdir(parents=True, exist_ok=True)
    tmp = raw / (MANIFEST + ".tmp.expired")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    tmp.replace(raw / MANIFEST)


def set_aside(path: Path, why: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    aside = path.with_name(path.name + ".expired_" + stamp + "_" + why)
    path.rename(aside)
    return aside


# ---------------------------------------------------------------- network

def head(url: str) -> dict:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return {"length": int(r.headers["Content-Length"]) if r.headers.get("Content-Length") else None,
                "last_modified": r.headers.get("Last-Modified"), "type": r.headers.get("Content-Type"),
                "etag": r.headers.get("ETag")}


def download(url: str, part: Path, length: int | None, budget_s: float,
             etag: str | None = None, opener=None) -> bool:
    """Append to part from where it stops. True when the server has nothing more to send.

    With an ETag the resumed request carries If-Range, so a server whose file was replaced since
    the first bytes were taken answers 200 with the whole new file; the old part is then set aside
    and the new file is taken from its first byte, never spliced onto the old one."""
    opener = opener or urllib.request.urlopen
    have = part.stat().st_size if part.exists() else 0
    if length is not None and have == length:
        return True
    headers = {"User-Agent": UA}
    if have:
        headers["Range"] = "bytes=%d-" % have
        if etag:
            headers["If-Range"] = etag
    req = urllib.request.Request(url, headers=headers)
    t0 = time.time()
    with opener(req, timeout=90) as r:
        if have and r.status != 206:
            # the server ignored the range: start over in a fresh part file, keep the old bytes aside
            set_aside(part, "range_refused")
            have = 0
        with open(part, "ab") as f:
            while True:
                block = r.read(CHUNK)
                if not block:
                    break
                f.write(block)
                if time.time() - t0 > budget_s:
                    return False
    return True


def cmd_plan() -> int:
    for it in ITEMS:
        print("%-10s %-5s %s\n           -> %s" % (it["id"], it["kind"], it["url"], it["dest"]))
    return 0


def cmd_verify(raw: Path = RAW) -> int:
    manifest = load_manifest(raw)
    bad = 0
    for it in ITEMS:
        p = raw / it["dest"]
        if not p.exists():
            print("MISSING  " + it["id"])
            bad += 1
            continue
        rec = manifest.get(it["id"], {})
        ok, why = check(it["kind"], p, rec.get("bytes"))
        same = rec.get("sha256") == sha256_file(p)
        print(("OK       " if ok and same else "BAD      ") + it["id"] + "  " + str(p.stat().st_size)
              + " bytes  " + why + ("" if same else "  [hash differs from the manifest]"))
        bad += 0 if ok and same else 1
    return 1 if bad else 0


def cmd_fetch(raw: Path = RAW, only: list[str] | None = None, budget_s: float = 420.0) -> int:
    manifest = load_manifest(raw)
    t_start = time.time()
    pending = 0
    for it in ITEMS:
        if only and it["id"] not in only:
            continue
        dest = raw / it["dest"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and it["id"] in manifest:
            ok, why = check(it["kind"], dest, manifest[it["id"]].get("bytes"))
            if ok:
                print("kept     " + it["id"])
                continue
            set_aside(dest, "failed_check")
        elif dest.exists():
            # on disk but missing from the manifest (another process saved its own copy of the manifest
            # meanwhile): adopt it when its length equals the server's and it passes its check
            try:
                h = head(it["url"])
            except (urllib.error.URLError, OSError, ValueError) as e:
                print("ERROR    " + it["id"] + "  " + repr(e))
                pending += 1
                continue
            ok, why = check(it["kind"], dest, h["length"])
            if ok:
                manifest[it["id"]] = {"who": it["who"], "url": it["url"], "dest": it["dest"], "kind": it["kind"],
                                      "bytes": dest.stat().st_size, "sha256": sha256_file(dest),
                                      "server_last_modified": h["last_modified"], "check": why,
                                      "etag": h.get("etag"), "retrieved_utc": now_utc(), "index": None,
                                      "note": "file on disk adopted into the manifest after a check against the server's length"}
                save_manifest(raw, manifest)
                print("adopted  " + it["id"])
                continue
            set_aside(dest, "failed_check")
        left = budget_s - (time.time() - t_start)
        if left < 15:
            print("deferred " + it["id"] + "  (time budget of this call used up; run --fetch again)")
            pending += 1
            continue
        try:
            h = head(it["url"])
            if h["length"] is not None and h["length"] > limit_of(it):
                print("skipped  " + it["id"] + "  %d bytes is over this item's ceiling of %d"
                      % (h["length"], limit_of(it)))
                manifest[it["id"] + "__not_fetched"] = {"url": it["url"], "bytes": h["length"],
                                                        "seen_utc": now_utc(),
                                                        "why": "over the ceiling of %d bytes" % limit_of(it)}
                save_manifest(raw, manifest)
                continue
            part = dest.with_name(dest.name + ".part")
            done = download(it["url"], part, h["length"], left - 10, etag=h.get("etag"))
            if not done:
                print("partial  " + it["id"] + "  %d of %s bytes; run --fetch again"
                      % (part.stat().st_size, h["length"]))
                pending += 1
                continue
            ok, why = check(it["kind"], part, h["length"])
            if not ok:
                aside = set_aside(part, "failed_check")
                print("FAILED   " + it["id"] + "  " + why + "  (set aside as " + aside.name + ")")
                pending += 1
                continue
            part.rename(dest)
            idx_note = None
            if it["index"]:
                try:
                    req = urllib.request.Request(it["index"], headers={"User-Agent": UA})
                    with urllib.request.urlopen(req, timeout=60) as r:
                        idx = r.read()
                    (dest.parent / "cms-hpt.txt").write_bytes(idx)
                    idx_note = {"url": it["index"], "bytes": len(idx),
                                "sha256": hashlib.sha256(idx).hexdigest(),
                                "names_this_file": it["url"].encode() in idx
                                or it["url"].replace("%20", " ").encode() in idx}
                except (urllib.error.URLError, OSError) as e:
                    idx_note = {"url": it["index"], "error": str(e)}
            manifest[it["id"]] = {"who": it["who"], "url": it["url"], "dest": it["dest"], "kind": it["kind"],
                                  "bytes": dest.stat().st_size, "sha256": sha256_file(dest),
                                  "server_last_modified": h["last_modified"], "check": why,
                                  "etag": h.get("etag"),
                                  "retrieved_utc": now_utc(), "index": idx_note}
            save_manifest(raw, manifest)
            print("fetched  " + it["id"] + "  %d bytes" % dest.stat().st_size)
        except (urllib.error.URLError, OSError, ValueError) as e:
            print("ERROR    " + it["id"] + "  " + repr(e))
            pending += 1
    return 2 if pending else 0


# ---------------------------------------------------------------- selftest

def selftest() -> int:
    fails = []

    def ok(label, cond):
        print(("ok    " if cond else "FAIL  ") + label)
        if not cond:
            fails.append(label)

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        good = ('hospital_name,last_updated_on,version\n"H","1/1/2026","3.0.0"\n'
                'description,code|1,standard_charge|gross\n' + '"x","1","10.00"\n' * 40).encode()
        p = d / "a.csv"
        p.write_bytes(good)
        ok("a whole CSV passes", check("csv", p, len(good))[0])
        ok("a CSV one byte short of the server's length fails", not check("csv", p, len(good) + 1)[0])
        q = d / "b.csv"
        q.write_bytes(good[:-8] + b'"x","1')
        ok("a CSV cut inside a quoted field fails", not check("csv", q)[0])
        h = d / "c.csv"
        h.write_bytes(b"<html><body>hospital_name standard_charge blocked</body></html>" + b" " * 300 + b"\n\n\n")
        ok("an HTML page served in place of the CSV fails", not check("csv", h)[0])

        z = d / "a.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("m.csv", good * 50)
        ok("a whole zip passes", check("zip", z)[0])
        data = bytearray(z.read_bytes())
        data[len(data) // 3] ^= 0xFF
        zb = d / "b.zip"
        zb.write_bytes(bytes(data))
        ok("a zip with one flipped byte fails", not check("zip", zb)[0])
        zc = d / "c.zip"
        zc.write_bytes(z.read_bytes()[: z.stat().st_size // 2])
        ok("a zip cut in half fails", not check("zip", zc)[0])

        j = d / "a.json"
        j.write_bytes(b'{"hospital_name": "H", "standard_charge_information": []}')
        ok("a whole JSON passes", check("json", j)[0])
        jb = d / "b.json"
        jb.write_bytes(b'{"hospital_name": "H", "standard_charge_information": [')
        ok("a JSON cut before its closing brace fails", not check("json", jb)[0])

        t = d / "dictionary_a.txt"
        t.write_bytes(b"standard_charge " * 200)
        ok("a dictionary text passes", check("text", t)[0])
        tb = d / "dictionary_b.txt"
        tb.write_bytes(b"404 not found")
        ok("a stub in place of the dictionary fails", not check("text", tb)[0])

        # resume: a part file holding the first bytes is completed, not restarted
        part = d / "r.part"
        part.write_bytes(good[:100])
        with open(part, "ab") as f:
            f.write(good[100:])
        ok("appending to a part file reproduces the whole file",
           hashlib.sha256(part.read_bytes()).hexdigest() == hashlib.sha256(good).hexdigest())

        # set_aside keeps the bytes
        s = d / "s.csv"
        s.write_bytes(b"abc")
        aside = set_aside(s, "failed_check")
        ok("a file set aside keeps its bytes and its name says why",
           aside.read_bytes() == b"abc" and "failed_check" in aside.name and not s.exists())

        # manifest round trip
        save_manifest(d, {"x": {"bytes": 3}})
        ok("the manifest reads back", load_manifest(d) == {"x": {"bytes": 3}})
    print("\n%d failed" % len(fails))
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true")
    g.add_argument("--fetch", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--selftest", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--budget", type=float, default=420.0, help="seconds this call may spend downloading")
    a = ap.parse_args()
    if a.plan:
        return cmd_plan()
    if a.verify:
        return cmd_verify()
    if a.selftest:
        return selftest()
    return cmd_fetch(only=a.only, budget_s=a.budget)


if __name__ == "__main__":
    sys.exit(main())
