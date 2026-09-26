"""B115: fetch the raw files for the soybean branch, on the machine that runs the project.

Nothing here reads a price. The script puts the raw files on disk, checks that each one is
whole, and keeps a manifest, b115_soy_manifest.json, with the URL, the byte count, the SHA-256
and the retrieval time of every file. Reading the files is a later step.

Sources, all public:

  agtransport  USDA AMS "Grain Basis" on the AgTransport open data platform, Socrata dataset
               v85y-3hep: every soybean row dated 2016-01-01 to 2020-12-31, every market,
               fetched in pages of PAGE rows ordered by date, market and row id.
  dce          Dalian Commodity Exchange yearly history files, as linked from the exchange's
               history page: No. 2 soybeans, soybean meal, No. 1 soybeans and corn, 2016 to
               2020. The 2016 files and 2017 corn are zip archives and the rest are workbooks;
               three 2017 links end in .csv and serve a workbook, which is checked and saved as one.
  fred         FRED series DEXCHUS, yuan per US dollar, daily, whole series, one CSV.
  cepea        CEPEA/ESALQ soybean indicator at Paranagua, the series file. On the indicator
               page the Paranagua series is id=92; id=12 there is the Parana state indicator.

A server may refuse a script. A file saved from a browser then goes in with --import, which runs
the same check as a fetch and records the file as a browser-saved copy of its URL, or with
--import-dir, which takes every planned file it finds in a folder under the name its link ends in.

Run from the repository root with the venv active:

    python experiments/b115_soy_fetch.py --plan               # the files and URLs, no network
    python experiments/b115_soy_fetch.py --probe              # one small request per source, timed
    python experiments/b115_soy_fetch.py --fetch              # fetch what is missing or fails its check
    python experiments/b115_soy_fetch.py --verify             # check what is on disk, no network
    python experiments/b115_soy_fetch.py --import DEST PATH   # one browser-saved file, DEST as --plan prints it
    python experiments/b115_soy_fetch.py --import-dir FOLDER  # every planned file found in a folder
    python experiments/b115_soy_fetch.py --selftest           # offline, seeded faults

Every fetch can be interrupted and run again: a file already on disk that passes its check is
kept, and a download is written to a temporary name and renamed only when it passes. Nothing is
deleted. A file on disk that fails its check is renamed aside with the time it was set aside and
fetched again, and a file that an import replaces is renamed aside the same way.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import io
import json
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data" / "b115" / "raw"
MANIFEST_NAME = "b115_soy_manifest.json"
USER_AGENT = "Mozilla/5.0 (research data fetch; one request at a time)"
TIMEOUT = 120
RETRIES = 3
PAUSE = 1.0

AGT_DATASET = "v85y-3hep"
AGT_BASE = f"https://agtransport.usda.gov/resource/{AGT_DATASET}.json"
AGT_COMMODITY = "Soybeans"
AGT_START, AGT_END = "2016-01-01T00:00:00", "2020-12-31T23:59:59"
PAGE = 5000
MAX_PAGES = 60
#: keys every row must carry; the platform leaves a null field out of a row, so a row without a
#: basis is counted and kept, not refused
AGT_KEYS = ("date", "market_name", "commodity")

DCE_ROOT = "http://www.dce.com.cn/dalianshangpin/resource/cms/"
#: (year, product, path under DCE_ROOT), read from the exchange's history page on 2026-09-16
DCE_FILES = (
    (2016, "corn", "2017/04/c.zip"),
    (2016, "no1_soybeans", "2017/04/a.zip"),
    (2016, "no2_soybeans", "2017/04/b.zip"),
    (2016, "soybean_meal", "2017/04/m.zip"),
    (2017, "corn", "article/6084184/6084269/2018011113545470783.zip"),
    (2017, "no1_soybeans", "2018/01/2018011113533776164.csv"),
    (2017, "no2_soybeans", "2018/01/2018011113530726662.csv"),
    (2017, "soybean_meal", "2018/01/2018011113522038255.csv"),
    (2018, "corn", "2019/01/2019012315465149647.xlsx"),
    (2018, "no1_soybeans", "2019/01/2019012315491595717.xlsx"),
    (2018, "no2_soybeans", "2019/01/2019012315494384352.xlsx"),
    (2018, "soybean_meal", "2019/01/2019012315503149436.xlsx"),
    (2019, "corn", "2020/03/2020030415204421551.xlsx"),
    (2019, "no1_soybeans", "2020/03/2020030415214926535.xlsx"),
    (2019, "no2_soybeans", "2020/03/2020030415221765732.xlsx"),
    (2019, "soybean_meal", "2020/03/2020030415233887199.xlsx"),
    (2020, "corn", "2021/01/2021013022310721941.xlsx"),
    (2020, "no1_soybeans", "2021/01/2021013022293775777.xlsx"),
    (2020, "no2_soybeans", "2021/01/2021013022290225068.xlsx"),
    (2020, "soybean_meal", "2021/01/2021013022274187325.xlsx"),
)
#: links whose name ends in .csv while the exchange serves a workbook, seen in the bodies fetched on
#: 2026-09-16; the check and the name on disk follow the body
BODY_KIND = {
    "2018/01/2018011113533776164.csv": "xlsx",
    "2018/01/2018011113530726662.csv": "xlsx",
    "2018/01/2018011113522038255.csv": "xlsx",
}

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXCHUS"
CEPEA_URL = "https://cepea.org.br/br/indicador/series/soja.aspx?id=92"


# ------------------------------------------------- the plan

def agt_page_url(page: int) -> str:
    params = {"$where": f"commodity='{AGT_COMMODITY}' AND date between '{AGT_START}' and '{AGT_END}'",
              "$order": "date,market_name,:id", "$limit": PAGE, "$offset": page * PAGE}
    return AGT_BASE + "?" + urllib.parse.urlencode(params)


def agt_count_url() -> str:
    params = {"$select": "count(*)",
              "$where": f"commodity='{AGT_COMMODITY}' AND date between '{AGT_START}' and '{AGT_END}'"}
    return AGT_BASE + "?" + urllib.parse.urlencode(params)


def agt_commodities_url() -> str:
    return AGT_BASE + "?" + urllib.parse.urlencode({"$select": "commodity", "$group": "commodity"})


def plan() -> list[dict]:
    """Every file the fetch is meant to leave on disk, with the check it must pass."""
    items = []
    for year, product, path in DCE_FILES:
        ext = BODY_KIND.get(path, path.rsplit(".", 1)[-1].lower())
        items.append({"source": "dce", "url": DCE_ROOT + path, "kind": ext,
                      "dest": f"dce/{year}_{product}.{ext}"})
    items.append({"source": "fred", "url": FRED_URL, "kind": "fred_csv", "dest": "fred/DEXCHUS.csv"})
    items.append({"source": "cepea", "url": CEPEA_URL, "kind": "cepea_series",
                  "dest": "cepea/soja_paranagua_series.xls"})
    return items


def plan_item(dest: str) -> dict:
    for item in plan():
        if item["dest"] == dest:
            return item
    raise RuntimeError(f"{dest} is not in the plan; --plan prints the destinations")


def dce_url(year: int, product: str) -> str:
    for y, p, path in DCE_FILES:
        if (y, p) == (year, product):
            return DCE_ROOT + path
    raise KeyError((year, product))


# ------------------------------------------------- checks

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
END_OF_CHAIN = 0xFFFFFFFE
LAST_SECTOR = 0xFFFFFFF9


def check_ole(data: bytes) -> tuple[bool, str]:
    """Whether an old binary workbook (a compound file) is whole: every sector that its allocation
    table, its directory and its streams point at is on disk, and it holds a workbook stream."""
    if len(data) < 512 or not data.startswith(OLE_MAGIC):
        return False, "not a compound file"

    def u32(buf: bytes, at: int) -> int:
        return int.from_bytes(buf[at:at + 4], "little")

    shift = int.from_bytes(data[30:32], "little")
    if shift not in (9, 12):
        return False, f"compound file with sector shift {shift}"
    size = 1 << shift

    def on_disk(s: int, need: int | None = None) -> bool:
        return s <= LAST_SECTOR and (s + 1) * size + (size if need is None else need) <= len(data)

    def sector(s: int) -> bytes:
        return data[(s + 1) * size:(s + 2) * size]

    n_fat = u32(data, 44)
    fat_sectors = [u32(data, 76 + 4 * i) for i in range(109)][:min(n_fat, 109)]
    difat, seen = u32(data, 68), set()
    for _ in range(u32(data, 72)):
        if not on_disk(difat) or difat in seen:
            return False, "a DIFAT sector is past the end of the file"
        seen.add(difat)
        block = sector(difat)
        fat_sectors += [u32(block, 4 * i) for i in range(size // 4 - 1)]
        difat = u32(block, size - 4)
    fat_sectors = fat_sectors[:n_fat]
    if len(fat_sectors) < n_fat or not all(on_disk(s) for s in fat_sectors):
        return False, "an allocation table sector is past the end of the file"
    fat = [u32(sector(s), 4 * i) for s in fat_sectors for i in range(size // 4)]

    def chain(start: int) -> list[int] | None:
        out, visited, s = [], set(), start
        while s != END_OF_CHAIN:
            if s >= len(fat) or s in visited:
                return None
            visited.add(s)
            out.append(s)
            s = fat[s]
        return out

    directory = chain(u32(data, 48))
    if not directory or not all(on_disk(s) for s in directory):
        return False, "the directory is broken or past the end of the file"
    entries = b"".join(sector(s) for s in directory)
    cutoff = u32(data, 56)
    streams, workbook = 0, None
    for k in range(len(entries) // 128):
        e = entries[128 * k:128 * (k + 1)]
        kind = e[66]
        if kind not in (2, 5):
            continue
        name_len = int.from_bytes(e[64:66], "little")
        name = e[:max(name_len - 2, 0)].decode("utf-16-le", errors="replace")
        start, length = u32(e, 116), u32(e, 120)
        if kind == 5 or length >= cutoff:
            needed = -(-length // size)
            sectors = chain(start) if needed else []
            if sectors is None or len(sectors) < needed:
                return False, f"stream {name!r} has a broken chain"
            used = sectors[:needed]
            tail = length - (needed - 1) * size
            if not all(on_disk(s) for s in used[:-1]) or (used and not on_disk(used[-1], tail)):
                return False, f"stream {name!r} is cut short"
        if kind == 2:
            streams += 1
            if name in ("Workbook", "Book"):
                workbook = length
    if workbook is None:
        return False, "compound file without a workbook stream"
    return True, f"binary workbook, {streams} stream(s), workbook stream {workbook} bytes"


def check_bytes(data: bytes, kind: str) -> tuple[bool, str]:
    """Whether a downloaded body is a whole file of the kind expected, and why not."""
    if not data:
        return False, "empty"
    head = data[:512].lstrip().lower()
    looks_html = head.startswith(b"<!doctype html") or head.startswith(b"<html")
    if kind in ("zip", "xlsx"):
        if not data.startswith(b"PK\x03\x04"):
            return False, "html error page" if looks_html else "not a zip archive"
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = z.namelist()
                bad = z.testzip()
        except zipfile.BadZipFile as e:
            return False, f"truncated or corrupt archive ({e})"
        if bad is not None:
            return False, f"archive member fails its CRC ({bad})"
        if not names:
            return False, "archive has no member"
        if kind == "xlsx" and "xl/workbook.xml" not in names:
            return False, "archive is not a workbook"
        if kind == "xlsx":
            return True, f"xlsx with {len(names)} member(s)"
        return True, f"zip with {len(names)} member(s): " + ", ".join(names[:4])
    if kind == "csv":
        if looks_html:
            return False, "html error page"
        text = None
        for enc in ("utf-8-sig", "gb18030"):
            try:
                text = data.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            return False, "not decodable as utf-8 or gb18030"
        lines = [ln for ln in text.splitlines() if ln.strip()]
        header_at = next((i for i, ln in enumerate(lines) if "," in ln), None)
        if header_at is None:
            return False, "no line with a comma"
        width, after = lines[header_at].count(","), len(lines) - header_at - 1
        if after < 1:
            return False, "no line after the header"
        above = f", {header_at} line(s) above the header" if header_at else ""
        last = lines[-1].count(",")
        if last == width:
            return True, f"csv with {after} data line(s){above}"
        if not text.rstrip(" \t").endswith(("\n", "\r")):
            return False, "last line has a different number of fields than the header and no line end (truncated)"
        return True, (f"csv with {after} line(s) after the header{above}; the last line has "
                      f"{last + 1} field(s) against {width + 1} in the header")
    if kind == "fred_csv":
        ok, why = check_bytes(data, "csv")
        if not ok:
            return ok, why
        first = data.decode("utf-8-sig").splitlines()[0].strip()
        if first not in ("DATE,DEXCHUS", "observation_date,DEXCHUS"):
            return False, f"unexpected header {first!r}"
        return True, why
    if kind == "cepea_series":
        if data.startswith(OLE_MAGIC):
            ok, why = check_ole(data)
            text = data.lower()
        elif data.startswith(b"PK\x03\x04"):
            ok, why = check_bytes(data, "xlsx")
            text = b""
            if ok:
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    text = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml")).lower()
        elif b"<table" in data[:20000].lower() and b"</table>" in data[-20000:].lower():
            ok, why, text = True, "html table saved as a workbook", data.lower()
        else:
            return False, "html error page" if looks_html else "not a workbook"
        if ok and b"paranagu" not in text and "paranagu".encode("utf-16-le") not in text:
            why += "; the text does not name Paranagua, open the file and look"
        return ok, why
    if kind == "agt_page":
        try:
            rows = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            return False, f"page does not parse ({e.__class__.__name__})"
        if not isinstance(rows, list):
            return False, "page is not a list of rows"
        if len(rows) > PAGE:
            return False, "page longer than the page size"
        without_basis = 0
        for r in rows:
            if not isinstance(r, dict) or any(k not in r for k in AGT_KEYS):
                return False, "a row lacks one of " + ", ".join(AGT_KEYS)
            if r["commodity"] != AGT_COMMODITY:
                return False, f"a row of commodity {r['commodity']!r}"
            without_basis += "basis" not in r
        return True, f"page with {len(rows)} row(s), {without_basis} without a basis"
    raise ValueError(f"unknown kind {kind}")


# ------------------------------------------------- disk

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_manifest(raw: Path) -> dict:
    p = raw / MANIFEST_NAME
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_manifest(raw: Path, manifest: dict) -> None:
    raw.mkdir(parents=True, exist_ok=True)
    tmp = raw / (MANIFEST_NAME + ".part")
    tmp.write_text(json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    tmp.replace(raw / MANIFEST_NAME)


def set_aside(path: Path, reason: str = "failed_check") -> Path:
    """Rename a file that failed its check or is being replaced, so it stays on disk and out of the way."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    aside = path.with_name(f"{path.name}.{reason}.{stamp}.expired")
    k = 1
    while aside.exists():
        aside = path.with_name(f"{path.name}.{reason}.{stamp}_{k}.expired")
        k += 1
    path.rename(aside)
    return aside


