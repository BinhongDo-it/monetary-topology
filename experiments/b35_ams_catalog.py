"""B35: enumerate the whole AMS report catalogue, then filter to poultry.

Why this exists. `--earliest 3646` returned 2022 as the first year with rows,
which is short of the window this station needs. That is one report. The
question "is there a poultry report on MARS that reaches 2020" cannot be
answered by trying report numbers one at a time, so this pulls the catalogue
once and prints what is in it.

Key resolution is the same as b41_ams_probe: MARS_API_KEY in the environment,
then `../.mars_api_key` beside the repository, then `data/.mars_api_key`.
The key never goes in a tracked file and is never printed.

Network: this must run on a Windows build. The bridged Linux VM's egress
proxy refuses marsapi.ams.usda.gov.

    python experiments/b35_ams_catalog.py
    python experiments/b35_ams_catalog.py --all      # print every report, not just poultry
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / "data" / "b35"
BASE = "https://marsapi.ams.usda.gov/services/v1.2"

# Filtered on the report title. Broad on purpose: the point is to see the
# whole poultry family, then narrow by reading, not to guess a slug.
POULTRY = ("poultry", "chicken", "broiler", "fryer", "turkey", "egg", "duck")


def api_key() -> str:
    env = os.environ.get("MARS_API_KEY")
    if env:
        return env.strip()
    for candidate in (REPO.parent / ".mars_api_key", REPO / "data" / ".mars_api_key"):
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8").strip()
    sys.exit(
        "No API key. Set MARS_API_KEY, or put the key in a file named "
        ".mars_api_key beside the repository. The key never goes in a tracked file."
    )


def fetch_catalogue(key: str, refresh: bool) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    hit = CACHE / "catalogue.json"
    if hit.is_file() and not refresh:
        try:
            payload = json.loads(hit.read_text(encoding="utf-8"))
            print(f"read cache {hit.relative_to(REPO)}  {len(payload)} report(s)")
            return payload
        except json.JSONDecodeError:
            # Discipline 6: a truncated file is not read silently. Set it aside.
            aside = hit.with_suffix(".corrupt.json")
            hit.rename(aside)
            print(f"cache was not valid json, moved to {aside.name}, refetching")

    token = base64.b64encode(f"{key}:".encode()).decode()
    req = urllib.request.Request(
        f"{BASE}/reports", headers={"Authorization": f"Basic {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        sys.exit(f"HTTP {exc.code} from {BASE}/reports: {exc.read()[:300]!r}")
    except urllib.error.URLError as exc:
        sys.exit(f"cannot reach {BASE}: {exc.reason}. Run this on a Windows build.")

    payload = json.loads(body)
    if isinstance(payload, dict):
        for k in ("results", "data", "reports"):
            if isinstance(payload.get(k), list):
                payload = payload[k]
                break
    hit.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                   encoding="utf-8", newline="\n")
    print(f"fetched {len(payload)} report(s), cached to {hit.relative_to(REPO)}")
    return payload


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="print every report")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache")
    args = ap.parse_args()

    rows = fetch_catalogue(api_key(), args.refresh)
    if not rows:
        sys.exit("catalogue is empty")

    # Discipline 11: print the object before filtering it.
    print("\nkeys on the first record:")
    print("   ", json.dumps(sorted(rows[0].keys()), ensure_ascii=False))
    print("first record:")
    print("   ", json.dumps(rows[0], ensure_ascii=False)[:600])

    def title_of(r: dict) -> str:
        for k in ("report_title", "reportTitle", "title", "name", "slug_name"):
            if isinstance(r.get(k), str):
                return r[k]
        return ""

    def id_of(r: dict) -> str:
        for k in ("slug_id", "slugId", "report_id", "reportId", "id"):
            if r.get(k) is not None:
                return str(r[k])
        return "?"

    picked = rows if args.all else [
        r for r in rows if any(w in title_of(r).lower() for w in POULTRY)
    ]
    label = "every report" if args.all else "poultry-family reports"
    print(f"\n{label}: {len(picked)} of {len(rows)}\n")
    for r in sorted(picked, key=lambda x: title_of(x).lower()):
        freq = r.get("report_frequency") or r.get("frequency") or ""
        print(f"  {id_of(r):>8}  {freq:<12}  {title_of(r)[:88]}")

    print("\nNext: run  python experiments/b41_ams_probe.py --earliest <ID>  "
          "on the ids that look like cut-level chicken quotations.")


if __name__ == "__main__":
    main()
