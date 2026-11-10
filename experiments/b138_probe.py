"""B138 block zero: how each company's split-share reform consideration can be read off cninfo, and at what cost.

**What this is for.** The 2005-2008 split-share reform ended the rule that kept a listed company's
non-tradable shares off the exchange. Each company's holders of non-tradable shares paid the
holders of tradable shares a published consideration for the change. Before any criterion is
scored the design needs: which announcements carry the consideration, how many there are per
year, how deep the platform lets a query page, how long one page and one PDF take at each size,
and how the consideration and the share structure are written in the PDF text.

**What it writes.** Nothing under `results/`. Answer pages, PDFs, the text of each PDF and the
request log land under `data/raw/b138/` and are reused on the next run; nothing is deleted.
The printout goes to `data/raw/b138/probe_printout_<time>.txt` as well as the screen.

    python experiments/b138_probe.py                 # sections 1 to 4
    python experiments/b138_probe.py --pdf-sample 0  # no PDFs

Needs a connection that reaches www.cninfo.com.cn, and PyMuPDF for the PDF text.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import random
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
RAW = ROOT / "data" / "raw" / "b138"

QUERY = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
STATIC = "http://static.cninfo.com.cn/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
           "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
           "Origin": "http://www.cninfo.com.cn", "X-Requested-With": "XMLHttpRequest",
           "Accept": "application/json, text/javascript, */*; q=0.01",
           "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
PDF_HEADERS = {"User-Agent": HEADERS["User-Agent"], "Referer": "http://www.cninfo.com.cn/"}
PAGE_SIZE = 30
# The implementation notice states the consideration as carried out; the reform statement states
# the plan and the share structure before the reform.
KEYWORDS = ("股权分置改革方案实施公告", "股权分置改革说明书")
YEARS = tuple(range(2005, 2016))
DELAY, JITTER = 1.0, 0.4
TRIES, WAITS = 3, (10.0, 30.0)
CHINA = dt.timezone(dt.timedelta(hours=8))
# Words around which the PDF text is printed.
CUES = ("对价", "每10股", "每 10 股", "每持有", "获付", "获送", "送股", "转增", "派发", "现金", "权证",
        "缩股", "非流通股", "流通股股东", "股权登记日", "总股本")

TIMINGS: dict[str, list[tuple[float, int]]] = {}
OUT: list[str] = []


def say(*a) -> None:
    s = " ".join(str(x) for x in a)
    OUT.append(s)
    print(s, flush=True)


def _stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%dT%H%M%S")


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part.expired")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def log_request(kind: str, outcome: str, seconds: float, nbytes: int, detail: str) -> None:
    path = RAW / "request_log.tsv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.exists() or path.stat().st_size == 0
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        if fresh:
            fh.write("stamp\tkind\toutcome\tseconds\tbytes\tdetail\n")
        clean = detail.replace("\t", " ").replace("\n", " ")[:300]
        fh.write(f"{dt.datetime.now().isoformat(timespec='seconds')}\t{kind}\t{outcome}\t{seconds:.3f}\t{nbytes}\t{clean}\n")


def fetch(kind: str, req: urllib.request.Request, label: str) -> bytes:
    last = None
    for attempt in range(TRIES):
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read()
        except Exception as exc:  # retried, then raised with the label
            last = exc
            log_request(kind, "fail", time.monotonic() - t0, 0, f"{label}: {exc!r}")
            if attempt + 1 < TRIES:
                time.sleep(WAITS[min(attempt, len(WAITS) - 1)])
            continue
        secs = time.monotonic() - t0
        TIMINGS.setdefault(kind, []).append((secs, len(body)))
        log_request(kind, "ok", secs, len(body), label)
        time.sleep(DELAY * (1.0 + random.uniform(-JITTER, JITTER)))
        return body
    raise RuntimeError(f"{kind}: {last!r} for {label}")


def clean_title(t) -> str:
    return html.unescape(re.sub(r"</?em>", "", str(t or ""))).strip()


def day_of(ms) -> str:
    return dt.datetime.fromtimestamp(ms / 1000, CHINA).date().isoformat()


def page_path(key: str, se: str, page: int) -> Path:
    return RAW / "cninfo" / key / f"{se.replace('~', '_')}_p{page:03d}.json"


def query(key: str, se: str, page: int, *, cached: bool = True) -> tuple[dict, bool]:
    """One answer page. A cached page is read back, not asked again, unless `cached` is False."""
    path = page_path(key, se, page)
    if cached and path.exists():
        return json.loads(path.read_text(encoding="utf-8")), True
    data = urllib.parse.urlencode({
        "pageNum": page, "pageSize": PAGE_SIZE, "column": "szse", "tabName": "fulltext", "plate": "",
        "stock": "", "searchkey": key, "secid": "", "category": "", "trade": "", "seDate": se,
        "sortName": "", "sortType": "", "isHLtitle": "true"}).encode()
    body = fetch("page", urllib.request.Request(QUERY, data=data, headers=HEADERS), f"{key} {se} p{page}")
    j = json.loads(body)
    if not isinstance(j, dict) or "totalAnnouncement" not in j:
        raise RuntimeError(f"unexpected answer for {key} {se} p{page}: {body[:200]!r}")
    if path.exists():
        os.replace(path, path.with_name(f"{path.name}.{_stamp()}.expired"))
    atomic_write_bytes(path, json.dumps(j, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    return j, False


def n_pages(total: int) -> int:
    """The platform's own `totalpages` is rounded down, so a last page short of 30 rows is left out."""
    return -(-total // PAGE_SIZE)


def rows_of(j: dict) -> list[dict]:
    return [r for r in (j.get("announcements") or []) if isinstance(r, dict)]


# ---------------------------------------------------------------------------


def section_counts() -> dict:
    say("\n1  announcements a year, by keyword (page one of each year's query; the platform's own total)")
    counts: dict = {}
    for key in KEYWORDS:
        for y in YEARS:
            j, hit = query(key, f"{y}-01-01~{y}-12-31", 1)
            counts[(key, y)] = (int(j.get("totalAnnouncement") or 0), rows_of(j))
        tot = sum(counts[(key, y)][0] for y in YEARS)
        say(f"  {key}: " + "  ".join(f"{y} {counts[(key, y)][0]}" for y in YEARS) + f"   all {tot}")
    say("  titles on the implementation notices' first pages, by kind (a year's first page, 30 rows):")
    kinds: dict = {}
    for y in YEARS:
        for r in counts[(KEYWORDS[0], y)][1]:
            t = clean_title(r.get("announcementTitle"))
            k = re.sub(r"[（(].*?[)）]", "", t)
            kinds[k] = kinds.get(k, 0) + 1
    for k, n in sorted(kinds.items(), key=lambda kv: -kv[1])[:12]:
        say(f"    {n:4d}  {k}")
    return counts


def section_depth() -> None:
    say("\n2  page depth: one window over the whole reform, pages at three depths, seconds and bytes each")
    for key in KEYWORDS:
        se = "2005-01-01~2015-12-31"
        j, _ = query(key, se, 1, cached=False)
        total = int(j.get("totalAnnouncement") or 0)
        pages = n_pages(total)
        mid, deep = max(1, pages // 2), max(1, pages)
        for p in (mid, deep):
            jj, _ = query(key, se, p, cached=False)
            rr = rows_of(jj)
            first = f"{rr[0]['secCode']} {day_of(rr[0]['announcementTime'])}" if rr else "no rows"
            say(f"  {key}  page {p:4d} of {pages}: {len(rr)} rows  first {first}")
        say(f"  {key}  total {total}, pages {pages}")


# Named cases the first run did not reach: warrant considerations (Baosteel, Yangtze Power, Vanke,
# Xingangfan) and Shenzhen companies.
NAMED = ("600019", "600900", "000002", "000629")
MAIN = re.compile(r"^(董事会)?(关于)?股权分置改革方案实施(的)?公告$")


#: The platform answers no page past this one: a deeper page number returns page one again. A window
#: with more rows than this many pages hold is split by month.
MAX_PAGES = 100


def month_windows(y: int) -> list[str]:
    out = []
    for m in range(1, 13):
        last = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).day
        out.append(f"{y}-{m:02d}-01~{y}-{m:02d}-{last:02d}")
    return out


def window_rows(key: str, se: str) -> tuple[list[dict], dict]:
    """Every row of one window, with what makes the listing checkable: the platform's own total, the
    rows and distinct ids returned, and whether any page repeated an earlier page of the window."""
    j, _ = query(key, se, 1)
    total = int(j.get("totalAnnouncement") or 0)
    pages = n_pages(total)
    rows = rows_of(j)
    seen = [tuple(str(r["announcementId"]) for r in rows)]
    repeated = []
    for p in range(2, pages + 1):
        rr = rows_of(query(key, se, p)[0])
        ids = tuple(str(r["announcementId"]) for r in rr)
        if ids and ids in seen:
            repeated.append(p)
        seen.append(ids)
        rows += rr
    distinct = len({str(r["announcementId"]) for r in rows})
    return rows, {"window": se, "total": total, "pages": pages, "rows": len(rows), "distinct": distinct,
                  "repeated_pages": repeated, "too_deep": pages > MAX_PAGES}


def listing(key: str, coverage: list | None = None) -> list[dict]:
    """Every row of every year's query, all pages; pages already on disk are read back.

    A year with more pages than the platform serves is asked month by month. Rows are returned once
    per announcement id. ``coverage`` receives one entry per window asked."""
    out, have = [], set()
    for y in YEARS:
        j, _ = query(key, f"{y}-01-01~{y}-12-31", 1)
        deep = n_pages(int(j.get("totalAnnouncement") or 0)) > MAX_PAGES
        for se in (month_windows(y) if deep else [f"{y}-01-01~{y}-12-31"]):
            rows, cov = window_rows(key, se)
            cov["year_total"] = int(j.get("totalAnnouncement") or 0)
            if coverage is not None:
                coverage.append(cov)
            for r in rows:
                rid = str(r["announcementId"])
                if rid not in have:
                    have.add(rid)
                    out.append(r)
    return out


def coverage_problems(coverage: list[dict]) -> list[str]:
    """What stands between a listing and the claim that it is whole."""
    bad = []
    for c in coverage:
        if c["too_deep"]:
            bad.append(f"{c['window']}: {c['pages']} pages, past the platform's depth")
        if c["repeated_pages"]:
            bad.append(f"{c['window']}: pages {c['repeated_pages'][:5]} repeat an earlier page")
        if c["distinct"] != c["rows"]:
            bad.append(f"{c['window']}: {c['rows']} rows, {c['distinct']} distinct ids")
        if c["distinct"] != c["total"]:
            bad.append(f"{c['window']}: {c['distinct']} distinct ids against the platform's total {c['total']}")
    return bad


def section_listing() -> list[dict]:
    rows = listing(KEYWORDS[0])
    say(f"\n2b the implementation notices' whole listing: {len(rows)} rows")
    ids = {r["announcementId"] for r in rows}
    say(f"  distinct announcement ids {len(ids)}")
    kinds: dict = {}
    for r in rows:
        t = re.sub(r"[（(].*?[)）]", "", clean_title(r.get("announcementTitle")))
        kinds.setdefault(t, set()).add(str(r["secCode"]))
    for k, cs in sorted(kinds.items(), key=lambda kv: -len(kv[1]))[:15]:
        say(f"    {len(cs):5d} companies  {k}")
    main = [r for r in rows if MAIN.match(re.sub(r"[（(].*?[)）]", "", clean_title(r.get("announcementTitle"))))]
    codes = {str(r["secCode"]) for r in main}
    sh = sum(c.startswith("6") for c in codes)
    say(f"  main notices (title is the implementation notice itself): {len(main)} rows, {len(codes)} companies, "
        f"Shanghai {sh}, Shenzhen {len(codes) - sh}")
    per: dict = {}
    for r in main:
        per.setdefault(str(r["secCode"]), []).append(r)
    multi = {c: v for c, v in per.items() if len(v) > 1}
    say(f"  companies with more than one main notice: {len(multi)}; e.g. "
        + "; ".join(f"{c} x{len(v)}" for c, v in list(multi.items())[:6]))
    return main


def pick_samples(main: list[dict], n: int) -> list[dict]:
    """The named cases, then Shenzhen notices spread over the years."""
    out = []
    by_code: dict = {}
    for r in sorted(main, key=lambda r: r["announcementTime"]):
        by_code.setdefault(str(r["secCode"]), r)
    for c in NAMED:
        if c in by_code:
            out.append(by_code[c])
    sz = [r for c, r in by_code.items() if not c.startswith("6") and c not in NAMED]
    sz.sort(key=lambda r: r["announcementTime"])
    step = max(1, len(sz) // max(1, n - len(out)))
    out += sz[::step][: max(0, n - len(out))]
    return out


def pdf_text(r: dict) -> tuple[str, float, int, bool]:
    aid = str(r["announcementId"])
    path = RAW / "pdf" / f"{aid}.pdf"
    hit = path.exists()
    secs = 0.0
    if not hit:
        t0 = time.monotonic()
        body = fetch("pdf", urllib.request.Request(STATIC + r["adjunctUrl"], headers=PDF_HEADERS), aid)
        secs = time.monotonic() - t0
        if not body.startswith(b"%PDF"):
            raise RuntimeError(f"{aid}: not a PDF ({body[:40]!r})")
        atomic_write_bytes(path, body)
    import pymupdf
    with pymupdf.open(path) as doc:
        text = "\n".join(page.get_text() for page in doc)
    tpath = RAW / "pdf_text" / f"{aid}.txt"
    if not tpath.exists():
        atomic_write_bytes(tpath, text.encode("utf-8"))
    return text, secs, path.stat().st_size, hit


def section_pdfs(counts: dict, n: int) -> None:
    say(f"\n3  {n} implementation notices opened, the lines around the consideration and the share structure")
    for r in pick_samples(counts, n):
        text, secs, size, hit = pdf_text(r)
        flat = re.sub(r"\s+", "", text)
        say(f"\n  -- {r['secCode']} {clean_title(r['secName'])} {day_of(r['announcementTime'])} "
            f"id {r['announcementId']}  {size / 1024:.0f} KB  {'cached' if hit else f'{secs:.2f} s'}  "
            f"{len(flat)} characters of text")
        shown = 0
        for cue in ("对价", "每10股", "每持有", "获付", "权证", "缩股", "派发"):
            for m in re.finditer(re.escape(cue), flat):
                s = flat[max(0, m.start() - 60): m.end() + 90]
                say(f"     [{cue}] {s}")
                shown += 1
                break
        for cue in ("非流通股", "流通股合计", "总股本"):
            m = re.search(re.escape(cue), flat)
            if m:
                say(f"     [{cue}] {flat[max(0, m.start() - 40): m.end() + 120]}")
        if not flat:
            say("     no text layer")


def section_cost(counts: dict) -> None:
    say("\n4  cost of the whole table (medians measured in this run and earlier runs in the log)")
    log = RAW / "request_log.tsv"
    per: dict = {}
    for line in log.read_text(encoding="utf-8").splitlines()[1:]:
        p = line.split("\t")
        if len(p) >= 5 and p[2] == "ok":
            per.setdefault(p[1], []).append((float(p[3]), int(p[4])))
    for kind, xs in sorted(per.items()):
        secs = sorted(s for s, _ in xs)
        say(f"  {kind}: {len(xs)} requests, seconds median {statistics.median(secs):.2f}, "
            f"max {max(secs):.2f}; bytes median {statistics.median(b for _, b in xs):,.0f}")
    n_impl = sum(counts[(KEYWORDS[0], y)][0] for y in YEARS)
    n_stmt = sum(counts[(KEYWORDS[1], y)][0] for y in YEARS)
    pages = sum(-(-counts[(k, y)][0] // PAGE_SIZE) for k in KEYWORDS for y in YEARS)
    pg = statistics.median(s for s, _ in per.get("page", [(1.0, 0)])) + DELAY
    pdf = statistics.median(s for s, _ in per.get("pdf", [(1.0, 0)])) + DELAY
    pdf_b = statistics.median(b for _, b in per.get("pdf", [(1.0, 0)]))
    say(f"  listing: {pages} pages (year windows, both keywords) x {pg:.2f} s = {pages * pg / 60:.1f} min")
    say(f"  implementation notices: {n_impl} PDFs x {pdf:.2f} s = {n_impl * pdf / 60:.1f} min, "
        f"about {n_impl * pdf_b / 2**20:.0f} MB")
    say(f"  reform statements (full text only, if the share structure is not in the notice): up to {n_stmt} "
        f"titles including summaries and revisions")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-sample", type=int, default=8)
    ap.add_argument("--skip-depth", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.monotonic()
    counts = section_counts()
    if not a.skip_depth:
        section_depth()
    main = section_listing()
    if a.pdf_sample:
        section_pdfs(main, a.pdf_sample)
    section_cost(counts)
    say(f"\nprobe {time.monotonic() - t0:.0f} s")
    atomic_write_bytes(RAW / f"probe_printout_{_stamp()}.txt", ("\n".join(OUT) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
