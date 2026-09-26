"""B120 probe: locked-price placement plans, the ones that issued and the ones that did not.

**What this is for.** A placement priced on the board resolution date to subscribers named in
advance fixes its price months before the shares are issued. The offering table B110 reads holds
only the plans that issued. This probe lists, from the disclosure platform, the announcements that
mark a plan's other ends: a termination, a pricing base date moved to the first day of the offering
period, a subscription agreement ended. Before any criterion is written it answers what the design
needs from data: which query settings cover both exchanges, whether the platform's placement
category holds these announcements, how many there are per year and how their titles read, and
whether a plan's base date and price can be read from its PDF.

**What it writes.** Nothing under `results/`. Pages, PDFs and the request log land under
`data/raw/b120/` and are reused on the next run. A month window that ended within the last seven
days is asked again, since the platform still adds to it, and a page whose answer changed is kept
under an `.expired` name before the new one is written. A cached page that fails its checks is
renamed the same way and asked again. Nothing is deleted.

    python experiments/b120_probe.py --selftest
    python experiments/b120_probe.py                         # sections 1 to 5
    python experiments/b120_probe.py --pdf-sample 0          # titles only
    python experiments/b120_probe.py --from 2023-01-01 --to 2023-03-31 --keywords 终止

The network part runs on a machine whose connection reaches www.cninfo.com.cn. Reading PDF text
needs PyMuPDF (`pip install pymupdf`); without it section 4 downloads and sizes the files only.
"""

from __future__ import annotations

import argparse
import calendar
import collections
import datetime as dt
import html
import importlib.util
import json
import math
import os
import random
import re
import statistics
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
RAW = ROOT / "data" / "raw" / "b120"

QUERY = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
STATIC = "http://static.cninfo.com.cn/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
           "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
           "Origin": "http://www.cninfo.com.cn", "X-Requested-With": "XMLHttpRequest",
           "Accept": "application/json, text/javascript, */*; q=0.01",
           "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
PDF_HEADERS = {"User-Agent": HEADERS["User-Agent"], "Referer": "http://www.cninfo.com.cn/"}
# From this day a board may price a placement to named subscribers of three kinds on its own resolution date.
START = dt.date(2020, 2, 14)
PAGE_SIZE = 30
# The platform's filter for placement announcements. Section 2 checks it against the same query with no filter.
CATEGORY = "category_zf_szsh"
KEYWORDS = ("终止", "定价基准日", "认购协议", "预案")
# Query settings section 1 tries, in this order: (column, plate).
VARIANTS = (("szse", ""), ("sse", ""), ("szse", "sz;sh"))
CHECK_WINDOW = (dt.date(2023, 3, 1), dt.date(2023, 3, 31))
FRESH_DAYS = 7
DELAY, JITTER = 1.0, 0.4
TRIES, WAITS = 3, (10.0, 30.0)
# Windows in a row with no valid answer before section 3 stops asking and reads the cache only.
BREAKER = 5
ROW_KEYS = ("secCode", "secName", "announcementId", "announcementTitle", "announcementTime", "adjunctUrl")
SENTENCE_WORDS = ("定价基准日", "发行价格", "元/股", "发行对象", "认购对象", "终止", "原因", "综合考虑", "违约", "生效")
CHINA = dt.timezone(dt.timedelta(hours=8))

TIMINGS: dict[str, list[tuple[float, int]]] = collections.defaultdict(list)


def _urlopen_read(req, timeout: float) -> bytes:
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# The selftest swaps these, so every path runs with no network and no clock.
OPEN = _urlopen_read
SLEEP = time.sleep
TODAY = dt.date.today


class Refused(RuntimeError):
    """Every attempt at one request failed."""


def _stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%dT%H%M%S%f")


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part.expired")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def retire(path: Path, reason: str) -> Path:
    """Rename a cached file out of the way. Never deletes."""
    new = path.with_name(f"{path.name}.bad_{_stamp()}.expired")
    os.replace(path, new)
    print(f"    kept {path.name} as {new.name} ({reason})", flush=True)
    return new


