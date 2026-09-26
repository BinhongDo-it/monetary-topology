"""B110 probe: what the private-placement carrier holds, and what a full pull costs.

**What this is for.** An offering to specified investors is an entry edge that only
one class of holder can walk: the price is floored by rule at a fraction of the
twenty-day average before the pricing base date, and the lock-up is written by rule
per class of subscriber. The station reads how much passes through that edge and to
which class. Before any criterion is written, this probe answers three questions
the design needs answered from data rather than assumed: how many offerings and
unlock records the public tables actually carry (a table's row count and the number
of records it holds for a given year are different things), what each date field
means, and what a full pull costs per request.

**What it writes.** Nothing under `results/`. Everything fetched lands under
`data/raw/b110/` and is reused on the next run. A table snapshot is keyed by the
server's row count at the start of the run, so a table that grows between runs
starts a new snapshot and the old one stays on disk.

**Cache rules.** A page is kept only if it parses, reports success, and carries the
number of rows its position in the paging implies. A cached page that fails those
checks is renamed with an `.expired` suffix and fetched again. Nothing is deleted.

    python experiments/b110_probe.py                    # tables, sample, cost
    python experiments/b110_probe.py --sample 36        # a larger sample of unlock batches
    python experiments/b110_probe.py --kline-delay 6    # slower pacing on the daily-bar host
    python experiments/b110_probe.py --selftest         # offline checks of every parser here

The network part has to run on a machine whose connection reaches the data portal.

**The daily-bar host can close a connection without answering.** The first run met that on
its third stock, three attempts in a row, and stopped there. A daily-bar request with no
answer now waits 15 s, then 45 s, and a stock that still gets nothing is recorded by name
while the run goes on. After three stocks in a row get nothing, the rest of that section
reads the cache only, so the cost section and the summary are still written. Every request,
answered or not, is appended to `data/raw/b110/request_log.tsv`, and the cost section reads
that log, so what one run measured is still there when the next run finds everything cached.

**The second run got no answer through the plain python client at all**, nine attempts on
three stocks across three minutes, while the table host kept answering. **The third run asked
once each through curl_cffi, curl and plain python, and all three connections were closed**
(curl reports error 56, the server closing the connection), so the refusal does not depend
on the client. Section 4 therefore also asks baostock, a separate daily-bar source reached over
its own socket protocol, which carries turnover in yuan, the exchange's previous close and a
trading-status flag. The first stock is asked once through each installed client in the order
curl_cffi, curl, plain python, baostock, and the rest are pulled through the first one that
answers. `pip install baostock` adds that source; it brings pandas along.
"""

from __future__ import annotations

import argparse
import calendar
import collections
import datetime as dt
import http.client
import importlib.util
import json
import os
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import types
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
RAW = ROOT / "data" / "raw" / "b110"

DATACENTER = "https://datacenter-web.eastmoney.com/api/data/v1/get"
KLINE = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"}
# The daily-bar host is the one the quote pages call, so its requests name that page as referer.
KLINE_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                               "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                 "Referer": "https://quote.eastmoney.com/"}
# Stocks in a row that get no answer before the daily-bar section stops asking.
KLINE_BREAKER = 3
# Pauses after a daily-bar attempt that got no answer, before the next attempt.
KLINE_WAITS = (15.0, 45.0)

# Share-type strings on the unlock tables that belong to offerings to specified
# investors. The probe prints every string the table carries, so this list is
# checked against the table rather than trusted.
PLACEMENT_MARKERS = ("增发", "定向", "非公开", "特定对象")

TIMINGS: dict[str, list[tuple[float, int]]] = collections.defaultdict(list)
# Attempts in this run that got no usable answer: endpoint -> [(attempt number, exception text)].
FAILURES: dict[str, list[tuple[int, str]]] = collections.defaultdict(list)


def _urlopen_read(req, timeout: float) -> bytes:
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# The selftest swaps these, so the retry path runs with no network, no clock and no subprocess.
OPEN = _urlopen_read
SLEEP = time.sleep
RUN = subprocess.run
WHICH = shutil.which

# Clients for daily bars, asked in this order at the start of section 4. The first three reach the
# eastmoney host; baostock is a separate source.
KLINE_BACKENDS = ("curl_cffi", "curl", "urllib", "baostock")


def _get_urllib(url: str, headers: dict, timeout: float) -> bytes:
    return OPEN(urllib.request.Request(url, headers=headers), timeout)


def _get_curl_cffi(url: str, headers: dict, timeout: float) -> bytes:
    from curl_cffi import requests as creq  # backend_available reports an absent package first
    r = creq.get(url, headers=headers, impersonate="chrome", timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"http {r.status_code}")
    return r.content


def curl_command(exe: str, url: str, headers: dict, timeout: float) -> list[str]:
    cmd = [exe, "--silent", "--show-error", "--fail", "--compressed", "--max-time", str(int(timeout))]
    for k, v in headers.items():
        cmd += ["-A", v] if k == "User-Agent" else ["-H", f"{k}: {v}"]
    return cmd + [url]


def _curl_exe() -> str | None:
    return WHICH("curl.exe") or WHICH("curl")


def _get_curl(url: str, headers: dict, timeout: float) -> bytes:
    exe = _curl_exe()
    if not exe:
        raise FileNotFoundError("curl not on PATH")
    p = RUN(curl_command(exe, url, headers, timeout), capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"curl exit {p.returncode}: {p.stderr.decode('utf-8', 'replace').strip()[:200]}")
    return p.stdout


GETTERS = {"urllib": _get_urllib, "curl_cffi": _get_curl_cffi, "curl": _get_curl}


def backend_available(name: str) -> bool:
    if name in ("curl_cffi", "baostock"):
        return importlib.util.find_spec(name) is not None
    if name == "curl":
        return _curl_exe() is not None
    return name in GETTERS


# ---------------------------------------------------------------------------
# Transport and cache
# ---------------------------------------------------------------------------

def _stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%dT%H%M%S")


class Refused(RuntimeError):
    """Every attempt at one request failed: no response, or an HTTP error status."""


def log_request(endpoint: str, outcome: str, seconds: float, nbytes: int, detail: str = "") -> None:
    """Append one request to the cost log. The log sits under data/, which the repository ignores."""
    path = RAW / "request_log.tsv"
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
            fh.write("stamp\tendpoint\toutcome\tseconds\tbytes\tdetail\n")
        fh.write(f"{lead}{dt.datetime.now().isoformat(timespec='seconds')}\t{endpoint}\t{outcome}\t"
                 f"{seconds:.3f}\t{nbytes}\t{clean}\n")


def read_request_log() -> dict:
    """endpoint -> {"ok": [(seconds, bytes)], "fail": count}, over every run in the log."""
    path = RAW / "request_log.tsv"
    out: dict = {}
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
        ep = p[1]
        if ep in ("kline_full", "kline_window"):
            ep += "/urllib"  # lines logged before the client was part of the name all came through urllib
        row = out.setdefault(ep, {"ok": [], "fail": 0})
        if p[2] == "ok":
            row["ok"].append((secs, nbytes))
        else:
            row["fail"] += 1
    return out


def with_retries(endpoint: str, call, delay: float, tries: int, waits, jitter: float, label: str) -> bytes:
    """`call()` returns bytes or raises. Retried; raises Refused, with `label` attached, when every
    attempt fails.

    After a success it pauses `delay`, stretched by up to `jitter` of itself either way. After
    failed attempt i it pauses `waits[i]` (the last entry repeats), or by default
    delay * 2**i + 1 s. There is no pause after the last attempt.
    """
    last = None
    for attempt in range(tries):
        t0 = time.monotonic()
        try:
            body = call()
        except Exception as exc:  # retried, then raised with the label attached
            last = exc
            FAILURES[endpoint].append((attempt + 1, repr(exc)))
            log_request(endpoint, "fail", time.monotonic() - t0, 0, repr(exc))
            if attempt + 1 < tries:
                wait = waits[min(attempt, len(waits) - 1)] if waits else delay * (2 ** attempt) + 1.0
                print(f"    {endpoint}: attempt {attempt + 1} of {tries} failed ({exc.__class__.__name__}), "
                      f"waiting {wait:.0f}s", flush=True)
                SLEEP(wait)
            continue
        secs = time.monotonic() - t0
        TIMINGS[endpoint].append((secs, len(body)))
        log_request(endpoint, "ok", secs, len(body))
        SLEEP(delay * (1.0 + random.uniform(-jitter, jitter)))
        return body
    raise Refused(f"{endpoint}: {last!r} for {label}")


def http_get(url: str, params: dict, endpoint: str, delay: float,
             tries: int = 3, timeout: float = 30.0, waits: tuple[float, ...] | None = None,
             headers: dict | None = None, jitter: float = 0.0, backend: str = "urllib") -> bytes:
    """One GET through `backend`, retried as `with_retries` says."""
    query = url + "?" + urllib.parse.urlencode(params)
    return with_retries(endpoint, lambda: GETTERS[backend](query, headers or HEADERS, timeout),
                        delay, tries, waits, jitter, query)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part.expired")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def retire(path: Path, reason: str) -> Path:
    """Rename a cached file that failed its checks. Never deletes."""
    new = path.with_name(f"{path.name}.bad_{_stamp()}.expired")
    os.replace(path, new)
    print(f"  retired {path.name} -> {new.name} ({reason})")
    return new


