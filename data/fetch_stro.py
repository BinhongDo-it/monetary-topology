"""Fetch the Sound Toll Registers re-engineered tables (STRO 2.0).

Carrier for A26 reading one, the edge that stays legal and stops being used.
The registers record every passage of the Sound from 1497 to 1857, and what
this stage needs from them is the *port* dimension: which port a ship left and
which it was bound for, per passage, per year. That is the pair panel.

**Only five of the eighteen tables are fetched by default, and which five is a
consequence of the design rather than a saving.** The commodity fields are
three hundred and fifty thousand unstandardised free-text strings and they are
what defeated the other reading of this carrier; the port fields are
standardised and carry three levels of region. This stage eats the ports, so it
does not pay for the cargo, tax, image, master or ship tables. Passing
``--all`` fetches everything, for a stage that needs the rest.

**Resumable, and it verifies rather than trusting the transfer.** Every file in
the manifest below carries the size and the MD5 the archive publishes, an
interrupted transfer resumes from the byte it reached, and a file whose digest
does not match is renamed aside rather than kept or removed. A truncated CSV
read silently is the failure this guards against: it does not raise, it just
ends early, and every count computed from it is quietly low.

Downloaded data is treated as irreplaceable. Nothing here deletes.

Usage::

    python data/fetch_stro.py              # the five port tables, ~202 MB
    python data/fetch_stro.py --all        # all eighteen, ~1.63 GB
    python data/fetch_stro.py --check      # verify what is already on disk
    python data/fetch_stro.py --schema     # print each file's header and first rows

Source: STRO 2.0, Re-engineered data from Sound Toll Registers Online,
figshare article 27176202, CC BY 4.0, published 2024-10-17.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "stro"
MANIFEST = ROOT / "data" / "raw" / "stro_manifest.json"

ARTICLE = 27176202
BASE = "https://ndownloader.figshare.com/files/"

#: name, figshare file id, published size in bytes, published md5.
#: Transcribed from the article's API record, not computed here: the point of
#: carrying them is that they come from the other side of the transfer.
FILES: tuple[tuple[str, int, int, str], ...] = (
    ("registers.csv", 49710717, 61950, "9c774358e0946aed47638c6db6f70a16"),
    ("sections.csv", 49710723, 388582, "af3bfc1b61a5540d7a7ee04c3b3d04fc"),
    ("customs_entries.csv", 49710744, 67632551, "7e831f5a9888f01ce18bff4bf2a6a2f8"),
    ("departure.csv", 49710741, 67789265, "566c660ca2cd261e07a61282a767d952"),
    ("destination.csv", 49710747, 65900463, "9fecfd98df5ab17515f08c1d1aba84a6"),
    # Not needed by this stage. Fetched only with --all.
    ("remarks_images.csv", 49710720, 1890072, "40e964735c6859c9e16c8e3d56adddb8"),
    ("remarks_taxes.csv", 49710726, 7672476, "df938c90870e3fe29632f29d957e3eda"),
    ("ships.csv", 49710729, 15678606, "e84de1df29cedbc25ebe51cc8e299ba0"),
    ("remarks_cargoes.csv", 49710732, 13937262, "517f9219c50dba21b54ec8ea168f57b8"),
    ("remarks_entries.csv", 49710735, 14752684, "b8deb8d2b967eed5a295501d0595ddfe"),
    ("taxes_master.csv", 49710738, 45291999, "cc5c3eda631f4613e5f3a7061f16f883"),
    ("masters.csv", 49710750, 90630657, "1b3372427fedf9f3901cc8d0b9e5231e"),
    ("img.csv", 49710759, 149835292, "60d457860f988deb04e16a9c1605bbb5"),
    ("taxes_cargoes.csv", 49710762, 169891869, "649179caaa9ba37523c8aaf9ace23f0c"),
    ("cargoes_regs.csv", 49710765, 196238141, "2c18367de2501d0614d8c0512aebbbb8"),
    ("taxes_totals.csv", 49710768, 175220115, "eb2339ac56e43bb50b5d17727a23c283"),
    ("cargoes_measurement.csv", 49710771, 227030264, "77fff52f02d11bdd1f6d5c36fa119fe0"),
    ("taxes_entry.csv", 49710774, 324770083, "2f7764a950681b2b519375be68bf0770"),
)

#: What this stage needs. The rest is behind --all.
CORE = ("registers.csv", "sections.csv", "customs_entries.csv",
        "departure.csv", "destination.csv")

CHUNK = 1 << 20


def digest(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def fetch_one(name: str, fid: int, size: int, md5: str) -> dict:
    """One file, resuming if a part is already there, verified before it counts."""
    final = OUT / name
    part = OUT / (name + ".part")
    url = BASE + str(fid)

    if final.exists():
        have = final.stat().st_size
        if have == size and digest(final) == md5:
            print(f"  {name:26s} already complete and verified")
            return {"name": name, "url": url, "bytes": have, "md5": md5,
                    "verified": True, "action": "kept"}
        # Present but wrong. Never overwritten and never removed: it is set
        # aside under a name that says what it is, and the fetch starts clean.
        aside = OUT / (name + f".corrupt_{time.strftime('%Y%m%d_%H%M%S')}")
        final.rename(aside)
        print(f"  {name:26s} on disk but does not verify, set aside as "
              f"{aside.name}")

    start = part.stat().st_size if part.exists() else 0
    if start >= size:
        # A part at or past the published size is not a resume point.
        aside = OUT / (name + f".part.bad_{time.strftime('%Y%m%d_%H%M%S')}")
        part.rename(aside)
        start = 0
    if start:
        print(f"  {name:26s} resuming at {start:,} of {size:,}")

    req = urllib.request.Request(url, headers={"User-Agent": "monetary-topology"})
    if start:
        req.add_header("Range", f"bytes={start}-")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        # A server that ignores the Range header answers 200 with the whole
        # file. Appending that to a part would concatenate two copies, and the
        # digest is what would catch it, so the mode is chosen on the status
        # rather than on what was asked for.
        mode = "ab" if (start and r.status == 206) else "wb"
        if start and r.status != 206:
            print(f"  {name:26s} range ignored, restarting from zero")
        done = start if mode == "ab" else 0
        with part.open(mode) as f:
            while True:
                block = r.read(CHUNK)
                if not block:
                    break
                f.write(block)
                done += len(block)
                if done % (32 * CHUNK) < CHUNK:
                    pct = 100.0 * done / size if size else 0.0
                    print(f"\r  {name:26s} {done:>13,} / {size:,}  {pct:5.1f}%",
                          end="", flush=True)
    secs = time.time() - t0
    got = part.stat().st_size
    print(f"\r  {name:26s} {got:>13,} / {size:,}  in {secs:6.1f}s", end="")

    if got != size:
        print("   SIZE MISMATCH, left as .part for the next resume")
        return {"name": name, "url": url, "bytes": got, "md5": None,
                "verified": False, "action": "incomplete"}
    d = digest(part)
    if d != md5:
        aside = OUT / (name + f".part.bad_{time.strftime('%Y%m%d_%H%M%S')}")
        part.rename(aside)
        print(f"   DIGEST MISMATCH {d}, set aside as {aside.name}")
        return {"name": name, "url": url, "bytes": got, "md5": d,
                "verified": False, "action": "digest mismatch"}
    part.rename(final)
    print("   verified")
    return {"name": name, "url": url, "bytes": got, "md5": d,
            "verified": True, "action": "fetched"}


def write_manifest(rows: list[dict]) -> None:
    """Per file: the URL queried, when, how many bytes, and the digest.

    Committed on purpose while the data is not. It is the part of the retrieval
    a reader cannot reconstruct afterwards.
    """
    doc = {}
    if MANIFEST.exists():
        doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    doc["source"] = ("STRO 2.0, Re-engineered data from Sound Toll Registers "
                     "Online, figshare article %d, CC BY 4.0" % ARTICLE)
    doc["article_url"] = f"https://doi.org/10.6084/m9.figshare.{ARTICLE}"
    doc.setdefault("files", {})
    for r in rows:
        r = dict(r)
        r["fetched_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        doc["files"][r.pop("name")] = r
    MANIFEST.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(f"\nmanifest: {MANIFEST.relative_to(ROOT)}, "
          f"{len(doc['files'])} file(s) recorded")


def check() -> int:
    """Verify what is on disk against the published sizes and digests."""
    bad = 0
    for name, _fid, size, md5 in FILES:
        p = OUT / name
        if not p.exists():
            print(f"  {name:26s} absent")
            continue
        got = p.stat().st_size
        d = digest(p)
        ok = got == size and d == md5
        bad += 0 if ok else 1
        print(f"  {name:26s} {got:>13,}  {'verified' if ok else 'DOES NOT VERIFY'}")
    return bad


def schema(rows: int = 3) -> None:
    """Print each present file's header and first rows.

    The first thing to do with a table nobody here has read is to look at it,
    not to write code against a guess at its columns.
    """
    for name, _fid, _size, _md5 in FILES:
        p = OUT / name
        if not p.exists():
            continue
        print(f"\n--- {name}")
        with p.open("r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i > rows:
                    break
                print("   " + line.rstrip("\n")[:400])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true",
                    help="every table, about 1.63 GB")
    ap.add_argument("--check", action="store_true",
                    help="verify what is on disk, fetch nothing")
    ap.add_argument("--schema", action="store_true",
                    help="print headers and first rows of what is on disk")
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    if a.check:
        return 1 if check() else 0
    if a.schema:
        schema()
        return 0

    want = [f for f in FILES if a.all or f[0] in CORE]
    total = sum(f[2] for f in want)
    print(f"STRO 2.0: {len(want)} file(s), {total:,} bytes "
          f"({total / 1e6:.0f} MB) into {OUT.relative_to(ROOT)}\n")
    rows = [fetch_one(*f) for f in want]
    write_manifest(rows)
    missing = [r["name"] for r in rows if not r["verified"]]
    if missing:
        print(f"\nnot verified: {missing}. Re-run to resume; nothing was removed.")
        return 1
    print("\nall verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
