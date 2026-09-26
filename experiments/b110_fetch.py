"""B110 fetch: the daily bars and holder rows the station reads, into a cache later stations reuse.

**Scope.** Offerings of `SEO_TYPE` 1 whose `ISSUE_DATE` falls on or after the start date (default
2017-02-15, the day the pricing base date of a bid offering became the first day of its offering
period). For each offering: daily bars from 450 days before `ISSUE_DATE` through the listing date
plus the longest lock written in `LOCKIN_PERIOD` plus 40 days, clipped to the stock's listing dates
and to yesterday. And holder rows for every placement unlock batch dated on or after the start date,
future batches included, since their holders name the class of an offering not yet unlocked.

**Sources.** The probe measured both hosts on 2026-09-16. The eastmoney daily-bar host closed every
connection from this machine through three different clients, and baostock answered every request,
at about 0.66 s per 100 rows with suspended days counted as rows. So bars come from baostock, and
the stock list with listing and delisting dates comes from baostock too. Holder rows come from the
eastmoney data centre, which answered throughout.

**The bar cache.** One file per stock under `data/raw/b110/daily_baostock/stock/`, holding the rows
and the date ranges already asked for. A window that overlaps what is on disk asks only for the
part that is missing, so a wider scope later fetches only the difference, and any station that needs
A-share daily bars reads the same files. The probe's windows are folded in on the first run and the
probe's own files stay where they are.

**Resumable.** Every answer is checked before it is written, and every write replaces its file in
one step. Stop the run at any point with Ctrl+C: each part finishes the request in hand and the
manifest is written. The next run asks only for what is not on disk. Nothing is deleted: a cached
file that fails its checks is renamed with an `.expired` suffix and fetched again.

**Refusals.** A request with no usable answer is tried three times. Five requests in a row with no
answer start a cool-down (five minutes for bars, two for holders; bars also log in again); a fourth
cool-down with nothing answered in between stops that part, and the next run resumes it. A range
inside a stock's listed dates that comes back with no rows is named and asked again next run.

**Hangs.** The first full run stopped making progress after 411 ranges with nothing logged: the
baostock library reads its socket with no timeout, loops forever on a closed connection, and on any
error hands back nothing, which ends a paged query early as if it were complete. This script
replaces that receive loop (guarded_send): a socket silent for 60 s, a message longer than 300 s,
or a closed connection is an error, and the request is tried again after a fresh login. And a
listed stock's answer that stops more than 15 days short of either end of the range asked for is
not written. The manifest is rewritten every five minutes while the run goes on; Ctrl+C waits up
to 90 s for both parts, then writes the manifest and exits, and every file on disk is whole.

**Exit.** A part that has finished no request for an hour, when every other part is done, ends the
run: the manifest names it, the exit code is 4, and the next run resumes from what is on disk. And a
run leaves through a hard exit once its manifest is written, so no thread left behind can keep the
window open.

Writes nothing under `results/`. Writes `data/raw/b110/fetch_manifest.json`: the scope, the table
snapshots, every outcome count and every named gap.

    python experiments/b110_fetch.py --plan              # offline: scope, on disk, left, hours
    python experiments/b110_fetch.py                     # bars and holders side by side
    python experiments/b110_fetch.py --part bars         # one part only
    python experiments/b110_fetch.py --from 2010-12-16   # a wider scope; only the difference is fetched
    python experiments/b110_fetch.py --selftest

Needs `pip install baostock`.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import types
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b110_probe as P  # noqa: E402

SCOPE_START = "2017-02-15"
WINDOW_BEFORE_DAYS = 450
WINDOW_AFTER_DAYS = 40
# An offering with no lock written gets 36 months, the longest lock the rules have given a cash offering.
DEFAULT_LOCK_YEARS = 3.0
TRADING_DAYS_PER_YEAR = 243
# Unlock batches of offerings to specified investors. "公开增发" alone is a public offering and stays out.
PLACEMENT_TYPE_MARKERS = ("定向增发", "非公开", "特定对象")
BASIC_FIELDS = ["code", "code_name", "ipoDate", "outDate", "type", "status"]
BARS_EP = "bars/baostock"
BASIC_EP = "basic/baostock"
BREAKER = 5
COOLDOWN = {"bars": 300.0, "holders": 120.0}
MAX_COOLDOWNS = 3
NAMED_CAP = 500
TABLES = {"RPT_SEO_DETAIL": ("ISSUE_DATE", "SECURITY_CODE", "ISSUE_NUM"),
          "RPT_LIFT_STAGE": ("FREE_DATE", "SECURITY_CODE", "CURRENT_FREE_SHARES")}
LOG_LOCK = threading.RLock()
ONE_DAY = dt.timedelta(days=1)
# baostock's own receive loop waits forever on a silent socket and spins forever on a closed one, and
# either way a paged answer can end early without an error. The first run of this script stopped
# making progress after 411 ranges. guarded_send replaces that loop.
BS_SILENCE_S = 60.0
BS_MESSAGE_S = 300.0
BS_END_MARK = b"<![CDATA[]]>\n"
# A listed stock's answer has to reach within this many days of both ends of the range asked for.
EDGE_DAYS = 15
STALL_S = 1200.0
STOP_WAIT_S = 90.0
MANIFEST_EVERY_S = 300.0
# A run ends by itself when every part still open has finished no job for this long. It is well past
# the longest one job can take while making progress: three tries of a baostock login and query at up
# to BS_MESSAGE_S a message, about half an hour.
STUCK_S = 3600.0
HEARTBEAT: dict = {}


def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s[:10])


def append_line(path: Path, header: str, line: str) -> None:
    """Append one line; a line left short by a killed run keeps its own line."""
    with LOG_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        fresh = not path.exists() or path.stat().st_size == 0
        lead = ""
        if not fresh:
            with open(path, "rb") as fh:
                fh.seek(-1, 2)
                lead = "" if fh.read(1) == b"\n" else "\n"
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write((header + "\n" if fresh else lead) + line + "\n")


def install_log_lock() -> None:
    """The two parts run in two threads and both append to the probe's request log."""
    raw = P.log_request
    if getattr(raw, "_locked", False):
        return

    def locked(*args, **kwargs):
        with LOG_LOCK:
            return raw(*args, **kwargs)

    locked._locked = True
    P.log_request = locked


# ---------------------------------------------------------------------------
# Date ranges
# ---------------------------------------------------------------------------

def add_interval(covered: list, beg: str, end: str) -> list[list[str]]:
    """Covered ranges after adding [beg, end], in normal form: sorted, merged where two overlap or touch."""
    spans = sorted([(_d(b), _d(e)) for b, e in covered] + [(_d(beg), _d(end))])
    out: list[list[dt.date]] = []
    for b, e in spans:
        if out and b <= out[-1][1] + ONE_DAY:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([b, e])
    return [[b.isoformat(), e.isoformat()] for b, e in out]


def missing(covered: list, beg: str, end: str) -> list[tuple[str, str]]:
    """The parts of [beg, end] that no covered range holds. `covered` is in normal form."""
    cur, stop = _d(beg), _d(end)
    gaps = []
    for b, e in covered:
        b, e = _d(b), _d(e)
        if e < cur:
            continue
        if b > stop:
            break
        if b > cur:
            gaps.append((cur, b - ONE_DAY))
        cur = max(cur, e + ONE_DAY)
        if cur > stop:
            break
    if cur <= stop:
        gaps.append((cur, stop))
    return [(b.isoformat(), e.isoformat()) for b, e in gaps]


def trading_rows(beg: str, end: str) -> float:
    return ((_d(end) - _d(beg)).days + 1) * TRADING_DAYS_PER_YEAR / 365.25


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------

def lock_years_max(text) -> float:
    nums = [float(x) for x in re.findall(r"[0-9]+(?:\.[0-9]+)?", text or "")]
    return max(nums) if nums else DEFAULT_LOCK_YEARS


def deals_in_scope(seo_rows: list[dict], start: str) -> list[dict]:
    return [s for s in seo_rows if str(s.get("SEO_TYPE")) == "1" and (s.get("ISSUE_DATE") or "")[:10] >= start]


def deal_window(s: dict, last_final: str) -> tuple[str, str] | None:
    t = (s.get("ISSUE_DATE") or "")[:10]
    if not t:
        return None
    listing = (s.get("ISSUE_LISTING_DATE") or "")[:10] or t
    months = round(lock_years_max(s.get("LOCKIN_PERIOD")) * 12)
    beg = (_d(t) - dt.timedelta(days=WINDOW_BEFORE_DAYS)).isoformat()
    end = min((P.add_months(_d(listing), months) + dt.timedelta(days=WINDOW_AFTER_DAYS)).isoformat(), last_final)
    return (beg, end) if beg <= end else None


def clip(beg: str, end: str, listed) -> tuple[str, str] | None:
    """[beg, end] inside the listed dates (ipoDate, outDate); outDate is empty while a stock is listed."""
    if listed is None:
        return beg, end
    ipo, out = listed
    b = max(beg, ipo) if ipo else beg
    e = min(end, out) if out else end
    return (b, e) if b <= e else None