def datacenter_page_ok(body: bytes, page: int, page_size: int,
                       expect_pages: int | None = None,
                       expect_count: int | None = None):
    """(ok, reason, obj) for one page of a paged datacenter table."""
    try:
        obj = json.loads(body.decode("utf-8"))
    except Exception as exc:
        return False, f"not json ({exc.__class__.__name__})", None
    if not obj.get("success"):
        return False, f"success={obj.get('success')} code={obj.get('code')} message={obj.get('message')}", obj
    res = obj.get("result")
    if not isinstance(res, dict) or not isinstance(res.get("data"), list):
        return False, "no result.data list", obj
    pages, count = res.get("pages"), res.get("count")
    if not isinstance(pages, int) or not isinstance(count, int) or pages < 1:
        return False, f"pages={pages!r} count={count!r}", obj
    if expect_pages is not None and pages != expect_pages:
        return False, f"pages {pages} != {expect_pages}", obj
    if expect_count is not None and count != expect_count:
        return False, f"count {count} != {expect_count}", obj
    if page > pages:
        return False, f"page {page} beyond {pages}", obj
    want = page_size if page < pages else count - page_size * (pages - 1)
    if len(res["data"]) != want:
        return False, f"rows {len(res['data'])} != {want}", obj
    return True, "ok", obj


def fetch_table(report: str, sort_cols: tuple[str, ...], page_size: int, delay: float) -> dict:
    # Paging over a sort key that ties can move rows between pages from one request
    # to the next, so the sort carries tie-breakers and the caller counts duplicate keys.
    params = {"reportName": report, "columns": "ALL", "sortColumns": ",".join(sort_cols),
              "sortTypes": ",".join("-1" for _ in sort_cols), "pageSize": str(page_size),
              "pageNumber": "1", "source": "WEB", "client": "WEB"}
    body = http_get(DATACENTER, params, report, delay)
    ok, why, obj = datacenter_page_ok(body, 1, page_size)
    if not ok:
        raise RuntimeError(f"{report} page 1: {why}")
    pages, count = obj["result"]["pages"], obj["result"]["count"]
    snap = RAW / report.lower() / f"count_{count}_ps{page_size}"
    first = snap / "page_0001.json"
    if not first.exists():
        atomic_write_bytes(first, body)
    rows, fetched = [], 0
    for page in range(1, pages + 1):
        path = snap / f"page_{page:04d}.json"
        if path.exists():
            ok, why, obj = datacenter_page_ok(path.read_bytes(), page, page_size, pages, count)
            if not ok:
                retire(path, why)
        if not path.exists():
            params["pageNumber"] = str(page)
            body = http_get(DATACENTER, params, report, delay)
            ok, why, obj = datacenter_page_ok(body, page, page_size, pages, count)
            if not ok:
                raise RuntimeError(f"{report} page {page}: {why}. The table moved during the "
                                   f"run or the page came back short; rerun to start a new snapshot.")
            atomic_write_bytes(path, body)
            fetched += 1
        rows.extend(obj["result"]["data"])
    return {"report": report, "count": count, "pages": pages, "rows": rows,
            "snapshot": str(snap.relative_to(ROOT)), "pages_fetched_this_run": fetched}


def lift_gd_ok(body: bytes):
    try:
        obj = json.loads(body.decode("utf-8"))
    except Exception as exc:
        return False, f"not json ({exc.__class__.__name__})", None
    res = obj.get("result")
    if not isinstance(res, dict) or not isinstance(res.get("data"), list):
        return False, f"no rows: success={obj.get('success')} code={obj.get('code')} message={obj.get('message')}", obj
    if res.get("pages", 1) != 1:
        return False, f"pages={res.get('pages')}, expected one page", obj
    return True, "ok", obj


def fetch_lift_gd(code: str, free_date: str, delay: float):
    path = RAW / "rpt_lift_gd" / f"{code}_{free_date}.json"
    if path.exists():
        ok, why, obj = lift_gd_ok(path.read_bytes())
        if ok:
            return obj, "cache"
        retire(path, why)
    params = {"reportName": "RPT_LIFT_GD", "columns": "ALL", "sortColumns": "ADD_LISTING_SHARES",
              "sortTypes": "-1", "pageSize": "500", "pageNumber": "1", "source": "WEB",
              "client": "WEB", "filter": f'(SECURITY_CODE="{code}")(FREE_DATE=\'{free_date}\')'}
    try:
        body = http_get(DATACENTER, params, "RPT_LIFT_GD", delay)
    except Refused as exc:
        return {"_not_ok": f"refused: {exc}"}, "refused"
    ok, why, obj = lift_gd_ok(body)
    if not ok:
        # an empty answer and a failed answer are printed apart and neither is cached
        return {"_not_ok": why}, "none"
    atomic_write_bytes(path, body)
    return obj, "fetched"


def secid(code: str) -> str:
    return ("1." if code.startswith("6") else "0.") + code


def kline_ok(body: bytes, beg: str | None = None, end: str | None = None):
    """(ok, reason, obj). With `beg` and `end` (YYYY-MM-DD), every bar must fall inside them."""
    try:
        obj = json.loads(body.decode("utf-8"))
    except Exception as exc:
        return False, f"not json ({exc.__class__.__name__})", None
    data = obj.get("data") if isinstance(obj, dict) else None
    if not isinstance(data, dict) or not isinstance(data.get("klines"), list) or not data["klines"]:
        return False, "no klines", obj
    parts = [line.split(",") for line in data["klines"]]
    if any(len(p) < 7 for p in parts):
        return False, "a bar has fewer than seven fields", obj
    dates = [p[0] for p in parts]
    if dates != sorted(set(dates)):
        return False, "dates not strictly increasing", obj
    if beg is not None and dates[0] < beg:
        return False, f"first bar {dates[0]} is before the window start {beg}", obj
    if end is not None and dates[-1] > end:
        return False, f"last bar {dates[-1]} is after the window end {end}", obj
    return True, "ok", obj


def kline_path(code: str, beg: str | None, end: str | None) -> Path:
    base = RAW / "kline_daily_unadjusted"
    if beg is None:
        return base / f"{code}.json"
    return base / "window" / f"{code}_{beg.replace('-', '')}_{end.replace('-', '')}.json"


def kline_window(issue_date: str, free_date: str, last_final: str) -> tuple[str, str]:
    """The bars the station needs for one offering.

    From 450 calendar days before the issue date, which holds the twenty-day base window at
    any offset up to T-10 and 250 trading days behind it, through 40 days after the unlock.
    The end never passes `last_final`, the last day whose bar is final, so a window written
    to disk does not change afterwards.
    """
    beg = (dt.date.fromisoformat(issue_date) - dt.timedelta(days=450)).isoformat()
    end = min((dt.date.fromisoformat(free_date) + dt.timedelta(days=40)).isoformat(), last_final)
    return beg, end


def fetch_kline(code: str, delay: float, beg: str | None = None, end: str | None = None,
                network: bool = True, backend: str = "urllib", tries: int = 3):
    """(obj, how). Without `beg`, the full history; with it, the bars from `beg` to `end`.

    how      meaning
    cache    read from disk, no request
    fetched  answered, checked, written to disk
    none     answered, but the answer failed its checks; nothing written
    refused  no usable answer after every retry; nothing written
    skipped  not on disk, and this section has stopped asking
    """
    path = kline_path(code, beg, end)
    if path.exists():
        ok, why, obj = kline_ok(path.read_bytes(), beg, end)
        if ok:
            return obj, "cache"
        retire(path, why)
    if not network:
        return {"_not_ok": "not requested: the daily-bar host stopped answering earlier in this run"}, "skipped"
    params = {"fields1": "f1,f2,f3,f4,f5,f6", "fields2": "f51,f52,f53,f54,f55,f56,f57",
              "ut": "7eea3edcaed734bea9cbfc24409ed989", "klt": "101", "fqt": "0", "secid": secid(code),
              "beg": (beg or "1990-01-01").replace("-", ""), "end": (end or "2050-01-01").replace("-", "")}
    endpoint = ("kline_full/" if beg is None else "kline_window/") + backend
    try:
        body = http_get(KLINE, params, endpoint, delay, tries=tries, timeout=20.0,
                        waits=KLINE_WAITS, headers=KLINE_HEADERS, jitter=0.25, backend=backend)
    except Refused as exc:
        return {"_not_ok": f"refused: {exc}"}, "refused"
    ok, why, obj = kline_ok(body, beg, end)
    if not ok:
        return {"_not_ok": why}, "none"
    atomic_write_bytes(path, body)
    return obj, "fetched"


# ---------------------------------------------------------------------------
# baostock: a second source of daily bars
# ---------------------------------------------------------------------------

BS_FIELDS = ("date", "code", "open", "high", "low", "close", "preclose", "volume", "amount",
             "tradestatus", "pctChg", "isST")
BS_FIRST_DAY = "1990-12-19"
BS_WAITS = (5.0, 15.0)
# The module and whether this process is logged in. The selftest puts a fake module here.
BS: dict = {"module": None, "logged_in": False}


def bs_code(code: str) -> str | None:
    """Shanghai and Shenzhen A shares; this source does not carry Beijing codes."""
    if code[:1] == "6":
        return "sh." + code
    if code[:1] in ("0", "3"):
        return "sz." + code
    return None


