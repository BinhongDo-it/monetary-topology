"""B149: fetch the raw pages behind the binding premise, the institution axis and the foreign-official class.

Nothing here reads a rate. The script puts each file on disk, checks that it is whole, and keeps
data/raw/b149/b149_manifest.json with the URL, byte count, SHA-256, the check it passed and the
retrieval time. Reading is done in data/b149_regq_cells.json and experiments/b149_regq_table.py.

Sources, all public:

  frb     Federal Reserve Bulletin issues on FRASER, page by page through FRASER's IIIF services:
          the issue manifest, then for each named page the page image (IIIF image API, full/max)
          and the page's ALTO text. Only the pages of the time-and-savings-deposit survey and of
          the monthly ceiling table are taken; whole-issue PDFs (over 10 MB) are not.
  nycirc  Federal Reserve Bank of New York circulars on FRASER, the same way: manifest, ALTO for
          every page, and images of the pages that carry the foreign-official clause (217.3).
  fr      Federal Register daily issues on govinfo. govinfo serves the historical Register only as
          whole-issue PDFs (its link service resolves a page cite to the issue PDF with #page=),
          so these are whole issues.

    python experiments/b149_fetch.py --plan       # what would be fetched, no network
    python experiments/b149_fetch.py --fetch      # fetch what is missing or fails its check
    python experiments/b149_fetch.py --verify     # check what is on disk against the manifest
    python experiments/b149_fetch.py --selftest   # offline, seeded faults

Every fetch can be interrupted and run again: a file already on disk that passes its check is
kept; a download goes to a temporary name and is renamed only when it passes. Nothing is
deleted; a file that fails its check is renamed aside (b123_fetch.set_aside).
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b123_fetch as f  # noqa: E402

RAW = f.REPO / "data" / "raw" / "b149"
f.MANIFEST_NAME = "b149_manifest.json"
IIIF = "https://iiif.slf.digirati.io/presentation/item/{item}"
ALTO = "https://iiif.slf.digirati.io/text/alto/item/{item}/{canvas}"

# Bulletin pages: canvas numbers are 1-based positions in the IIIF manifest (FRASER's viewer pages).
FRB = (
    # survey of April 27, 1977 (1975-12-04 table in force): article "Changes in Time and Savings
    # Deposits at Commercial Banks", tables for governmental and other time deposits by maturity
    {"item": 20434, "issue": "1977-09", "canvases": list(range(19, 30)), "why": "survey 1977-04-27"},
    # survey of July 26, 1978 (1978-06-01 table in force)
    {"item": 20447, "issue": "1978-11", "canvases": list(range(14, 20)), "why": "survey 1978-07-26"},
    # statistical tables on the surveys of 1979 and January 1980
    {"item": 20459, "issue": "1979-11", "canvases": list(range(138, 142)), "why": "survey tables"},
    {"item": 20463, "issue": "1980-03", "canvases": list(range(175, 179)), "why": "survey tables"},
    {"item": 20466, "issue": "1980-06", "canvases": list(range(167, 171)), "why": "survey tables"},
    # monthly table "Maximum interest rates payable on time and savings deposits at federally
    # insured institutions": commercial banks beside savings and loan associations and mutual
    # savings banks, one issue per revision regime
    {"item": 20434, "issue": "1977-09", "canvases": [115], "why": "ceiling table"},
    {"item": 20445, "issue": "1978-09", "canvases": [95], "why": "ceiling table"},
    {"item": 20458, "issue": "1979-09", "canvases": [119], "why": "ceiling table"},
    {"item": 20463, "issue": "1980-03", "canvases": [116], "why": "ceiling table"},
)

# NY Fed circulars carrying the foreign-official exemption; ALTO for every page, images for the
# pages named in "images" (filled after reading the ALTO).
NYCIRC = (
    {"item": 12630, "circular": "5248", "images": [2], "why": "217.3(a) sentence, 1962-10-15"},
    {"item": 12787, "circular": "5690", "images": [2], "why": "extension to 1968-10-15"},
    {"item": 13399, "circular": "6100", "images": [2], "why": "two-year carry-over after 1968-10-15"},
    {"item": 13901, "circular": "6227", "images": [1, 2], "why": "217.3(g) new, two years or less"},
    {"item": 13888, "circular": "6220", "images": [1], "why": "PL 90-505 to 1969-09-21"},
    {"item": 14181, "circular": "6436", "images": [2], "why": "217.3(g) rewritten 1969-11-05"},
    {"item": 496118, "circular": "7847a", "images": [7], "why": "1975-12-04 pamphlet, 217.3(g)"},
    {"item": 522198, "circular": "9022", "images": [14], "why": "1981-01-15 pamphlet, 217.3(g)"},
    {"item": 522845, "circular": "9563", "images": [12], "why": "1983 Regulation D cross-reference to 217.3(g)"},
    # the two amendments on the retain list of 8347 (and of 8473) that B149-8 still counted unopened
    {"item": 496694, "circular": "8338", "images": [], "why": "retain list: amendment effective 1978-11-01"},
    {"item": 496698, "circular": "8341", "images": [], "why": "retain list: amendment effective 1978-07-06"},
)

# Federal Register whole issues (govinfo), chosen by full-text search of the collection for the
# section numbers in the weeks before each effective date; see the record's sources block.
FR = (
    "FR-1974-12-17",  # FHLBB 526.5 and FDIC 329.7 hits; ceilings effective 1974-12-23 (in force 1975-12-04)
    "FR-1978-05-18",  # FHLBB 526.5 and FDIC 329.7 hits; the 1978-06-01 changes
    "FR-1979-06-06",  # FDIC 329.7 hit; the 1979-07-01 changes
    "FR-1979-08-07",  # FDIC 329.7 hit; the 1979-08-01 change
)


def fr_url(pkg: str) -> str:
    return f"https://www.govinfo.gov/content/pkg/{pkg}/pdf/{pkg}.pdf"


# ------------------------------------------------- checks

def check_jpg(data: bytes) -> tuple[bool, str]:
    """Whole means: JPEG start and end markers, and an image that opens with a size."""
    if not data.startswith(b"\xff\xd8"):
        return False, "does not start with the JPEG SOI marker"
    if b"\xff\xd9" not in data[-64:]:
        return False, "no JPEG EOI marker at the end (truncated?)"
    try:
        import pymupdf
        doc = pymupdf.open(stream=data, filetype="jpg")
        r = doc[0].rect
    except Exception as exc:
        return False, "does not open as an image: " + type(exc).__name__
    return True, "jpg, %dx%d" % (int(r.width), int(r.height))


def check_alto(data: bytes) -> tuple[bool, str]:
    """Whole means: it parses as XML and is an ALTO document (a page with no words passes, and
    says so)."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        return False, "does not parse as XML: " + str(exc)[:60]
    if not root.tag.endswith("alto"):
        return False, "root element is not alto"
    words = sum(1 for e in root.iter() if e.tag.endswith("String"))
    return True, "alto, %d words" % words