def keep(raw: Path, rel: str, data: bytes, url: str, why: str, manifest: dict) -> None:
    dest = raw / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    tmp.write_bytes(data)
    tmp.replace(dest)
    manifest[rel] = {"url": url, "bytes": len(data), "sha256": sha256(data),
                     "retrieved_utc": now_utc(), "check": why}


# ------------------------------------------------- network

def http_get(url: str, head: bool = False, opener=None) -> tuple[bytes, dict]:
    """GET (or HEAD) with retries. A body shorter than the server said is an error, whether
    http.client notices it (IncompleteRead) or the Content-Length comparison below does."""
    req = urllib.request.Request(url, method="HEAD" if head else "GET",
                                 headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    open_url = urllib.request.urlopen if opener is None else opener.open
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            with open_url(req, timeout=TIMEOUT) as r:
                body = b"" if head else r.read()
                headers = {k.lower(): v for k, v in r.headers.items()}
                length = headers.get("content-length")
                if not head and length is not None and int(length) != len(body):
                    raise IOError(f"got {len(body)} bytes of {length}")
                return body, headers
        except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
            last = e
            if isinstance(e, urllib.error.HTTPError) and e.code in (401, 403, 404):
                break
            time.sleep(PAUSE * attempt)
    raise RuntimeError(f"{url}: {last}")


# ------------------------------------------------- the three actions

def fetch_file(raw: Path, item: dict, manifest: dict, get=http_get) -> str:
    dest = raw / item["dest"]
    if dest.exists():
        ok, why = check_bytes(dest.read_bytes(), item["kind"])
        if ok:
            return f"kept      {item['dest']}  ({why})"
        aside = set_aside(dest)
        print(f"  set aside {aside.name}: {why}")
    body, _ = get(item["url"])
    ok, why = check_bytes(body, item["kind"])
    if not ok:
        raise RuntimeError(f"{item['url']}: fetched body fails its check: {why}; it begins {body[:120]!r}")
    keep(raw, item["dest"], body, item["url"], why, manifest)
    return f"fetched   {item['dest']}  ({why}, {len(body)} bytes)"


def fetch_agtransport(raw: Path, manifest: dict, get=http_get) -> str:
    body, _ = get(agt_count_url())
    try:
        total = int(next(iter(json.loads(body.decode("utf-8"))[0].values())))
    except (ValueError, LookupError, TypeError, AttributeError, StopIteration) as e:
        raise RuntimeError(f"the count query answered {body[:300]!r}") from e
    if total == 0:
        values, _ = get(agt_commodities_url())
        raise RuntimeError(f"no {AGT_COMMODITY} rows; commodity values on the platform: "
                           f"{values.decode('utf-8')[:300]}")
    pages = -(-total // PAGE)
    if pages > MAX_PAGES:
        raise RuntimeError(f"{total} rows need {pages} pages, more than {MAX_PAGES}; check the query")
    seen = 0
    for page in range(pages):
        rel = f"agtransport/grain_basis_{AGT_COMMODITY.lower()}_2016_2020_p{page:03d}.json"
        dest = raw / rel
        expect = PAGE if page < pages - 1 else total - PAGE * (pages - 1)
        if dest.exists():
            data = dest.read_bytes()
            ok, why = check_bytes(data, "agt_page")
            if ok and len(json.loads(data.decode("utf-8"))) == expect:
                seen += expect
                continue
            print(f"  set aside {set_aside(dest).name}: {why if not ok else 'row count differs'}")
        body, _ = get(agt_page_url(page))
        ok, why = check_bytes(body, "agt_page")
        n = len(json.loads(body.decode("utf-8"))) if ok else -1
        if not ok or n != expect:
            raise RuntimeError(f"page {page}: {why if not ok else f'{n} rows, expected {expect}'}")
        keep(raw, rel, body, agt_page_url(page), why, manifest)
        seen += n
        time.sleep(PAUSE)
    manifest["agtransport/_count"] = {"url": agt_count_url(), "rows": total, "pages": pages,
                                      "retrieved_utc": now_utc()}
    return f"agtransport {total} rows in {pages} page(s), {seen} on disk"


def verify(raw: Path) -> int:
    bad = 0
    for item in plan():
        dest = raw / item["dest"]
        if not dest.exists():
            print(f"  missing   {item['dest']}")
            bad += 1
            continue
        ok, why = check_bytes(dest.read_bytes(), item["kind"])
        print(f"  {'ok' if ok else 'FAILS':9s} {item['dest']}  ({why})")
        bad += int(not ok)
    pages = sorted((raw / "agtransport").glob("grain_basis_*_p*.json")) if (raw / "agtransport").exists() else []
    rows = 0
    for p in pages:
        ok, why = check_bytes(p.read_bytes(), "agt_page")
        bad += int(not ok)
        rows += len(json.loads(p.read_text(encoding="utf-8"))) if ok else 0
        if not ok:
            print(f"  FAILS     {p.name}  ({why})")
    count = load_manifest(raw).get("agtransport/_count", {}).get("rows")
    print(f"  agtransport pages {len(pages)}, rows {rows}, count at fetch {count}")
    if count is None or rows != count:
        bad += 1
    return bad


def probe() -> None:
    """One small request per source, timed, so the cost of a fetch is measured, not guessed."""
    tests = [("agtransport count", agt_count_url(), False),
             ("agtransport commodity values", agt_commodities_url(), False),
             ("dce 2018 no2_soybeans (HEAD)", dce_url(2018, "no2_soybeans"), True),
             ("fred DEXCHUS (HEAD)", FRED_URL, True),
             ("cepea series (HEAD)", CEPEA_URL, True)]
    for name, url, head in tests:
        t0 = time.perf_counter()
        try:
            body, headers = http_get(url, head=head)
            print(f"  {name:32s} {time.perf_counter() - t0:6.2f} s  "
                  f"type {headers.get('content-type', '?')}  length "
                  f"{headers.get('content-length', len(body) if body else '?')}  {body[:240]!r}")
        except RuntimeError as e:
            print(f"  {name:32s} {time.perf_counter() - t0:6.2f} s  refused: {e}")


def import_file(raw: Path, dest: str, src: Path, manifest: dict) -> str:
    """Put a browser-saved file where the fetch would have put it, after the same check."""
    item = plan_item(dest)
    data = src.read_bytes()
    ok, why = check_bytes(data, item["kind"])
    if not ok:
        raise RuntimeError(f"{src.name}: {why}")
    target = raw / dest
    if target.exists():
        if sha256(target.read_bytes()) == sha256(data):
            return f"same      {dest}  (already on disk with the same SHA-256)"
        print(f"  set aside {set_aside(target, 'replaced').name}: replaced by {src.name}")
    keep(raw, dest, data, f"browser-saved copy of {item['url']}", why, manifest)
    manifest[dest]["imported_from"] = src.name
    return f"imported  {dest}  ({why}, {len(data)} bytes, from {src.name})"


def import_dir(raw: Path, folder: Path, manifest: dict) -> tuple[list[str], int]:
    """Import every planned file found in a folder under the name its link ends in."""
    if not folder.is_dir():
        raise RuntimeError(f"{folder} is not a folder")
    lines, problems = [], 0
    for item in plan():
        name = urllib.parse.urlsplit(item["url"]).path.rsplit("/", 1)[-1]
        src = folder / name
        if not src.is_file():
            lines.append(f"not found {item['dest']}  (looked for {name})")
            continue
        try:
            lines.append(import_file(raw, item["dest"], src, manifest))
        except RuntimeError as e:
            problems += 1
            lines.append(f"FAILS     {item['dest']}: {e}")
    return lines, problems


# ------------------------------------------------- self-test

def selftest() -> int:
    """Offline. Pauses between requests are set to zero while it runs."""
    saved = globals()["PAUSE"]
    globals()["PAUSE"] = 0.0
    try:
        return _selftest()
    finally:
        globals()["PAUSE"] = saved


def _selftest() -> int:
    checks, fails = 0, []

    def expect(cond, what):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(what)

    def zip_bytes(names):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for n in names:
                z.writestr(n, "x" * 2000)
        return buf.getvalue()

    good_zip = zip_bytes(["a.csv"])
    good_xlsx = zip_bytes(["[Content_Types].xml", "xl/workbook.xml"])
    expect(check_bytes(good_zip, "zip")[0], "a whole zip fails")
    expect(not check_bytes(good_zip[:-40], "zip")[0], "a truncated zip passes")
    flipped = bytearray(good_zip)
    flipped[flipped.index(b"x" * 100) + 50] ^= 0x01
    expect(not check_bytes(bytes(flipped), "zip")[0], "a zip whose member fails its CRC passes")
    expect(check_bytes(good_xlsx, "xlsx")[0], "a whole workbook fails")
    expect(not check_bytes(good_zip, "xlsx")[0], "a zip without a workbook passes as a workbook")
    html = b"<!DOCTYPE html><html><body>403 Forbidden</body></html>"
    expect(check_bytes(html, "xlsx") == (False, "html error page"), "an error page passes as a workbook")
    csv_ok = "日期,开盘价,收盘价\n2017-01-03,3000,3010\n2017-01-04,3010,3020\n".encode("gb18030")
    expect(check_bytes(csv_ok, "csv")[0], "a whole gb18030 csv fails")
    expect(not check_bytes(csv_ok[:-6], "csv")[0], "a csv cut mid-line passes")
    footer = csv_ok + "注：成交量单位为手\n".encode("gb18030")
    ok_f, why_f = check_bytes(footer, "csv")
    expect(ok_f and "the last line has 1 field(s)" in why_f,
           "a whole csv ending in a note line fails, or the note line is not reported")
    expect(not check_bytes(footer[:-1], "csv")[0], "a csv whose short last line has no line end passes")
    titled = "大连商品交易所 历史行情\n".encode("gb18030") + csv_ok
    ok_t, why_t = check_bytes(titled, "csv")
    expect(ok_t and "2 data line(s), 1 line(s) above the header" in why_t,
           "a whole csv under a title line fails, or its header is taken from the title")
    expect(not check_bytes(titled[:-6], "csv")[0], "a csv under a title line cut mid-line passes")
    expect(not check_bytes("大连商品交易所 历史行情\n日期,开盘价,收盘价\n".encode("gb18030"), "csv")[0],
           "a csv with a header and no line under it passes")
    fred = b"observation_date,DEXCHUS\n2018-07-06,6.6417\n2018-07-09,6.6346\n"
    expect(check_bytes(fred, "fred_csv")[0], "a whole FRED csv fails")
    expect(not check_bytes(fred.replace(b"DEXCHUS", b"DEXUSEU"), "fred_csv")[0], "another FRED series passes")
    expect(not check_bytes(b"\xd0\xcf\x11\xe0" + b"\x00" * 600, "cepea_series")[0],
           "four magic bytes and zeros pass as a workbook")
    expect(not check_bytes(html, "cepea_series")[0], "an error page passes as the CEPEA series")

    def ole_bytes(payload: bytes, stream: str = "Workbook", loop: bool = False, fat_last: bool = False) -> bytes:
        """A compound file of 512-byte sectors holding one stream: allocation table, directory,
        stream; or, with fat_last, directory, stream, allocation table."""
        size, end, free = 512, END_OF_CHAIN, 0xFFFFFFFF
        n = -(-len(payload) // size)
        first = 1 if fat_last else 2
        fat_at, dir_at = (n + 1, 0) if fat_last else (0, 1)
        fat = [free] * (size // 4)
        fat[fat_at], fat[dir_at] = 0xFFFFFFFD, end
        for k in range(n):
            fat[first + k] = first + k + 1 if k < n - 1 else end
        if loop:
            fat[first + n - 1] = first
        head = bytearray(512)
        head[0:8] = OLE_MAGIC
        for at, value, width in ((24, 0x3E, 2), (26, 3, 2), (28, 0xFFFE, 2), (30, 9, 2), (32, 6, 2),
                                 (44, 1, 4), (48, dir_at, 4), (56, 4096, 4), (60, end, 4), (68, end, 4),
                                 (76, fat_at, 4)):
            head[at:at + width] = value.to_bytes(width, "little")
        head[80:512] = free.to_bytes(4, "little") * 108

        def entry(name: str, kind: int, start: int, length: int, child: int = free) -> bytes:
            e = bytearray(128)
            encoded = name.encode("utf-16-le") + b"\x00\x00"
            e[:len(encoded)] = encoded
            e[64:66] = len(encoded).to_bytes(2, "little")
            e[66], e[67] = kind, 1
            for at, value in ((68, free), (72, free), (76, child), (116, start), (120, length)):
                e[at:at + 4] = value.to_bytes(4, "little")
            return bytes(e)

        directory = entry("Root Entry", 5, end, 0, child=1) + entry(stream, 2, first, len(payload)) + bytes(256)
        table = b"".join(v.to_bytes(4, "little") for v in fat)
        data = payload + bytes(n * size - len(payload))
        return bytes(head) + (directory + data + table if fat_last else table + directory + data)

    named = (b"Indicador da soja Paranagu\xe1;" * 200)[:5000]
    whole = ole_bytes(named)
    expect(check_ole(whole)[0], "a whole binary workbook fails")
    expect(check_ole(whole[:-100])[0], "a binary workbook cut only in the padding after its data fails")
    expect(not check_ole(whole[:-300])[0], "a binary workbook cut inside its data passes")
    expect(not check_ole(whole[:-1024])[0], "a binary workbook missing whole sectors passes")
    expect(not check_ole(ole_bytes(named, stream="WordDocument"))[0], "a compound file without a workbook stream passes")
    expect(not check_ole(ole_bytes(named, loop=True))[0], "an allocation chain that loops passes")
    moved = ole_bytes(named, fat_last=True)
    expect(check_ole(moved)[0], "a whole binary workbook with its allocation table at the end fails")
    ok_m, why_m = check_ole(moved[:-512])
    expect(not ok_m and "allocation table" in why_m,
           "a binary workbook missing its allocation table passes, or is reported as something else")
    ok_c, why_c = check_bytes(whole, "cepea_series")
    expect(ok_c and "does not name" not in why_c, "the Paranagua series in a binary workbook fails, or is flagged")
    ok_p, why_p = check_bytes(ole_bytes((b"Indicador da soja Paran\xe1;" * 250)[:5000]), "cepea_series")
    expect(ok_p and "does not name Paranagua" in why_p, "a workbook of another series is not flagged")
    expect(not check_bytes(whole[:-300], "cepea_series")[0], "a cut binary workbook passes as the CEPEA series")

    per_year = {y: sorted(q for yy, q, _ in DCE_FILES if yy == y) for y in range(2016, 2021)}
    dce_dests = [i["dest"] for i in plan() if i["source"] == "dce"]
    expect(len(DCE_FILES) == 20 and len(set(dce_dests)) == 20
           and all(v == ["corn", "no1_soybeans", "no2_soybeans", "soybean_meal"] for v in per_year.values()),
           "the plan does not hold the four products in each of the five years")
    bodies = {i["dest"]: i["kind"] for i in plan() if i["source"] == "dce"}
    expect(all(bodies.get(f"dce/2017_{p}.xlsx") == "xlsx" for p in ("no1_soybeans", "no2_soybeans", "soybean_meal"))
           and not any(d.endswith(".csv") for d in bodies),
           "the 2017 links that serve a workbook are not checked and saved as workbooks")
    row = {"date": "2018-07-06T00:00:00.000", "market_name": "Pacific Northwest",
           "commodity": AGT_COMMODITY, "basis": "1.2"}
    page = json.dumps([row, row]).encode("utf-8")
    expect(check_bytes(page, "agt_page")[0], "a whole page fails")
    expect(not check_bytes(page[:-5], "agt_page")[0], "a truncated page passes")
    expect(not check_bytes(json.dumps([dict(row, commodity="Corn")]).encode(), "agt_page")[0],
           "a page of another commodity passes")
    ok_b, why_b = check_bytes(json.dumps([row, {k: v for k, v in row.items() if k != "basis"}]).encode(), "agt_page")
    expect(ok_b and "1 without a basis" in why_b, "a row without a basis stops its page, or is not counted")
    expect(not check_bytes(json.dumps([{k: v for k, v in row.items() if k != "market_name"}]).encode(), "agt_page")[0],
           "a row without a market passes")
    expect(not check_bytes(b'{"error": true, "message": "No such column"}', "agt_page")[0],
           "an error object passes as a page")

    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw"
        manifest: dict = {}
        item = {"source": "dce", "url": "http://example.invalid/b.xlsx", "kind": "xlsx", "dest": "dce/2018_x.xlsx"}
        calls = []

        def get_good(url, head=False):
            calls.append(url)
            return good_xlsx, {}

        def get_trunc(url, head=False):
            calls.append(url)
            return good_xlsx[:-30], {}

        fetch_file(raw, item, manifest, get=get_good)
        expect(len(calls) == 1 and (raw / item["dest"]).exists() and manifest[item["dest"]]["sha256"] == sha256(good_xlsx),
               "a fetched file is not kept with its hash")
        fetch_file(raw, item, manifest, get=get_good)
        expect(len(calls) == 1, "a file that passes its check is fetched again")
        (raw / item["dest"]).write_bytes(good_xlsx[:-30])
        fetch_file(raw, item, manifest, get=get_good)
        asides = list((raw / "dce").glob("2018_x.xlsx.failed_check.*.expired"))
        expect(len(calls) == 2 and len(asides) == 1 and check_bytes((raw / item["dest"]).read_bytes(), "xlsx")[0],
               "a truncated file on disk is not set aside and fetched again")
        before = sorted(p.name for p in (raw / "dce").iterdir())
        try:
            fetch_file(raw, dict(item, dest="dce/2019_y.xlsx"), manifest, get=get_trunc)
            expect(False, "a truncated download is kept")
        except RuntimeError:
            pass
        expect(not (raw / "dce" / "2019_y.xlsx").exists() and set(before) <= set(p.name for p in (raw / "dce").iterdir()),
               "a failed download leaves a file under the final name, or a file disappears")

        # agtransport paging: the count decides the pages, and a short page stops the fetch
        rows = [dict(row, market_name=f"m{k}") for k in range(7)]
        saved_page = globals()["PAGE"]
        globals()["PAGE"] = 3
        try:
            def get_agt(url, head=False):
                calls.append(url)
                if "count" in urllib.parse.unquote(url):
                    return json.dumps([{"count": str(len(rows))}]).encode(), {}
                off = int(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["$offset"][0])
                return json.dumps(rows[off:off + 3]).encode(), {}

            msg = fetch_agtransport(raw, manifest, get=get_agt)
            pages = sorted((raw / "agtransport").glob("*.json"))
            expect(len(pages) == 3 and manifest["agtransport/_count"]["rows"] == 7 and "7 rows in 3" in msg,
                   "agtransport paging does not follow the count")
            n_calls = len(calls)
            fetch_agtransport(raw, manifest, get=get_agt)
            expect(len(calls) == n_calls + 1, "pages already on disk are fetched again")

            def get_short(url, head=False):
                if "count" in urllib.parse.unquote(url):
                    return json.dumps([{"count": "8"}]).encode(), {}
                return get_agt(url, head)

            raw2 = Path(td) / "raw2"
            try:
                fetch_agtransport(raw2, {}, get=get_short)
                expect(False, "a page shorter than the count requires is kept")
            except RuntimeError:
                pass
            try:
                fetch_agtransport(Path(td) / "raw2b", {}, get=lambda url, head=False: (b'{"error": true}', {}))
                expect(False, "an error answer to the count query is taken as a count")
            except RuntimeError:
                pass
            except Exception as e:
                expect(False, f"an error answer to the count query escapes as {e.__class__.__name__}")
        finally:
            globals()["PAGE"] = saved_page

        # a browser-saved file goes in through the same check, and nothing on disk disappears
        dest = "dce/2018_no2_soybeans.xlsx"
        bad_src, good_src, other_src = (Path(td) / n for n in ("bad.xlsx", "good.xlsx", "other.xlsx"))
        bad_src.write_bytes(good_xlsx[:-30])
        good_src.write_bytes(good_xlsx)
        other = zip_bytes(["[Content_Types].xml", "xl/workbook.xml", "xl/worksheets/sheet1.xml"])
        other_src.write_bytes(other)
        raw3, m3 = Path(td) / "raw3", {}
        try:
            import_file(raw3, dest, bad_src, m3)
            expect(False, "a truncated browser-saved file is imported")
        except RuntimeError:
            pass
        expect(not (raw3 / dest).exists() and dest not in m3, "a failed import leaves a file or a manifest entry")
        import_file(raw3, dest, good_src, m3)
        expect((raw3 / dest).exists() and m3[dest]["url"] == "browser-saved copy of " + dce_url(2018, "no2_soybeans")
               and m3[dest]["imported_from"] == "good.xlsx", "an import is not recorded as a browser-saved copy of its URL")
        expect(import_file(raw3, dest, good_src, m3).startswith("same"), "importing the same file again replaces it")
        import_file(raw3, dest, other_src, m3)
        expect(len(list((raw3 / "dce").glob("2018_no2_soybeans.xlsx.replaced.*.expired"))) == 1
               and sha256((raw3 / dest).read_bytes()) == sha256(other), "a replaced file is not set aside")
        try:
            import_file(raw3, "dce/2018_rapeseed.xlsx", good_src, m3)
            expect(False, "a destination outside the plan is accepted")
        except RuntimeError:
            pass

        folder, raw4, m4 = Path(td) / "downloads", Path(td) / "raw4", {}
        folder.mkdir()
        (folder / "2019012315491595717.xlsx").write_bytes(good_xlsx)        # 2018 No. 1 soybeans
        (folder / "2019012315503149436.xlsx").write_bytes(good_xlsx[:-30])  # 2018 soybean meal, cut
        (folder / "unrelated.xlsx").write_bytes(good_xlsx)
        lines, problems = import_dir(raw4, folder, m4)
        landed = sorted(q.name for q in (raw4 / "dce").iterdir()) if (raw4 / "dce").exists() else []
        expect(landed == ["2018_no1_soybeans.xlsx"] and problems == 1
               and sum(ln.startswith("not found") for ln in lines) == len(plan()) - 2,
               "a folder import takes the wrong files, or misses a failed check")

    # a transfer cut short: a local server promises 1000 bytes and sends 64 (http.client notices), or
    # sends 64 in chunks under a Content-Length of 1000 (only the comparison in http_get notices)
    def serve(srv: socket.socket, count: int) -> None:
        for _ in range(count):
            try:
                conn, _ = srv.accept()
            except OSError:
                return
            with conn:
                first_line = conn.recv(4096).split(b"\r\n", 1)[0]
                body = b"PK\x03\x04" + b"x" * 60
                if b"/chunked" in first_line:
                    conn.sendall(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nContent-Length: 1000\r\n"
                                 b"Connection: close\r\n\r\n" + b"%x\r\n" % len(body) + body + b"\r\n0\r\n\r\n")
                    continue
                length = len(body) if b"/whole" in first_line else 1000
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % length + body)

    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)
    srv.settimeout(20)
    threading.Thread(target=serve, args=(srv, 1 + 2 * RETRIES), daemon=True).start()
    direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    base = f"http://127.0.0.1:{srv.getsockname()[1]}"
    try:
        body, _ = http_get(base + "/whole", opener=direct)
        expect(len(body) == 64, "a whole transfer from the local server does not arrive")
        try:
            http_get(base + "/cut", opener=direct)
            expect(False, "a transfer cut short is returned as a body")
        except RuntimeError as e:
            expect("IncompleteRead" in str(e) or "bytes of" in str(e), f"a transfer cut short fails for another reason: {e}")
        except Exception as e:
            expect(False, f"a transfer cut short escapes as {e.__class__.__name__}")
        try:
            http_get(base + "/chunked", opener=direct)
            expect(False, "a body shorter than its Content-Length header is returned")
        except RuntimeError as e:
            expect("bytes of" in str(e), f"a body shorter than its Content-Length header fails for another reason: {e}")
    except RuntimeError as e:
        expect(False, f"the local server could not be reached: {e}")
    finally:
        srv.close()

    for f in fails:
        print(f"SELFTEST FAIL  {f}")
    print(f"selftest: {checks - len(fails)} of {checks} passed")
    return 1 if fails else 0


# ------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true")
    g.add_argument("--probe", action="store_true")
    g.add_argument("--fetch", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--import", dest="import_file", nargs=2, metavar=("DEST", "PATH"))
    g.add_argument("--import-dir", type=Path, metavar="FOLDER")
    g.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.plan:
        print(f"raw files go under {RAW}")
        print(f"  agtransport {AGT_COMMODITY} {AGT_START[:10]} to {AGT_END[:10]}, pages of {PAGE}: {agt_count_url()}")
        for item in plan():
            print(f"  {item['source']:6s} {item['dest']:40s} {item['url']}")
        return 0
    if a.probe:
        probe()
        return 0
    if a.verify:
        bad = verify(RAW)
        print(f"{bad} problem(s)")
        return 1 if bad else 0
    manifest = load_manifest(RAW)
    if a.import_file:
        dest, src = a.import_file
        try:
            print(import_file(RAW, dest, Path(src), manifest))
        except (RuntimeError, OSError) as e:
            print(f"  not imported: {e}")
            return 1
        finally:
            save_manifest(RAW, manifest)
        return 0
    if a.import_dir:
        try:
            lines, problems = import_dir(RAW, a.import_dir, manifest)
        except RuntimeError as e:
            print(f"  {e}")
            return 1
        finally:
            save_manifest(RAW, manifest)
        for line in lines:
            print(f"  {line}")
        took = sum(line.startswith(("imported", "same")) for line in lines)
        print(f"{took} planned file(s) on disk from the folder, {problems} failed a check")
        return 1 if problems else 0
    problems = 0
    try:
        print(fetch_agtransport(RAW, manifest))
    except RuntimeError as e:
        problems += 1
        print(f"  agtransport: {e}")
    finally:
        save_manifest(RAW, manifest)
    for item in plan():
        try:
            print(fetch_file(RAW, item, manifest))
        except RuntimeError as e:
            problems += 1
            print(f"  {item['source']}: {e}")
        finally:
            save_manifest(RAW, manifest)
        time.sleep(PAUSE)
    print(f"{problems} source(s) with a problem; manifest {RAW / MANIFEST_NAME}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