def bs_path(code: str, beg: str, end: str) -> Path:
    return RAW / "daily_baostock" / f"{code}_{beg.replace('-', '')}_{end.replace('-', '')}.json"


def bs_session():
    if BS["module"] is None:
        import baostock  # backend_available reports an absent package first
        BS["module"] = baostock
    if not BS["logged_in"]:
        lg = BS["module"].login()
        if lg.error_code != "0":
            raise RuntimeError(f"baostock login {lg.error_code}: {lg.error_msg}")
        BS["logged_in"] = True
    return BS["module"]


def bs_logout() -> None:
    if BS["logged_in"]:
        BS["logged_in"] = False
        try:
            BS["module"].logout()
        except Exception as exc:  # the session ends either way
            print(f"  baostock logout: {exc!r}")


def bs_body(bcode: str, beg: str, end: str) -> bytes:
    """One query, as bytes. Any error, returned or raised, marks the session logged out, so the
    next attempt logs in again."""
    try:
        bs = bs_session()
        rs = bs.query_history_k_data_plus(bcode, ",".join(BS_FIELDS), start_date=beg, end_date=end,
                                          frequency="d", adjustflag="3")
        rows = []
        while rs.error_code == "0" and rs.next():
            rows.append(rs.get_row_data())
        if rs.error_code != "0":
            raise RuntimeError(f"baostock {rs.error_code}: {rs.error_msg}")
    except Exception:
        BS["logged_in"] = False
        raise
    return json.dumps({"source": "baostock", "code": bcode, "fields": list(rs.fields), "rows": rows},
                      ensure_ascii=False, sort_keys=True).encode("utf-8")


def bs_ok(body: bytes, beg: str, end: str):
    """(ok, reason, obj) for one baostock answer, fetched or cached."""
    try:
        obj = json.loads(body.decode("utf-8"))
    except Exception as exc:
        return False, f"not json ({exc.__class__.__name__})", None
    if not isinstance(obj, dict) or obj.get("fields") != list(BS_FIELDS):
        return False, "the fields are not the ones asked for", obj
    rows = obj.get("rows")
    if not isinstance(rows, list) or not rows:
        return False, "no rows", obj
    if any(not isinstance(r, list) or len(r) != len(BS_FIELDS) for r in rows):
        return False, "a row has the wrong number of fields", obj
    dates = [r[0] for r in rows]
    if dates != sorted(set(dates)):
        return False, "dates not strictly increasing", obj
    if dates[0] < beg or dates[-1] > end:
        return False, f"rows {dates[0]}..{dates[-1]} fall outside the window {beg}..{end}", obj
    if any(r[9] not in ("0", "1") for r in rows):
        return False, "a trading status other than 0 or 1", obj
    try:
        for r in rows:
            if r[9] == "1":
                float(r[5]), float(r[7]), float(r[8])
    except ValueError:
        return False, "a traded day whose close, volume or amount does not parse", obj
    return True, "ok", obj


def bs_to_klines(obj: dict, source: str) -> dict:
    """The traded days in the eastmoney line layout (date,open,close,high,low,volume,amount), so
    the readers below take either source. Volume stays in shares; `volume_unit` finds the unit.
    Counts the suspended days dropped, and the traded days whose previous close from the exchange
    differs from the close of the traded day before (ex-rights and ex-dividend days do)."""
    lines, suspended, breaks, prev_close = [], 0, 0, None
    for r in obj["rows"]:
        date, _, o, h, lo, c, pre, vol, amt, status = r[:10]
        if status != "1":
            suspended += 1
            continue
        if prev_close is not None and pre and abs(float(pre) - prev_close) > 0.005:
            breaks += 1
        prev_close = float(c)
        lines.append(f"{date},{o},{c},{h},{lo},{vol},{amt}")
    return {"data": {"klines": lines}, "_source": source, "_suspended_days": suspended,
            "_preclose_breaks": breaks}


def fetch_bars_bs(code: str, delay: float, beg: str, end: str, network: bool = True, tries: int = 3):
    """(obj, how) as fetch_kline gives, from baostock, for the bars from `beg` to `end`. how adds
    `uncovered`: a code this source does not carry, for which nothing was asked."""
    source = "baostock full history" if beg == BS_FIRST_DAY else "baostock window"
    path = bs_path(code, beg, end)
    if path.exists():
        ok, why, raw = bs_ok(path.read_bytes(), beg, end)
        if ok:
            obj = bs_to_klines(raw, source)
            return (obj, "cache") if obj["data"]["klines"] else ({"_not_ok": "no traded day in the window"}, "none")
        retire(path, why)
    if not network:
        return {"_not_ok": "not requested: daily bars stopped answering earlier in this run"}, "skipped"
    bcode = bs_code(code)
    if bcode is None:
        return {"_not_ok": "uncovered: baostock carries Shanghai and Shenzhen A shares only"}, "uncovered"
    endpoint = ("kline_full/" if beg == BS_FIRST_DAY else "kline_window/") + "baostock"
    try:
        body = with_retries(endpoint, lambda: bs_body(bcode, beg, end), delay, tries, BS_WAITS, 0.25,
                            f"{bcode} {beg}..{end}")
    except Refused as exc:
        return {"_not_ok": f"refused: {exc}"}, "refused"
    ok, why, raw = bs_ok(body, beg, end)
    if not ok:
        return {"_not_ok": why}, "none"
    atomic_write_bytes(path, body)
    obj = bs_to_klines(raw, source)
    return (obj, "fetched") if obj["data"]["klines"] else ({"_not_ok": "no traded day in the window"}, "none")


def volume_multiplier(unit: dict) -> int:
    """1 when volume counts shares, 100 when it counts lots; lots when nothing decides it."""
    return 1 if unit["inside_range_at_1"] > unit["inside_range_at_100"] else 100


def fetch_bars(code: str, delay: float, beg: str, end: str, network: bool = True, backend: str = "urllib",
               tries: int = 3):
    """Daily bars for one window: any cache first (a full history from the eastmoney host covers
    every window), then a request through `backend`."""
    reads = (("eastmoney full history", lambda: fetch_kline(code, delay, None, None, network=False)),
             ("eastmoney window", lambda: fetch_kline(code, delay, beg, end, network=False)),
             ("baostock window", lambda: fetch_bars_bs(code, delay, beg, end, network=False)))
    for label, read in reads:
        obj, how = read()
        if how == "cache":
            obj.setdefault("_source", label)
            return obj, how
    if not network:
        return {"_not_ok": "not requested: daily bars stopped answering earlier in this run"}, "skipped"
    if backend == "baostock":
        return fetch_bars_bs(code, delay, beg, end, tries=tries)
    obj, how = fetch_kline(code, delay, beg, end, backend=backend, tries=tries)
    if how == "fetched":
        obj["_source"] = "eastmoney window"
    return obj, how


def choose_backend(job: tuple, delay: float, order=KLINE_BACKENDS, available=backend_available):
    """Ask for one stock once through each installed client in `order`; stop at the first one that
    answers. An answer that fails its checks still shows the client gets through.
    Returns (client or None, attempts)."""
    code, beg, end = job
    attempts = []
    for name in order:
        if not available(name):
            attempts.append({"backend": name, "how": "not installed", "why": ""})
            print(f"  client {name}: not installed", flush=True)
            continue
        obj, how = fetch_bars(code, delay, beg, end, backend=name, tries=1)
        why = obj.get("_not_ok", "") if isinstance(obj, dict) else ""
        attempts.append({"backend": name, "how": how, "why": why[:300]})
        print(f"  client {name}: {how}" + (f" ({why[:120]})" if why else ""), flush=True)
        if how in ("fetched", "cache", "none"):
            return name, attempts
        SLEEP(delay)
    return None, attempts


def kline_pass(jobs: list, fetch, breaker: int = KLINE_BREAKER, progress: bool = True):
    """Run `fetch(code, beg, end, network)` over `jobs` in order. Returns (results, stopped_at).

    After `breaker` jobs in a row come back `refused`, the rest run with the network closed and
    read the cache only; `stopped_at` is the index of the job that closed it, or None. A job
    the server answered (`fetched` or `none`) ends a run of refusals. A cache read never reaches
    the server, and neither does a code the source does not carry (`uncovered`), so both leave
    the count where it was.
    """
    out, streak, network, stopped_at = [], 0, True, None
    for i, (code, beg, end) in enumerate(jobs):
        obj, how = fetch(code, beg, end, network)
        if progress:
            print(f"  [{i + 1}/{len(jobs)}] {code} {how}", flush=True)
        if how == "refused":
            streak += 1
            if network and streak >= breaker:
                network, stopped_at = False, i
                print(f"  the daily-bar host gave nothing for {streak} stocks in a row; "
                      f"the remaining {len(jobs) - i - 1} read the cache only", flush=True)
        elif how in ("fetched", "none"):
            streak = 0
        out.append(((code, beg, end), obj, how))
    return out, stopped_at


# ---------------------------------------------------------------------------
# Reading what came back
# ---------------------------------------------------------------------------

def bars(kobj: dict) -> list[dict]:
    out = []
    for line in kobj["data"]["klines"]:
        p = line.split(",")
        out.append({"date": p[0], "open": float(p[1]), "close": float(p[2]),
                    "high": float(p[3]), "low": float(p[4]),
                    "volume": float(p[5]), "amount": float(p[6]), "close_text": p[2]})
    return out