def check_json(data: bytes) -> tuple[bool, str]:
    try:
        m = json.loads(data)
    except Exception:
        return False, "does not parse as JSON"
    if m.get("type") != "Manifest" or not m.get("items"):
        return False, "not a IIIF manifest with canvases"
    return True, "iiif manifest, %d canvases" % len(m["items"])


f.CHECKS.update({"jpg": check_jpg, "alto": check_alto, "json": check_json})


# ------------------------------------------------- plan

def manifest_items(raw: Path, group: str, item: int) -> list | None:
    p = raw / group / str(item) / "manifest.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))["items"]


def canvas_ids(canvases: list) -> list[tuple[str, str]]:
    """(canvas id, image service base) for every canvas."""
    out = []
    for c in canvases:
        cid = c["id"].rsplit("/", 1)[1]
        body = c["items"][0]["items"][0]["body"]["id"]
        out.append((cid, body.split("/full/")[0]))
    return out


def build_plan(raw: Path = RAW) -> list[dict]:
    """The plan needs the manifests to name pages, so it is built in two layers: manifests
    first, then the pages the manifests name. A missing manifest leaves its pages out of this
    pass; --fetch runs the layers in order."""
    plan = []
    seen = set()
    for grp, rows in (("frb", FRB), ("nycirc", NYCIRC)):
        for row in rows:
            item = row["item"]
            if (grp, item) not in seen:
                seen.add((grp, item))
                plan.append({"dest": f"{grp}/{item}/manifest.json", "kind": "json", "url": IIIF.format(item=item),
                             "layer": 0})
            cv = manifest_items(raw, grp, item)
            if cv is None:
                continue
            ids = canvas_ids(cv)
            if grp == "frb":
                alto_pages, img_pages = row["canvases"], row["canvases"]
            else:
                alto_pages, img_pages = list(range(1, len(ids) + 1)), row["images"]
            for n in alto_pages:
                cid, _ = ids[n - 1]
                plan.append({"dest": f"{grp}/{item}/p{n:03d}.alto.xml", "kind": "alto",
                             "url": ALTO.format(item=item, canvas=cid), "layer": 1})
            for n in img_pages:
                _, base = ids[n - 1]
                plan.append({"dest": f"{grp}/{item}/p{n:03d}.jpg", "kind": "jpg",
                             "url": base + "/full/max/0/default.jpg", "layer": 1})
    for pkg in FR:
        plan.append({"dest": f"fr/{pkg}.pdf", "kind": "pdf", "url": fr_url(pkg), "layer": 1})
    out, have = [], set()
    for p in plan:
        if p["dest"] not in have:
            have.add(p["dest"])
            out.append(p)
    return out


