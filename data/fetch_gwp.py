# -*- coding: utf-8 -*-
"""IPCC global warming potentials, every assessment report in one table.

Stage C1 needs the conversion factors themselves, not emissions. A GWP is an
administratively published exchange rate: one tonne of species `a` is declared
equal to `GWP_s(a)` tonnes of CO2-equivalent under standard `s`, and that
declaration is executable, because compliance schemes offset against it. So the
carrier here is the table of declarations, and its size is six kilobytes.

`openclimatedata/globalwarmingpotentials` collects them from the primary
sources, which are named in the CSV's own comment header: the GHG Protocol's
calculation tools for SAR, AR4 and AR5; IPCC TAR chapter 6 table 6.7; AR5
chapter 8 supplementary table 8.SM.16 for the climate-carbon-feedback variant;
and AR6 chapter 7 supplementary table 7.SM.7. Released CC0.

**Pinned to a commit, not to `main`.** The upstream file gains species over
time, so `main` is a moving target and a reading taken against it cannot be
reproduced later. `COMMIT` below is the revision this stage read, `SHA256` is
what that revision hashes to, and `--pull` refuses to rename a file that
disagrees with either. That refusal is the whole integrity story at this size:
the transfer is short enough that truncation is unlikely and cheap enough that
re-running costs nothing, so a checksum mismatch means the pin moved rather
than that the wire dropped bytes, and the correct response is to stop and
re-derive the reading, not to retry.

**What this does not supply.** The table says what each standard declares. It
does not say which declarations are mutually redeemable, and that second object
is what decides whether a given loop can actually be walked: registry
acceptance lists, compliance-scheme eligibility, linkage agreements, and the
haircuts applied on transfer. Those are policy documents rather than a
dataset, and C1's second half reads them separately. Nothing in this file
should be read as evidence about them.

Usage::

    python data/fetch_gwp.py --list
    python data/fetch_gwp.py --pull
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

REPO = "openclimatedata/globalwarmingpotentials"
COMMIT = "d3cb48938de7ec35d2f6a0d8072237e6a0db6ce7"
NAME = "globalwarmingpotentials.csv"
URL = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/{NAME}"

#: Measured 2026-08-27 against the pinned commit. `--pull` compares both.
SHA256 = "9b80412cb5aeeb91038ef84145a10cdab0ab202cbb623cb14d2ec35ec2454f36"
BYTES = 6744

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "gwp"


def get() -> bytes:
    with urllib.request.urlopen(URL, timeout=60) as fh:
        return fh.read()


def describe(blob: bytes) -> dict:
    text = blob.decode("utf-8")
    lines = [ln for ln in text.splitlines() if ln and not ln.startswith("#")]
    header = lines[0].split(",")
    return {
        "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "columns": header,
        "standards": header[1:],
        "species": len(lines) - 1,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true",
                    help="fetch and describe without writing anything")
    ap.add_argument("--pull", action="store_true")
    args = ap.parse_args()
    if not (args.list or args.pull):
        return ap.error("pass --list or --pull")

    dest = OUT / NAME
    if args.pull and dest.exists():
        have = describe(dest.read_bytes())
        if have["sha256"] == SHA256:
            print("have  %s  %d B  %d species" % (dest, have["bytes"], have["species"]))
            return 0
        print("STOP. %s is on disk but hashes to %s, not the pinned %s. "
              "It is left untouched. Re-derive the reading against whatever "
              "that file actually is before overwriting anything."
              % (dest, have["sha256"][:16], SHA256[:16]))
        return 1

    blob = get()
    seen = describe(blob)
    print("url        %s" % URL)
    print("commit     %s" % COMMIT)
    print("bytes      %d  (expected %d)" % (seen["bytes"], BYTES))
    print("sha256     %s" % seen["sha256"])
    print("           %s  <- pinned" % SHA256)
    print("species    %d" % seen["species"])
    print("standards  %s" % ", ".join(seen["standards"]))

    if seen["sha256"] != SHA256 or seen["bytes"] != BYTES:
        print("\nSTOP. The pin moved. Nothing was written. Either the upstream "
              "file changed under a commit that should be immutable, which is "
              "worth understanding before proceeding, or COMMIT/SHA256 in this "
              "file are stale. Do not update them to match without re-running "
              "the stage: the reading is a function of this table.")
        return 1
    if args.list:
        print("\nok, nothing written (--list)")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    part.write_bytes(blob)
    part.rename(dest)
    # One level up, because `.gitignore` re-includes
    # `data/raw/*_manifest.json` at that depth and not below it.
    manifest = OUT.parent / "gwp_manifest.json"
    manifest.write_text(
        json.dumps({"url": URL, "repo": REPO, "commit": COMMIT, "file": NAME,
                    "retrieved": "2026-08-27", "license": "CC0-1.0", **seen},
                   indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n")
    print("\nwrote %s\nwrote %s" % (dest, manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
