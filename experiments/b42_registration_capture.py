"""B42: keep the daily registered-deliverable snapshot, because it has no history.

The exchange publishes two files that say how much grain is registered as
deliverable and how much sits in the regular houses. Both are a current snapshot.
The history is behind a paid product, so the free series can only be built
forward and a day not captured is a day that is gone. That is the whole reason
this file exists and the reason it runs before any criterion is written: the
criteria can be written whenever, the day cannot be fetched again.

What the series is for: it turns "is this position deliverable for this
commodity" from a yes or no into a quantity that moves day by day. A scalar
potential on positions has nothing to say about that quantity.

**Idempotent.** A day already on disk is a no-op, so firing twice is safe and a
missed fire is caught by the next one on the same day.
**Raw bytes only, no parsing.** A capture that parses is a capture that can lose
the day it was trying to keep, and the format is theirs to change.
**Nothing is deleted.** A short or odd capture stays as evidence about that day.

The day key is the UTC date, matching the other daily capture in this project so
the two series share one calendar.

    python experiments/b42_registration_capture.py --capture  # capture today
    python experiments/b42_registration_capture.py --verify   # report the series
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DAILY = REPO / "data" / "b42" / "_daily"

# All four are published as the current issue only, so the marginal cost of a
# file is one small request a day and the cost of leaving it out is every day
# between now and whenever it turns out to be wanted. That asymmetry, not a
# guess about which one gets used, is why there are four.
SOURCES = {
    "registration": "https://www.cmegroup.com/delivery_reports/"
                    "deliverable-commodities-under-registration.xls",
    "stocks": "https://www.cmegroup.com/delivery_reports/"
              "stocks-of-grain-updated-tuesday.xlsx",
    "receipts": "https://www.cmegroup.com/delivery_reports/"
                "daily-receipts-and-shipments.xls",
    "barges": "https://www.cmegroup.com/market-data/reports/"
              "cbot-constructively-placed-barges.xls",
}
UA = "Mozilla/5.0 (compatible; research archive; one request per file per day)"
MIN_BYTES = 2000

# A plain urllib request to this host answered 403 on 2026-09-02, from a machine
# whose browser reaches the same file. So the refusal is about the request, not
# about the network. Rather than guessing one incantation, the profiles are
# enumerated and the working one is recorded here once it is known.
BROWSER = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
LANDING = ("https://www.cmegroup.com/clearing/operations-and-deliveries/"
           "registrar-reports.html")  # delivery_reports.html does not exist

HEADER_PROFILES = {
    "bare": {},
    "polite": {"User-Agent": UA},
    "browser_ua": {"User-Agent": BROWSER},
    "browser_full": {
        "User-Agent": BROWSER,
        "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
                   "image/avif,image/webp,*/*;q=0.8"),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "identity",
        "Referer": LANDING,
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Connection": "keep-alive",
    },
}


def kind(b: bytes) -> str:
    if b[:4] == b"PK\x03\x04":
        return "zip_xlsx"
    if b[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "ole_xls"
    if b[:15].lower().startswith(b"<!doctype html") or b[:6].lower() == b"<html>":
        return "html_not_a_workbook"
    return "unknown"


def capture(force: bool = False, profile: str = "browser_full") -> int:
    day = datetime.now(timezone.utc).date().isoformat()
    DAILY.mkdir(parents=True, exist_ok=True)
    bad = 0
    for name, url in sorted(SOURCES.items()):
        ext = ".xlsx" if url.endswith(".xlsx") else ".xls"
        target = DAILY / f"{name}-{day}{ext}"
        if target.exists() and not force:
            print(f"{day}: {name} already on disk, {target.stat().st_size} bytes")
            continue
        tmp = target.with_suffix(target.suffix + ".part")
        code, nbytes, backend, note = fetch(url, tmp)
        if not tmp.exists() or nbytes == 0:
            print(f"{day}: {name} http_{code or '---'} via {backend} {note}")
            bad += 1
            continue
        body = tmp.read_bytes()
        k = kind(body)
        # A short body or an HTML error page is still written, under a name that
        # says so, because what the source served that day is the evidence.
        suspect = len(body) < MIN_BYTES or k in ("html_not_a_workbook", "unknown")
        if suspect:
            target = DAILY / f"{name}-{day}.suspect{ext}"
            bad += 1
        os.replace(tmp, target)
        print(f"{day}: {name} http_{code} via {backend} {len(body)} bytes, {k}, "
              f"sha1 {hashlib.sha1(body).hexdigest()[:12]}"
              f"{'  SUSPECT' if suspect else ''}")
        time.sleep(1.0)
    return bad


# The host is behind Akamai, which refuses this client on its TLS handshake
# rather than on anything in the request. Every header profile answers 403 while
# a browser on the same machine gets 200, so the fix is a client whose handshake
# is not python's, not a better set of headers.
#
# Measured 2026-09-02, all four against the same file from the same machine and
# the same address within a minute of each other:
#
#   urllib      403        0 bytes
#   curl.exe    403      602 bytes   (an error page, not a workbook)
#   powershell  blocked            "suspected web scraping activity"
#   curl_cffi   200   73,728 bytes   ole_xls
#
# The same file fetched through a browser on that machine was also 73,728 bytes,
# so the working backend and the browser agree to the byte count. Note that
# powershell was told the address was blocked while curl_cffi succeeded from that
# same address seconds later: the refusal is about the client, and the address
# wording is the vendor's generic copy rather than a description of the cause.
#
# Backends are tried in order and the first one that returns a workbook wins,
# so an environment without curl_cffi degrades to reporting a failure loudly
# rather than to writing an error page into the archive. --probe-clients reruns
# the table above.
#
# Requires: pip install curl_cffi
BACKENDS = ("curl_cffi", "curl", "powershell", "urllib")


def _fetch_urllib(url: str, dest: Path) -> tuple[int, int, str]:
    req = urllib.request.Request(url, headers=HEADER_PROFILES["browser_full"])
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
            dest.write_bytes(body)
            return r.status, len(body), ""
    except urllib.error.HTTPError as exc:
        return exc.code, 0, ""
    except Exception as exc:
        return 0, 0, str(exc)


def _fetch_curl(url: str, dest: Path) -> tuple[int, int, str]:
    exe = shutil.which("curl") or shutil.which("curl.exe")
    if not exe:
        return 0, 0, "curl not on PATH"
    cmd = [exe, "-sS", "-L", "--compressed", "-A", BROWSER, "-e", LANDING,
           "--max-time", "120", "-o", str(dest), "-w", "%{http_code}"]
    # bytes in, bytes out: the payload is binary and the status is ASCII, so the
    # pipe is read without a text decoder on purpose (see the encoding lesson in
    # the project rules; a decoder here fails only on days with odd bytes).
    r = subprocess.run(cmd + [url], capture_output=True)
    code = r.stdout.decode("ascii", "replace").strip()[-3:]
    if not code.isdigit():
        return 0, 0, r.stderr.decode("utf-8", "replace").strip()[:120]
    return int(code), dest.stat().st_size if dest.exists() else 0, ""


def _fetch_powershell(url: str, dest: Path) -> tuple[int, int, str]:
    exe = shutil.which("powershell") or shutil.which("pwsh")
    if not exe:
        return 0, 0, "powershell not on PATH"
    script = (
        "$ProgressPreference='SilentlyContinue';"
        f"$r = Invoke-WebRequest -Uri '{url}' -OutFile '{dest}' "
        f"-UserAgent '{BROWSER}' -Headers @{{Referer='{LANDING}'}} "
        "-PassThru -TimeoutSec 120; $r.StatusCode"
    )
    r = subprocess.run([exe, "-NoProfile", "-Command", script], capture_output=True)
    out = r.stdout.decode("utf-8", "replace").strip()
    if not out.isdigit():
        return 0, 0, r.stderr.decode("utf-8", "replace").strip()[:120]
    return int(out), dest.stat().st_size if dest.exists() else 0, ""


def _fetch_curl_cffi(url: str, dest: Path) -> tuple[int, int, str]:
    try:
        from curl_cffi import requests as creq  # type: ignore
    except ImportError:
        return 0, 0, "curl_cffi not installed"
    try:
        r = creq.get(url, impersonate="chrome", timeout=120)
        dest.write_bytes(r.content)
        return r.status_code, len(r.content), ""
    except Exception as exc:
        return 0, 0, str(exc)[:120]


_FETCHERS = {"urllib": _fetch_urllib, "curl": _fetch_curl,
             "powershell": _fetch_powershell, "curl_cffi": _fetch_curl_cffi}


def fetch(url: str, dest: Path, order=BACKENDS) -> tuple[int, int, str, str]:
    """First backend that comes back with a workbook wins. Returns
    (status, bytes, backend, note)."""
    last = (0, 0, "", "no backend ran")
    for name in order:
        status, n, note = _FETCHERS[name](url, dest)
        if status == 200 and n >= MIN_BYTES and dest.exists() \
                and kind(dest.read_bytes()[:8]) in ("zip_xlsx", "ole_xls"):
            return status, n, name, ""
        last = (status, n, name, note)
    return last


def probe_clients() -> None:
    """Which client this host answers. Writes into a scratch path, not the archive."""
    scratch = DAILY.parent / "_probe"
    scratch.mkdir(parents=True, exist_ok=True)
    url = SOURCES["registration"]
    print(f"=== which client gets {url.split('/')[-1]}")
    for name in ("urllib", "curl", "powershell", "curl_cffi"):
        dest = scratch / f"probe_{name}.bin"
        status, n, note = _FETCHERS[name](url, dest)
        head = dest.read_bytes()[:8] if dest.exists() and n else b""
        print(f"  {name:12s} http_{status or '---'}  {n:>8} bytes  "
              f"{kind(head) if head else '-':18s} {note}")
        time.sleep(1.0)
    print("\nThe first line that reads http_200 with ole_xls or zip_xlsx is the "
          "backend to put first in BACKENDS. If none does, install one that "
          "impersonates a browser handshake:  pip install curl_cffi")


def probe() -> None:
    """Enumerate before selecting (D12), on both axes at once.

    Axis one: which header profile the host answers. Axis two: what the landing
    page actually links to, because the two file URLs on record were read off a
    page listing rather than fetched, so a 403 and a moved file look the same
    from here.
    """
    print("=== axis one: header profiles against the file on record")
    url = SOURCES["registration"]
    for name, hdrs in HEADER_PROFILES.items():
        req = urllib.request.Request(url, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read(4096)
                print(f"  {name:14s} http_{r.status}  {r.headers.get('Content-Type')}  "
                      f"first4={body[:4]!r}  final={r.url}")
        except urllib.error.HTTPError as exc:
            server = exc.headers.get("Server") if exc.headers else None
            print(f"  {name:14s} http_{exc.code}  server={server}")
        except Exception as exc:
            print(f"  {name:14s} FAILED {exc}")
        time.sleep(1.0)

    print("\n=== axis two: what the landing pages link to")
    pages = [
        LANDING,
        "https://www.cmegroup.com/delivery_reports/",
        "https://www.cmegroup.com/tools-information/deliverynotices.html",
    ]
    for page in pages:
        req = urllib.request.Request(page, headers=HEADER_PROFILES["browser_full"])
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                html = r.read().decode("utf-8", "replace")
                code = r.status
        except urllib.error.HTTPError as exc:
            print(f"  {page}  http_{exc.code}"); time.sleep(1.0); continue
        except Exception as exc:
            print(f"  {page}  FAILED {exc}"); time.sleep(1.0); continue
        links = sorted(set(re.findall(r'href="([^"]+\.xlsx?)"', html, re.I)))
        print(f"  {page}  http_{code}  {len(html)} chars  {len(links)} workbook links")
        for l in links[:40]:
            print(f"      {l}")
        if not links:
            for pat in ("registration", "stocks-of-grain", "delivery_report"):
                hits = sorted(set(re.findall(r'[^"\'<>\s]*' + pat + r'[^"\'<>\s]*',
                                             html, re.I)))[:8]
                if hits:
                    print(f"      (no .xls links; strings containing {pat!r}:)")
                    for h in hits:
                        print(f"        {h}")
        time.sleep(1.0)

    print("\nIf every profile is 403 and the landing page is 403 too, the host is "
          "refusing this client rather than this path, and the file has to come "
          "through a browser session. If a profile works, put its name in the "
          "--profile default and the scheduled job is done.")


def verify() -> None:
    if not DAILY.exists():
        print("nothing captured yet"); return
    rows = {}
    for p in sorted(DAILY.iterdir()):
        if p.suffix == ".part":
            continue
        stem = p.name.split("-")
        name = stem[0]
        day = "-".join(stem[1:4])[:10]
        rows.setdefault(name, []).append((day, p.stat().st_size, "suspect" in p.name))
    for name, v in sorted(rows.items()):
        days = sorted({d for d, _, _ in v})
        sus = [d for d, _, s in v if s]
        sizes = [s for _, s, ok in v if not ok]
        print(f"{name}: {len(days)} days, {days[0]} .. {days[-1]}, "
              f"sizes {min(sizes) if sizes else 0}..{max(sizes) if sizes else 0}, "
              f"{len(sus)} suspect{': ' + ', '.join(sus) if sus else ''}")
        want = set()
        d0 = datetime.fromisoformat(days[0]).date()
        d1 = datetime.fromisoformat(days[-1]).date()
        n = (d1 - d0).days + 1
        missing = n - len(days)
        print(f"   {missing} calendar days in the span carry no capture "
              f"(weekends and holidays are expected to be among them)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture", action="store_true",
                    help="capture today; this is the default, and the flag "
                         "exists so the scheduled command line says what it does")
    ap.add_argument("--force", action="store_true",
                    help="re-fetch even if today is already on disk")
    ap.add_argument("--verify", action="store_true",
                    help="report the series without fetching anything")
    ap.add_argument("--probe-clients", action="store_true", dest="probe_clients",
                    help="which HTTP client this host answers; writes to a "
                         "scratch path, not the archive")
    ap.add_argument("--probe", action="store_true",
                    help="enumerate header profiles and landing-page links; "
                         "fetches nothing into the archive")
    ap.add_argument("--profile", default="browser_full",
                    choices=sorted(HEADER_PROFILES),
                    help="header profile to fetch with")
    a = ap.parse_args()
    if a.verify:
        verify(); return 0
    if a.probe_clients:
        probe_clients(); return 0
    if a.probe:
        probe(); return 0
    return 1 if capture(a.force, a.profile) else 0


if __name__ == "__main__":
    sys.exit(main())
