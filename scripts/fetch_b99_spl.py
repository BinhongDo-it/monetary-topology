"""Fetch a small sample of DailyMed SPL documents for B99, the `D21` first step only.

B99-0 and B99-3 need the repackaging pair graph, and that graph lives only in SPL: under
21 CFR 207.53 a repackaged or relabeled product names its source product, and the SPL prints it
as `asEquivalentEntity/definingMaterialKind/code` (code system 2.16.840.1.113883.6.69) under the
repackaged product's own code. The full SPL set is GB-scale; this script fetches a sample and
the companion `scripts/b99_spl_pairs.py` counts how many pairs have both ends in NADAC.

The frame is NADAC itself, so the count reads straight off it: a NADAC product whose SPL names a
source that is also in NADAC is one usable pair.

    stage A   300 NADAC products drawn at random (seed 99) from the two annual files
    stage B   up to 100 NADAC products drawn at random from each labeler that stage A found
              carrying a source NDC (the labelers are read off stage A, not guessed)

Each product is looked up by one of its package NDCs in the labeler's own hyphenated form,
taken from NSDE's `Item Code`, through the DailyMed web service
(`/services/v2/spls.json?ndc=`), and every set id it returns is fetched as XML
(`/services/v2/spls/<setid>.xml`).

Rules this obeys:
  - resumable: a file is written to `<name>.part` and only moved into place once whole; a rerun
    skips every file whose bytes and SHA-256 match the manifest
  - detects truncation: the body must be as long as the Content-Length the server sent, a JSON
    answer must parse, an XML answer must parse, end in `</document>`, and have the HL7 v3
    `document` root; a file that fails is renamed `.expired_*`, never deleted (rule 5)
  - untrusted content: a body carrying `<!DOCTYPE` or `<!ENTITY` is refused before parsing;
    nothing in a body is ever executed
  - measured cost (`D38`): bytes and seconds per transfer go into the manifest, and `--probe`
    fetches three documents and prints the projected total before anything else runs;
    `--cap-mb` stops the run before it passes a byte budget (default 400 MB)

Run with `python -I` (downloads are untrusted):

    python -I scripts/fetch_b99_spl.py --probe
    python -I scripts/fetch_b99_spl.py --stage A
    python -I scripts/fetch_b99_spl.py --stage B
    python -I scripts/fetch_b99_spl.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import random
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "b99"
OUT = RAW / "spl_sample"
UA = "Mozilla/5.0 (monetary-topology research fetcher)"
API = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
HL7 = "{urn:hl7-org:v3}"
SEED = 99
N_A = 300
N_B = 100
PAUSE = 0.1


def stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def retire(path: Path, why: str) -> None:
    dead = path.with_name(f"{path.name}.expired_{stamp()}_{why}")
    path.rename(dead)  # never delete (engineering rule 5)
    print(f"    retired {path.name} -> {dead.name}")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------------------- checks

def check_json(body: bytes) -> tuple[bool, str]:
    try:
        d = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return False, f"not JSON ({e.__class__.__name__})"
    if not isinstance(d, dict) or "data" not in d or "metadata" not in d:
        return False, "JSON without the service's data and metadata keys"
    return True, f"{len(d['data'])} set ids"


def check_xml(body: bytes) -> tuple[bool, str]:
    head = body[:4096]
    if b"<!DOCTYPE" in body or b"<!ENTITY" in body:
        return False, "carries a DOCTYPE or ENTITY declaration; refused unparsed"
    if not body.rstrip().endswith(b"</document>"):
        return False, "does not end in </document> (cut)"
    if b"<document" not in head:
        return False, "no document root near the top"
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        return False, f"does not parse ({e})"
    if root.tag != HL7 + "document":
        return False, f"root is {root.tag}, not the HL7 v3 document"
    return True, f"{len(body)} bytes, parses"


# ---------------------------------------------------------------------------- transfer

class Budget(Exception):
    pass


def get(url: str, dest: Path, kind: str, man: dict, cap: int) -> bytes | None:
    """Fetch url into dest unless the manifest already holds that exact file."""
    key = dest.relative_to(OUT).as_posix()
    if dest.exists():
        e = man["files"].get(key)
        body = dest.read_bytes()
        if e and e["bytes"] == len(body) and e["sha256"] == sha(body):
            return body
        retire(dest, "not_in_manifest")
    if man["total_bytes"] >= cap:
        raise Budget(f"byte budget {cap / 1e6:.0f} MB reached")
    part = dest.with_name(dest.name + ".part")
    if part.exists():
        retire(part, "stale_part")
    t = time.perf_counter()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            announced = r.headers.get("Content-Length")
            body = r.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"    {key}: transfer stopped ({e}); rerun resumes")
        return None
    secs = round(time.perf_counter() - t, 3)
    part.write_bytes(body)
    if announced is not None and int(announced) != len(body):
        print(f"    {key}: {len(body)} bytes against the announced {announced}")
        retire(part, "short")
        return None
    ok, why = (check_json if kind == "json" else check_xml)(body)
    if not ok:
        print(f"    {key}: {why}")
        retire(part, "failed_check")
        return None
    os.replace(part, dest)
    man["files"][key] = {"url": url, "bytes": len(body), "sha256": sha(body), "seconds": secs,
                         "fetched": time.strftime("%Y-%m-%d"), "check": why}
    man["total_bytes"] += len(body)
    time.sleep(PAUSE)
    return body


# ---------------------------------------------------------------------------- frame

def nadac_products() -> dict[str, list[str]]:
    """{product9: sorted NDC-11s} over both annual NADAC files."""
    out: dict[str, set] = {}
    for p in sorted(glob.glob(str(RAW / "nadac" / "*.csv"))):
        with open(p, newline="", encoding="utf-8-sig") as f:
            rd = csv.reader(f)
            h = next(rd)
            i = h.index("NDC")
            for r in rd:
                if r and len(r[i]) == 11 and r[i].isdigit():
                    out.setdefault(r[i][:9], set()).add(r[i])
    return {k: sorted(v) for k, v in out.items()}


def nsde_items() -> dict[str, str]:
    """NDC-11 -> NSDE Item Code (the labeler's own hyphenated NDC)."""
    out = {}
    for p in sorted(glob.glob(str(RAW / "nsde" / "extracted_*" / "*.csv"))):
        with open(p, newline="", encoding="utf-8-sig") as f:
            rd = csv.reader(f)
            h = next(rd)
            ii, ni = h.index("Item Code"), h.index("NDC11")
            for r in rd:
                if r and re.fullmatch(r"\d{4,5}-\d{3,4}-\d{1,2}", r[ii]):
                    out[r[ni]] = r[ii]
    return out


def frame(stage: str, man: dict) -> list[str]:
    prods = nadac_products()
    keys = sorted(prods)
    rng = random.Random(SEED)
    a = sorted(rng.sample(keys, N_A))
    if stage == "A":
        return a
    counted = OUT / "pairs.json"
    labs = (sorted(json.loads(counted.read_text(encoding="utf-8"))
                   .get("stage_A_source_labelers", [])) if counted.exists() else [])
    if not labs:
        raise SystemExit("stage B needs stage A's labelers; run --stage A and the pair "
                         "counter first")
    b = []
    for lab in labs:
        pool = sorted(k for k in keys if k[:5] == lab and k not in a)
        b += sorted(random.Random(f"{SEED}-{lab}").sample(pool, min(N_B, len(pool))))
    return b


def run(stage: str, cap: int) -> int:
    man_path = OUT / "manifest.json"
    man = (json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists()
           else {"files": {}, "total_bytes": 0, "lookups": {}})
    prods, items = nadac_products(), nsde_items()
    todo = frame(stage, man)
    (OUT / "query").mkdir(parents=True, exist_ok=True)
    (OUT / "xml").mkdir(parents=True, exist_ok=True)
    print(f"stage {stage}: {len(todo)} NADAC products")
    t0, bad = time.perf_counter(), 0
    try:
        for k, p9 in enumerate(todo, 1):
            look = man["lookups"].setdefault(p9, {"stage": stage})
            ndcs = [n for n in prods[p9] if n in items]
            if not ndcs:
                look["item_code"] = None
                continue
            item = items[ndcs[0]]
            look["item_code"], look["ndc11"] = item, ndcs[0]
            q = get(f"{API}/spls.json?ndc={urllib.parse.quote(item)}",
                    OUT / "query" / f"{ndcs[0]}.json", "json", man, cap)
            if q is None:
                bad += 1
                continue
            sids = [d["setid"] for d in json.loads(q.decode("utf-8"))["data"]
                    if re.fullmatch(r"[0-9a-f-]{36}", d.get("setid", ""))]
            look["setids"] = sids
            for s in sids:
                if get(f"{API}/spls/{s}.xml", OUT / "xml" / f"{s}.xml", "xml", man,
                       cap) is None:
                    bad += 1
            if k % 25 == 0:
                print(f"  {k}/{len(todo)}  {man['total_bytes'] / 1e6:.1f} MB  "
                      f"{time.perf_counter() - t0:.0f} s")
                man_path.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n",
                                    encoding="utf-8", newline="\n")
    except Budget as e:
        print(f"  stopped: {e}")
        bad += 1
    man_path.write_text(json.dumps(man, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")
    print(f"stage {stage} done: {man['total_bytes'] / 1e6:.1f} MB on disk in the sample, "
          f"{time.perf_counter() - t0:.0f} s, {bad} transfers to redo")
    return 1 if bad else 0


def probe() -> int:
    """Three lookups and their documents, timed, then the projection (`D38`)."""
    prods, items = nadac_products(), nsde_items()
    keys = sorted(prods)
    sample = random.Random(SEED).sample(keys, N_A)[:3]
    tot_b, tot_s, docs = 0, 0.0, 0
    for p9 in sample:
        ndcs = [n for n in prods[p9] if n in items]
        if not ndcs:
            continue
        for url in [f"{API}/spls.json?ndc={urllib.parse.quote(items[ndcs[0]])}"]:
            t = time.perf_counter()
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}),
                                        timeout=120) as r:
                body = r.read()
            tot_s += time.perf_counter() - t
            tot_b += len(body)
            for d in json.loads(body.decode("utf-8"))["data"]:
                t = time.perf_counter()
                with urllib.request.urlopen(urllib.request.Request(
                        f"{API}/spls/{d['setid']}.xml", headers={"User-Agent": UA}),
                        timeout=120) as r:
                    x = r.read()
                tot_s += time.perf_counter() - t
                tot_b += len(x)
                docs += 1
                print(f"  {p9}: {len(x)} bytes")
    per = tot_b / max(1, len(sample))
    print(f"  {len(sample)} products, {docs} documents, {tot_b} bytes, {tot_s:.1f} s")
    print(f"  projected: stage A {N_A} products about {per * N_A / 1e6:.0f} MB; "
          f"stage B at most {N_B} per labeler")
    return 0


def selftest() -> None:
    good = (b'<?xml version="1.0" encoding="UTF-8"?>\n<document xmlns="urn:hl7-org:v3">'
            b"<id/></document>\n")
    assert check_xml(good)[0]
    assert not check_xml(good[:-14])[0]                                   # cut
    assert not check_xml(b'<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "x">]>'
                         b'<document xmlns="urn:hl7-org:v3">&a;</document>')[0]
    assert not check_xml(b"<html><body>error</body></html><document></document>")[0]
    assert not check_xml(b'<document xmlns="urn:other">x</document>')[0]  # wrong root
    assert check_json(b'{"data": [], "metadata": {}}')[0]
    assert not check_json(b'{"data": [], "meta')[0]                      # cut
    assert not check_json(b"<html>busy</html>")[0]
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.xml"
        p.write_bytes(good)
        retire(p, "test")
        assert not p.exists() and len(list(Path(d).iterdir())) == 1      # renamed, kept
    print("selftest ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--stage", choices=["A", "B"])
    ap.add_argument("--cap-mb", type=float, default=400.0)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    if a.probe:
        return probe()
    if a.stage:
        return run(a.stage, int(a.cap_mb * 1e6))
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