def volume_unit(bar_list: list[dict]) -> dict:
    """Which multiplier puts amount/volume inside the day's range: 1 share or 100."""
    fit = {1: 0, 100: 0}
    n = 0
    for b in bar_list:
        if b["volume"] <= 0 or b["amount"] <= 0:
            continue
        n += 1
        for m in fit:
            vwap = b["amount"] / (b["volume"] * m)
            if b["low"] - 0.01 <= vwap <= b["high"] + 0.01:
                fit[m] += 1
    return {"bars_with_volume": n, "inside_range_at_1": fit[1], "inside_range_at_100": fit[100]}


def decimals(text: str) -> int:
    return len(text.split(".")[1]) if "." in text else 0


def is_placement_type(value) -> bool:
    return isinstance(value, str) and any(m in value for m in PLACEMENT_MARKERS)


def add_months(d: dt.date, months: int) -> dt.date:
    y, m = divmod(d.month - 1 + months, 12)
    y, m = d.year + y, m + 1
    return dt.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def match_offering(offerings: list[dict], free_date: str, lock_months) -> tuple[dict | None, str]:
    """(offering, how it was matched) for one unlock batch.

    First choice: the offering whose listing date plus one of the batch's lock months lands on
    the unlock date, from 3 days before to 20 days after (weekends and holidays roll the unlock
    forward). A stock can have an older offering whose long lock ends after a newer offering, so
    the latest offering before the unlock is only the fallback, and the printout says which rule
    was used. Two offerings that fit equally well are not guessed between.
    """
    months = set()
    for x in lock_months:
        try:
            months.add(int(x))
        except (TypeError, ValueError):
            pass
    fd = dt.date.fromisoformat(free_date)
    hits = []
    for s in offerings:
        listing = (s.get("ISSUE_LISTING_DATE") or "")[:10]
        if not listing:
            continue
        lags = [(fd - add_months(dt.date.fromisoformat(listing), m)).days for m in sorted(months)]
        fits = [abs(g) for g in lags if -3 <= g <= 20]
        if fits:
            hits.append((min(fits), s))
    if hits:
        hits.sort(key=lambda h: h[0])
        if len(hits) == 1 or hits[0][0] < hits[1][0]:
            return hits[0][1], "listing date plus lock months"
        return None, "two offerings fit the listing date plus lock months equally"
    prior = sorted((s for s in offerings
                    if (s.get("ISSUE_DATE") or "")[:10] and (s.get("ISSUE_DATE") or "")[:10] <= free_date),
                   key=lambda s: s.get("ISSUE_DATE") or "")
    if prior:
        return prior[-1], "latest offering before the unlock, since no listing date plus lock months fits"
    return None, "no offering in the table before this unlock"


def pick_sample(stage_rows: list[dict], cutoff: str, n: int) -> list[dict]:
    """Evenly spaced over every placement unlock batch dated on or before the cutoff."""
    cands = sorted((r for r in stage_rows
                    if is_placement_type(r.get("FREE_SHARES_TYPE"))
                    and isinstance(r.get("FREE_DATE"), str) and r["FREE_DATE"][:10] <= cutoff),
                   key=lambda r: (r["FREE_DATE"], r.get("SECURITY_CODE") or ""))
    if not cands or n <= 0:
        return []
    if n >= len(cands):
        return cands
    idx = sorted({round(i * (len(cands) - 1) / (n - 1)) for i in range(n)}) if n > 1 else [0]
    return [cands[i] for i in idx]


def coverage(rows: list[dict]) -> list[tuple[str, int]]:
    cols = sorted({k for r in rows for k in r})
    return [(c, sum(1 for r in rows if r.get(c) not in (None, ""))) for c in cols]


def row_key_seo(r: dict) -> tuple:
    return (r.get("SECUCODE"), r.get("ISSUE_DATE"), r.get("ISSUE_NUM"), r.get("ISSUE_PRICE"), r.get("SEO_TYPE"))


def row_key_stage(r: dict) -> tuple:
    return (r.get("SECUCODE"), r.get("FREE_DATE"), r.get("FREE_SHARES_TYPE"), r.get("CURRENT_FREE_SHARES"))


def print_counter(title: str, counter: collections.Counter, top: int) -> None:
    print(f"\n{title}  ({len(counter)} distinct)")
    for value, count in counter.most_common(top):
        print(f"  {count:6d}  {value}")
    if len(counter) > top:
        print(f"  ... {len(counter) - top} more distinct values, all in probe_summary.json")


def timing_table(log: dict) -> dict:
    out = {}
    for ep in sorted(log):
        ok = log[ep]["ok"]
        row = {"requests": len(ok), "failed": log[ep]["fail"]}
        if ok:
            secs = sorted(s for s, _ in ok)
            kbs = sorted(b / 1024 for _, b in ok)
            row.update({"seconds_median": f"{statistics.median(secs):.3f}",
                        "seconds_p90": f"{secs[min(len(secs) - 1, int(0.9 * len(secs)))]:.3f}",
                        "kb_median": f"{statistics.median(kbs):.1f}", "kb_max": f"{max(kbs):.1f}"})
        out[ep] = row
    return out


def cost_line(label: str, n: int, row: dict | None, pace: float) -> str:
    """One line of the full-pull estimate. No measured answer on that endpoint, no hours."""
    if not row or not row.get("requests"):
        return f"  {label}: {n} requests, not measured, no hours printed"
    per = float(row["seconds_median"]) + pace
    line = f"  {label}: {n} requests x {per:.2f}s = {n * per / 3600:.2f} h at this pacing"
    if row.get("failed"):
        line += f"; {row['failed']} attempts in the log failed on this endpoint, so the hours are a floor"
    return line


# ---------------------------------------------------------------------------
# The probe
# ---------------------------------------------------------------------------