def log_request(root: Path, kind: str, outcome: str, seconds: float, nbytes: int, detail: str = "") -> None:
    path = root / "request_log.tsv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.exists() or path.stat().st_size == 0
    lead = ""
    if not fresh:
        with open(path, "rb") as fh:
            fh.seek(-1, os.SEEK_END)
            lead = "" if fh.read(1) == b"\n" else "\n"  # a line left short by a killed run stays alone
    clean = detail.replace("\t", " ").replace("\n", " ")[:300]
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        if fresh:
            fh.write("stamp\tkind\toutcome\tseconds\tbytes\tdetail\n")
        fh.write(f"{lead}{dt.datetime.now().isoformat(timespec='seconds')}\t{kind}\t{outcome}\t{seconds:.3f}\t{nbytes}\t{clean}\n")


def read_request_log(root: Path) -> dict:
    """kind -> {"ok": [(seconds, bytes)], "fail": count}, over every run in the log."""
    out: dict = {}
    path = root / "request_log.tsv"
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        p = line.split("\t")
        if len(p) < 6 or p[2] not in ("ok", "fail"):
            continue  # a line cut short is skipped, not guessed at
        try:
            secs, nbytes = float(p[3]), int(p[4])
        except ValueError:
            continue
        row = out.setdefault(p[1], {"ok": [], "fail": 0})
        if p[2] == "ok":
            row["ok"].append((secs, nbytes))
        else:
            row["fail"] += 1
    return out


def with_retries(root: Path, kind: str, call, label: str) -> bytes:
    """`call()` returns bytes or raises. Pauses DELAY after a success, WAITS after a failed attempt."""
    last = None
    for attempt in range(TRIES):
        t0 = time.monotonic()
        try:
            body = call()
        except Exception as exc:  # retried, then raised with the label attached
            last = exc
            log_request(root, kind, "fail", time.monotonic() - t0, 0, f"{label}: {exc!r}")
            if attempt + 1 < TRIES:
                wait = WAITS[min(attempt, len(WAITS) - 1)]
                print(f"    {kind}: attempt {attempt + 1} of {TRIES} failed ({exc.__class__.__name__}: {str(exc)[:80]}), "
                      f"waiting {wait:.0f}s", flush=True)
                SLEEP(wait)
            continue
        secs = time.monotonic() - t0
        TIMINGS[kind].append((secs, len(body)))
        log_request(root, kind, "ok", secs, len(body), label)
        SLEEP(DELAY * (1.0 + random.uniform(-JITTER, JITTER)))
        return body
    raise Refused(f"{kind}: {last!r} for {label}")


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def clean_title(title) -> str:
    """The platform marks the search word with <em> tags and escapes a few characters."""
    return html.unescape(re.sub(r"</?em>", "", str(title or ""))).strip()


def exchange_of(code) -> str:
    c = str(code)
    if c.startswith(("60", "68", "90")):
        return "Shanghai"
    if c.startswith(("00", "30", "20")):
        return "Shenzhen"
    if c.startswith(("92", "8", "4")):
        return "Beijing"
    return "other"


def day_of(row: dict) -> dt.date:
    return dt.datetime.fromtimestamp(int(row["announcementTime"]) / 1000, tz=CHINA).date()


def month_windows(start: dt.date, end: dt.date) -> list[tuple[dt.date, dt.date]]:
    out, d = [], start
    while d <= end:
        last = dt.date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])
        out.append((d, min(last, end)))
        d = last + dt.timedelta(days=1)
    return out


def page_problem(obj, page: int) -> str | None:
    """Why one answer page is not usable, or None. A page holds PAGE_SIZE rows unless it is the last."""
    if not isinstance(obj, dict):
        return "not a JSON object"
    if "totalAnnouncement" not in obj or "announcements" not in obj:
        return f"keys {sorted(obj)[:12]} carry no totalAnnouncement or announcements"
    total = obj["totalAnnouncement"]
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        return f"total {total!r} is not a count"
    rows = obj["announcements"] or []
    pages = max(1, math.ceil(total / PAGE_SIZE))
    if page > pages:
        return f"page {page} beyond the {pages} a total of {total} fills"
    want = 0 if total == 0 else (PAGE_SIZE if page < pages else total - PAGE_SIZE * (pages - 1))
    if len(rows) != want:
        return f"{len(rows)} rows where page {page} of {pages} holds {want}"
    for r in rows:
        missing = [k for k in ROW_KEYS if k not in r]
        if missing:
            return f"a row without {missing}"
    return None