def fetch(raw: Path = RAW) -> int:
    failures = 0
    for layer in (0, 1):
        f.PLAN = tuple(p for p in build_plan(raw) if p["layer"] == layer)
        failures += f.cmd_fetch(raw)
    return 1 if failures else 0


def selftest() -> int:
    checks = []

    def ok(label, cond):
        checks.append((label, bool(cond)))

    import pymupdf
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 30), 0)
    jpg = pix.tobytes("jpg")
    ok("a whole jpg passes", check_jpg(jpg)[0])
    ok("a jpg cut short fails", not check_jpg(jpg[: len(jpg) // 2])[0])
    ok("an error text served as an image fails", not check_jpg(b"Invalid size. 'full' invalid")[0])
    alto = (b'<alto xmlns="http://www.loc.gov/standards/alto/ns-v3#"><Layout><Page><PrintSpace>'
            b'<TextLine><String CONTENT="7.75"/></TextLine></PrintSpace></Page></Layout></alto>')
    ok("a whole alto passes", check_alto(alto)[0])
    ok("an alto cut short fails", not check_alto(alto[:-20])[0])
    man = json.dumps({"type": "Manifest", "items": [{"id": "x/canvases/1_0_0000", "items": [{"items": [
        {"body": {"id": "https://img/1_0_0000/full/740,1024/0/default.jpg"}}]}]}]}).encode()
    ok("a manifest passes", check_json(man)[0])
    ok("a manifest without canvases fails", not check_json(b'{"type": "Manifest", "items": []}')[0])
    with tempfile.TemporaryDirectory() as d:
        raw = Path(d)
        (raw / "frb" / "20434").mkdir(parents=True)
        p0 = [p for p in build_plan(raw) if p["dest"].startswith("frb/20434/")]
        ok("without a manifest only the manifest is planned", [p["kind"] for p in p0] == ["json"])
        canv = [{"id": f"x/canvases/20434_0_{i:04d}", "items": [{"items": [
            {"body": {"id": f"https://img/20434_0_{i:04d}/full/740,1024/0/default.jpg"}}]}]} for i in range(200)]
        (raw / "frb" / "20434" / "manifest.json").write_text(json.dumps({"type": "Manifest", "items": canv}))
        p1 = [p for p in build_plan(raw) if p["dest"].startswith("frb/20434/p")]
        ok("with the manifest every named page gets an image and an alto",
           len(p1) == 2 * (11 + 1) and any(p["url"].endswith("20434_0_0024/full/max/0/default.jpg") for p in p1))
        ok("canvas numbers are 1-based", any(p["dest"] == "frb/20434/p025.jpg" and "20434_0_0024" in p["url"] for p in p1))
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
    g.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.plan:
        f.PLAN = tuple(build_plan(RAW))
        return f.cmd_plan()
    if a.verify:
        f.PLAN = tuple(build_plan(RAW))
        return f.cmd_verify(RAW)
    return fetch(RAW)


if __name__ == "__main__":
    sys.exit(main())