def needed_by_stock(deals: list[dict], basic: dict, last_final: str):
    """code -> the date ranges its offerings need, merged; and the offerings that need nothing, by reason."""
    need: dict[str, list] = {}
    notes: dict = {"uncovered": set(), "not_in_security_list": set(), "not_listed_in_window": [], "no_window": []}
    for s in deals:
        code = str(s.get("SECURITY_CODE"))
        w = deal_window(s, last_final)
        if w is None:
            notes["no_window"].append(code)
            continue
        if P.bs_code(code) is None:
            notes["uncovered"].add(code)
            continue
        listed = basic.get(code) if basic else None
        if basic and listed is None:
            notes["not_in_security_list"].add(code)
        c = clip(w[0], w[1], listed)
        if c is None:
            notes["not_listed_in_window"].append(f"{code} {(s.get('ISSUE_DATE') or '')[:10]}")
            continue
        need[code] = add_interval(need.get(code, []), *c)
    return need, notes


def holder_batches(stage_rows: list[dict], start: str) -> list[tuple[str, str]]:
    return sorted({(str(r.get("SECURITY_CODE")), r["FREE_DATE"][:10]) for r in stage_rows
                   if isinstance(r.get("FREE_SHARES_TYPE"), str)
                   and any(m in r["FREE_SHARES_TYPE"] for m in PLACEMENT_TYPE_MARKERS)
                   and isinstance(r.get("FREE_DATE"), str) and r["FREE_DATE"][:10] >= start})


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def snapshot_on_disk(report: str) -> dict | None:
    """The complete snapshot of a table on disk with the largest row count, read without a request."""
    base = P.RAW / report.lower()
    if not base.exists():
        return None
    snaps = []
    for d in base.iterdir():
        m = re.match(r"^count_(\d+)_ps(\d+)$", d.name)
        if d.is_dir() and m:
            snaps.append((int(m.group(1)), int(m.group(2)), d))
    for count, ps, d in sorted(snaps, reverse=True):
        pages = -(-count // ps)
        rows = []
        for page in range(1, pages + 1):
            f = d / f"page_{page:04d}.json"
            if not f.exists():
                break
            ok, _, obj = P.datacenter_page_ok(f.read_bytes(), page, ps, pages, count)
            if not ok:
                break
            rows.extend(obj["result"]["data"])
        else:
            return {"report": report, "count": count, "rows": rows, "snapshot": d.name, "how": "disk"}
    return None


def load_tables(network: bool, delay: float) -> dict:
    out = {}
    for report, sort_cols in TABLES.items():
        got = None
        if network:
            try:
                t = P.fetch_table(report, sort_cols, 500, delay)
                got = {"report": report, "count": t["count"], "rows": t["rows"],
                       "snapshot": Path(t["snapshot"]).name, "how": f"fetched {t['pages_fetched_this_run']} pages"}
            except RuntimeError as exc:  # Refused is a RuntimeError as well
                print(f"  {report}: {str(exc)[:200]}; reading the complete snapshot on disk", flush=True)
        if got is None:
            got = snapshot_on_disk(report)
        if got is None:
            raise RuntimeError(f"{report}: no answer and no complete snapshot on disk")
        out[report] = got
    return out


# ---------------------------------------------------------------------------
# The security list (listing and delisting dates)
# ---------------------------------------------------------------------------

def basic_ok(body: bytes, min_rows: int = 1000):
    try:
        obj = json.loads(body.decode("utf-8"))
    except Exception as exc:
        return False, f"not json ({exc.__class__.__name__})", None
    if not isinstance(obj, dict) or obj.get("fields") != BASIC_FIELDS:
        return False, "the fields are not the ones asked for", obj
    rows = obj.get("rows")
    if not isinstance(rows, list) or len(rows) < min_rows:
        return False, f"{len(rows) if isinstance(rows, list) else 'no'} rows, fewer than {min_rows}", obj
    date = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for r in rows:
        if not isinstance(r, list) or len(r) != len(BASIC_FIELDS) or not re.match(r"^(sh|sz|bj)\.\d{6}$", str(r[0])):
            return False, f"a malformed row {str(r)[:80]}", obj
        if (r[2] and not date.match(r[2])) or (r[3] and not date.match(r[3])):
            return False, f"a malformed date in {str(r)[:80]}", obj
    return True, "ok", obj


def basic_body() -> bytes:
    try:
        bs = P.bs_session()
        rs = bs.query_stock_basic()
        rows = []
        while rs.error_code == "0" and rs.next():
            rows.append(rs.get_row_data())
        if rs.error_code != "0":
            raise RuntimeError(f"baostock {rs.error_code}: {rs.error_msg}")
    except Exception:
        P.BS["logged_in"] = False
        raise
    return json.dumps({"source": "baostock", "fields": list(rs.fields), "rows": rows},
                      ensure_ascii=False, sort_keys=True).encode("utf-8")


def basic_map(obj: dict) -> dict:
    """code -> (ipoDate, outDate), stocks only (type 1)."""
    return {r[0][3:]: (r[2], r[3]) for r in obj["rows"] if r[4] == "1"}


def load_basic(network: bool, refresh: bool, delay: float, day: str, repair: bool = True, min_rows: int = 1000):
    """(code -> listed dates, how). The newest good list on disk, or one asked for when there is none
    or `refresh` is set. ({}, why) when neither works, and then windows are not clipped."""
    base = P.RAW / "daily_baostock"
    if not refresh:
        for path in sorted(base.glob("stock_basic_*.json"), reverse=True):
            ok, why, obj = basic_ok(path.read_bytes(), min_rows)
            if ok:
                return basic_map(obj), f"read {path.name}"
            if repair:
                P.retire(path, why)
    if not network:
        return {}, "no security list on disk; windows are not clipped to listing dates"
    try:
        body = P.with_retries(BASIC_EP, basic_body, delay, 3, P.BS_WAITS, 0.25, "query_stock_basic")
    except P.Refused as exc:
        return {}, f"refused: {str(exc)[:200]}"
    ok, why, obj = basic_ok(body, min_rows)
    if not ok:
        return {}, f"the security list failed its checks: {why}"
    P.atomic_write_bytes(base / f"stock_basic_{day}.json", body)
    return basic_map(obj), f"fetched stock_basic_{day}.json"


# ---------------------------------------------------------------------------
# baostock's receive loop, with timeouts
# ---------------------------------------------------------------------------

def guarded_send(context, cons, silence: float = BS_SILENCE_S, whole: float = BS_MESSAGE_S, clock=time.monotonic):
    """baostock's send_msg, with the same framing and three differences: a socket silent for
    `silence` seconds raises, a message still arriving after `whole` seconds raises, and a
    connection the server closed raises. On any of these the socket is closed and dropped, so the
    next request logs in again. The library's own version waits, spins, or returns None."""
    def send_msg(msg):
        sock = getattr(context, "default_socket", None)
        if sock is None:
            raise ConnectionError("baostock: no connection; log in first")
        try:
            sock.settimeout(silence)
            sock.sendall(bytes(msg + "\n", encoding="utf-8"))
            receive = b""
            deadline = clock() + whole
            while not receive.endswith(BS_END_MARK):
                chunk = sock.recv(8192)
                if not chunk:
                    raise ConnectionError("baostock: the server closed the connection in the middle of a message")
                receive += chunk
                if clock() > deadline:
                    raise TimeoutError(f"baostock: a message was still arriving after {whole:.0f}s")
        except BaseException:
            try:
                sock.close()
            finally:
                setattr(context, "default_socket", None)
            raise
        head = receive[:cons.MESSAGE_HEADER_LENGTH].decode("utf-8")
        parts = head.split(cons.MESSAGE_SPLIT)
        if parts[1] in cons.COMPRESSED_MESSAGE_TYPE_TUPLE:
            n = int(parts[2])
            return head + zlib.decompress(receive[cons.MESSAGE_HEADER_LENGTH:cons.MESSAGE_HEADER_LENGTH + n]).decode("utf-8")
        return receive.decode("utf-8")
    return send_msg


def install_socket_guard(su=None, cons=None, context=None, set_default=socket.setdefaulttimeout) -> str:
    """Put guarded_send in place of baostock's send_msg. Every baostock module calls it through
    `baostock.util.socketutil`, so replacing that one attribute covers them all."""
    if su is None:
        try:
            import baostock.common.contants as cons
            import baostock.common.context as context
            import baostock.util.socketutil as su
        except ImportError as exc:
            return f"not installed ({exc})"
    needed = ("MESSAGE_HEADER_LENGTH", "MESSAGE_SPLIT", "COMPRESSED_MESSAGE_TYPE_TUPLE")
    if not hasattr(su, "send_msg") or not all(hasattr(cons, n) for n in needed):
        set_default(BS_SILENCE_S)
        return (f"not installed: this baostock is laid out differently; new sockets time out after "
                f"{BS_SILENCE_S:.0f}s instead")
    if getattr(su.send_msg, "_guarded", False):
        return "already installed"
    guarded = guarded_send(context, cons)
    guarded._guarded = True
    su.send_msg = guarded
    return "installed"


# ---------------------------------------------------------------------------
# The bar cache, one file per stock
# ---------------------------------------------------------------------------

def store_path(code: str) -> Path:
    return P.RAW / "daily_baostock" / "stock" / f"{code}.json"


def empty_store(code: str) -> dict:
    return {"source": "baostock", "code": P.bs_code(code), "fields": list(P.BS_FIELDS), "covered": [], "rows": []}


def store_ok(obj) -> tuple[bool, str]:
    if not isinstance(obj, dict) or obj.get("fields") != list(P.BS_FIELDS):
        return False, "the fields are not the ones this cache holds"
    cov, rows = obj.get("covered"), obj.get("rows")
    if not isinstance(cov, list) or not isinstance(rows, list):
        return False, "no covered ranges or no rows"
    try:
        norm: list = []
        for b, e in cov:
            if b > e:
                return False, f"a covered range {b}..{e} runs backwards"
            norm = add_interval(norm, b, e)
    except (TypeError, ValueError) as exc:
        return False, f"a malformed covered range ({exc.__class__.__name__})"
    if norm != cov:
        return False, "covered ranges not sorted and merged"
    if any(not isinstance(r, list) or len(r) != len(P.BS_FIELDS) for r in rows):
        return False, "a row has the wrong number of fields"
    dates = [r[0] for r in rows]
    if dates != sorted(set(dates)):
        return False, "row dates not strictly increasing"
    j = 0
    for d in dates:
        while j < len(cov) and cov[j][1] < d:
            j += 1
        if j == len(cov) or d < cov[j][0]:
            return False, f"row {d} lies outside every covered range"
    if any(r[9] not in ("0", "1") for r in rows):
        return False, "a trading status other than 0 or 1"
    return True, "ok"


def load_store(code: str, repair: bool = True) -> dict:
    path = store_path(code)
    if not path.exists():
        return empty_store(code)
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        ok, why = store_ok(obj)
    except Exception as exc:
        ok, why = False, f"not json ({exc.__class__.__name__})"
    if ok:
        return obj
    if repair:
        P.retire(path, why)
    return empty_store(code)


def write_store(code: str, store: dict) -> None:
    P.atomic_write_bytes(store_path(code), json.dumps(store, ensure_ascii=False, sort_keys=True,
                                                      separators=(",", ":")).encode("utf-8"))


def merge_rows(old: list, new: list) -> tuple[list, int]:
    """Rows by date; a date on both sides with different values counts as a conflict and the new row wins."""
    by = {r[0]: r for r in old}
    conflicts = 0
    for r in new:
        if r[0] in by and by[r[0]] != r:
            conflicts += 1
        by[r[0]] = r
    return [by[d] for d in sorted(by)], conflicts


def gap_ok(body: bytes, beg: str, end: str):
    """(ok, reason, rows). An answer with no rows is well formed and comes back ok with []."""
    try:
        obj = json.loads(body.decode("utf-8"))
    except Exception as exc:
        return False, f"not json ({exc.__class__.__name__})", []
    if isinstance(obj, dict) and obj.get("fields") == list(P.BS_FIELDS) and obj.get("rows") == []:
        return True, "no rows", []
    ok, why, obj = P.bs_ok(body, beg, end)
    return ok, why, (obj["rows"] if ok else [])


def log_bars(code: str, beg: str, end: str, rows: int, secs: float, nbytes: int) -> None:
    append_line(P.RAW / "bars_log.tsv", "stamp\tcode\tbeg\tend\trows\tseconds\tbytes",
                f"{dt.datetime.now().isoformat(timespec='seconds')}\t{code}\t{beg}\t{end}\t{rows}\t{secs:.3f}\t{nbytes}")


def fetch_gap(code: str, beg: str, end: str, delay: float, listed: bool) -> tuple[str, str, int]:
    """(how, detail, conflicts) for one missing range of one stock."""
    bcode = P.bs_code(code)
    if bcode is None:
        return "uncovered", "baostock carries Shanghai and Shenzhen A shares only", 0
    try:
        body = P.with_retries(BARS_EP, lambda: P.bs_body(bcode, beg, end), delay, 3, P.BS_WAITS, 0.25,
                              f"{bcode} {beg}..{end}")
    except P.Refused as exc:
        return "refused", str(exc)[:300], 0
    ok, why, rows = gap_ok(body, beg, end)
    if not ok:
        return "none", why, 0
    if not rows:
        return "empty", ("no rows inside the listed dates" if listed
                         else "no rows, and the code is not in the security list"), 0
    first, last = rows[0][0], rows[-1][0]
    if listed and ((_d(first) - _d(beg)).days > EDGE_DAYS or (_d(end) - _d(last)).days > EDGE_DAYS):
        return "none", (f"rows run {first}..{last}, more than {EDGE_DAYS} days short of {beg}..{end}: "
                        f"a paged answer cut off, or a gap in the source"), 0
    secs, nbytes = P.TIMINGS[BARS_EP][-1]
    store = load_store(code)
    merged, conflicts = merge_rows(store["rows"], rows)
    store.update(rows=merged, covered=add_interval(store["covered"], beg, end), code=bcode)
    write_store(code, store)
    log_bars(code, beg, end, len(rows), secs, nbytes)
    return "fetched", f"{len(rows)} rows", conflicts


def probe_windows() -> dict[str, list[tuple[str, str, Path]]]:
    """The probe's cached windows: code -> [(beg, end, file)]."""
    out: dict = collections.defaultdict(list)
    base = P.RAW / "daily_baostock"
    if base.exists():
        for f in sorted(base.glob("*.json")):
            m = re.match(r"^(\d{6})_(\d{4})(\d{2})(\d{2})_(\d{4})(\d{2})(\d{2})$", f.stem)
            if m:
                out[m.group(1)].append((f"{m.group(2)}-{m.group(3)}-{m.group(4)}",
                                        f"{m.group(5)}-{m.group(6)}-{m.group(7)}", f))
    return out


def import_probe_windows() -> int:
    """Fold the probe's windows into the per-stock files. Returns how many windows were folded in."""
    n = 0
    for code, items in sorted(probe_windows().items()):
        store = load_store(code)
        changed = False
        for b, e, f in items:
            if not missing(store["covered"], b, e):
                continue
            ok, _, obj = P.bs_ok(f.read_bytes(), b, e)
            if not ok:
                continue  # that window is fetched like any other
            store["rows"], _ = merge_rows(store["rows"], obj["rows"])
            store["covered"] = add_interval(store["covered"], b, e)
            store["code"] = P.bs_code(code)
            changed, n = True, n + 1
        if changed:
            write_store(code, store)
    return n


def bar_jobs(need: dict, repair: bool = True, probe: dict | None = None) -> list[tuple[str, str, str]]:
    """Every missing range, per stock in code order. `probe` counts the probe's windows as on disk."""
    jobs = []
    for code in sorted(need):
        cov = load_store(code, repair)["covered"]
        for b, e, f in (probe or {}).get(code, []):
            if P.bs_ok(f.read_bytes(), b, e)[0]:
                cov = add_interval(cov, b, e)
        for b, e in need[code]:
            jobs += [(code, gb, ge) for gb, ge in missing(cov, b, e)]
    return jobs


# ---------------------------------------------------------------------------
# Running a list of requests
# ---------------------------------------------------------------------------

def run_jobs(name: str, jobs: list, do_job, stop: threading.Event, breaker: int, cooldown: float,
             max_cooldowns: int, every: int, relogin=None, live: dict | None = None):
    """`do_job(job) -> (how, detail)` over `jobs` in order. Returns (counts, named, ended).

    `refused` counts toward the breaker; an answer (`fetched`, `none`, `empty`) resets it and the
    count of cool-downs; a cache read or an uncovered code leaves both where they were. Every
    outcome other than `cache` and `fetched` is named, up to a cap per kind. `live`, when given,
    holds the counts, the names and the position as they change, for the manifest written during the
    run, and HEARTBEAT[name] holds the time the last job finished.
    """
    counts: collections.Counter = collections.Counter()
    named: dict = collections.defaultdict(list)
    if live is not None:
        with LOG_LOCK:
            live.update(jobs=len(jobs), position=0, counts=counts, named=named, ended="running")
    streak = trips = 0
    ended = "finished"
    t0 = time.monotonic()
    HEARTBEAT[name] = t0
    for i, job in enumerate(jobs):
        if stop.is_set():
            ended = f"stopped on request after {i} of {len(jobs)}"
            break
        how, detail = do_job(job)
        HEARTBEAT[name] = time.monotonic()
        with LOG_LOCK:
            counts[how] += 1
            if how not in ("cache", "fetched") and len(named[how]) < NAMED_CAP:
                named[how].append(list(job) + [detail])
            if live is not None:
                live["position"] = i + 1
        if how == "refused":
            streak += 1
            if streak >= breaker:
                trips += 1
                if trips > max_cooldowns:
                    ended = (f"stopped: {breaker} refusals in a row after {max_cooldowns} cool-downs with no "
                             f"answer between them, at {i + 1} of {len(jobs)}")
                    break
                print(f"  {name}: {streak} refusals in a row; cooling down {cooldown:.0f}s "
                      f"({trips} of {max_cooldowns})", flush=True)
                if relogin:
                    relogin()
                HEARTBEAT[name] = time.monotonic() + cooldown  # a cool-down is not a stall
                P.SLEEP(cooldown)
                streak = 0
        elif how in ("fetched", "none", "empty"):
            streak = trips = 0
        if (i + 1) % every == 0 or i + 1 == len(jobs):
            elapsed = time.monotonic() - t0
            eta = elapsed / (i + 1) * (len(jobs) - i - 1)
            with LOG_LOCK:
                tally = " ".join(f"{h} {c}" for h, c in sorted(counts.items()))
            print(f"  {name}: {i + 1}/{len(jobs)} {tally}  elapsed {elapsed / 60:.1f} min, "
                  f"about {eta / 3600:.2f} h left at this pace", flush=True)
    if live is not None:
        with LOG_LOCK:
            live["ended"] = ended
    return counts, named, ended


def wait_parts(tasks: dict, timeout: float, clock=time.monotonic, sleep=time.sleep) -> list[str]:
    """Wait up to `timeout` seconds for every part to finish; returns the names still running."""
    deadline = clock() + timeout
    while clock() < deadline and not all(t.done() for t in tasks.values()):
        sleep(0.5)
    return sorted(n for n, t in tasks.items() if not t.done())


def stalled(names, heartbeat: dict, now: float, threshold: float) -> list[str]:
    """The parts whose last job finished more than `threshold` seconds ago."""
    return sorted(n for n in names if n in heartbeat and now - heartbeat[n] > threshold)


def all_stuck(open_parts, heartbeat: dict, now: float, threshold: float) -> list[str]:
    """The open parts, when every one of them has finished no job for `threshold` seconds; else none.
    A part still making progress keeps the run going however long another part has been silent."""
    stuck = stalled(open_parts, heartbeat, now, threshold)
    return stuck if open_parts and len(stuck) == len(open_parts) else []


def hard_exit(code: int) -> None:
    """Leave the process now, whatever thread is still alive. Every file this script writes is whole on
    disk when its write returns, so the console is the only thing left to flush."""
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def seconds_per_row() -> tuple[float | None, str]:
    """Seconds per row of a baostock answer, as total seconds over total rows, so that slow answers
    weigh what they cost: this script's own log, and the probe's windows matched to the request log
    by answer size. Answers under 100 rows are left out."""
    secs_total, rows_total, own, probe = 0.0, 0, 0, 0
    path = P.RAW / "bars_log.tsv"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines()[1:]:
            p = line.split("\t")
            if len(p) != 7:
                continue
            try:
                rows, secs = int(p[4]), float(p[5])
            except ValueError:
                continue
            if rows >= 100:
                secs_total, rows_total, own = secs_total + secs, rows_total + rows, own + 1
    sizes = {}
    base = P.RAW / "daily_baostock"
    if base.exists():
        for f in base.glob("*.json"):
            if re.match(r"^\d{6}_\d{8}_\d{8}$", f.stem):
                try:
                    sizes[f.stat().st_size] = len(json.loads(f.read_text(encoding="utf-8"))["rows"])
                except Exception:  # a file that does not parse prices nothing
                    continue
    log = P.RAW / "request_log.tsv"
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines()[1:]:
            p = line.split("\t")
            if len(p) >= 6 and p[1].endswith("/baostock") and p[1] != BARS_EP and p[2] == "ok":
                try:
                    n = sizes.get(int(p[4]))
                    if n and n >= 100:
                        secs_total, rows_total, probe = secs_total + float(p[3]), rows_total + n, probe + 1
                except ValueError:
                    continue
    if rows_total == 0:
        return None, "not measured"
    return secs_total / rows_total, (f"total seconds over total rows of {own + probe} answers "
                                     f"({own} from this script, {probe} from the probe)")


def holders_seconds() -> tuple[float | None, str]:
    row = P.timing_table(P.read_request_log()).get("RPT_LIFT_GD")
    if not row or not row.get("requests"):
        return None, "not measured"
    return float(row["seconds_median"]), f"median of {row['requests']} requests"


def outcome_block(counts, named, ended) -> dict:
    return {"counts": dict(sorted(counts.items())), "named": {k: v for k, v in sorted(named.items())}, "ended": ended}


# ---------------------------------------------------------------------------
# The two parts
# ---------------------------------------------------------------------------

def bars_part(deals: list, last_final: str, bs_delay: float, refresh_basic: bool, stop, result: dict) -> None:
    guard = install_socket_guard()
    print(f"  bars: socket guard {guard}", flush=True)
    basic, basic_note = load_basic(network=True, refresh=refresh_basic, delay=bs_delay, day=last_final)
    print(f"  bars: security list: {basic_note}; {len(basic)} stocks", flush=True)
    need, notes = needed_by_stock(deals, basic, last_final)
    folded = import_probe_windows()
    jobs = bar_jobs(need)
    rows_left = sum(trading_rows(b, e) for _, b, e in jobs)
    print(f"  bars: {len(need)} stocks, probe windows folded in {folded}, {len(jobs)} ranges to ask, "
          f"about {rows_left:,.0f} rows", flush=True)
    with LOG_LOCK:
        result.update({"socket_guard": guard, "security_list": basic_note, "stocks": len(need),
                       "probe_windows_folded": folded, "ranges": len(jobs), "rows_estimated": round(rows_left),
                       "row_conflicts": 0, "offerings_without_bars": {k: sorted(v) for k, v in notes.items()}})

    def do(job):
        code, b, e = job
        how, detail, c = fetch_gap(code, b, e, bs_delay, listed=code in basic)
        if c:
            with LOG_LOCK:
                result["row_conflicts"] += c
        return how, detail

    try:
        counts, named, ended = run_jobs("bars", jobs, do, stop, BREAKER, COOLDOWN["bars"], MAX_COOLDOWNS, 25,
                                        relogin=P.bs_logout, live=result)
    finally:
        P.bs_logout()
    with LOG_LOCK:
        result.update(outcome_block(counts, named, ended))
    print(f"  bars: {ended}", flush=True)


def holders_part(stage_rows: list, start: str, today: str, delay: float, stop, result: dict) -> None:
    batches = holder_batches(stage_rows, start)
    future = sum(1 for _, d in batches if d > today)
    print(f"  holders: {len(batches)} unlock batches from {start}, {future} of them after today", flush=True)
    with LOG_LOCK:
        result.update({"batches": len(batches), "future_batches": future})

    def do(job):
        obj, how = P.fetch_lift_gd(job[0], job[1], delay)
        return how, (obj.get("_not_ok", "")[:300] if isinstance(obj, dict) and "_not_ok" in obj else "")

    counts, named, ended = run_jobs("holders", batches, do, stop, BREAKER, COOLDOWN["holders"], MAX_COOLDOWNS, 100,
                                    live=result)
    with LOG_LOCK:
        result.update(outcome_block(counts, named, ended))
    print(f"  holders: {ended}", flush=True)


def write_manifest(obj: dict) -> Path:
    path = P.RAW / "fetch_manifest.json"
    with LOG_LOCK:
        body = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8")
    P.atomic_write_bytes(path, body)
    return path


def scope_counts(deals: list) -> dict:
    by = collections.Counter()
    for s in deals:
        d = (s.get("ISSUE_DATE") or "")[:10]
        era = "2020-02-14 on" if d >= "2020-02-14" else ("2017-02-15 to 2020-02-13" if d >= "2017-02-15" else "before 2017-02-15")
        by[f"{era} / {s.get('ISSUE_WAY')}"] += 1
    return dict(sorted(by.items()))


def plan(start: str, delay: float, bs_delay: float) -> int:
    today = dt.date.today().isoformat()
    last_final = (dt.date.today() - ONE_DAY).isoformat()
    tables = load_tables(network=False, delay=delay)
    seo, stage = tables["RPT_SEO_DETAIL"], tables["RPT_LIFT_STAGE"]
    deals = deals_in_scope(seo["rows"], start)
    print(f"tables on disk: offerings {seo['snapshot']}, unlock batches {stage['snapshot']}")
    print(f"scope: SEO_TYPE 1, ISSUE_DATE from {start}; {len(deals)} offerings")
    for k, v in scope_counts(deals).items():
        print(f"  {v:5d}  {k}")
    basic, note = load_basic(network=False, refresh=False, delay=bs_delay, day=last_final, repair=False)
    print(f"security list: {note}")
    need, notes = needed_by_stock(deals, basic, last_final)
    jobs = bar_jobs(need, repair=False, probe=probe_windows())
    need_rows = sum(trading_rows(b, e) for spans in need.values() for b, e in spans)
    left_rows = sum(trading_rows(b, e) for _, b, e in jobs)
    print(f"bars: {len(need)} stocks, about {need_rows:,.0f} rows needed, {len(jobs)} ranges and about "
          f"{left_rows:,.0f} rows not on disk")
    print(f"  offerings without bars: " + ", ".join(f"{k} {len(v)}" for k, v in sorted(notes.items())))
    rate, how = seconds_per_row()
    if rate is None:
        print(f"  hours: not measured, no hours printed")
    else:
        hours = (left_rows * rate + len(jobs) * bs_delay) / 3600
        print(f"  hours: {hours:.2f} at {rate * 100:.3f} s per 100 rows ({how}) plus {bs_delay}s per range")
    batches = holder_batches(stage["rows"], start)
    on_disk = sum(1 for c, d in batches if (P.RAW / "rpt_lift_gd" / f"{c}_{d}.json").exists())
    print(f"holders: {len(batches)} unlock batches, {on_disk} on disk, {len(batches) - on_disk} left "
          f"({sum(1 for _, d in batches if d > today)} dated after today)")
    secs, how = holders_seconds()
    if secs is None:
        print("  hours: not measured, no hours printed")
    else:
        print(f"  hours: {(len(batches) - on_disk) * (secs + delay) / 3600:.2f} at {secs:.3f}s ({how}) plus {delay}s")
    return 0


def run(start: str, part: str, delay: float, bs_delay: float, refresh_basic: bool) -> int:
    today = dt.date.today().isoformat()
    last_final = (dt.date.today() - ONE_DAY).isoformat()
    install_log_lock()
    tables = load_tables(network=True, delay=delay)
    seo, stage = tables["RPT_SEO_DETAIL"], tables["RPT_LIFT_STAGE"]
    deals = deals_in_scope(seo["rows"], start)
    print(f"scope: SEO_TYPE 1, ISSUE_DATE from {start}; {len(deals)} offerings; bars through {last_final}", flush=True)
    manifest = {"scope": {"from": start, "seo_type": "1", "bars_through": last_final, "part": part,
                          "offerings": len(deals), "by_period_and_way": scope_counts(deals)},
                "tables": {k: {"snapshot": v["snapshot"], "count": v["count"], "how": v["how"]} for k, v in tables.items()},
                "pacing": {"table_delay": delay, "baostock_delay": bs_delay, "breaker": BREAKER, "cooldown": COOLDOWN,
                           "max_cooldowns": MAX_COOLDOWNS, "baostock_silence_s": BS_SILENCE_S,
                           "baostock_message_s": BS_MESSAGE_S, "edge_days": EDGE_DAYS},
                "bars": {}, "holders": {}, "state": "running", "crashed": {}}
    stop = threading.Event()
    ex = ThreadPoolExecutor(max_workers=2)
    tasks = {}
    if part in ("both", "bars"):
        tasks["bars"] = ex.submit(bars_part, deals, last_final, bs_delay, refresh_basic, stop, manifest["bars"])
    if part in ("both", "holders"):
        tasks["holders"] = ex.submit(holders_part, stage["rows"], start, today, delay, stop, manifest["holders"])
    for name in tasks:
        HEARTBEAT[name] = time.monotonic()  # a part that hangs before its first request still counts
    last_write, warned, stuck = time.monotonic(), {}, []
    try:
        while not all(t.done() for t in tasks.values()):
            time.sleep(1.0)
            now = time.monotonic()
            open_parts = [n for n, t in tasks.items() if not t.done()]
            for name in stalled(open_parts, HEARTBEAT, now, STALL_S):
                if now - warned.get(name, 0.0) > 600:
                    print(f"  {name}: no request has finished for {(now - HEARTBEAT[name]) / 60:.0f} min; the run "
                          f"ends if every open part stays so for {STUCK_S / 60:.0f} min", flush=True)
                    warned[name] = now
            stuck = all_stuck(open_parts, HEARTBEAT, now, STUCK_S)
            if stuck:
                break
            if now - last_write > MANIFEST_EVERY_S:
                write_manifest(manifest)
                last_write = now
    except KeyboardInterrupt:
        print("\nstopping: each part finishes the request in hand, then the manifest is written", flush=True)
        stop.set()
        left = wait_parts(tasks, STOP_WAIT_S)
        if left:
            manifest["state"] = f"stopped on request; {', '.join(left)} had not stopped after {STOP_WAIT_S:.0f}s"
            path = write_manifest(manifest)
            print(f"  {', '.join(left)} did not stop within {STOP_WAIT_S:.0f}s; wrote {path.relative_to(P.ROOT)} "
                  f"and exiting. Every file on disk is whole.", flush=True)
            os._exit(130)
        manifest["state"] = "stopped on request"
    if stuck:
        print(f"\n{', '.join(stuck)}: no request has finished for {STUCK_S / 60:.0f} min, and every other part "
              f"is done; ending the run", flush=True)
        stop.set()
        wait_parts(tasks, STOP_WAIT_S)
        manifest["state"] = f"ended: {', '.join(stuck)} finished no request for {STUCK_S / 60:.0f} min"
    else:
        ex.shutdown(wait=True)
    for name, t in tasks.items():
        exc = t.exception() if t.done() else None
        if exc is not None:
            manifest["crashed"][name] = repr(exc)
            traceback.print_exception(type(exc), exc, exc.__traceback__)
    if manifest["state"] == "running":
        manifest["state"] = "crashed" if manifest["crashed"] else "finished"
    path = write_manifest(manifest)
    print(f"\nwrote {path.relative_to(P.ROOT)}", flush=True)
    return 4 if stuck else (1 if manifest["crashed"] else 0)


# ---------------------------------------------------------------------------
# Selftest: every piece above on data built here, including data built to fail
# ---------------------------------------------------------------------------

def selftest() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'} {name}")
        if not cond:
            fails.append(name)

    def outcome(fn):
        try:
            return fn(), None
        except Exception as exc:  # a raise is itself what some checks look for
            return None, exc

    check("touching ranges merge", add_interval([["2020-01-01", "2020-01-31"]], "2020-02-01", "2020-02-10")
          == [["2020-01-01", "2020-02-10"]])
    check("ranges a day apart stay apart", add_interval([["2020-01-01", "2020-01-31"]], "2020-02-02", "2020-02-10")
          == [["2020-01-01", "2020-01-31"], ["2020-02-02", "2020-02-10"]])
    check("an unsorted list merges into one range", add_interval([["2020-03-01", "2020-03-31"], ["2020-01-01", "2020-01-31"]],
                                                                 "2020-01-15", "2020-03-05") == [["2020-01-01", "2020-03-31"]])
    check("with nothing covered the whole range is missing",
          missing([], "2020-01-01", "2020-01-10") == [("2020-01-01", "2020-01-10")])
    check("a covered middle leaves a head and a tail",
          missing([["2020-02-01", "2020-02-10"]], "2020-01-01", "2020-03-01")
          == [("2020-01-01", "2020-01-31"), ("2020-02-11", "2020-03-01")])
    check("a fully covered range is not missing", missing([["2019-12-01", "2020-12-31"]], "2020-01-01", "2020-03-01") == [])
    check("a one-day hole is found", missing([["2020-01-01", "2020-01-10"], ["2020-01-12", "2020-01-20"]],
                                             "2020-01-01", "2020-01-20") == [("2020-01-11", "2020-01-11")])

    check("the longest lock written is read", lock_years_max("0.5-1.5年") == 1.5 and lock_years_max("3-6.17年") == 6.17
          and lock_years_max(None) == DEFAULT_LOCK_YEARS)
    deal = {"ISSUE_DATE": "2021-01-10 00:00:00", "ISSUE_LISTING_DATE": "2021-02-01 00:00:00", "LOCKIN_PERIOD": "0.5-1.5年"}
    check("a window runs 450 days before the issue to 40 days after listing plus the longest lock",
          deal_window(deal, "2026-09-15") == ("2019-10-18", "2022-09-10"))
    check("no lock written gives 36 months, and no listing date counts from the issue",
          deal_window(dict(deal, LOCKIN_PERIOD=None), "2026-09-15") == ("2019-10-18", "2024-03-12")
          and deal_window(dict(deal, LOCKIN_PERIOD=None, ISSUE_LISTING_DATE=None), "2026-09-15") == ("2019-10-18", "2024-02-19"))
    check("a window stops at the last final day", deal_window(deal, "2022-01-01") == ("2019-10-18", "2022-01-01"))
    check("a window is clipped to the listed dates",
          clip("2019-10-18", "2022-09-10", ("2020-03-02", "")) == ("2020-03-02", "2022-09-10")
          and clip("2019-10-18", "2022-09-10", ("2010-01-04", "2021-06-30")) == ("2019-10-18", "2021-06-30")
          and clip("2019-10-18", "2022-09-10", ("2023-01-03", "")) is None)

    def offering(code, t, listing, lock):
        return {"SECURITY_CODE": code, "SEO_TYPE": "1", "ISSUE_DATE": f"{t} 00:00:00",
                "ISSUE_LISTING_DATE": f"{listing} 00:00:00", "LOCKIN_PERIOD": lock}

    deals = [offering("600001", "2021-01-10", "2021-02-01", "0.5年"), offering("600001", "2021-06-01", "2021-06-20", "0.5年"),
             offering("920047", "2021-01-10", "2021-02-01", "0.5年"), offering("600002", "2021-01-10", "2021-02-01", "0.5年"),
             offering("600003", "2021-01-10", "2021-02-01", "0.5年")]
    need, notes = needed_by_stock(deals, {"600001": ("2000-01-04", ""), "600003": ("2025-01-02", "")}, "2026-09-15")
    check("two offerings of one stock need one merged range", need.get("600001") == [["2019-10-18", "2022-01-29"]])
    check("a Beijing code is uncovered, a code missing from the list is named and still needed, a later listing needs nothing",
          notes["uncovered"] == {"920047"} and notes["not_in_security_list"] == {"600002"} and "600002" in need
          and notes["not_listed_in_window"] == ["600003 2021-01-10"] and "600003" not in need)
    check("the scope keeps type-1 offerings from the start date",
          [s["SECURITY_CODE"] for s in deals_in_scope(deals + [dict(deals[0], ISSUE_DATE="2016-12-30"),
                                                                dict(deals[0], SEO_TYPE="2")], "2017-02-15")]
          == ["600001", "600001", "920047", "600002", "600003"])

    stage = [{"SECURITY_CODE": "600001", "FREE_DATE": "2021-08-02 00:00:00", "FREE_SHARES_TYPE": "定向增发机构配售股份"},
             {"SECURITY_CODE": "600001", "FREE_DATE": "2021-08-02 00:00:00", "FREE_SHARES_TYPE": "首发原股东限售股份,定向增发机构配售股份"},
             {"SECURITY_CODE": "600002", "FREE_DATE": "2021-08-02 00:00:00", "FREE_SHARES_TYPE": "公开增发机构配售股份"},
             {"SECURITY_CODE": "600003", "FREE_DATE": "2016-01-04 00:00:00", "FREE_SHARES_TYPE": "定向增发机构配售股份"},
             {"SECURITY_CODE": "600004", "FREE_DATE": "2027-01-04 00:00:00", "FREE_SHARES_TYPE": "定向增发机构配售股份,股权激励限售股份"},
             {"SECURITY_CODE": "600005", "FREE_DATE": None, "FREE_SHARES_TYPE": "定向增发机构配售股份"}]
    check("holder batches: placements from the start date, once per stock and day, future ones kept, public offerings out",
          holder_batches(stage, "2017-02-15") == [("600001", "2021-08-02"), ("600004", "2027-01-04")])

    row = lambda d, c="10.00", st="1": [d, "sh.600009", "10.00", "10.10", "9.90", c, "10.00", "1000", "10000.00", st, "0", "0"]
    good_store = {"source": "baostock", "code": "sh.600009", "fields": list(P.BS_FIELDS),
                  "covered": [["2021-01-04", "2021-01-08"], ["2021-02-01", "2021-02-05"]],
                  "rows": [row("2021-01-04"), row("2021-01-05"), row("2021-02-01")]}
    check("a well formed store passes", store_ok(good_store)[0])
    check("a row between two covered ranges or after the last one fails",
          not store_ok(dict(good_store, rows=[row("2021-01-04"), row("2021-01-05"), row("2021-01-20"), row("2021-02-01")]))[0]
          and not store_ok(dict(good_store, rows=good_store["rows"] + [row("2021-02-10")]))[0])
    check("rows out of order fail", not store_ok(dict(good_store, rows=[row("2021-01-05"), row("2021-01-04")]))[0])
    check("touching covered ranges left unmerged fail",
          not store_ok(dict(good_store, covered=[["2021-01-04", "2021-01-08"], ["2021-01-09", "2021-02-05"]]))[0])
    check("a trading status other than 0 or 1 fails", not store_ok(dict(good_store, rows=[row("2021-01-04", st="2")]))[0])
    check("other fields fail", not store_ok(dict(good_store, fields=list(P.BS_FIELDS)[:-1]))[0])
    merged, conflicts = merge_rows([row("2021-01-04", c="10.00")], [row("2021-01-05"), row("2021-01-04", c="11.00")])
    check("a date on both sides with different values is one conflict, and the new row wins",
          conflicts == 1 and [r[0] for r in merged] == ["2021-01-04", "2021-01-05"] and merged[0][5] == "11.00")

    class FakeRS:
        def __init__(self, rows, fields, error_code="0"):
            self.rows, self.fields, self.error_code, self.error_msg, self.i = list(rows), list(fields), error_code, "msg", -1

        def next(self):
            self.i += 1
            return self.i < len(self.rows)

        def get_row_data(self):
            return self.rows[self.i]

    def weekday_rows(bcode, beg, end):
        out, d = [], _d(beg)
        while d <= _d(end):
            if d.weekday() < 5:
                out.append([d.isoformat(), bcode, "10.00", "10.10", "9.90", "10.00", "10.00", "1000", "10000.00", "1", "0", "0"])
            d += ONE_DAY
        return out

    queries, basic_calls, behaviour, logins = [], [], {}, []

    def history(code, fields, start_date, end_date, frequency, adjustflag):
        queries.append((code, start_date, end_date))
        mode = behaviour.get(code, "rows")
        if mode == "raise":
            raise ConnectionResetError("socket")
        if mode == "empty":
            return FakeRS([], P.BS_FIELDS)
        if mode == "outside":
            return FakeRS(weekday_rows(code, "2020-12-28", end_date), P.BS_FIELDS)
        if mode == "short":
            return FakeRS(weekday_rows(code, start_date, (_d(end_date) - dt.timedelta(days=20)).isoformat()), P.BS_FIELDS)
        if mode == "edge15":
            return FakeRS(weekday_rows(code, start_date, (_d(end_date) - dt.timedelta(days=15)).isoformat()), P.BS_FIELDS)
        if mode == "late":
            return FakeRS(weekday_rows(code, (_d(start_date) + dt.timedelta(days=20)).isoformat(), end_date), P.BS_FIELDS)
        return FakeRS(weekday_rows(code, start_date, end_date), P.BS_FIELDS)

    basic_rows = [["sh.600010", "甲", "2000-01-04", "", "1", "1"], ["sh.000001", "指数", "1991-07-15", "", "2", "1"],
                  ["sz.000002", "乙", "1991-01-29", "2020-06-30", "1", "0"]]

    def stock_basic():
        basic_calls.append(1)
        return FakeRS(basic_rows, BASIC_FIELDS)

    saved = {k: getattr(P, k) for k in ("RAW", "SLEEP")}
    bs_saved = dict(P.BS)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            P.RAW = Path(tmp)
            paused = []
            P.SLEEP = paused.append
            P.BS.update(module=types.SimpleNamespace(
                login=lambda: logins.append(1) or types.SimpleNamespace(error_code="0", error_msg="success"),
                logout=lambda: None, query_history_k_data_plus=history, query_stock_basic=stock_basic), logged_in=False)

            res, exc = outcome(lambda: fetch_gap("600010", "2021-01-04", "2021-01-15", 0.0, listed=True))
            st = load_store("600010")
            check("a missing range is fetched and written with its covered range",
                  exc is None and res[0] == "fetched" and st["covered"] == [["2021-01-04", "2021-01-15"]]
                  and len(st["rows"]) == 10 and st["code"] == "sh.600010")
            res, exc = outcome(lambda: fetch_gap("600010", "2021-01-16", "2021-01-31", 0.0, listed=True))
            st = load_store("600010")
            check("a touching range extends the same covered range and adds its rows",
                  exc is None and res[0] == "fetched" and st["covered"] == [["2021-01-04", "2021-01-31"]] and len(st["rows"]) == 20)
            log_lines = (P.RAW / "bars_log.tsv").read_text(encoding="utf-8").splitlines()
            check("each fetched range is logged with its row count", len(log_lines) == 3 and log_lines[1].split("\t")[4] == "10")
            check("after those two, only the uncovered parts of a wider range are asked",
                  bar_jobs({"600010": [["2021-01-01", "2021-02-10"]]})
                  == [("600010", "2021-01-01", "2021-01-03"), ("600010", "2021-02-01", "2021-02-10")])

            behaviour["sh.600011"] = "empty"
            res, exc = outcome(lambda: fetch_gap("600011", "2021-01-04", "2021-01-15", 0.0, listed=True))
            check("no rows inside the listed dates is named empty and nothing is written",
                  exc is None and res[0] == "empty" and "listed" in res[1] and not store_path("600011").exists())
            behaviour["sh.600012"] = "raise"
            res, exc = outcome(lambda: fetch_gap("600012", "2021-01-04", "2021-01-15", 0.0, listed=True))
            check("three socket errors come back refused, nothing written, and the session is marked logged out",
                  exc is None and res[0] == "refused" and not store_path("600012").exists() and P.BS["logged_in"] is False)
            asked = len(queries)
            res, exc = outcome(lambda: fetch_gap("920047", "2021-01-04", "2021-01-15", 0.0, listed=False))
            check("a Beijing code is uncovered and not asked", exc is None and res[0] == "uncovered" and len(queries) == asked)
            behaviour["sh.600013"] = "outside"
            res, exc = outcome(lambda: fetch_gap("600013", "2021-01-04", "2021-01-15", 0.0, listed=True))
            check("rows outside the asked range fail the check and nothing is written",
                  exc is None and res[0] == "none" and not store_path("600013").exists())

            behaviour["sh.600016"] = "short"
            res, exc = outcome(lambda: fetch_gap("600016", "2021-01-04", "2021-03-31", 0.0, listed=True))
            check("a listed stock's answer ending more than 15 days before the asked end is not written",
                  exc is None and res[0] == "none" and "short" in res[1] and not store_path("600016").exists())
            behaviour["sh.600017"] = "late"
            res, exc = outcome(lambda: fetch_gap("600017", "2021-01-04", "2021-03-31", 0.0, listed=True))
            check("a listed stock's answer starting more than 15 days after the asked start is not written",
                  exc is None and res[0] == "none" and not store_path("600017").exists())
            behaviour["sh.600018"] = "edge15"
            res, exc = outcome(lambda: fetch_gap("600018", "2021-01-04", "2021-03-31", 0.0, listed=True))
            check("an answer ending exactly 15 days early is written", exc is None and res[0] == "fetched")
            res, exc = outcome(lambda: fetch_gap("600016", "2021-01-04", "2021-03-31", 0.0, listed=False))
            check("a code outside the security list is not held to the edges", exc is None and res[0] == "fetched")

            store_path("600014").parent.mkdir(parents=True, exist_ok=True)
            store_path("600014").write_bytes(b"{broken")
            kept = load_store("600014", repair=False)
            check("a broken store reads as empty and, when not repairing, stays on disk",
                  kept["covered"] == [] and store_path("600014").exists())
            fixed = load_store("600014")
            check("a broken store is renamed with .expired when repairing, not removed",
                  fixed["rows"] == [] and not store_path("600014").exists()
                  and any(p.name.startswith("600014.json.bad_") and p.name.endswith(".expired")
                          for p in store_path("600014").parent.iterdir()))

            probe_file = P.RAW / "daily_baostock" / "600015_20210104_20210108.json"
            probe_file.write_bytes(json.dumps({"source": "baostock", "code": "sh.600015", "fields": list(P.BS_FIELDS),
                                               "rows": weekday_rows("sh.600015", "2021-01-04", "2021-01-08")},
                                              sort_keys=True).encode("utf-8"))
            check("the plan counts a probe window as on disk without writing anything",
                  bar_jobs({"600015": [["2021-01-04", "2021-01-08"]]}, repair=False, probe=probe_windows()) == []
                  and bar_jobs({"600015": [["2021-01-04", "2021-01-08"]]}, repair=False)
                  == [("600015", "2021-01-04", "2021-01-08")] and not store_path("600015").exists())
            first, second = import_probe_windows(), import_probe_windows()
            st = load_store("600015")
            check("a probe window is folded in once, its file stays, and it covers its range",
                  first == 1 and second == 0 and probe_file.exists() and st["covered"] == [["2021-01-04", "2021-01-08"]]
                  and len(st["rows"]) == 5)

            basic, note = load_basic(network=True, refresh=False, delay=0.0, day="2026-09-15", min_rows=1)
            check("the security list is asked for, written, and keeps stocks only",
                  basic == {"600010": ("2000-01-04", ""), "000002": ("1991-01-29", "2020-06-30")}
                  and note.startswith("fetched") and len(basic_calls) == 1)
            basic2, note2 = load_basic(network=False, refresh=False, delay=0.0, day="2026-09-16", min_rows=1)
            check("a security list on disk is read without asking", basic2 == basic and note2.startswith("read")
                  and len(basic_calls) == 1)
            bad = P.RAW / "daily_baostock" / "stock_basic_2026-09-16.json"
            bad.write_bytes(b"{bad")
            basic3, note3 = load_basic(network=False, refresh=False, delay=0.0, day="2026-09-16", repair=False, min_rows=1)
            check("a broken newer list is passed over for the good older one", basic3 == basic and bad.exists()
                  and note3 == "read stock_basic_2026-09-15.json")
            check("a list with too few rows fails", not basic_ok(bad.read_bytes())[0]
                  and not basic_ok((P.RAW / "daily_baostock" / "stock_basic_2026-09-15.json").read_bytes(), min_rows=1000)[0])

            snap = P.RAW / "rpt_seo_detail"
            page = lambda data, pages, count: json.dumps({"success": True, "code": 0, "result": {"pages": pages, "count": count,
                                                                                                  "data": data}}).encode("utf-8")
            P.atomic_write_bytes(snap / "count_3_ps2" / "page_0001.json", page([{"a": 1}, {"a": 2}], 2, 3))
            P.atomic_write_bytes(snap / "count_3_ps2" / "page_0002.json", page([{"a": 3}], 2, 3))
            P.atomic_write_bytes(snap / "count_5_ps2" / "page_0001.json", page([{"a": 1}, {"a": 2}], 3, 5))
            P.atomic_write_bytes(snap / "count_2_ps2" / "page_0001.json", page([{"a": 1}, {"a": 2}], 1, 2))
            got = snapshot_on_disk("RPT_SEO_DETAIL")
            check("the largest complete snapshot on disk is read, over a smaller complete one and a larger incomplete one",
                  got is not None and got["count"] == 3 and len(got["rows"]) == 3 and got["snapshot"] == "count_3_ps2")

            check("no measurement, no rate", seconds_per_row() == (None, "not measured"))
            append_line(P.RAW / "bars_log.tsv", "h", "2026-09-16T00:00:00\t600020\t2021-01-01\t2021-12-31\t200\t1.200\t9")
            append_line(P.RAW / "bars_log.tsv", "h", "2026-09-16T00:00:00\t600021\t2021-01-01\t2021-12-31\t100\t0.800\t9")
            append_line(P.RAW / "bars_log.tsv", "h", "2026-09-16T00:00:00\t600022\t2021-01-01\t2021-02-01\t50\t9.000\t9")
            rate, how = seconds_per_row()
            check("the rate is total seconds over total rows, over answers of 100 rows or more",
                  rate is not None and abs(rate - 2.0 / 300) < 1e-12)
            with open(P.RAW / "bars_log.tsv", "a", encoding="utf-8", newline="\n") as fh:
                fh.write("2026-09-16T00:00:00\t600023\t2021")  # a line cut short by a killed run
            append_line(P.RAW / "bars_log.tsv", "h", "2026-09-16T00:00:00\t600024\t2021-01-01\t2021-12-31\t100\t0.700\t9")
            rate2, _ = seconds_per_row()
            check("a line cut short is skipped and the next line still counts", rate2 is not None and abs(rate2 - 2.7 / 400) < 1e-12
                  and (P.RAW / "bars_log.tsv").read_text(encoding="utf-8").splitlines()[-1].split("\t")[1] == "600024")
        finally:
            for k, v in saved.items():
                setattr(P, k, v)
            P.BS.clear()
            P.BS.update(bs_saved)

    def scripted(hows):
        calls, seq = [], list(hows)

        def do(job):
            calls.append(job)
            return seq.pop(0), "detail"
        return do, calls

    sleeps, relogins = [], []
    saved_sleep = P.SLEEP
    P.SLEEP = sleeps.append
    try:
        hows = ["refused", "refused", "refused", "refused", "fetched", "refused", "refused", "refused", "refused", "refused", "refused"]
        do, calls = scripted(hows)
        counts, named, ended = run_jobs("t", [(i,) for i in range(11)], do, threading.Event(), 2, 7.0, 2, 1000,
                                        relogin=lambda: relogins.append(1))
        check("refusals trip cool-downs with a fresh login, an answer resets them, and a third trip in a row stops",
              ended.startswith("stopped: 2 refusals") and sleeps == [7.0] * 4 and len(relogins) == 4 and len(calls) == 11
              and counts == collections.Counter({"refused": 10, "fetched": 1}) and len(named["refused"]) == 10
              and named["refused"][0] == [0, "detail"])
        sleeps.clear()
        do, calls = scripted(["refused", "cache", "uncovered", "refused", "fetched"])
        counts, named, ended = run_jobs("t", [(i,) for i in range(5)], do, threading.Event(), 2, 7.0, 2, 1000)
        check("a cache read and an uncovered code neither reset the count nor count toward it",
              sleeps == [7.0] and ended == "finished" and "cache" not in named)
        stop = threading.Event()
        stop.set()
        do, calls = scripted(["fetched"])
        counts, named, ended = run_jobs("t", [(0,)], do, stop, 2, 7.0, 2, 1000)
        check("a stop request ends the list before the next job", calls == [] and ended.startswith("stopped on request after 0"))
        live, marks = {}, []

        def do_live(job):
            time.sleep(0.002)
            marks.append(time.monotonic())
            return ("fetched" if job == (1,) else "none"), "detail"

        HEARTBEAT.pop("live-test", None)
        run_jobs("live-test", [(1,), (2,)], do_live, threading.Event(), 5, 1.0, 1, 1000, live=live)
        check("the live record carries the position, the counts, the names and the end, and the heartbeat follows each job",
              live.get("position") == 2 and live.get("counts") == collections.Counter({"fetched": 1, "none": 1})
              and live.get("named", {}).get("none") == [[2, "detail"]] and live.get("ended") == "finished"
              and HEARTBEAT.get("live-test", 0.0) >= marks[-1])
    finally:
        P.SLEEP = saved_sleep

    class FakeSock:
        def __init__(self, chunks):
            self.chunks, self.sent, self.timeout, self.closed = list(chunks), [], None, False

        def settimeout(self, s):
            self.timeout = s

        def sendall(self, b):
            self.sent.append(b)

        def recv(self, n):
            step = self.chunks.pop(0)
            if isinstance(step, BaseException):
                raise step
            return step

        def close(self):
            self.closed = True

    cons = types.SimpleNamespace(MESSAGE_HEADER_LENGTH=21, MESSAGE_SPLIT="\1", COMPRESSED_MESSAGE_TYPE_TUPLE=("96",))

    def head(kind, n):
        return "00.9.30\1" + kind + "\1" + str(n).zfill(10)

    plain = (head("01", 20) + "0\1success\1login\1anonymous").encode("utf-8") + BS_END_MARK
    sock = FakeSock([plain[:10], plain[10:-5], plain[-5:]])
    ctx = types.SimpleNamespace(default_socket=sock)
    res, exc = outcome(lambda: guarded_send(ctx, cons, silence=7.0)("hello"))
    check("guard: a message in pieces, the end mark split across two reads, comes back whole",
          exc is None and res == plain.decode("utf-8") and sock.sent == [b"hello\n"] and sock.timeout == 7.0
          and ctx.default_socket is sock and not sock.closed)
    body = "0\1success\1query_history_k_data_plus\1u\1" + "x" * 50 + "\n"
    packed = zlib.compress(body.encode("utf-8"))
    ctx = types.SimpleNamespace(default_socket=FakeSock([head("96", len(packed)).encode("utf-8") + packed + BS_END_MARK]))
    res, exc = outcome(lambda: guarded_send(ctx, cons)("q"))
    check("guard: a compressed message comes back as its header and its unpacked body",
          exc is None and res == head("96", len(packed)) + body)
    sock = FakeSock([plain[:10], b""])
    ctx = types.SimpleNamespace(default_socket=sock)
    res, exc = outcome(lambda: guarded_send(ctx, cons)("q"))
    check("guard: a connection closed mid-message raises, and the socket is closed and dropped",
          isinstance(exc, ConnectionError) and sock.closed and ctx.default_socket is None)
    sock = FakeSock([plain[:10], socket.timeout("timed out")])
    ctx = types.SimpleNamespace(default_socket=sock)
    res, exc = outcome(lambda: guarded_send(ctx, cons)("q"))
    check("guard: a silent socket raises, and the socket is closed and dropped",
          isinstance(exc, OSError) and sock.closed and ctx.default_socket is None)
    ticks = iter([0.0, 1.0, 2.0, 400.0])
    ctx = types.SimpleNamespace(default_socket=FakeSock([plain[:5], plain[5:10], plain[10:15], plain[15:]]))
    res, exc = outcome(lambda: guarded_send(ctx, cons, whole=300.0, clock=lambda: next(ticks))("q"))
    check("guard: a message still arriving after the whole-message limit raises",
          isinstance(exc, TimeoutError) and ctx.default_socket is None)
    res, exc = outcome(lambda: guarded_send(types.SimpleNamespace(), cons)("q"))
    check("guard: with no connection it raises", isinstance(exc, ConnectionError))
    su = types.SimpleNamespace(send_msg=lambda m: None)
    first, second = install_socket_guard(su, cons, types.SimpleNamespace()), install_socket_guard(su, cons, types.SimpleNamespace())
    check("guard: installed once in place of send_msg", first == "installed" and second == "already installed"
          and getattr(su.send_msg, "_guarded", False))
    defaults = []
    third = install_socket_guard(types.SimpleNamespace(send_msg=lambda m: None), types.SimpleNamespace(),
                                 types.SimpleNamespace(), set_default=defaults.append)
    check("guard: a library laid out differently gets a default socket timeout instead",
          third.startswith("not installed") and defaults == [BS_SILENCE_S])

    class Fut:
        def __init__(self, done):
            self._done = done

        def done(self):
            return self._done

    now = [0.0]

    def fake_clock():
        return now[0]

    def fake_sleep(s):
        now[0] += s

    check("waiting for the parts returns the ones still running when the time is up",
          wait_parts({"bars": Fut(False), "holders": Fut(True)}, 5.0, clock=fake_clock, sleep=fake_sleep) == ["bars"]
          and now[0] >= 5.0)
    check("waiting ends at once when every part is done",
          wait_parts({"holders": Fut(True)}, 5.0, clock=fake_clock, sleep=fake_sleep) == [])
    check("a part is stalled only past the threshold, and a part with no heartbeat yet is not",
          stalled(["bars", "holders", "new"], {"bars": 0.0, "holders": 900.0}, 1300.0, 1200.0) == ["bars"])

    # Exit for certain: the stuck rule, a run with a part that never returns, a run that finishes, the
    # hard exit against a thread that never ends, and main's route through it.
    check("exit: a run ends only when every open part has been silent past the limit",
          all_stuck(["bars"], {"bars": 0.0}, 4000.0, 3600.0) == ["bars"]
          and all_stuck(["bars", "holders"], {"bars": 0.0, "holders": 3900.0}, 4000.0, 3600.0) == []
          and all_stuck(["bars"], {"bars": 1000.0}, 4000.0, 3600.0) == []
          and all_stuck([], {}, 4000.0, 3600.0) == [])
    release = threading.Event()

    def stuck_part(*args):
        release.wait()  # a receive that never returns

    def quick_part(*args):
        return None

    def stub_tables(network, delay):
        return {k: {"rows": [], "snapshot": "stub", "count": 0, "how": "stub"} for k in TABLES}

    def run_with(bars_stub, holders_stub, limit):
        names = ("load_tables", "bars_part", "holders_part", "write_manifest", "STUCK_S", "STOP_WAIT_S")
        saved, states, box = {k: globals()[k] for k in names}, [], {}
        for part_name in ("bars", "holders"):
            HEARTBEAT.pop(part_name, None)
        runner = threading.Thread(target=lambda: box.update(rc=run(SCOPE_START, "both", 0.0, 0.0, False)),
                                  daemon=True)
        try:
            globals().update(load_tables=stub_tables, bars_part=bars_stub, holders_part=holders_stub,
                             write_manifest=lambda obj: states.append(obj.get("state")) or P.RAW / "fetch_manifest.json",
                             STUCK_S=2.0, STOP_WAIT_S=1.0)
            t0 = time.monotonic()
            runner.start()
            runner.join(timeout=limit)
            took, alone = time.monotonic() - t0, not runner.is_alive()
        finally:
            release.set()
            runner.join(timeout=limit)
            globals().update(saved)
        return alone, box.get("rc"), (states[-1] if states else None), took

    alone, rc, state, took = run_with(stuck_part, quick_part, 20.0)
    check("exit: a part that never returns, with the other part done, ends the run with code 4 and a manifest naming it",
          alone and rc == 4 and state is not None and state.startswith("ended: bars") and took < 20.0)
    alone, rc, state, took = run_with(quick_part, quick_part, 20.0)
    check("exit: parts that finish end the run with code 0, and the manifest says finished",
          alone and rc == 0 and state == "finished")
    here = str(Path(__file__).resolve().parent)
    child = ("import sys, threading; sys.path.insert(0, sys.argv[1]); import b110_fetch as F; "
             "threading.Thread(target=threading.Event().wait).start(); print('left behind', flush=True); "
             "F.hard_exit(4)")
    try:
        r = subprocess.run([sys.executable, "-c", child, here], capture_output=True, text=True, timeout=20)
        exited = (r.returncode, r.stdout.strip())
    except subprocess.TimeoutExpired:
        exited = ("still running after 20 s", "")
    check("exit: the hard exit leaves at once with its code, though a thread that never ends is still alive",
          exited == (4, "left behind"))
    saved_run, saved_exit, routed = globals()["run"], globals()["hard_exit"], []
    try:
        globals()["run"] = lambda *a, **k: 4
        globals()["hard_exit"] = routed.append
        main(["--part", "bars"])
    finally:
        globals()["run"], globals()["hard_exit"] = saved_run, saved_exit
    check("exit: a fetch run's code leaves through the hard exit", routed == [4])

    print(f"\n{'selftest passed' if not fails else 'selftest FAILED: ' + ', '.join(fails)}")
    return 0 if not fails else 1


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true", help="offline: scope, what is on disk, what is left, hours")
    ap.add_argument("--from", dest="start", default=SCOPE_START, help="first ISSUE_DATE in scope, YYYY-MM-DD")
    ap.add_argument("--part", choices=("both", "bars", "holders"), default="both")
    ap.add_argument("--delay", type=float, default=0.4, help="seconds to wait after each data-centre request")
    ap.add_argument("--bs-delay", type=float, default=0.2, help="seconds to wait after each baostock answer")
    ap.add_argument("--refresh-basic", action="store_true", help="ask baostock for a new security list")
    ap.add_argument("--selftest", action="store_true", help="offline checks only")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.start):
        ap.error("--from takes YYYY-MM-DD")
    if args.plan:
        return plan(args.start, args.delay, args.bs_delay)
    hard_exit(run(args.start, args.part, args.delay, args.bs_delay, args.refresh_basic))
    return 0  # reached only when the selftest stands in for hard_exit


if __name__ == "__main__":
    sys.exit(main())