def run(sample_n: int, delay: float, kline_delay: float = 3.0, full_history: int = 3,
        measure_n: int = 3, bs_delay: float = 0.2) -> None:
    cutoff = dt.date.today().isoformat()
    summary: dict = {"cutoff_date": cutoff}

    print("=" * 78)
    print("1. offerings table RPT_SEO_DETAIL")
    seo = fetch_table("RPT_SEO_DETAIL", ("ISSUE_DATE", "SECURITY_CODE", "ISSUE_NUM"), 500, delay)
    rows = seo["rows"]
    keys = collections.Counter(row_key_seo(r) for r in rows)
    dup = sum(c - 1 for c in keys.values() if c > 1)
    print(f"server count {seo['count']}, rows cached {len(rows)}, pages {seo['pages']}, "
          f"fetched this run {seo['pages_fetched_this_run']}, duplicate row keys {dup}")
    print(f"snapshot {seo['snapshot']}")
    by_type = collections.Counter(str(r.get("SEO_TYPE")) for r in rows)
    print_counter("SEO_TYPE", by_type, 10)
    print_counter("ISSUE_WAY", collections.Counter(str(r.get("ISSUE_WAY")) for r in rows), 20)
    print_counter("TRADE_MARKET", collections.Counter(str(r.get("TRADE_MARKET")) for r in rows), 10)
    pp = collections.Counter(str(r.get("PRICE_PRINCIPLE")) for r in rows)
    print_counter("PRICE_PRINCIPLE", pp, 40)
    lk = collections.Counter(str(r.get("LOCKIN_PERIOD")) for r in rows)
    print_counter("LOCKIN_PERIOD", lk, 30)
    years = collections.defaultdict(collections.Counter)
    for r in rows:
        years[(r.get("ISSUE_DATE") or "none")[:4]][str(r.get("SEO_TYPE"))] += 1
    print("\nISSUE_DATE year x SEO_TYPE")
    for y in sorted(years):
        print(f"  {y}  " + "  ".join(f"{t}:{c}" for t, c in sorted(years[y].items())))
    print("\nfield coverage (non-empty rows of all rows)")
    for col, nonempty in coverage(rows):
        print(f"  {col:28s} {nonempty:6d} / {len(rows)}")
    summary["seo"] = {"count": seo["count"], "rows": len(rows), "duplicate_row_keys": dup,
                      "seo_type": dict(by_type), "price_principle": dict(pp),
                      "lockin_period": dict(lk),
                      "year_by_type": {y: dict(c) for y, c in sorted(years.items())}}

    print("\n" + "=" * 78)
    print("2. unlock batches RPT_LIFT_STAGE")
    stage = fetch_table("RPT_LIFT_STAGE", ("FREE_DATE", "SECURITY_CODE", "CURRENT_FREE_SHARES"), 500, delay)
    srows = stage["rows"]
    skeys = collections.Counter(row_key_stage(r) for r in srows)
    sdup = sum(c - 1 for c in skeys.values() if c > 1)
    print(f"server count {stage['count']}, rows cached {len(srows)}, pages {stage['pages']}, "
          f"fetched this run {stage['pages_fetched_this_run']}, duplicate row keys {sdup}")
    types = collections.defaultdict(list)
    for r in srows:
        types[str(r.get("FREE_SHARES_TYPE"))].append((r.get("FREE_DATE") or "")[:10])
    print("\nFREE_SHARES_TYPE: count, first and last FREE_DATE, placement marker")
    type_table = {}
    for t, ds in sorted(types.items(), key=lambda kv: -len(kv[1])):
        ds = sorted(d for d in ds if d)
        mark = "placement" if is_placement_type(t) else ""
        print(f"  {len(ds):6d}  {ds[0] if ds else '-'}  {ds[-1] if ds else '-'}  {mark:9s}  {t}")
        type_table[t] = {"count": len(ds), "first": ds[0] if ds else None,
                         "last": ds[-1] if ds else None, "placement": bool(mark)}
    per_year = collections.Counter()
    holders = collections.Counter()
    for r in srows:
        if is_placement_type(r.get("FREE_SHARES_TYPE")) and (r.get("FREE_DATE") or "")[:10] <= cutoff:
            y = r["FREE_DATE"][:4]
            per_year[y] += 1
            holders[y] += int(r.get("BATCH_HOLDER_NUM") or 0)
    print("\nplacement unlock batches dated on or before the cutoff, by year: batches, holders")
    for y in sorted(per_year):
        print(f"  {y}  {per_year[y]:5d}  {holders[y]:6d}")
    summary["lift_stage"] = {"count": stage["count"], "rows": len(srows), "duplicate_row_keys": sdup, "types": type_table,
                             "placement_batches_by_year": dict(per_year),
                             "placement_holders_by_year": dict(holders)}

    print("\n" + "=" * 78)
    print(f"3. holders on a sample of {sample_n} placement unlock batches RPT_LIFT_GD")
    sample = pick_sample(srows, cutoff, sample_n)
    lock_months = collections.Counter()
    batch_locks: dict = {}
    gd_rows_total = 0
    sample_out = []
    for r in sample:
        code, date = r["SECURITY_CODE"], r["FREE_DATE"][:10]
        obj, how = fetch_lift_gd(code, date, delay)
        if "_not_ok" in obj:
            print(f"\n  {code} {date} {r.get('FREE_SHARES_TYPE')}: no holder rows ({obj['_not_ok']})")
            sample_out.append({"code": code, "free_date": date, "holders": None, "why": obj["_not_ok"]})
            continue
        data = obj["result"]["data"]
        batch_locks[(code, date)] = [h.get("LOCK_MONTH") for h in data]
        gd_rows_total += len(data)
        for h in data:
            lock_months[str(h.get("LOCK_MONTH"))] += 1
        print(f"\n  {code} {date} [{how}] type={r.get('FREE_SHARES_TYPE')} batch_holders={r.get('BATCH_HOLDER_NUM')} rows={len(data)}")
        for h in data[:6]:
            print(f"    lock={h.get('LOCK_MONTH')!s:>4} shares={h.get('ADD_LISTING_SHARES')!s:>14} "
                  f"type={h.get('FREE_SHARES_TYPE')} name={h.get('LIMITED_HOLDER_NAME')}")
        if len(data) > 6:
            print(f"    ... {len(data) - 6} more holders")
        sample_out.append({"code": code, "free_date": date, "holders": len(data),
                           "fields": sorted({k for h in data for k in h})})
    print_counter("LOCK_MONTH over the sampled holders", lock_months, 20)
    summary["lift_gd_sample"] = {"batches": len(sample), "holder_rows": gd_rows_total,
                                 "lock_month": dict(lock_months), "per_batch": sample_out}
    # A sample read from disk costs nothing, so a few batches outside it are fetched to price the request.
    in_sample = {(x["SECURITY_CODE"], x["FREE_DATE"][:10]) for x in sample}
    extra = [x for x in pick_sample(srows, cutoff, sample_n + measure_n)
             if (x["SECURITY_CODE"], x["FREE_DATE"][:10]) not in in_sample
             and not (RAW / "rpt_lift_gd" / f"{x['SECURITY_CODE']}_{x['FREE_DATE'][:10]}.json").exists()]
    if measure_n > 0 and extra:
        print(f"\n  {min(measure_n, len(extra))} more batches, fetched for the request cost only")
        for x in extra[:measure_n]:
            obj, how = fetch_lift_gd(x["SECURITY_CODE"], x["FREE_DATE"][:10], delay)
            n_rows = None if "_not_ok" in obj else len(obj["result"]["data"])
            print(f"    {x['SECURITY_CODE']} {x['FREE_DATE'][:10]} [{how}] holder rows={n_rows}")

    print("\n" + "=" * 78)
    print("4. daily bars for the sampled stocks, around the matching offering")
    seo_by_code = collections.defaultdict(list)
    for s in rows:
        seo_by_code[str(s.get("SECURITY_CODE"))].append(s)
    last_final = (dt.date.fromisoformat(cutoff) - dt.timedelta(days=1)).isoformat()
    matched, jobs = [], []
    for r in sample:
        code, date = r["SECURITY_CODE"], r["FREE_DATE"][:10]
        s, rule = match_offering(seo_by_code.get(code, []), date, batch_locks.get((code, date), []))
        if s is None:
            print(f"\n  {code} {date}: {rule}, nothing requested")
            continue
        t = (s.get("ISSUE_DATE") or "")[:10]
        beg, end = kline_window(t, date, last_final)
        matched.append((r, s, t, rule))
        jobs.append((code, beg, end))

    def cached(c, b, e):
        return any(p.exists() for p in (kline_path(c, None, None), kline_path(c, b, e), bs_path(c, b, e)))

    probe_job = next((j for j in jobs if not cached(*j) and bs_code(j[0])), None)
    if probe_job is None:
        backend, attempts = "urllib", []
    else:
        print(f"  which client answers for daily bars, asked with {probe_job[0]}:", flush=True)
        backend, attempts = choose_backend(probe_job, kline_delay)
    summary["kline_backend"] = backend
    summary["kline_backend_check"] = attempts
    pace = bs_delay if backend == "baostock" else kline_delay
    if backend is None:
        print("  no installed client got an answer; this section reads the cache only")
    print(f"  {len(jobs)} stocks through {backend}; {pace:.1f}s after each answer, "
          f"stretched by up to a quarter", flush=True)

    def ask(c, b, e, n):
        return fetch_bars(c, pace, b, e, network=n and backend is not None, backend=backend or "urllib")

    got, stopped_at = kline_pass(jobs, ask)
    bars_out, failed = [], []
    for (r, s, t, rule), ((code, beg, end), obj, how) in zip(matched, got):
        span = f"{beg}..{end}"
        if "_not_ok" in obj:
            print(f"\n  {code} [{how}] {span}: no bars ({obj['_not_ok'][:160]})")
            failed.append({"code": code, "secid_prefix": secid(code)[0], "window": span, "how": how,
                           "why": obj["_not_ok"][:400]})
            continue
        bl = bars(obj)
        unit = volume_unit(bl)
        mult = volume_multiplier(unit)
        dec = collections.Counter(decimals(b["close_text"]) for b in bl)
        source = obj.get("_source", "")
        extra = ""
        if "_suspended_days" in obj:
            extra = (f"\n    suspended days dropped={obj['_suspended_days']}, traded days whose previous close "
                     f"differs from the close before={obj['_preclose_breaks']}")
        print(f"\n  {code} [{how}] {source}, asked {span}, bars={len(bl)} {bl[0]['date']}..{bl[-1]['date']} "
              f"close decimals={dict(dec)} volume fit={unit} volume unit={mult}{extra}")
        print(f"    unlock {r['FREE_DATE'][:10]} matched to its offering by {rule}")
        print(f"    offering ISSUE_DATE={t} ISSUE_LISTING_DATE={(s.get('ISSUE_LISTING_DATE') or '')[:10]} "
              f"EQUITY_RECORD_DATE={(s.get('EQUITY_RECORD_DATE') or '')[:10]} SEO_TYPE={s.get('SEO_TYPE')} "
              f"price={s.get('ISSUE_PRICE')} num={s.get('ISSUE_NUM')} lock={s.get('LOCKIN_PERIOD')}")
        print(f"    principle={s.get('PRICE_PRINCIPLE')}")
        print(f"    object={str(s.get('ISSUE_OBJECT'))[:160]}")
        dates = [b["date"] for b in bl]
        pos = next((i for i, d in enumerate(dates) if d >= t), None)
        if pos is None:
            print("    no bar on or after ISSUE_DATE")
            continue
        price = float(s.get("ISSUE_PRICE") or 0)
        for b in bl[max(0, pos - 5): pos + 6]:
            vwap = b["amount"] / (b["volume"] * mult) if b["volume"] > 0 else float("nan")
            ratio = price / b["close"] if b["close"] > 0 and price > 0 else float("nan")
            mark = "<- ISSUE_DATE" if b["date"] == dates[pos] else ""
            print(f"    {b['date']} close={b['close']:.2f} high={b['high']:.2f} low={b['low']:.2f} "
                  f"vwap={vwap:.3f} price/close={ratio:.4f} {mark}")
        base = []
        for k in range(0, 11):
            j = pos - k
            if j - 20 < 0:
                break
            window = bl[j - 20:j]
            vol = sum(w["volume"] for w in window) * mult
            amt = sum(w["amount"] for w in window)
            if vol > 0 and price > 0:
                base.append(f"T-{k}:{price / (amt / vol):.4f}")
        print("    price over the 20-day volume-weighted average ending the day before T-k: " + " ".join(base))
        bars_out.append({"code": code, "window": span, "how": how, "source": source, "bars": len(bl),
                         "first": bl[0]["date"], "last": bl[-1]["date"], "close_decimals": dict(dec),
                         "volume_fit": unit, "volume_unit": mult, "suspended_days": obj.get("_suspended_days"),
                         "preclose_breaks": obj.get("_preclose_breaks")})
    tally: dict = collections.defaultdict(collections.Counter)
    for (code, _, _), _, how in got:
        tally[secid(code)[0]][how] += 1
    print("\n  daily-bar outcomes by the market prefix in the request")
    for m in sorted(tally):
        print(f"    secid {m}.  " + "  ".join(f"{h} {c}" for h, c in sorted(tally[m].items())))

    full_rows = []
    if stopped_at is None and backend is not None and full_history > 0:
        pick = []
        for code, _, _ in jobs:
            done = kline_path(code, None, None).exists() or (
                backend == "baostock" and bs_path(code, BS_FIRST_DAY, last_final).exists())
            if code not in pick and not done:
                pick.append(code)
        pick = pick[:full_history]
        if pick:
            print(f"\n  full daily history for {len(pick)} of these stocks through {backend}, "
                  f"fetched to price that request shape", flush=True)
            if backend == "baostock":
                fjobs = [(c, BS_FIRST_DAY, last_final) for c in pick]

                def fask(c, b, e, n):
                    return fetch_bars_bs(c, pace, b, e, network=n)
            else:
                fjobs = [(c, None, None) for c in pick]

                def fask(c, b, e, n):
                    return fetch_kline(c, pace, b, e, network=n, backend=backend)
            full_got, _ = kline_pass(fjobs, fask)
            for (code, b, e), obj, how in full_got:
                n_bars = None if "_not_ok" in obj else len(obj["data"]["klines"])
                path = bs_path(code, b, e) if backend == "baostock" else kline_path(code, None, None)
                size = path.stat().st_size if n_bars is not None and path.exists() else None
                print(f"    {code} [{how}] bars={n_bars} bytes={size}")
                full_rows.append({"code": code, "how": how, "bars": n_bars, "bytes": size, "via": backend})
    on_disk = sorted((RAW / "kline_daily_unadjusted").glob("*.json"))
    if on_disk:
        print("  eastmoney full histories on disk: "
              + ", ".join(f"{p.stem} {p.stat().st_size // 1024} KB" for p in on_disk))
    bs_logout()
    summary["kline_sample"] = bars_out
    summary["kline_failures"] = failed
    summary["kline_stopped_at"] = stopped_at
    summary["kline_full_history"] = full_rows

    print("\n" + "=" * 78)
    print("5. cost per request, and what a full pull would take")
    tt = timing_table(read_request_log())
    print(f"  over every run in {(RAW / 'request_log.tsv').relative_to(ROOT)}")
    for ep, v in tt.items():
        print(f"  {ep:16s} answered={v['requests']:4d} failed={v['failed']:3d} "
              f"median={v.get('seconds_median', '-')}s p90={v.get('seconds_p90', '-')}s "
              f"kb median={v.get('kb_median', '-')} max={v.get('kb_max', '-')}")
    print("  this run: answered " + (", ".join(f"{ep} {len(v)}" for ep, v in sorted(TIMINGS.items())) or "none")
          + "; failed attempts " + (", ".join(f"{ep} {len(v)}" for ep, v in sorted(FAILURES.items())) or "none"))
    n_batches = sum(per_year.values())
    type1 = [r for r in rows if str(r.get("SEO_TYPE")) == "1" and r.get("ISSUE_DATE")]
    n_codes = len({str(r.get("SECURITY_CODE")) for r in type1})
    plans = [("holder rows, one request per placement unlock batch", n_batches, "RPT_LIFT_GD", delay)]
    for ep in tt:
        shape, _, via = ep.partition("/")
        via_pace = bs_delay if via == "baostock" else kline_delay
        if shape == "kline_full":
            plans.append((f"daily bars through {via}, full history, one request per stock with a type-1 offering",
                          n_codes, ep, via_pace))
        elif shape == "kline_window":
            plans.append((f"daily bars through {via}, one window per type-1 offering", len(type1), ep, via_pace))
    for label, n, ep, step in plans:
        print(cost_line(label, n, tt.get(ep), step))
    summary["timings"] = tt
    summary["full_pull_requests"] = {"RPT_LIFT_GD": n_batches, "kline_full": n_codes, "kline_window": len(type1)}
    summary["pacing"] = {"table_delay": delay, "kline_delay": kline_delay, "kline_waits": list(KLINE_WAITS),
                         "kline_breaker": KLINE_BREAKER, "baostock_delay": bs_delay,
                         "baostock_waits": list(BS_WAITS)}
    out = RAW / "probe_summary.json"
    atomic_write_bytes(out, json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8"))
    print(f"\nwrote {out.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Selftest: every parser above, on pages built here, including pages built to fail
# ---------------------------------------------------------------------------

def selftest() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'} {name}")
        if not cond:
            fails.append(name)

    def page(data, pages, count, success=True):
        return json.dumps({"success": success, "code": 0 if success else 9201,
                           "result": {"pages": pages, "count": count, "data": data}}).encode("utf-8")

    two = [{"a": 1}, {"a": 2}]
    check("a full first page passes", datacenter_page_ok(page(two, 2, 3), 1, 2)[0])
    check("a last page with the remainder passes", datacenter_page_ok(page([{"a": 3}], 2, 3), 2, 2, 2, 3)[0])
    check("a short first page fails", not datacenter_page_ok(page([{"a": 1}], 2, 3), 1, 2)[0])
    check("a last page with too many rows fails", not datacenter_page_ok(page(two, 2, 3), 2, 2, 2, 3)[0])
    check("a truncated body fails", not datacenter_page_ok(page(two, 2, 3)[:-7], 1, 2)[0])
    check("success false fails", not datacenter_page_ok(page(two, 2, 3, success=False), 1, 2)[0])
    check("a count that moved fails", not datacenter_page_ok(page(two, 2, 4), 1, 2, 2, 3)[0])

    good = json.dumps({"data": {"klines": ["2024-01-02,10.00,10.10,10.20,9.90,1000,1010000.00",
                                           "2024-01-03,10.10,10.00,10.30,9.95,2000,2010000.00"]}}).encode("utf-8")
    back = json.dumps({"data": {"klines": ["2024-01-03,10,10,10,10,1,1000", "2024-01-02,10,10,10,10,1,1000"]}}).encode("utf-8")
    short = json.dumps({"data": {"klines": ["2024-01-02,10,10,10,10"]}}).encode("utf-8")
    check("ordered bars pass", kline_ok(good)[0])
    check("bars out of order fail", not kline_ok(back)[0])
    check("a bar missing fields fails", not kline_ok(short)[0])
    unit = volume_unit(bars(json.loads(good)))
    check("volume in lots is detected", unit["inside_range_at_100"] == 2 and unit["inside_range_at_1"] == 0)

    stage = [{"FREE_SHARES_TYPE": "定向增发机构配售股份", "FREE_DATE": f"20{y:02d}-06-01 00:00:00",
              "SECURITY_CODE": f"{600000 + y}"} for y in range(10, 26)]
    # the other share type is dated after every placement row, so dropping the type filter puts it last
    stage += [{"FREE_SHARES_TYPE": "首发原股东限售股份", "FREE_DATE": "2025-12-31 00:00:00", "SECURITY_CODE": "1"},
              {"FREE_SHARES_TYPE": "定向增发机构配售股份", "FREE_DATE": "2099-01-01 00:00:00", "SECURITY_CODE": "2"}]
    picked = pick_sample(stage, "2026-09-16", 4)
    check("the sample takes four", len(picked) == 4)
    check("the sample spans first to last", picked[0]["FREE_DATE"].startswith("2010") and picked[-1]["FREE_DATE"].startswith("2025-06"))
    check("the sample skips other share types and future dates",
          all(is_placement_type(p["FREE_SHARES_TYPE"]) and p["FREE_DATE"] < "2026" for p in picked))
    check("the sample is deterministic", [p["SECURITY_CODE"] for p in picked] == [p["SECURITY_CODE"] for p in pick_sample(stage, "2026-09-16", 4)])

    check("lift rows pass", lift_gd_ok(page([{"LOCK_MONTH": 6}], 1, 1))[0])
    check("an answer without rows fails", not lift_gd_ok(json.dumps({"success": False, "result": None, "code": 9201}).encode("utf-8"))[0])

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "page_0001.json"
        atomic_write_bytes(p, b"{broken")
        moved = retire(p, "selftest")
        check("a retired page is renamed, not removed", (not p.exists()) and moved.exists() and moved.read_bytes() == b"{broken")
        check("the retired name carries .expired", moved.name.endswith(".expired"))
        check("an atomic write leaves no part file", not any(x.name.endswith(".part.expired") for x in Path(tmp).iterdir()))

    # The retry path, the named refusal, the cost log and the breaker, on transports built to fail.
    def outcome(fn):
        try:
            return fn(), None
        except Exception as exc:  # a raise is itself what some checks look for
            return None, exc

    saved = {k: globals()[k] for k in ("OPEN", "SLEEP", "RAW", "GETTERS", "RUN", "WHICH")}
    bs_saved = dict(BS)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            globals()["RAW"] = Path(tmp)
            paused = []
            globals()["SLEEP"] = paused.append
            calls = []

            def dropping(req, timeout):
                calls.append(req.full_url)
                raise http.client.RemoteDisconnected("Remote end closed connection without response")

            globals()["OPEN"] = dropping
            FAILURES.clear()
            _, exc = outcome(lambda: http_get(KLINE, {"secid": "0.002247"}, "t_drop", 0.0,
                                              tries=3, waits=(15.0, 45.0)))
            check("a request with no answer is tried three times, then raised by name",
                  isinstance(exc, Refused) and len(calls) == 3)
            check("the pauses are the ones asked for, with none after the last attempt", paused == [15.0, 45.0])
            check("every failed attempt is recorded", len(FAILURES["t_drop"]) == 3)

            res, exc = outcome(lambda: fetch_kline("002247", 0.0, "2013-01-01", "2014-05-11"))
            check("a refused stock comes back named instead of raising",
                  exc is None and res[1] == "refused" and res[0]["_not_ok"].startswith("refused"))
            check("a refused stock writes nothing", not list(Path(tmp).rglob("*.json")))

            answers = [http.client.RemoteDisconnected("x"), http.client.RemoteDisconnected("x"), good]

            def flaky(req, timeout):
                a = answers.pop(0)
                if isinstance(a, Exception):
                    raise a
                return a

            globals()["OPEN"] = flaky
            res, exc = outcome(lambda: fetch_kline("600000", 0.0, "2024-01-01", "2024-01-31"))
            check("two drops and then an answer: fetched and written",
                  exc is None and res[1] == "fetched" and kline_path("600000", "2024-01-01", "2024-01-31").exists())
            res, exc = outcome(lambda: fetch_kline("600000", 0.0, "2024-01-01", "2024-01-31", network=False))
            check("a window on disk is read with the network closed", exc is None and res[1] == "cache")
            res, exc = outcome(lambda: fetch_kline("600001", 0.0, "2024-01-01", "2024-01-31", network=False))
            check("a window not on disk is skipped with the network closed", exc is None and res[1] == "skipped")

            globals()["OPEN"] = lambda req, timeout: good
            res, exc = outcome(lambda: fetch_kline("600002", 0.0, "2024-01-03", "2024-01-31"))
            check("bars before the window start fail the check and are not written",
                  exc is None and res[1] == "none" and not kline_path("600002", "2024-01-03", "2024-01-31").exists())
            check("two windows of one stock are two files, and neither is the full history",
                  len({kline_path("600000", "2024-01-01", "2024-01-31"), kline_path("600000", "2023-01-01", "2024-01-31"),
                       kline_path("600000", None, None)}) == 3)

            log = read_request_log()
            check("the cost log counts answers and failures per endpoint and client",
                  log.get("t_drop", {}).get("fail") == 3 and log.get("kline_window/urllib", {}).get("fail") == 5
                  and len(log.get("kline_window/urllib", {}).get("ok", [])) == 2)
            with open(Path(tmp) / "request_log.tsv", "a", encoding="utf-8", newline="\n") as fh:
                fh.write("2026-01-01T00:00:00\tkline_window\tok\t1.2")  # a line cut short by a killed run
            log_request("kline_window", "ok", 1.0, 100)  # the name lines had before the client was part of it
            again = read_request_log()
            check("a line cut short is skipped, and a line under the old name counts under urllib",
                  len(again["kline_window/urllib"]["ok"]) == 3 and again["kline_window/urllib"]["fail"] == 5
                  and "kline_window" not in again)
            tt = timing_table(read_request_log())
            check("an endpoint with failures only has no timing",
                  tt["t_drop"]["requests"] == 0 and "seconds_median" not in tt["t_drop"])
            check("no measured answer, no hours",
                  cost_line("x", 10, tt["t_drop"], 3.0).endswith("no hours printed")
                  and cost_line("x", 10, None, 3.0).endswith("no hours printed"))
            check("hours are requests times the median plus the pacing",
                  "= 4.00 h" in cost_line("x", 3600, {"requests": 5, "failed": 0, "seconds_median": "1.000"}, 3.0))
            check("failures on the endpoint mark the hours as a floor",
                  cost_line("x", 3600, {"requests": 5, "failed": 2, "seconds_median": "1.000"}, 3.0).endswith("a floor"))

            calls = collections.Counter()

            def refusing(name):
                def get(url, headers, timeout):
                    calls[name] += 1
                    raise http.client.RemoteDisconnected("Remote end closed connection without response")
                return get

            def answering(name):
                def get(url, headers, timeout):
                    calls[name] += 1
                    return good
                return get

            globals()["GETTERS"] = {"curl_cffi": refusing("curl_cffi"), "curl": answering("curl"),
                                    "urllib": refusing("urllib")}
            name, attempts = choose_backend(("600020", "2024-01-01", "2024-01-31"), 0.0,
                                            order=("curl_cffi", "curl", "urllib"), available=lambda n: True)
            check("the first client the host answers is chosen, after one attempt on each one it refused",
                  name == "curl" and [a["how"] for a in attempts] == ["refused", "fetched"]
                  and calls == collections.Counter({"curl_cffi": 1, "curl": 1}))
            log = read_request_log()
            check("what a client fetched or failed is logged under that client",
                  len(log.get("kline_window/curl", {}).get("ok", [])) == 1
                  and log.get("kline_window/curl_cffi", {}).get("fail") == 1)
            calls.clear()
            name, attempts = choose_backend(("600021", "2024-01-01", "2024-01-31"), 0.0,
                                            order=("curl_cffi", "curl", "urllib"), available=lambda n: n != "curl")
            check("with every installed client refused none is chosen, and a missing one is named and not asked",
                  name is None and [a["how"] for a in attempts] == ["refused", "not installed", "refused"]
                  and calls == collections.Counter({"curl_cffi": 1, "urllib": 1}))
            globals()["GETTERS"] = {"curl_cffi": lambda url, headers, timeout: b'{"data": null}',
                                    "curl": answering("curl"), "urllib": refusing("urllib")}
            name, attempts = choose_backend(("600022", "2024-01-01", "2024-01-31"), 0.0,
                                            order=("curl_cffi", "curl", "urllib"), available=lambda n: True)
            check("an answer that fails its checks still shows the client gets through",
                  name == "curl_cffi" and attempts[0]["how"] == "none")

            cmd = curl_command("curl", "https://h/x?a=1", {"User-Agent": "UA", "Referer": "https://r/"}, 20.0)
            check("the curl command fails on an HTTP error, decompresses, and carries the headers",
                  cmd[0] == "curl" and "--fail" in cmd and "--compressed" in cmd and cmd[-1] == "https://h/x?a=1"
                  and cmd[cmd.index("-A") + 1] == "UA" and cmd[cmd.index("-H") + 1] == "Referer: https://r/"
                  and cmd[cmd.index("--max-time") + 1] == "20")
            globals()["WHICH"] = lambda exe: "curl" if exe == "curl" else None
            globals()["RUN"] = lambda cmd, capture_output: types.SimpleNamespace(
                returncode=52, stdout=b"", stderr=b"curl: (52) Empty reply from server")
            _, exc = outcome(lambda: _get_curl("https://h/x", {"User-Agent": "UA"}, 5.0))
            check("a curl exit code is raised with curl's own message", isinstance(exc, RuntimeError) and "52" in str(exc))
            globals()["RUN"] = lambda cmd, capture_output: types.SimpleNamespace(returncode=0, stdout=good, stderr=b"")
            res, exc = outcome(lambda: _get_curl("https://h/x", {"User-Agent": "UA"}, 5.0))
            check("a curl success returns its bytes", exc is None and res == good)

            statuses = [403, 200]
            fake_requests = types.SimpleNamespace(
                get=lambda url, headers, impersonate, timeout: types.SimpleNamespace(status_code=statuses.pop(0),
                                                                                     content=good))
            fake_pkg = types.ModuleType("curl_cffi")
            fake_pkg.requests = fake_requests
            held = {k: sys.modules.get(k) for k in ("curl_cffi", "curl_cffi.requests")}
            sys.modules["curl_cffi"], sys.modules["curl_cffi.requests"] = fake_pkg, fake_requests
            try:
                _, exc = outcome(lambda: _get_curl_cffi("https://h/x", {}, 5.0))
                check("a curl_cffi answer other than 200 is raised", isinstance(exc, RuntimeError) and "403" in str(exc))
                res, exc = outcome(lambda: _get_curl_cffi("https://h/x", {}, 5.0))
                check("a curl_cffi 200 returns its bytes", exc is None and res == good)
            finally:
                for k, v in held.items():
                    if v is None:
                        sys.modules.pop(k, None)
                    else:
                        sys.modules[k] = v

            # baostock, on a fake module
            class FakeRS:
                def __init__(self, rows, error_code="0"):
                    self.rows, self.error_code, self.error_msg = list(rows), error_code, "message"
                    self.fields, self.i = list(BS_FIELDS), -1

                def next(self):
                    self.i += 1
                    return self.i < len(self.rows)

                def get_row_data(self):
                    return self.rows[self.i]

            logins, queries, script = [], [], []

            def fake_query(code, fields, start_date, end_date, frequency, adjustflag):
                queries.append((code, fields, start_date, end_date, frequency, adjustflag))
                step = script.pop(0)
                if isinstance(step, Exception):
                    raise step
                return step

            def fake_login():
                logins.append(1)
                return types.SimpleNamespace(error_code="0", error_msg="success")

            BS.update(module=types.SimpleNamespace(login=fake_login, logout=lambda: None,
                                                   query_history_k_data_plus=fake_query), logged_in=False)

            def row(d, o, h, lo, c, pre, v, a, st):
                return [d, "sh.600030", o, h, lo, c, pre, v, a, st, "0", "0"]

            rows3 = [row("2024-01-02", "10.00", "10.20", "9.90", "10.10", "10.00", "100000", "1010000.00", "1"),
                     row("2024-01-03", "10.10", "10.10", "10.10", "10.10", "10.10", "0", "0.00", "0"),
                     row("2024-01-04", "9.60", "9.80", "9.50", "9.70", "9.60", "200000", "1940000.00", "1")]
            script[:] = [FakeRS([], error_code="10001001"), FakeRS(rows3)]
            res, exc = outcome(lambda: fetch_bars_bs("600030", 0.0, "2024-01-01", "2024-01-31"))
            check("baostock: an error code logs in again, and the second attempt is fetched and written",
                  exc is None and res[1] == "fetched" and len(logins) == 2
                  and bs_path("600030", "2024-01-01", "2024-01-31").exists())
            check("baostock: the query asks for unadjusted daily bars with the fields named here",
                  bool(queries) and queries[-1] == ("sh.600030", ",".join(BS_FIELDS), "2024-01-01", "2024-01-31", "d", "3"))
            kl = res[0] if exc is None else {"data": {"klines": []}}
            check("baostock: a suspended day is dropped and counted, and an ex-rights break is counted",
                  len(kl["data"]["klines"]) == 2 and kl.get("_suspended_days") == 1 and kl.get("_preclose_breaks") == 1)
            unit = volume_unit(bars(kl))
            check("baostock volume reads as shares", volume_multiplier(unit) == 1 and unit["inside_range_at_1"] == 2)
            check("eastmoney volume reads as lots, and an undecided unit reads as lots",
                  volume_multiplier(volume_unit(bars(json.loads(good)))) == 100
                  and volume_multiplier({"inside_range_at_1": 0, "inside_range_at_100": 0}) == 100)
            asked = len(queries)
            res, exc = outcome(lambda: fetch_bars_bs("920047", 0.0, "2024-01-01", "2024-01-31"))
            check("baostock: a Beijing code is named uncovered and not asked",
                  exc is None and res[1] == "uncovered" and len(queries) == asked)
            script[:] = [ConnectionResetError("socket")] * 3
            res, exc = outcome(lambda: fetch_bars_bs("600031", 0.0, "2024-01-01", "2024-01-31"))
            check("baostock: three socket errors come back refused by name and write nothing",
                  exc is None and res[1] == "refused" and not bs_path("600031", "2024-01-01", "2024-01-31").exists())
            script[:] = [FakeRS(rows3)]
            res, exc = outcome(lambda: fetch_bars_bs("600032", 0.0, "2024-01-03", "2024-01-31"))
            check("baostock: rows before the window start fail the check and are not written",
                  exc is None and res[1] == "none" and not bs_path("600032", "2024-01-03", "2024-01-31").exists())
            script[:] = [FakeRS([row("2024-01-03", "10.10", "10.10", "10.10", "10.10", "10.10", "0", "0.00", "0")])]
            res, exc = outcome(lambda: fetch_bars_bs("600033", 0.0, "2024-01-01", "2024-01-31"))
            check("baostock: a window with no traded day is named instead of handed on as empty bars",
                  exc is None and res[1] == "none")
            res, exc = outcome(lambda: fetch_bars("600030", 0.0, "2024-01-01", "2024-01-31", network=False,
                                                  backend="baostock"))
            check("a baostock window on disk is read with the network closed",
                  exc is None and res[1] == "cache" and res[0].get("_source") == "baostock window")
            atomic_write_bytes(kline_path("600030", None, None), good)
            res, exc = outcome(lambda: fetch_bars("600030", 0.0, "2024-01-01", "2024-01-31", backend="baostock"))
            check("a full history from the eastmoney host is read first, whichever client was chosen",
                  exc is None and res[1] == "cache" and res[0].get("_source") == "eastmoney full history")
            globals()["GETTERS"] = {"curl_cffi": refusing("curl_cffi"), "curl": refusing("curl"),
                                    "urllib": refusing("urllib")}
            script[:] = [FakeRS([row("2024-02-01", "10.00", "10.20", "9.90", "10.10", "10.00", "100000",
                                     "1010000.00", "1")])]
            name, attempts = choose_backend(("600034", "2024-01-01", "2024-02-29"), 0.0, available=lambda n: True)
            check("with the eastmoney host refusing every client, baostock is chosen",
                  name == "baostock" and [a["how"] for a in attempts] == ["refused", "refused", "refused", "fetched"])
        finally:
            globals().update(saved)
            BS.clear()
            BS.update(bs_saved)

    def scripted(hows):
        seen, seq = [], list(hows)

        def fetch(code, beg, end, network):
            seen.append(network)
            how = seq.pop(0)
            if not network and how != "cache":
                how = "skipped"
            return ({"data": {}} if how in ("cache", "fetched") else {"_not_ok": how}), how
        return fetch, seen

    jobs5 = [(str(i), "2024-01-01", "2024-01-31") for i in range(5)]
    fetch, seen = scripted(["refused", "refused", "refused", "fetched", "cache"])
    got, stopped = kline_pass(jobs5, fetch, progress=False)
    check("three refusals in a row stop the asking", stopped == 2 and seen == [True, True, True, False, False])
    check("after the stop, a stock not on disk is skipped and one on disk is read",
          [h for _, _, h in got] == ["refused", "refused", "refused", "skipped", "cache"])
    fetch, seen = scripted(["refused", "none", "refused", "refused", "fetched"])
    got, stopped = kline_pass(jobs5, fetch, progress=False)
    check("an answer that fails its checks still ends a run of refusals", stopped is None and all(seen))
    fetch, seen = scripted(["refused", "cache", "refused", "refused", "fetched"])
    got, stopped = kline_pass(jobs5, fetch, progress=False)
    check("a cache read does not end a run of refusals", stopped == 3 and seen == [True, True, True, True, False])
    fetch, seen = scripted(["refused", "uncovered", "refused", "refused", "fetched"])
    got, stopped = kline_pass(jobs5, fetch, progress=False)
    check("a code the source does not carry neither counts as a refusal nor ends a run of them",
          stopped == 3 and seen == [True, True, True, True, False])
    check("baostock codes: Shanghai and Shenzhen A shares mapped, Beijing codes not",
          [bs_code(c) for c in ("600000", "688256", "000001", "300750", "920047", "830799", "430017")]
          == ["sh.600000", "sh.688256", "sz.000001", "sz.300750", None, None, None])
    check("the window reaches 450 days back and stops at the last final bar",
          kline_window("2026-08-01", "2026-09-10", "2026-09-15") == ("2025-05-08", "2026-09-15")
          and kline_window("2014-01-10", "2015-01-12", "2026-09-15") == ("2012-10-17", "2015-02-21"))

    older = {"ISSUE_DATE": "2018-12-24 00:00:00", "ISSUE_LISTING_DATE": "2019-01-25 00:00:00"}
    newer = {"ISSUE_DATE": "2021-08-03 00:00:00", "ISSUE_LISTING_DATE": "2021-08-26 00:00:00"}
    twin = {"ISSUE_DATE": "2021-08-05 00:00:00", "ISSUE_LISTING_DATE": "2021-08-26 00:00:00"}
    s, rule = match_offering([older, newer], "2022-01-28", [36, 36])
    check("an unlock goes to the offering whose listing plus lock lands on it, over a later offering",
          s is older and rule.startswith("listing"))
    s, rule = match_offering([older, newer], "2022-02-05", [36])
    check("a lock landing eleven days before the unlock still matches", s is older and rule.startswith("listing"))
    s, rule = match_offering([older, newer], "2022-02-25", [6])
    check("a lock landing one day after the unlock still matches", s is newer and rule.startswith("listing"))
    s, rule = match_offering([older, newer], "2022-01-28", [None])
    check("with no usable lock month the latest earlier offering is used, and the rule says so",
          s is newer and rule.startswith("latest"))
    s, rule = match_offering([newer, twin], "2022-02-28", [6])
    check("two offerings that fit equally are not guessed between", s is None)
    s, rule = match_offering([newer], "2021-01-01", [])
    check("an unlock before every offering matches none", s is None)
    check("adding months clips to the month end", add_months(dt.date(2020, 8, 31), 6) == dt.date(2021, 2, 28))

    print(f"\n{'selftest passed' if not fails else 'selftest FAILED: ' + ', '.join(fails)}")
    return 0 if not fails else 1


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sample", type=int, default=24, help="placement unlock batches to sample")
    ap.add_argument("--delay", type=float, default=0.4, help="seconds to wait after each table request")
    ap.add_argument("--kline-delay", type=float, default=3.0,
                    help="seconds to wait after each daily-bar answer, stretched by up to a quarter either way")
    ap.add_argument("--full-history", type=int, default=3,
                    help="stocks whose full daily history is also fetched, to price that request shape")
    ap.add_argument("--measure", type=int, default=3,
                    help="unlock batches outside the sample fetched to price the holder-table request")
    ap.add_argument("--bs-delay", type=float, default=0.2,
                    help="seconds to wait after each baostock answer, stretched by up to a quarter either way")
    ap.add_argument("--selftest", action="store_true", help="offline checks only")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    run(args.sample, args.delay, args.kline_delay, args.full_history, args.measure, args.bs_delay)
    return 0


if __name__ == "__main__":
    sys.exit(main())