def query_form(keyword: str, w0: dt.date, w1: dt.date, page: int, category: bool, column: str, plate: str) -> dict:
    return {"pageNum": str(page), "pageSize": str(PAGE_SIZE), "column": column, "tabName": "fulltext", "plate": plate,
            "stock": "", "searchkey": keyword, "secid": "", "category": CATEGORY if category else "", "trade": "",
            "seDate": f"{w0.isoformat()}~{w1.isoformat()}", "sortName": "", "sortType": "", "isHLtitle": "true"}


def cache_path(root: Path, keyword: str, category: bool, column: str, plate: str, w0: dt.date, w1: dt.date, page: int) -> Path:
    setting = f"{column}_{plate.replace(';', '-') or 'all'}_{'zf' if category else 'any'}"
    return root / "cninfo" / keyword / setting / f"{w0.isoformat()}_{w1.isoformat()}_p{page:03d}.json"


def ask_page(root: Path, form: dict) -> tuple[bytes, dict]:
    body = urllib.parse.urlencode(form).encode("utf-8")
    label = f"{form['searchkey']} {form['seDate']} p{form['pageNum']} {form['column']}/{form['plate'] or '-'}/{form['category'] or 'any'}"
    page = int(form["pageNum"])

    def call() -> bytes:
        got = OPEN(urllib.request.Request(QUERY, data=body, headers=HEADERS, method="POST"), 30.0)
        obj = json.loads(got.decode("utf-8"))
        why = page_problem(obj, page)
        if why:
            raise ValueError(why)
        return got

    got = with_retries(root, "query", call, label)
    return got, json.loads(got.decode("utf-8"))


def fetch_window(root: Path, keyword: str, w0: dt.date, w1: dt.date, category: bool, column: str, plate: str,
                 today: dt.date, max_pages: int | None = None) -> tuple[list[dict], str]:
    """Every row the platform returns for one keyword and window, from the cache where it holds, and the state.
    With `max_pages`, the pages past it are not asked."""
    rows, page, pages = [], 1, 1
    fresh = (today - w1).days < FRESH_DAYS
    while page <= pages and (max_pages is None or page <= max_pages):
        path = cache_path(root, keyword, category, column, plate, w0, w1, page)
        form = query_form(keyword, w0, w1, page, category, column, plate)
        obj = None
        if path.exists():
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
                why = page_problem(obj, page)
            except ValueError as exc:
                why = f"not JSON ({exc})"
            if why:
                retire(path, why)
                obj = None
        try:
            if obj is not None and fresh:
                body, new = ask_page(root, form)
                if new != obj:
                    retire(path, "a window that ended within seven days answered differently")
                    atomic_write_bytes(path, body)
                    obj = new
            if obj is None:
                body, obj = ask_page(root, form)
                atomic_write_bytes(path, body)
        except Refused as exc:
            return rows, f"refused at page {page}: {str(exc)[:160]}"
        pages = max(1, math.ceil(obj["totalAnnouncement"] / PAGE_SIZE))
        rows.extend(obj["announcements"] or [])
        page += 1
    return rows, "ok"


def choose_variants(results: list[tuple[tuple[str, str], str, collections.Counter]]) -> list[tuple[str, str]]:
    """The first setting whose rows cover both exchanges; else every answering setting among the first two."""
    for variant, state, ex in results:
        if state == "ok" and ex.get("Shanghai") and ex.get("Shenzhen"):
            return [variant]
    return [v for v, state, _ in results[:2] if state == "ok"]


def template(title) -> str:
    t = clean_title(title)
    head = t.find("：")
    if 0 <= head <= 20:
        t = t[head + 1:]
    t = re.sub(r"20\d\d\s*年", "YYYY年", t)
    return re.sub(r"\d+", "#", t)


