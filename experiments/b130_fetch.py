"""Fetch the B130 sources: Singapore's tenancy and income tables, HDB's key statistics, HDB's rules.

Each file is named in FILES with the address it came from. Nothing here is scraped: every
file is a published table, document or rule page at a fixed address.

Rules this obeys:
  - resumable: a file on disk that passes its check is skipped
  - never deletes: a file that fails its check is renamed .bad_<n> and fetched again
  - checks: HTTP 200; a PDF starts with %PDF and carries %%EOF in its last 2 KB; a data.gov.sg
    answer parses, says success and returns every record it counts; a SingStat answer parses and
    carries its rows; an HTML page closes and carries the phrases it was fetched for
  - measured cost only (`D38`): each request prints its seconds and bytes

Run from the repo root:
    python experiments/b130_fetch.py --fetch
    python experiments/b130_fetch.py --check
    python experiments/b130_fetch.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "b130" / "raw"
MANIFEST = RAW / "manifest.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 120
PAUSE = 3.0
DGS = "https://data.gov.sg/api/action/datastore_search?limit=1000&resource_id="

FILES = {
    # Resident households by tenancy, annual 1980-2025: owner-occupied share by dwelling type
    "singstat_m810401.json": "https://tablebuilder.singstat.gov.sg/api/table/tabledata/M810401",
    # Resident households by type of dwelling, annual (counts)
    "dgs_households_by_dwelling.json": DGS + "d_edf8bb4773c25dd16b8b6875fd0b52da",
    # Average monthly household employment income per household member, resident employed
    # households, by type of dwelling (excluding employer CPF)
    "dgs_income_per_member_by_dwelling.json": DGS + "d_c49b6cc84ccab3a0523ad15a907e57be",
    "hdb_key_statistics_2024_2025.pdf":
        "https://www.hdb.gov.sg/-/media/hdb-pulse/reports/annual-reports-and-financial-statements/"
        "HDB_Key-Statistics-2025.pdf",
    "hdb_renting_out_flat_eligibility.html":
        "https://www.hdb.gov.sg/managing-my-home/home-ownership/renting-out-a-flat-or-bedrooms/"
        "renting-out-a-flat/eligibility",
    "hdb_buying_couples_and_families.html":
        "https://www.hdb.gov.sg/buying-a-flat/flat-grant-and-loan-eligibility/couples-and-families",
    # Side question 2026-09-25: what the resale price of a bound flat follows
    "dgs_hdb_resale_price_index.json": DGS + "d_14f63e595975691e7c24a27ae4c07c79",
    "dgs_ura_private_price_index.json": DGS + "d_97f8a2e995022d311c6c68cfda6d034c",
    "dgs_median_income_fulltime.json": DGS + "d_9cd9c40f22a4e45cac8f8b9d895fd5ce",
    # Side question to A50, 2026-09-25: how much CPF money goes back out through housing
    "dgs_cpf_contributions_annual.json": DGS + "d_bb9b7f963ef295b750c9925e9e026524",
    "dgs_cpf_housing_withdrawn_annual.json": DGS + "d_7cce20f5d2d8ae2582da809e66a1cdd7",
    # hdb_general_conditions_for_purchase.pdf (services-homes.hdb.gov.sg/sales/files/
    # general_conditions_for_purchase.pdf) answered 200 with a body that is not a PDF, 2026-09-24.
    # Not load-bearing: the two HDB pages above carry the eligibility and occupation rules read here.
}

#: phrases an HTML page must carry to be the page it was fetched for
PHRASES = {
    "hdb_renting_out_flat_eligibility.html": (b"Minimum Occupation Period", b"Non-Citizen Quota"),
    "hdb_buying_couples_and_families.html": (b"Singapore Citizen", b"Permanent Resident"),
}


def check(name: str, body: bytes) -> str | None:
    """None if the body is a whole file of its kind, else why not."""
    if name.endswith(".pdf"):
        if not body.startswith(b"%PDF"):
            return "not a PDF (no %PDF header)"
        if b"%%EOF" not in body[-2048:]:
            return "truncated PDF (no %%EOF in the last 2 KB)"
        return None
    if name.endswith(".json"):
        try:
            d = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return "not JSON"
        if name.startswith("dgs_"):
            if not d.get("success"):
                return "data.gov.sg did not report success"
            res = d.get("result", {})
            recs = res.get("records") or []
            if not recs:
                return "no records"
            if res.get("total") is not None and int(res["total"]) != len(recs):
                return f"{len(recs)} records of {res['total']}: page limit reached"
            return None
        rows = (d.get("Data") or {}).get("row") or []
        if not rows:
            return "SingStat answer without rows"
        return None
    if name.endswith(".html"):
        if b"</html>" not in body[-8192:].lower():
            return "truncated HTML (no closing </html>)"
        missing = [p.decode() for p in PHRASES.get(name, ()) if p not in body]
        if missing:
            return f"page does not carry {missing}"
        return None
    return "unknown kind"


def set_aside(path: Path) -> None:
    n = 1
    while path.with_name(f"{path.name}.bad_{n}").exists():
        n += 1
    path.rename(path.with_name(f"{path.name}.bad_{n}"))


def fetch(raw: Path = RAW) -> int:
    raw.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    failures = 0
    for name, url in FILES.items():
        path = raw / name
        if path.exists():
            why = check(name, path.read_bytes())
            if why is None:
                print(f"skip  {name}")
                continue
            print(f"bad   {name}: {why}; set aside")
            set_aside(path)
        time.sleep(PAUSE)
        t0 = time.perf_counter()
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                status, body = r.status, r.read()
        except Exception as e:  # noqa: BLE001 - reported, not swallowed
            print(f"FAIL  {name}: {e}")
            failures += 1
            continue
        secs = time.perf_counter() - t0
        why = check(name, body) if status == 200 else f"HTTP {status}"
        if why is not None:
            print(f"FAIL  {name}: {why} ({secs:.1f} s)")
            failures += 1
            continue
        path.write_bytes(body)
        manifest[name] = {"url": url, "bytes": len(body),
                          "sha256": hashlib.sha256(body).hexdigest()}
        print(f"ok    {name}: {len(body):,} bytes in {secs:.1f} s")
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")
    return failures


def check_all(raw: Path = RAW) -> int:
    bad = 0
    for name in FILES:
        path = raw / name
        why = "missing" if not path.exists() else check(name, path.read_bytes())
        print(f"{'ok  ' if why is None else 'BAD '} {name}{'' if why is None else ': ' + why}")
        bad += why is not None
    return bad


def selftest() -> None:
    good_pdf = b"%PDF-1.4\n" + b"x" * 5000 + b"\n%%EOF\n"
    assert check("a.pdf", good_pdf) is None
    assert check("a.pdf", good_pdf[:3000]) is not None, "a truncated PDF must fail"
    ok = json.dumps({"success": True, "result": {"total": 2, "records": [{"a": 1}, {"a": 2}]}}).encode()
    assert check("dgs_x.json", ok) is None
    cut = json.dumps({"success": True, "result": {"total": 3, "records": [{"a": 1}, {"a": 2}]}}).encode()
    assert check("dgs_x.json", cut) is not None, "a paged answer must fail"
    assert check("dgs_x.json", ok[:30]) is not None, "a cut JSON body must fail"
    assert check("singstat_x.json", json.dumps({"Data": {"row": []}}).encode()) is not None, "no rows must fail"
    page = b"<html>Minimum Occupation Period</html>"
    assert check("hdb_renting_out_flat_eligibility.html", page) is not None, "a page missing a phrase must fail"
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "f.pdf"
        p.write_bytes(b"junk")
        set_aside(p)
        assert not p.exists() and (Path(d) / "f.pdf.bad_1").exists(), "set_aside renames"
    print("selftest ok: 7 checks and set_aside")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fetch", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.fetch:
        sys.exit(1 if fetch() else 0)
    else:
        sys.exit(1 if check_all() else 0)