def title_flags(title) -> tuple[str, str, str, str]:
    t = clean_title(title)
    return ("issue" if re.search(r"发行|增发", t) else "-",
            "agreement" if re.search(r"认购协议|终止协议|解除", t) else "-",
            "withdraw" if "撤回" in t else "-",
            "review" if re.search(r"审核|注册", t) else "-")


def pick_spread(rows: list[dict], n: int) -> list[dict]:
    rows = sorted(rows, key=lambda r: (int(r["announcementTime"]), str(r["announcementId"])))
    if n <= 0 or not rows:
        return []
    if n >= len(rows):
        return rows
    return [rows[round(i * (len(rows) - 1) / (n - 1))] for i in range(n)] if n > 1 else [rows[len(rows) // 2]]


def pdf_problem(data: bytes) -> str | None:
    if not data.startswith(b"%PDF"):
        return "does not start with %PDF"
    if b"%%EOF" not in data[-2048:]:
        return "no %%EOF in its last 2 KB"
    return None


def sentences(text: str, words=SENTENCE_WORDS, limit: int = 10, width: int = 160) -> list[str]:
    out = []
    for s in re.split(r"[。；\n]", re.sub(r"[ \t\r　]+", "", text)):
        if any(w in s for w in words):
            out.append(s[:width])
            if len(out) >= limit:
                break
    return out


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def section_settings(root: Path, today: dt.date) -> list[tuple[str, str]]:
    w0, w1 = CHECK_WINDOW
    print(f"\n== 1. query settings: 终止 in the placement category, {w0} to {w1}", flush=True)
    results = []
    for column, plate in VARIANTS:
        rows, state = fetch_window(root, "终止", w0, w1, True, column, plate, today)
        ex = collections.Counter(exchange_of(r["secCode"]) for r in rows)
        results.append(((column, plate), state, ex))
        print(f"  column={column!r} plate={plate!r}: {state}, {len(rows)} rows, {dict(sorted(ex.items()))}", flush=True)
    chosen = choose_variants(results)
    print(f"  used from here on: {chosen or 'none answered'}")
    return chosen


def section_category(root: Path, today: dt.date, variants: list[tuple[str, str]]) -> None:
    w0, w1 = CHECK_WINDOW
    print(f"\n== 2. the placement category against no category: 终止, {w0} to {w1}", flush=True)
    with_cat, without, states = {}, {}, []
    for column, plate in variants:
        for category, bag in ((True, with_cat), (False, without)):
            rows, state = fetch_window(root, "终止", w0, w1, category, column, plate, today)
            states.append((column, plate, category, state))
            for r in rows:
                bag[str(r["announcementId"])] = r
    for s in states:
        if s[3] != "ok":
            print(f"  {s}")
    extra = [r for k, r in without.items() if k not in with_cat]
    lost = [r for k, r in with_cat.items() if k not in without]
    near = [r for r in extra if re.search(r"发行|增发|认购|定价基准日", clean_title(r["announcementTitle"]))]
    print(f"  with the category {len(with_cat)}, without {len(without)}; only without {len(extra)}, of them naming an issue, "
          f"a subscription or a base date {len(near)}; only with {len(lost)}")
    for r in sorted(near, key=day_of)[:25]:
        print(f"    not in the category: {r['secCode']} {day_of(r)} {clean_title(r['announcementTitle'])[:90]}")
    for r in sorted([r for r in extra if r not in near], key=day_of)[:8]:
        print(f"    other, not in the category: {r['secCode']} {day_of(r)} {clean_title(r['announcementTitle'])[:70]}")


def section_titles(root: Path, today: dt.date, variants: list[tuple[str, str]], keywords, start: dt.date, end: dt.date) -> dict:
    print(f"\n== 3. titles in the placement category by keyword, month windows {start} to {end}", flush=True)
    windows = month_windows(start, end)
    out = {}
    refused_in_row, stopped = 0, False
    for kw in keywords:
        bag, gaps = {}, []
        for i, (w0, w1) in enumerate(windows):
            for column, plate in variants:
                if stopped and not cache_path(root, kw, True, column, plate, w0, w1, 1).exists():
                    gaps.append((w0.isoformat(), column, "not asked: the section stopped asking"))
                    continue
                rows, state = fetch_window(root, kw, w0, w1, True, column, plate, today)
                if state != "ok":
                    gaps.append((w0.isoformat(), column, state))
                    refused_in_row += 1
                    if refused_in_row >= BREAKER and not stopped:
                        stopped = True
                        print(f"  {BREAKER} windows in a row without a valid answer; reading the cache only from here", flush=True)
                else:
                    refused_in_row = 0
                for r in rows:
                    bag[str(r["announcementId"])] = r
            if (i + 1) % 12 == 0:
                print(f"  {kw}: through {w1}, {len(bag)} rows", flush=True)
        rows = sorted(bag.values(), key=lambda r: (int(r["announcementTime"]), str(r["announcementId"])))
        out[kw] = rows
        years = collections.Counter(day_of(r).year for r in rows)
        ex = collections.Counter(exchange_of(r["secCode"]) for r in rows)
        print(f"\n  {kw}: {len(rows)} announcements, {len({r['secCode'] for r in rows})} companies, "
              f"{dict(sorted(ex.items()))}; by year {dict(sorted(years.items()))}")
        for g in gaps[:12]:
            print(f"    gap: {g}")
        if len(gaps) > 12:
            print(f"    gaps: {len(gaps)} in all")
        for t, c in collections.Counter(template(r["announcementTitle"]) for r in rows).most_common(30):
            print(f"    {c:5d}  {t[:100]}")
        if kw == "终止":
            flags = collections.defaultdict(list)
            for r in rows:
                flags[title_flags(r["announcementTitle"])].append(r)
            print("    flags (issue, agreement, withdraw, review):")
            for f, rs in sorted(flags.items(), key=lambda x: -len(x[1])):
                print(f"      {f}: {len(rs)}")
                for r in pick_spread(rs, 3):
                    print(f"        {r['secCode']} {day_of(r)} {clean_title(r['announcementTitle'])[:90]}")
    return out


def fetch_pdf(root: Path, row: dict) -> tuple[Path | None, str]:
    path = root / "pdf" / f"{row['announcementId']}.pdf"
    if path.exists():
        why = pdf_problem(path.read_bytes())
        if why is None:
            return path, "cached"
        retire(path, why)
    url = STATIC + str(row["adjunctUrl"]).lstrip("/")

    def call() -> bytes:
        got = OPEN(urllib.request.Request(url, headers=PDF_HEADERS), 60.0)
        why = pdf_problem(got)
        if why:
            raise ValueError(why)
        return got

    try:
        data = with_retries(root, "pdf", call, url)
    except Refused as exc:
        return None, str(exc)[:160]
    atomic_write_bytes(path, data)
    return path, "fetched"


def pdf_text(path: Path) -> tuple[str | None, int]:
    if importlib.util.find_spec("pymupdf") is None:
        return None, 0
    import pymupdf
    with pymupdf.open(path) as doc:
        return "\n".join(page.get_text() for page in doc), doc.page_count


def section_pdfs(root: Path, titles: dict, n: int) -> None:
    print(f"\n== 4. a sample of PDFs, {n} per kind, spread over time", flush=True)
    if importlib.util.find_spec("pymupdf") is None:
        print("  PyMuPDF is not installed (pip install pymupdf): files are downloaded and sized, no text is read")
    pools = (("termination of an issue", [r for r in titles.get("终止", []) if title_flags(r["announcementTitle"])[0] == "issue"]),
             ("plan", [r for r in titles.get("预案", [])
                       if not re.search(r"修订|更新|摘要|论证|报告|说明|提示|意见|公告", clean_title(r["announcementTitle"]))]),
             ("base date", titles.get("定价基准日", [])))
    for label, pool in pools:
        print(f"\n  {label}: {len(pool)} in the pool")
        for r in pick_spread(pool, n):
            path, state = fetch_pdf(root, r)
            head = f"  {r['secCode']} {r['secName']} {day_of(r)} {clean_title(r['announcementTitle'])[:80]}"
            if path is None:
                print(f"{head}\n      {state}")
                continue
            text, pages = pdf_text(path)
            size = path.stat().st_size
            if text is None:
                print(f"{head}\n      {state}, {size:,} bytes")
                continue
            print(f"{head}\n      {state}, {size:,} bytes, {pages} pages, {len(text):,} characters")
            for s in sentences(text):
                print(f"        | {s}")


def section_cost(root: Path) -> None:
    print("\n== 5. cost, over every run in the request log", flush=True)
    for kind, row in sorted(read_request_log(root).items()):
        ok = row["ok"]
        if ok:
            print(f"  {kind}: {len(ok)} answered, {row['fail']} failed attempts; median {statistics.median(s for s, _ in ok):.2f}s, "
                  f"median {statistics.median(b for _, b in ok):,.0f} bytes")
        else:
            print(f"  {kind}: none answered, {row['fail']} failed attempts")


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest() -> int:
    global OPEN, SLEEP, DELAY
    fails = []

    def check(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'} {name}")
        if not cond:
            fails.append(name)

    check("titles lose the search marks and escapes",
          clean_title("关于<em>终止</em>2021年度&amp;向特定对象发行") == "关于终止2021年度&向特定对象发行")
    check("codes fall to their exchange",
          [exchange_of(c) for c in ("600206", "688001", "000001", "300909", "920118", "830799", "123456")]
          == ["Shanghai", "Shanghai", "Shenzhen", "Shenzhen", "Beijing", "Beijing", "other"])
    check("month windows start on the start day and end on the end day",
          month_windows(dt.date(2020, 2, 14), dt.date(2020, 4, 3))
          == [(dt.date(2020, 2, 14), dt.date(2020, 2, 29)), (dt.date(2020, 3, 1), dt.date(2020, 3, 31)),
              (dt.date(2020, 4, 1), dt.date(2020, 4, 3))])

    def row(i, code="600206", t0=1678723200000):
        return {"secCode": code, "secName": "测试", "announcementId": str(1000 + i), "announcementTitle": f"关于<em>终止</em>第{i}次",
                "announcementTime": t0 + i * 86400000, "adjunctUrl": f"finalpage/2023-03-14/{1000 + i}.PDF"}

    def page_obj(total, page, start=0):
        n = 0 if total == 0 else (PAGE_SIZE if page < math.ceil(total / PAGE_SIZE) else total - PAGE_SIZE * (math.ceil(total / PAGE_SIZE) - 1))
        base = start + PAGE_SIZE * (page - 1)
        return {"totalAnnouncement": total, "announcements": [row(base + k) for k in range(n)] or None, "hasMore": False}

    check("a full first page and a short last page pass", page_problem(page_obj(45, 1), 1) is None and page_problem(page_obj(45, 2), 2) is None)
    cut = page_obj(45, 2)
    cut["announcements"] = cut["announcements"][:-1]
    bare = page_obj(45, 1)
    del bare["announcements"][3]["adjunctUrl"]
    check("a last page one row short, a row without its file, a page beyond the total and an error body all fail",
          page_problem(cut, 2) is not None and page_problem(bare, 1) is not None and page_problem(page_obj(45, 2), 3) is not None
          and page_problem({"msg": "error"}, 1) is not None and page_problem(page_obj(0, 1), 1) is None)

    served = []
    state = {"total": 45, "down": False}

    def fake_open(req, timeout):
        if state["down"]:
            raise OSError("no network in the selftest")
        form = urllib.parse.parse_qs(req.data.decode("utf-8"))
        page = int(form["pageNum"][0])
        served.append((form["searchkey"][0], form["seDate"][0], page, form["category"][0]))
        return json.dumps(page_obj(state["total"], page), ensure_ascii=False).encode("utf-8")

    sleeps = []
    OPEN, SLEEP, DELAY = fake_open, sleeps.append, 0.0
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            w0, w1 = dt.date(2023, 3, 1), dt.date(2023, 3, 31)
            today = dt.date(2026, 9, 17)
            rows, st = fetch_window(root, "终止", w0, w1, True, "szse", "", today)
            check(f"a window of 45 rows comes back in two pages ({st}, {len(rows)} rows, {len(served)} asked)",
                  st == "ok" and len(rows) == 45 and len({r["announcementId"] for r in rows}) == 45 and len(served) == 2)
            state["down"] = True
            again, st2 = fetch_window(root, "终止", w0, w1, True, "szse", "", today)
            check("the second read comes from the cache with the network down", st2 == "ok" and again == rows)
            p2 = cache_path(root, "终止", True, "szse", "", w0, w1, 2)
            obj = json.loads(p2.read_text(encoding="utf-8"))
            obj["announcements"] = obj["announcements"][:-1]
            p2.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            state["down"] = False
            third, st3 = fetch_window(root, "终止", w0, w1, True, "szse", "", today)
            kept = [x for x in p2.parent.iterdir() if x.name.endswith(".expired")]
            check(f"a cached page one row short is kept under an .expired name and asked again ({len(kept)} kept)",
                  st3 == "ok" and len(third) == 45 and len(kept) == 1)

            recent0, recent1 = dt.date(2026, 9, 1), dt.date(2026, 9, 14)
            state["total"] = 31
            fetch_window(root, "预案", recent0, recent1, True, "szse", "", today)
            before = len(served)
            same, st4 = fetch_window(root, "预案", recent0, recent1, True, "szse", "", today)
            settled = [x for x in cache_path(root, "预案", True, "szse", "", recent0, recent1, 1).parent.iterdir() if x.name.endswith(".expired")]
            check("a window that ended within seven days is asked again, and an unchanged answer keeps its file",
                  st4 == "ok" and len(served) == before + 2 and not settled and len(same) == 31)
            state["total"] = 32
            grown, st5 = fetch_window(root, "预案", recent0, recent1, True, "szse", "", today)
            settled = [x for x in cache_path(root, "预案", True, "szse", "", recent0, recent1, 1).parent.iterdir() if x.name.endswith(".expired")]
            check(f"and an answer that grew replaces the page, the old one kept ({len(grown)} rows, {len(settled)} kept)",
                  st5 == "ok" and len(grown) == 32 and len(settled) >= 1)
            old0, old1 = dt.date(2021, 5, 1), dt.date(2021, 5, 31)
            fetch_window(root, "认购协议", old0, old1, True, "szse", "", today)
            before = len(served)
            fetch_window(root, "认购协议", old0, old1, True, "szse", "", today)
            check("a window that ended long ago is not asked again", len(served) == before)

            attempts = {"n": 0}

            def flaky(req, timeout):
                attempts["n"] += 1
                if attempts["n"] == 1:
                    raise OSError("reset")
                if attempts["n"] == 2:
                    return b'{"msg": "busy", "announcements": null}'
                return fake_open(req, timeout)

            OPEN = flaky
            sleeps.clear()
            state["total"] = 5
            got, st6 = fetch_window(root, "终止", dt.date(2022, 1, 1), dt.date(2022, 1, 31), True, "sse", "", today)
            check(f"a refused attempt and an answer with no total are both asked again ({attempts['n']} attempts, waits {sleeps[:2]})",
                  st6 == "ok" and len(got) == 5 and attempts["n"] == 3 and sleeps[:2] == [WAITS[0], WAITS[1]])
            OPEN = lambda req, timeout: (_ for _ in ()).throw(OSError("down"))
            gone, st7 = fetch_window(root, "终止", dt.date(2022, 2, 1), dt.date(2022, 2, 28), True, "sse", "", today)
            check("three refusals end the window with a named state and no rows", gone == [] and st7.startswith("refused at page 1"))
            log = read_request_log(root)
            with open(root / "request_log.tsv", "a", encoding="utf-8", newline="") as fh:
                fh.write("2026-09-17T00:00:00\tquery\tok\t0.5")
            check(f"the request log counts answers and failures and skips a line cut short ({log['query']['fail']} failed)",
                  read_request_log(root)["query"]["ok"] == log["query"]["ok"] and log["query"]["fail"] >= 4)
            log_request(root, "query", "ok", 0.1, 10, "after a cut line")
            lines = (root / "request_log.tsv").read_text(encoding="utf-8").splitlines()
            check("a line written after a cut line starts on its own line",
                  lines[-2] == "2026-09-17T00:00:00\tquery\tok\t0.5" and lines[-1].endswith("\tafter a cut line"))
    finally:
        OPEN, SLEEP, DELAY = _urlopen_read, time.sleep, 1.0

    ex = collections.Counter
    check("settings: the first covering both exchanges is used alone",
          choose_variants([(("szse", ""), "ok", ex({"Shenzhen": 3})), (("sse", ""), "ok", ex({"Shanghai": 2, "Shenzhen": 1}))])
          == [("sse", "")])
    check("settings: with none covering both, the answering ones of the first two are used together",
          choose_variants([(("szse", ""), "ok", ex({"Shenzhen": 3})), (("sse", ""), "ok", ex({"Shanghai": 2})),
                           (("szse", "sz;sh"), "refused", ex())]) == [("szse", ""), ("sse", "")]
          and choose_variants([(("szse", ""), "refused", ex()), (("sse", ""), "refused", ex())]) == [])
    check("a title's company prefix, years and numbers fold into one template",
          template("有研新材：关于终止2021年度非公开发行A股股票事项的公告") == "关于终止YYYY年度非公开发行A股股票事项的公告"
          and template("关于第3次调整向特定对象发行股票定价基准日的公告") == "关于第#次调整向特定对象发行股票定价基准日的公告")
    check("termination flags read issue, agreement, withdrawal and review apart",
          title_flags("关于终止向特定对象发行股票事项并撤回申请文件的公告") == ("issue", "-", "withdraw", "-")
          and title_flags("关于与认购对象签署附条件生效的股份认购协议之终止协议的公告") == ("-", "agreement", "-", "-")
          and title_flags("关于收到深交所终止审核的通知") == ("-", "-", "-", "review"))
    spread = pick_spread([row(i) for i in range(10)][::-1], 4)
    check("a sample spreads over time from the first to the last", [r["announcementId"] for r in spread] == ["1000", "1003", "1006", "1009"]
          and len(pick_spread([row(1)], 3)) == 1 and pick_spread([row(1)], 0) == [])
    check("a PDF passes with its header and end mark, and fails cut short or without a header",
          pdf_problem(b"%PDF-1.7 body %%EOF\n") is None and pdf_problem(b"%PDF-1.7 body") is not None and pdf_problem(b"<html>") is not None)
    text = "本次发行的定价基准日为公司第三届董事会第十次会议决议公告日。发行价格为7.16元/股。\n公司经营正常；综合考虑资本市场环境，决定终止本次发行。"
    got = sentences(text, width=20)
    check(f"sentences carrying the words are printed, each clipped ({got})",
          got == ["本次发行的定价基准日为公司第三届董事会第", "发行价格为7.16元/股", "综合考虑资本市场环境，决定终止本次发行"])
    check("a day is read in China time", day_of({"announcementTime": 1678723200000}) == dt.date(2023, 3, 14))

    print(f"\n{'selftest passed' if not fails else 'selftest FAILED: ' + ', '.join(fails)}")
    return 0 if not fails else 1


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--from", dest="start", type=dt.date.fromisoformat, default=START)
    ap.add_argument("--to", dest="end", type=dt.date.fromisoformat, default=None)
    ap.add_argument("--keywords", default=",".join(KEYWORDS), help="comma separated")
    ap.add_argument("--pdf-sample", type=int, default=8, help="PDFs per kind in section 4; 0 skips it")
    ap.add_argument("--skip-checks", action="store_true", help="skip sections 1 and 2 and use the first setting")
    ap.add_argument("--selftest", action="store_true", help="offline checks only")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    today = TODAY()
    end = min(args.end or today, today)
    keywords = tuple(k for k in args.keywords.split(",") if k)
    if args.skip_checks:
        variants = [VARIANTS[0]]
    else:
        variants = section_settings(RAW, today)
        if not variants:
            print("\nNo query setting answered. Nothing more is asked; the request log names each refusal.")
            section_cost(RAW)
            return 3
        section_category(RAW, today, variants)
    titles = section_titles(RAW, today, variants, keywords, args.start, end)
    if args.pdf_sample > 0:
        section_pdfs(RAW, titles, args.pdf_sample)
    section_cost(RAW)
    return 0


if __name__ == "__main__":
    sys.exit(main())
