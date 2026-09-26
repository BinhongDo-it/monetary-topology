"""B120 plans: the locked-price plans, their terms, and what became of each.

**What this is for.** The census (`b120_fetch.py`) holds announcement titles, the plans themselves from
the placement category, and the PDFs of the subscription agreements and of the plan documents no
agreement announcement covers. This script reads each PDF's pricing base date and price, keeps the
documents whose price was fixed on the board's resolution date, groups them into plans, and links each
plan to the first of its ends on record. It prints the objects. It writes no criterion and nothing
under `results/`.

**Inputs, all on disk.** The census cache and PDFs under `data/raw/b120/` and the B110 offering table.
**Outputs.** The PDF text at `data/cache/b120_pdf_text.jsonl.gz`, read again for a PDF whose size or
time changed; the plan documents it still needs read at `data/raw/b120/plan_documents_wanted.txt`
(those whose nearby agreements read neither a locked price nor first-day pricing), which
`b120_fetch.py --plan-pdfs` fetches; and the printout at `data/raw/b120/plans_printout_<time>.txt`.

    python experiments/b120_plans.py --selftest
    python experiments/b120_plans.py

**Reading rules.** A document fixes its price on the board's day when its pricing base date is a board
or shareholder resolution date (written with or without 的 or book marks, or implied by an average taken
before that day), or a written calendar date, and it names no first day of the offering period (a span
from the base date to the first day names none); one that names a price per share and no base date is
counted with them and named apart. Documents of one company (signed agreements, agreement texts,
supplements and plan documents) belong to one plan while no termination, lapse, refusal or end of review
falls between them, and either they name a price the plan already names, or the same board meeting in
their base clause, or, naming no other meeting, the document is a supplement or follows within 180 days.
A later plan whose first document is a supplement or a revised or re-signed agreement re-locks the plan
before it on a new base date. A plan document belongs to the plan of the same company holding a document
dated from 45 days before it to 120 days after it, the nearest if two; any other plan document of the
company dated after a plan's first document starts a later plan. A plan's end is the first on record
after its first document, on or before the later plan's day: an issue priced in advance in the B110
table whose text reads cash, an issue priced by bids, a termination (announcements of one company within
15 days are one termination), an exchange's decision to end the review (a notice within 90 days after a
termination confirms that termination and ends nothing more), a refusal, a vote against, a lapse, a
withdrawn application, or an announcement moving the base date to the first day, after which the plan's
issue, if any, is kept. An end naming only an earlier plan (前次, 上次, 原, with or without the plan's year)
ends none and marks where a later plan starts. A notice ending a review or approving a withdrawal within
30 days of a plan's first document ends none and splits nothing, since no application of that plan can
be filed by then. A plan with none is ended by the later plan; with no later plan either, by its
subscribers' exits if any; else it is pending. The completed placements the B110 table reads as priced
in advance and paid in cash are split by their pricing text: matching funds of an asset deal and pricing
on the first day of the offering are outside the plans read here.

**Data end.** 2026-09-16, the day of the B110 offering table on disk. A document or event after it
starts no plan and ends none, and no plan document after it is wanted, so a census refreshed later reads
the same plans; the day moves with the offering table.
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import datetime as dt
import gzip
import io
import json
import os
import re
import sys
from pathlib import Path

import b120_fetch as F
import b120_probe as P

ROOT = P.ROOT
TEXT_CACHE = ROOT / "data" / "cache" / "b120_pdf_text.jsonl.gz"
TEXT_CLASSES = F.PDF_CLASSES + ("plan ended", "review ended")
AGREEMENT_CLASSES = ("agreement signed", "agreement text", "agreement supplemented")
SIGNING = AGREEMENT_CLASSES + ("plan document",)
GAP_DAYS = 180
MERGE_DAYS = 15
CONFIRM_DAYS = 90
FILING_DAYS = 30
ISSUED_FROM = "2020-02-14"
DATA_END = dt.date(2026, 9, 16)

NUM = r"(\d+(?:\.\d+)?)"
CN = r"[一二三四五六七八九十百零〇\d]+"
BOARD_BASE = re.compile(r"定价基准日[^。；]{0,60}?(?:董事会|股东大会|股东会)[^。；]{0,40}?决议[》”\"]?(?:的)?公告(?:之)?日"
                        r"|(?:董事会|股东大会|股东会)[^。；]{0,30}?决议[》”\"]?(?:的)?公告日前(?:二十|20)个交易日")
DATE_BASE = re.compile(r"定价基准日(?:为|是|：|:)?(20\d\d)年(\d{1,2})月(\d{1,2})日")
FIRST_BASE = re.compile(r"定价基准日[^。；至]{0,20}?发行期的?首日")
MOVED = re.compile(r"定价基准日由[^。；]{0,100}?(?:董事会|股东大会|股东会)[^。；]{0,40}?决议公告(?:之)?日[^。；]{0,30}?调整为[^。；]{0,6}?发行期的?首日")
MEETING = re.compile(r"第" + CN + r"届董事会第" + CN + r"次(?:[（(]?临时[）)]?)?会议")
DAY_IN = re.compile(r"(20\d\d)年(\d{1,2})月(\d{1,2})日")
PRICE_PATTERNS = (re.compile(r"价格(?:为|确定为|是|：|:)(?:人民币)?" + NUM + r"元(?:/|每)?股?"),
                  re.compile(r"即(?:人民币)?" + NUM + r"元(?:/|每)股"),
                  re.compile(r"每股(?:发行价格|认购价格|价格)?为?(?:人民币)?" + NUM + r"元"))
NOT_PRICE = re.compile(r"均价(?:为|是)?(?:人民币)?" + NUM + r"元(?:/|每)?股|" + NUM + r"元(?:/|每)股的(?:80|90|百分之八十|百分之九十)")
PLACEMENT_TEXT = re.compile(r"向特定对象发行|非公开发行|定向增发|定向发行")
# An agreement's own text may say only 特定对象 or 认购甲方本次发行之股票; a fund's subscription speaks of 份额.
PLACEMENT_LOOSE = re.compile(r"向特定对象发行|非公开发行|定向增发|定向发行|特定对象|(?:发行|认购)[^。；]{0,12}?(?:A股)?股(?:票|份)")
NOT_OFFERING_TEXT = re.compile(r"重大资产重组|购买资产|吸收合并|可转换公司债券|公司债券|要约收购")
EARLIER = re.compile(r"前次|上次|原(?:\d{4}年度?)?(?:非公开|向特定)")
LOCKED = ("locked", "price fixed, base not read")
STATES = ("locked", "price fixed, base not read", "first day", "both bases named", "not read", "not a placement")
LINKED_PRICED = ("cash", "cash by its text, net equal to gross", "cash by its text, net above gross", "cash by its text, proceeds not printed")
MERGED = ("plan ended", "review ended", "review refused", "voted down", "plan lapsed", "application withdrawn", "agreement ended")
ENDS = ("issued", "issued by bids", "plan ended", "review ended", "review ended, offering not named", "review refused", "voted down",
        "plan lapsed", "application withdrawn", "moved to first day")
BREAKS = ("plan ended", "earlier plan ended", "review ended", "review ended, offering not named", "review refused", "voted down",
          "plan lapsed", "application withdrawn")
NOTICES = ("review ended", "review ended, offering not named")
REGULATOR = NOTICES + ("review refused", "application withdrawn")
WANTED = "plan_documents_wanted.txt"
OUTCOMES = ENDS + ("re-locked on a new base date", "new locked plan", "new plan", "subscribers exited", "pending")
RELOCK_TITLE = re.compile(r"修订|重新签署|重新签订")


def flat(text: str) -> str:
    """PDF lines break inside sentences and carry private-use marks; drop both before reading a clause."""
    return re.sub(r"[ \t\r\n　-]+", "", text or "")


def census_offline() -> tuple[dict, dict, dict, dict, list]:
    """The census, the extra keywords and the plan rows, all from the cache; the classes over the census and extra rows, as the
    fetch sorts them, and over those and the plan rows."""
    undo = F.go_offline()
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            bag, gaps = F.census(P.RAW, P.TODAY(), network=False)
            extra, extra_gaps, _ = F.extra_census(P.RAW, P.TODAY(), network=False)
            plans, plan_gaps = F.plan_rows(P.RAW, P.TODAY(), network=False)
    finally:
        undo()
    rows = {**bag, **extra}
    return rows, plans, F.by_class(rows.values()), F.by_class(list(rows.values()) + list(plans.values())), gaps + extra_gaps + plan_gaps


def pdf_signature(path: Path) -> str:
    st = path.stat()
    return f"{st.st_size}:{int(st.st_mtime)}"


def text_cache(ids: list[str], pdf_dir: Path, cache: Path = TEXT_CACHE, reader=None) -> tuple[dict, dict]:
    """announcementId -> text for every id whose PDF is on disk, read from the cache where the signature holds."""
    reader = reader or (lambda p: P.pdf_text(p)[0])
    old = {}
    if cache.exists():
        with gzip.open(cache, "rt", encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                old[d["id"]] = d
    out, counts = {}, collections.Counter()
    for aid in sorted(set(ids)):
        path = pdf_dir / f"{aid}.pdf"
        if not path.exists():
            counts["no PDF"] += 1
            continue
        sig = pdf_signature(path)
        if aid in old and old[aid]["sig"] == sig:
            out[aid] = old[aid]
            counts["cached"] += 1
            continue
        text = reader(path)
        if text is None:
            counts["no text reader"] += 1
            continue
        out[aid] = {"id": aid, "sig": sig, "text": text}
        counts["read"] += 1
    if counts["read"]:
        keep = {**{k: v for k, v in old.items() if k not in out}, **out}
        tmp = cache.with_name(cache.name + ".part.expired")
        cache.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(tmp, "wt", encoding="utf-8") as fh:
            for k in sorted(keep):
                fh.write(json.dumps(keep[k], ensure_ascii=False) + "\n")
        os.replace(tmp, cache)
    return {k: v["text"] for k, v in out.items()}, dict(counts)


def to_day(y, m, d) -> dt.date | None:
    try:
        return dt.date(int(y), int(m), int(d))
    except ValueError:
        return None


def agreement_terms(text: str) -> dict:
    t = flat(text)
    board, date, first = BOARD_BASE.search(t), DATE_BASE.search(t), FIRST_BASE.search(t) or MOVED.search(t)
    fixed = board or date
    clause = fixed.group(0) if fixed else (first.group(0) if first else "")
    meeting = MEETING.search(t[fixed.start():fixed.end() + 20]) if fixed else None
    meeting = re.sub(r"(?<=[一二三四五六七八九十])\d+|\d+(?=[一二三四五六七八九十])", "", meeting.group(0)) if meeting else None
    day = None
    if date:
        day = to_day(*date.groups())
    elif board:
        near = DAY_IN.search(t[board.start():board.end() + 30])
        day = to_day(*near.groups()) if near else None
    not_prices = {float(x) for m in NOT_PRICE.finditer(t) for x in m.groups() if x}
    prices = sorted({float(m.group(1)) for pat in PRICE_PATTERNS for m in pat.finditer(t)} - not_prices)
    return {"board": bool(board), "date": bool(date), "first": bool(first), "placement": bool(PLACEMENT_LOOSE.search(t)),
            "meeting": meeting, "base_day": day, "prices": prices, "clause": clause[:120]}


def lock_state(terms: dict) -> str:
    if not terms["placement"]:
        return "not a placement"
    fixed = terms["board"] or terms["date"]
    if fixed and terms["first"]:
        return "both bases named"
    if fixed:
        return "locked"
    if terms["first"]:
        return "first day"
    return "price fixed, base not read" if terms["prices"] else "not read"


def notice_state(text: str | None) -> str:
    """What a review notice naming no offering in its title is about, read from its text."""
    if text is None:
        return "not read"
    t = flat(text)
    return "an offering" if PLACEMENT_TEXT.search(t) and not NOT_OFFERING_TEXT.search(t) else "not an offering"


def group_plans(agreements: list[dict], gap_days: int = GAP_DAYS, breaks: dict | None = None,
                data_end: dt.date = DATA_END) -> list[dict]:
    """Locked documents of one company form one plan while no break day falls after the plan's first document and on
    or before the next, and they name the same board meeting or, one naming none, follow within gap_days. Documents
    after data_end are left out."""
    plans, by_code = [], collections.defaultdict(list)
    for a in sorted(agreements, key=lambda a: (a["code"], a["day"], a["id"])):
        if a["cls"] in SIGNING and a["state"] in LOCKED and a["day"] <= data_end:
            by_code[a["code"]].append(a)
    for code in sorted(by_code):
        cur, stops = None, (breaks or {}).get(code, ())
        stops = [x if isinstance(x, tuple) else (x, "plan ended") for x in stops]
        for a in by_code[code]:
            same = bool(cur and ((a["meeting"] and a["meeting"] in cur["meetings"]) or set(a["prices"]) & set(cur["prices"])))
            other_meeting = bool(a["meeting"] and cur and cur["meetings"] and a["meeting"] not in cur["meetings"])
            broke = bool(cur and any(cur["b"] < d <= a["day"] and not (k in REGULATOR + ("earlier plan ended",)
                                                                        and (d - cur["b"]).days <= FILING_DAYS) for d, k in stops))
            joins = bool(cur) and (same or (not other_meeting and (a["cls"] == "agreement supplemented" or (a["day"] - cur["last"]).days <= gap_days)))
            if cur is None or broke or not joins:
                cur = {"code": code, "name": a["name"], "b": a["day"], "last": a["day"], "agreements": [], "days": [], "routes": [],
                       "relock": a["cls"] == "agreement supplemented" or bool(RELOCK_TITLE.search(a.get("title") or "")),
                       "meetings": [], "prices": [], "base_days": [], "states": []}
                plans.append(cur)
            cur["agreements"].append(a["id"])
            cur["days"].append(a["day"])
            cur["last"] = a["day"]
            cur["states"].append(a["state"])
            route = {"plan document": "plan document", "agreement supplemented": "supplement"}.get(a["cls"], "agreement")
            if route not in cur["routes"]:
                cur["routes"].append(route)
            if a["meeting"] and a["meeting"] not in cur["meetings"]:
                cur["meetings"].append(a["meeting"])
            cur["prices"] = sorted(set(cur["prices"]) | set(a["prices"]))
            if a["base_day"] and a["base_day"] not in cur["base_days"]:
                cur["base_days"].append(a["base_day"])
    return plans


def merge_days(days: list[tuple[dt.date, dict]], within: int = MERGE_DAYS) -> list[tuple[dt.date, list[dict]]]:
    """Announcements of one company within `within` days of the previous one are one event, dated by the first."""
    out = []
    for day, row in sorted(days, key=lambda x: x[0]):
        if out and (day - out[-1][2]).days <= within:
            out[-1][1].append(row)
            out[-1][2] = day
        else:
            out.append([day, [row], day])
    return [(d, rows) for d, rows, _ in out]


def offering_rows(since: str = ISSUED_FROM) -> tuple[list[dict], list[dict]]:
    """The B110 offering table's placements issued from `since`: priced in advance, each with B110's reading of what its
    pricing text prices, and priced by bids."""
    import b110_fetch as F110
    import b110_placements as B110
    table = F110.snapshot_on_disk("RPT_SEO_DETAIL")
    if table is None:
        return [], []
    priced, bids = [], []
    for s in table["rows"]:
        if str(s.get("SEO_TYPE")) != "1" or str(s.get("ISSUE_DATE") or "")[:10] < since:
            continue
        if s.get("ISSUE_WAY") == B110.PRICED_WAY:
            o = {"principle": s.get("PRICE_PRINCIPLE") or "", "gross": B110.num(s.get("TOTAL_RAISE_FUNDS")),
                 "net": B110.num(s.get("NET_RAISE_FUNDS"))}
            priced.append({**s, "PRICED_STATE": B110.priced_state(o)})
        elif s.get("ISSUE_WAY") == B110.BID_WAY:
            bids.append(s)
    return priced, bids


def issue_key(s: dict) -> str:
    return f"{s['SECURITY_CODE']}:{str(s['ISSUE_DATE'])[:10]}:{s.get('ISSUE_NUM')}"


def build_events(classes: dict, texts: dict, priced: list[dict], bids: list[dict], docs: list[dict]) -> tuple[dict, collections.Counter]:
    """code -> [(day, kind, detail)] sorted by day, and how the review notices naming no offering read."""
    ev = collections.defaultdict(list)
    notices = collections.Counter()
    per = collections.defaultdict(list)
    for kind in MERGED:
        for r in classes.get(kind, []):
            per[(str(r["secCode"]), kind)].append((P.day_of(r), r))
    for r in classes.get("review ended, offering not named", []):
        state = notice_state(texts.get(str(r["announcementId"])))
        notices[state] += 1
        if state != "not an offering":
            per[(str(r["secCode"]), "review ended" if state == "an offering" else "review ended, offering not named")].append((P.day_of(r), r))
    for (code, kind), days in sorted(per.items()):
        for day, rows in merge_days(days):
            titles = [P.clean_title(x["announcementTitle"]) for x in rows]
            name = "subscriber exit" if kind == "agreement ended" else kind
            if kind != "agreement ended" and all(EARLIER.search(t) for t in titles):
                name = "earlier plan ended"
            ev[code].append((day, name, {"titles": titles}))
    for code in list(ev):
        ends = sorted(d for d, k, _ in ev[code] if k in ("plan ended", "earlier plan ended", "application withdrawn"))
        kept = []
        for day, kind, detail in ev[code]:
            before = [d for d in ends if d <= day]
            if kind in NOTICES and before and (day - before[-1]).days <= CONFIRM_DAYS:
                notices[f"confirms a termination {(day - before[-1]).days // 30 * 30}-{(day - before[-1]).days // 30 * 30 + 29} days before"] += 1
                continue
            kept.append((day, kind, detail))
        ev[code] = kept
    for r in classes.get("base date or price adjusted", []):
        t = texts.get(str(r["announcementId"]))
        if t is not None and MOVED.search(flat(t)):
            ev[str(r["secCode"])].append((P.day_of(r), "moved to first day", {"titles": [P.clean_title(r["announcementTitle"])]}))
    for s in priced:
        kind = "issued" if s.get("PRICED_STATE") in LINKED_PRICED else "issued, not a cash placement"
        ev[str(s["SECURITY_CODE"])].append((dt.date.fromisoformat(str(s["ISSUE_DATE"])[:10]), kind,
                                           {"P": s.get("ISSUE_PRICE"), "n": s.get("ISSUE_NUM"), "state": s.get("PRICED_STATE"),
                                            "objects": str(s.get("ISSUE_OBJECT") or "")[:60], "key": issue_key(s)}))
    for s in bids:
        ev[str(s["SECURITY_CODE"])].append((dt.date.fromisoformat(str(s["ISSUE_DATE"])[:10]), "issued by bids",
                                           {"P": s.get("ISSUE_PRICE"), "n": s.get("ISSUE_NUM"), "key": issue_key(s)}))
    for r in docs:
        ev[str(r["secCode"])].append((P.day_of(r), "plan document", {"id": str(r["announcementId"]),
                                                                     "titles": [P.clean_title(r["announcementTitle"])]}))
    for code in ev:
        ev[code].sort(key=lambda x: (x[0], x[1]))
    return ev, notices


def assign_documents(plans: list[dict], docs: list[tuple[dt.date, dict]], near: tuple[int, int] = F.PLAN_DOC_NEAR) -> dict:
    """plan document id -> index of the plan (within `plans`, one company's) holding a document dated from near[0] days
    before it to near[1] days after it, the nearest if two; ids with none are left out."""
    out = {}
    for d, det in docs:
        best = None
        for i, p in enumerate(plans):
            for a in p["days"]:
                if d - dt.timedelta(days=near[0]) <= a <= d + dt.timedelta(days=near[1]):
                    gap = abs((a - d).days)
                    if best is None or gap < best[0]:
                        best = (gap, i)
        if best is not None:
            out[det["id"]] = best[1]
    return out


def link_plans(plans: list[dict], events: dict, data_end: dt.date = DATA_END) -> None:
    by_code = collections.defaultdict(list)
    for p in plans:
        by_code[p["code"]].append(p)
    rank = {k: i for i, k in enumerate(ENDS)}
    for code, ps in by_code.items():
        ps.sort(key=lambda p: (p["b"], p["agreements"][0]))
        for p in ps:
            p["then"] = None
        evs = events.get(code, [])
        docs = [(d, det) for d, k, det in evs if k == "plan document" and d <= data_end]
        owner = assign_documents(ps, docs)
        for i, p in enumerate(ps):
            p["documents"] = [det["id"] for _, det in docs if owner.get(det["id"]) == i]
            later = [(q["b"], "re-locked on a new base date" if q["relock"] else "new locked plan") for q in ps[i + 1:]]
            later += [(d, "new locked plan" if det["id"] in owner else "new plan") for d, det in docs
                      if d > p["b"] and owner.get(det["id"], len(ps)) > i]
            stop = min(later, key=lambda x: (x[0], x[1] != "re-locked on a new base date")) if later else None
            found, exits = None, []
            for day, kind, detail in sorted(evs, key=lambda x: (x[0], rank.get(x[1], 99))):
                if day <= p["b"] or (stop and day > stop[0]) or (not stop and day > data_end):
                    continue
                if kind == "subscriber exit":
                    exits.append(day)
                elif kind in REGULATOR and (day - p["b"]).days <= FILING_DAYS:
                    continue
                elif kind in ENDS:
                    found = (day, kind, detail)
                    break
            if found:
                p["outcome"], p["t"], p["detail"] = found[1], found[0], found[2]
                if found[1] == "moved to first day":
                    p["then"] = next(((d, k, det) for d, k, det in evs if k in ("issued", "issued by bids") and found[0] < d
                                      and (d <= stop[0] if stop else d <= data_end)), None)
            elif stop:
                p["outcome"], p["t"], p["detail"] = stop[1], stop[0], {}
            elif exits:
                p["outcome"], p["t"], p["detail"] = "subscribers exited", exits[-1], {}
            else:
                p["outcome"], p["t"], p["detail"] = "pending", data_end, {}
            p["exits"] = [d for d in exits if d <= p["t"]]


def price_ratio(p: dict) -> float | None:
    if p.get("outcome") != "issued" or not p["prices"]:
        return None
    try:
        table = float(p["detail"]["P"])
    except (TypeError, ValueError):
        return None
    return min((table / x for x in p["prices"] if x > 0), key=lambda r: abs(r - 1.0))


# ---------------------------------------------------------------------------
# The printout
# ---------------------------------------------------------------------------

def documents_read(classes: dict, texts: dict, docs: list[dict]) -> list[dict]:
    out = []
    for c in AGREEMENT_CLASSES:
        for r in classes.get(c, []):
            aid = str(r["announcementId"])
            if aid in texts:
                terms = agreement_terms(texts[aid])
                out.append({"id": aid, "code": str(r["secCode"]), "name": str(r["secName"]), "day": P.day_of(r), "cls": c,
                            "title": P.clean_title(r["announcementTitle"]), "state": lock_state(terms), **terms})
    for r in docs:
        aid = str(r["announcementId"])
        if aid in texts:
            terms = agreement_terms(texts[aid])
            out.append({"id": aid, "code": str(r["secCode"]), "name": str(r["secName"]), "day": P.day_of(r), "cls": "plan document",
                        "title": P.clean_title(r["announcementTitle"]), "state": lock_state(terms), **terms})
    return out


def unread_plans(covered: list[dict], read: list[dict], near: tuple[int, int] = F.PLAN_DOC_NEAR,
                 data_end: dt.date = DATA_END) -> list[tuple[dict, list[str]]]:
    """Plan documents up to data_end with an agreement announcement near whose agreements read neither a locked price nor
    first-day pricing: the plan document is the place left to read the pricing base date. Each with the states read near it."""
    by = collections.defaultdict(list)
    for a in read:
        if a["cls"] in AGREEMENT_CLASSES:
            by[a["code"]].append(a)
    out = []
    for r in covered:
        d = P.day_of(r)
        if d > data_end:
            continue
        states = sorted({a["state"] for a in by.get(str(r["secCode"]), [])
                         if d - dt.timedelta(days=near[0]) <= a["day"] <= d + dt.timedelta(days=near[1])})
        if not set(states) & set(LOCKED + ("first day",)):
            out.append((r, states))
    return out


def write_wanted(root: Path, wanted: list[tuple[dict, list[str]]]) -> Path:
    lines = ["# plan documents b120_plans.py needs read; b120_fetch.py --plan-pdfs fetches them. Rewritten on every run.",
             "# announcementId\tcode\tday\tstates read in the agreements near it"]
    for r, states in sorted(wanted, key=lambda x: (int(x[0]["announcementTime"]), str(x[0]["announcementId"]))):
        lines.append(f"{r['announcementId']}\t{r['secCode']}\t{P.day_of(r)}\t{', '.join(states) or 'no agreement text read'}")
    path = root / WANTED
    P.atomic_write_bytes(path, ("\n".join(lines) + "\n").encode("utf-8"))
    return path


def known_state(s: dict) -> str:
    """What a completed placement the B110 table reads as priced in advance and paid in cash is, by its pricing text."""
    text = flat(str(s.get("PRICE_PRINCIPLE") or ""))
    if "配套" in text:
        return "matching funds of an asset deal"
    if FIRST_BASE.search(text) and not BOARD_BASE.search(text):
        return "priced on the first day of the offering"
    return "a locked cash placement"


def build(write: bool = True) -> dict:
    """Every object the printout and the stations after this one read: the census, the documents read, the events and the
    plans with their ends. `write` rewrites the wanted list."""
    rows, plan_rows, census_classes, classes, gaps = census_offline()
    docs = F.plan_documents(plan_rows.values())
    uncovered, covered = F.split_plan_documents(docs, census_classes)
    ids = [str(r["announcementId"]) for c in TEXT_CLASSES for r in classes.get(c, [])] + [str(r["announcementId"]) for r in docs]
    texts, counts = text_cache(ids, P.RAW / "pdf")
    uncovered_ids = {str(r["announcementId"]) for r in uncovered}
    read = documents_read(classes, texts, docs)
    wanted = unread_plans(covered, read)
    path = write_wanted(P.RAW, wanted) if write else P.RAW / WANTED
    wanted_ids = {str(r["announcementId"]) for r, _ in wanted}
    agreements = [a for a in read if a["cls"] != "plan document" or a["id"] in uncovered_ids | wanted_ids]
    priced, bids = offering_rows()
    events, notices = build_events(classes, texts, priced, bids, docs)
    breaks = collections.defaultdict(list)
    for code, evs in events.items():
        breaks[code] = sorted((d, k) for d, k, _ in evs if k in BREAKS)
    plans = group_plans(agreements, breaks=breaks)
    link_plans(plans, events, DATA_END)
    return {"rows": rows, "plan_rows": plan_rows, "census_classes": census_classes, "classes": classes, "gaps": gaps, "docs": docs,
            "uncovered": uncovered, "covered": covered, "texts": texts, "counts": counts, "read": read, "wanted": wanted,
            "wanted_path": path, "agreements": agreements, "events": events, "notices": notices, "plans": plans}


def report(b: dict | None = None) -> int:
    b = b or build()
    rows, plan_rows, census_classes, classes, gaps = b["rows"], b["plan_rows"], b["census_classes"], b["classes"], b["gaps"]
    docs, uncovered, covered, counts, read, wanted = b["docs"], b["uncovered"], b["covered"], b["counts"], b["read"], b["wanted"]
    agreements, events, notices, plans, path = b["agreements"], b["events"], b["notices"], b["plans"], b["wanted_path"]
    print(f"== 0. from the cache: {len(rows)} census announcements, {len(plan_rows)} rows in the placement category; windows not cached {len(gaps)} "
          f"({dict(collections.Counter(g[0] for g in gaps))})")
    print(f"   plan documents (first versions) {len(docs)}: with an agreement announcement near {len(covered)}, without {len(uncovered)}")
    extra_rows = {c: len(classes.get(c, [])) - len(census_classes.get(c, [])) for c in F.CLASSES if len(classes.get(c, [])) != len(census_classes.get(c, []))}
    print(f"   rows of the placement category falling in a census class, added to the events: {extra_rows}")
    print(f"   PDF text: {counts}")

    uncovered_ids = {str(r["announcementId"]) for r in uncovered}
    wanted_ids = {str(r["announcementId"]) for r, _ in wanted}
    print("\n== 1. documents read, by class and state")
    tab = collections.Counter((a["cls"], a["state"]) for a in read)
    for c in SIGNING:
        print(f"   {c}: " + "; ".join(f"{s} {tab[(c, s)]}" for s in STATES))
    unc_docs = [a for a in read if a["id"] in uncovered_ids]
    print(f"   plan documents without an agreement announcement: {len(uncovered)}, text read {len(unc_docs)}; by state "
          f"{dict(collections.Counter(a['state'] for a in unc_docs))}")
    want_docs = [a for a in read if a["id"] in wanted_ids]
    print(f"   plan documents whose nearby agreements read neither a locked price nor first-day pricing: {len(wanted)} "
          f"(by the states near them {dict(collections.Counter(', '.join(st) or 'no agreement text read' for _, st in wanted))}); "
          f"text read {len(want_docs)}, by state {dict(collections.Counter(a['state'] for a in want_docs))}; "
          f"listed in data/raw/b120/{path.name}")
    locked = [a for a in agreements if a["cls"] in SIGNING and a["state"] in LOCKED]
    print(f"   locked documents {len(locked)} ({dict(collections.Counter(a['cls'] for a in locked))}): with a price read {sum(1 for a in locked if a['prices'])}, with more than one "
          f"price {sum(1 for a in locked if len(a['prices']) > 1)}, with the board meeting read {sum(1 for a in locked if a['meeting'])}, "
          f"with a calendar base date {sum(1 for a in locked if a['base_day'])}")
    for s in ("both bases named", "not read", "price fixed, base not read"):
        rows_s = [a for a in agreements if a["cls"] in SIGNING and a["state"] == s]
        print(f"   {s}: {len(rows_s)}")
        for a in rows_s[:: max(1, len(rows_s) // 8)][:8]:
            print(f"      {a['cls'][:9]} {a['code']} {a['name']} {a['day']} prices {a['prices'][:3]} | {a['clause'][:80]}")

    kinds = collections.Counter(k for evs in events.values() for _, k, _ in evs)
    print(f"\n== 2. events by company (announcements of one company within {MERGE_DAYS} days merged): {dict(sorted(kinds.items()))}")
    print(f"   review notices naming no offering in the title, by their text: {dict(notices)}")
    for k in ("earlier plan ended", "review ended, offering not named", "plan lapsed", "application withdrawn", "review refused", "voted down"):
        sample = [(c, d, det) for c, evs in events.items() for d, kk, det in evs if kk == k]
        for c, d, det in sample[:: max(1, len(sample) // 4)][:4]:
            print(f"      {k}: {c} {d} {det['titles'][0][:80]}")

    print(f"\n== 3. plans: {len(plans)} from {len(locked)} locked documents, {len({p['code'] for p in plans})} companies; by route "
          f"{dict(collections.Counter(' and '.join(p['routes']) for p in plans))}")
    years = collections.Counter(p["b"].year for p in plans)
    print(f"   by year of the first document: {dict(sorted(years.items()))}")
    print(f"   documents per plan: {dict(sorted(collections.Counter(len(p['agreements']) for p in plans).items()))}; "
          f"board meetings named per plan: {dict(sorted(collections.Counter(len(p['meetings']) for p in plans).items()))}; "
          f"plan documents held: {dict(sorted(collections.Counter(len(p['documents']) for p in plans).items()))}")
    tab = collections.Counter((p["b"].year, p["outcome"]) for p in plans)
    print("   outcome by year of the first document:")
    for y in sorted(years):
        print(f"     {y}: " + "; ".join(f"{o} {tab[(y, o)]}" for o in OUTCOMES if tab[(y, o)]))
    total = collections.Counter(p["outcome"] for p in plans)
    print("   all: " + "; ".join(f"{o} {total[o]}" for o in OUTCOMES))
    lags = collections.defaultdict(list)
    for p in plans:
        lags[p["outcome"]].append((p["t"] - p["b"]).days)
    for o in OUTCOMES:
        if lags[o]:
            v = sorted(lags[o])
            print(f"   days from the first document to {o}: n {len(v)}, median {v[len(v) // 2]}, tenth {v[len(v) // 10]}, "
                  f"ninetieth {v[len(v) * 9 // 10]}, max {v[-1]}")
    long = sorted([p for p in plans if p["outcome"] != "pending" and (p["t"] - p["b"]).days > 3 * 365], key=lambda p: p["b"])
    print(f"   ends more than three years after the first document: {len(long)}")
    for p in long:
        det = p["detail"]
        print(f"      {p['code']} {p['name']} b {p['b']} -> {p['outcome']} {p['t']} {det.get('P') or (det.get('titles') or [''])[0][:50]}")
    with_exit = [p for p in plans if p["exits"]]
    print(f"   plans with a subscriber exit on or before their end: {len(with_exit)}; by outcome "
          f"{dict(collections.Counter(p['outcome'] for p in with_exit))}")

    issued = [p for p in plans if p["outcome"] == "issued"]
    ratios = sorted(r for r in (price_ratio(p) for p in plans) if r is not None)
    if ratios:
        q = lambda f: ratios[min(len(ratios) - 1, int(f * (len(ratios) - 1)))]
        print(f"\n== 4. issued plans: {len(issued)}, with a price read {len(ratios)}; issue price in the B110 table over the document's "
              f"price: min {ratios[0]:.4f}, tenth {q(0.1):.4f}, median {q(0.5):.4f}, ninetieth {q(0.9):.4f}, max {ratios[-1]:.4f}")
        tails = sorted([p for p in issued if price_ratio(p) is not None], key=price_ratio)
        for p in tails[:6] + tails[-4:]:
            print(f"      {p['code']} {p['name']} b {p['b']} prices {p['prices'][:4]} issued {p['t']} at {p['detail']['P']} ({price_ratio(p):.4f})")
    print(f"   issues by the B110 reading of the pricing text: {dict(collections.Counter(p['detail'].get('state') for p in issued))}")
    known = F.completed_locked_cash(since=F.RECALL_FROM)
    linked = {p["detail"]["key"]: p for p in issued}
    then = [p for p in plans if p.get("then")]
    print(f"   plans moved to first-day pricing and issued after: {len(then)} "
          f"({dict(collections.Counter(p['then'][1] for p in then))})")
    linked.update({p["then"][2]["key"]: p for p in then})
    hit = [s for s in known if issue_key(s) in linked]
    miss = [s for s in known if issue_key(s) not in linked]
    kinds_known = collections.Counter(known_state(s) for s in known)
    kinds_miss = collections.Counter(known_state(s) for s in miss)
    print(f"   by what their pricing text prices: {dict(kinds_known)}; not linked {dict(kinds_miss)}")
    print(f"   completed locked cash placements issued from {F.RECALL_FROM}: {len(known)}; linked to a plan's issue or its issue after a move {len(hit)} "
          f"(by route {dict(collections.Counter(' and '.join(linked[issue_key(s)]['routes']) for s in hit))}), not linked {len(miss)} "
          f"(by year {dict(sorted(collections.Counter(str(s['ISSUE_DATE'])[:4] for s in miss).items()))})")
    for s in sorted(miss, key=lambda s: (known_state(s) != "a locked cash placement", s["ISSUE_DATE"]))[:60]:
        print(f"      {known_state(s)[:24]}: {s['SECURITY_CODE']} {s['SECURITY_NAME_ABBR']} T {str(s['ISSUE_DATE'])[:10]} P {s['ISSUE_PRICE']} "
              f"to {str(s.get('ISSUE_OBJECT') or '')[:30]}")

    covered_ids = {str(r["announcementId"]) for r in covered}
    check = [a for a in read if a["id"] in covered_ids]
    by_doc = {d: p for p in plans for d in p["documents"]}
    print(f"\n== 5. plan documents with an agreement announcement, text read {len(check)}: the document's state against its plan")
    cross = collections.Counter((a["state"], "in a locked plan" if a["id"] in by_doc else "in no locked plan") for a in check)
    for (s, where), n in sorted(cross.items()):
        print(f"      {s}, {where}: {n}")
    moved = [(code, d) for code, evs in events.items() for d, k, _ in evs if k == "moved to first day"]
    moved_plans = [p for p in plans if p["outcome"] == "moved to first day"]
    print(f"   moves to first-day pricing read in the adjustment PDFs: {len(moved)} announcements, {len({c for c, _ in moved})} companies; "
          f"plans ended by one {len(moved_plans)}; companies with a move and no plan ended by it "
          f"{sorted({c for c, _ in moved} - {p['code'] for p in moved_plans})}")

    print("\n== 6. a spread of plans in each outcome")
    for o in OUTCOMES:
        rows_o = sorted([p for p in plans if p["outcome"] == o], key=lambda p: (p["b"], p["code"]))
        for p in P.pick_spread([{**p, "announcementTime": 0, "announcementId": f"{p['code']}{p['b']}"} for p in rows_o], 6):
            det = p["detail"]
            extra = det.get("P") or (det.get("titles") or [""])[0][:50]
            print(f"   {o}: {p['code']} {p['name']} b {p['b']} {'/'.join(p['routes'])} prices {p['prices'][:3]} -> {p['t']} {extra}")
    return 0


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'} {name}")
        if not cond:
            fails.append(name)

    board = ("本次非公开发行股票的定价基准日为公司第三届\n董事会第十七次会议决议公告日，发行价格为13.67元/股，发行价格不低于定价基准日前二十个交易日"
             "公司股票交易均价的80%。")
    dated = "定价基准日为2020年2月25日，经甲乙双方协商，本次股份发行价格为4.06元/股，不低于定价基准日前20个交易日甲方股票均价的80%。本次非公开发行。"
    first = "本次向特定对象发行股票的定价基准日为发行期首日，发行价格不低于定价基准日前二十个交易日公司股票交易均价的80%。"
    floor = ("本次非公开发行股票的定价基准日为甲方第五届董事会第九次（临时）会议决议公告日（即2021年4月7日），发行价格为定价基准日前20个交易日"
             "公司股票交易均价的80%，即6.53元/股，不低于均价为8.16元/股的均价。")
    price_only = "认购价格：本次非公开发行股票的价格为3.00元。认购款以现金支付。每股价格为人民币10.20元/股的80%，即2.50元/股的认购价不适用。"
    fund = "公司全资子公司与专业投资机构签署有限合伙协议及认购协议，认购基金份额。"
    both = "定价基准日为公司第四届董事会第二十八次会议决议公告日。后经修订，定价基准日为发行期首日。本次非公开发行。"
    terms = {k: agreement_terms(v) for k, v in (("board", board), ("dated", dated), ("first", first), ("floor", floor),
                                                ("price", price_only), ("fund", fund), ("both", both))}
    states = {k: lock_state(v) for k, v in terms.items()}
    check(f"document states ({states})",
          states == {"board": "locked", "dated": "locked", "first": "first day", "floor": "locked",
                     "price": "price fixed, base not read", "fund": "not a placement", "both": "both bases named"})
    check(f"prices read with averages and floors of an average left out ({terms['board']['prices']}, {terms['floor']['prices']}, "
          f"{terms['price']['prices']}, {terms['first']['prices']})",
          terms["board"]["prices"] == [13.67] and terms["floor"]["prices"] == [6.53] and terms["price"]["prices"] == [2.5, 3.0]
          and terms["first"]["prices"] == [])
    more = {k: agreement_terms(v) for k, v in (
        ("de", "定价基准日为公司第八届董事会第十三次会议决议的公告日，发行价格（认购价格）为22.73元/股。本次非公开发行。"),
        ("book", "定价基准日为《董事会决议》公告日，即2020年4月24日；发行暨认购价格为不低于定价基准日前20个交易日均价的80%，即人民币11.92元/股。本次非公开发行。"),
        ("implied", "认购价格：发行价格为（不低于）关于本次发行的董事会决议公告日前二十个交易日均价的80%。本次非公开发行股票。"),
        ("range", "本次非公开发行股票的定价基准日为甲方第五届董事会第九次会议决议公告日。若甲方股票在本次发行定价基准日至发行期首日之间发生派息，价格调整。"),
        ("loose", "乙方以现金方式认购甲方本次发行之股票。定价基准日为甲方第三届董事会第七次会议决议公告日。发行价格为29.77元/股。"),
        ("moved", "本次发行的定价基准日由“公司第九届董事会第三次会议决议公告日”调整为“发行期首日”。本次向特定对象发行。"))}
    more_states = {k: lock_state(v) for k, v in more.items()}
    check(f"a board date written with 的 or in book marks or implied by the average before it, a range to the first day, an agreement "
          f"naming only 特定对象 or 本次发行之股票, and a move read as both bases ({more_states}, {more['de']['meeting']}, {more['book']['base_day']})",
          more_states == {"de": "locked", "book": "locked", "implied": "locked", "range": "locked", "loose": "locked", "moved": "both bases named"}
          and more["de"]["meeting"] == "第八届董事会第十三次会议" and more["book"]["base_day"] == dt.date(2020, 4, 24) and more["book"]["prices"] == [11.92])
    noisy = agreement_terms("定价基准日为关于本次发行的董事会（即2020年3月11日召开的第四2届董事会第三十八次会议）决议公告日。非公开发行。")
    check(f"a stray digit inside a board meeting's numeral is dropped ({noisy['meeting']})", noisy["meeting"] == "第四届董事会第三十八次会议")
    check(f"the board meeting and the calendar base date are read inside the base clause ({terms['board']['meeting']}, "
          f"{terms['floor']['meeting']}, {terms['floor']['base_day']}, {terms['dated']['base_day']})",
          terms["board"]["meeting"] == "第三届董事会第十七次会议" and terms["floor"]["meeting"] == "第五届董事会第九次（临时）会议"
          and terms["floor"]["base_day"] == dt.date(2021, 4, 7) and terms["dated"]["base_day"] == dt.date(2020, 2, 25))
    moved = "本次发行的定价基准日由“公司第九届董事会第三次会议决议公告日”调整为“发行期首日”，发行价格由“7.05元/股”调整为“不低于均价的80%”。"
    dividend = "因实施2025年年度权益分派，本次发行价格由20.97元/股调整为20.92元/股，定价基准日为公司第四届董事会第九次会议决议公告日。"
    check("a move to first-day pricing is told from a dividend adjustment", bool(MOVED.search(flat(moved))) and not MOVED.search(flat(dividend)))
    notice = {k: notice_state(v) for k, v in (("offering", "关于终止审查公司非公开发行A股股票申请的通知"), ("restructuring",
              "关于终止审查公司发行股份购买资产并募集配套资金暨关联交易（非公开发行股份募集配套资金）的通知"),
              ("bond", "关于终止审查公司公开发行可转换公司债券申请的通知"), ("none", None))}
    check(f"a review notice naming no offering in its title is read from its text ({notice})",
          notice == {"offering": "an offering", "restructuring": "not an offering", "bond": "not an offering", "none": "not read"})

    def ag(code, day, meeting=None, state="locked", cls="agreement signed", prices=(5.0,), aid=None, title=""):
        return {"id": aid or f"{code}{day}{meeting}{cls}{prices}", "code": code, "name": "测试", "day": day, "cls": cls, "state": state,
                "meeting": meeting, "prices": list(prices), "base_day": None, "title": title}

    d = dt.date
    signings = [ag("000001", d(2021, 1, 5), "第一届董事会第一次会议"), ag("000001", d(2021, 3, 1), "第一届董事会第一次会议"),
                ag("000001", d(2021, 4, 1), "第一届董事会第五次会议", prices=(6.0,)), ag("000001", d(2022, 6, 1), None, prices=(4.0,)),
                ag("000001", d(2022, 7, 1), None, state="first day"), ag("000001", d(2022, 7, 2), None, cls="agreement supplemented", prices=(4.0,)),
                ag("000002", d(2021, 1, 5), None, state="price fixed, base not read"), ag("000003", d(2021, 2, 1), cls="plan document")]
    plans = group_plans(signings)
    check(f"plans split on a new board meeting and on a gap of more than 180 days, take plan documents and supplements, and skip "
          f"first-day and other states ({[(p['code'], p['b'].isoformat(), len(p['agreements']), p['routes']) for p in plans]})",
          [(p["code"], p["b"], len(p["agreements"]), p["routes"]) for p in plans]
          == [("000001", d(2021, 1, 5), 2, ["agreement"]), ("000001", d(2021, 4, 1), 1, ["agreement"]),
              ("000001", d(2022, 6, 1), 2, ["agreement", "supplement"]),
              ("000002", d(2021, 1, 5), 1, ["agreement"]), ("000003", d(2021, 2, 1), 1, ["plan document"])])
    grouped = group_plans([ag("000016", d(2020, 5, 1)), ag("000016", d(2020, 8, 31), "第四届董事会第六十五次会议"),
                           ag("000017", d(2021, 1, 1), "第一届董事会第一次会议"), ag("000017", d(2021, 9, 1), "第一届董事会第一次会议", prices=(5.5,)),
                           ag("000018", d(2021, 2, 5), "第四届董事会第七次会议", cls="agreement supplemented"),
                           ag("000018", d(2021, 5, 29), "第四届董事会第七次会议", cls="agreement supplemented"),
                           ag("000020", d(2020, 6, 29), None, prices=(9.41,)), ag("000020", d(2021, 1, 9), "第五届董事会第三十次会议", prices=(9.41,)),
                           ag("000021", d(2020, 8, 31), None, prices=(5.84,)), ag("000021", d(2021, 10, 22), None, cls="agreement supplemented", prices=(5.5,)),
                           ag("000022", d(2023, 6, 19), "第六届董事会第九次会议", prices=(8.94,)),
                           ag("000022", d(2024, 3, 12), "第六届董事会第二十三次会议", cls="agreement supplemented", prices=(7.05,))]
                           + [ag("000023", d(2020, 9, 15), "第三届董事会第二十八次会议", prices=(36.05,)),
                              ag("000023", d(2020, 12, 1), None, cls="agreement supplemented", prices=(36.0,)),
                              ag("000024", d(2020, 3, 1), None, prices=(3.0,)), ag("000024", d(2020, 11, 1), None, cls="agreement supplemented", prices=(3.1,))],
                          breaks={"000016": [(d(2020, 6, 2), "plan ended")], "000017": [(d(2020, 12, 1), "plan ended")],
                                  "000023": [(d(2020, 9, 23), "application withdrawn"), (d(2020, 9, 30), "earlier plan ended")],
                                  "000024": [(d(2020, 9, 28), "application withdrawn")]})
    link_plans(grouped, {}, d(2026, 9, 16))
    relocked = [(p["code"], p["outcome"]) for p in grouped if p["code"] == "000022"]
    check(f"a termination between documents starts a plan unless it is a notice or an earlier plan's end within 30 days of the plan's "
          f"first document, the same board meeting or a price already named joins documents across any "
          f"gap, a supplement naming no other meeting joins, a supplement naming another meeting and price re-locks the plan before it "
          f"({[(p['code'], p['b'].isoformat(), len(p['agreements']), p['routes']) for p in grouped]}, {relocked})",
          relocked == [("000022", "re-locked on a new base date"), ("000022", "pending")] and
          [(p["code"], p["b"], len(p["agreements"]), p["routes"]) for p in grouped]
          == [("000016", d(2020, 5, 1), 1, ["agreement"]), ("000016", d(2020, 8, 31), 1, ["agreement"]),
              ("000017", d(2021, 1, 1), 2, ["agreement"]), ("000018", d(2021, 2, 5), 2, ["supplement"]),
              ("000020", d(2020, 6, 29), 2, ["agreement"]), ("000021", d(2020, 8, 31), 2, ["agreement", "supplement"]),
              ("000022", d(2023, 6, 19), 1, ["agreement"]), ("000022", d(2024, 3, 12), 1, ["supplement"]),
              ("000023", d(2020, 9, 15), 2, ["agreement", "supplement"]),
              ("000024", d(2020, 3, 1), 1, ["agreement"]), ("000024", d(2020, 11, 1), 1, ["supplement"])])
    merged = merge_days([(d(2023, 3, 1), {"x": 1}), (d(2023, 3, 10), {"x": 2}), (d(2023, 3, 24), {"x": 3}), (d(2023, 5, 1), {"x": 4})])
    check(f"announcements within 15 days of the previous one merge, chained ({[(m[0].isoformat(), len(m[1])) for m in merged]})",
          [(m[0], len(m[1])) for m in merged] == [(d(2023, 3, 1), 3), (d(2023, 5, 1), 1)])

    def row(code, day, title, aid):
        ms = int(dt.datetime(day.year, day.month, day.day, 12, tzinfo=P.CHINA).timestamp() * 1000)
        return {"secCode": code, "secName": "测试", "announcementId": aid, "announcementTitle": title, "announcementTime": ms}

    def issue(code, day, way_state=None, n=1):
        s = {"SECURITY_CODE": code, "ISSUE_DATE": f"{day.isoformat()} 00:00:00", "ISSUE_NUM": n, "ISSUE_PRICE": 5.0}
        if way_state:
            s["PRICED_STATE"] = way_state
        return s

    classes = {"agreement ended": [row("000001", d(2021, 2, 1), "t", "e1"), row("000006", d(2020, 6, 1), "t", "e6")],
               "plan ended": [row("000001", d(2021, 3, 20), "关于终止非公开发行股票事项的公告", "p1"),
                              row("000007", d(2020, 5, 1), "关于终止前次非公开发行股票事项的公告", "p7")],
               "review ended, offering not named": [row("000012", d(2021, 5, 1), "t", "n12"), row("000012", d(2021, 8, 1), "t", "n12b")],
               "base date or price adjusted": [row("000015", d(2026, 6, 10), "t", "a15"), row("000015", d(2026, 5, 10), "t", "a15b")],
               "review ended": [row("000019", d(2021, 5, 20), "t", "r19"), row("000019", d(2022, 5, 20), "t", "r19b")]}
    classes["plan ended"].append(row("000019", d(2021, 4, 10), "关于终止前次非公开发行股票事项的公告", "p19"))
    classes["review ended"].append(row("000025", d(2020, 4, 21), "关于收到中国证监会终止审查公司原2019年非公开发行A股股票申请通知书的公告", "r25"))
    classes["application withdrawn"] = [row("000026", d(2022, 1, 12), "关于深圳证券交易所同意公司撤回向特定对象发行股票申请文件的公告", "w26"),
                                        row("000027", d(2022, 2, 16), "关于深圳证券交易所同意公司撤回向特定对象发行股票申请文件的公告", "w27")]
    texts = {"n12": "关于终止审查公司发行股份购买资产暨关联交易申请的通知", "n12b": "关于终止审查公司非公开发行股票申请的通知",
             "a15": moved, "a15b": dividend}
    priced = [issue("000001", d(2021, 9, 1), "cash"), issue("000001", d(2023, 1, 1), "cash by its text, proceeds not printed"),
              issue("000008", d(2025, 6, 1), "cash"), issue("000011", d(2021, 5, 1), "for assets"),
              issue("000011", d(2021, 6, 1), "cash by its text, proceeds not printed")]
    bids = [issue("000004", d(2022, 1, 1)), issue("000005", d(2020, 12, 1))]
    docs = [row("000004", d(2021, 6, 1), "2021年度非公开发行A股股票预案", "doc4"), row("000006", d(2020, 3, 1), "2020年度非公开发行A股股票预案", "doc6"),
            row("000009", d(2021, 1, 15), "2021年度非公开发行A股股票预案", "doc9"), row("000013", d(2020, 3, 20), "2020年度非公开发行A股股票预案", "doc13"),
            row("000014", d(2020, 6, 1), "2020年度非公开发行A股股票预案", "doc14"),
            row("000002", d(2026, 9, 18), "2026年度向特定对象发行A股股票预案", "doc2")]
    priced.append(issue("000013", d(2020, 10, 1), "cash"))
    priced.append(issue("000015", d(2026, 7, 24), "cash"))
    events, notices = build_events(classes, texts, priced, bids, docs)
    kinds = {c: [k for _, k, _ in evs] for c, evs in sorted(events.items())}
    check(f"events: a termination naming only an earlier plan, notices read from their text, issues by what their text prices, bids and "
          f"plan documents ({kinds}, {dict(notices)})",
          kinds["000007"] == ["earlier plan ended"] and kinds["000012"] == ["review ended"] and dict(notices) == {"not an offering": 1, "an offering": 1, "confirms a termination 30-59 days before": 1}
          and kinds["000011"] == ["issued, not a cash placement", "issued"] and kinds["000005"] == ["issued by bids"]
          and kinds["000004"] == ["plan document", "issued by bids"] and kinds["000006"] == ["plan document", "subscriber exit"]
          and kinds["000015"] == ["moved to first day", "issued"] and kinds["000019"] == ["earlier plan ended", "review ended"]
          and kinds["000025"] == ["earlier plan ended"] and kinds["000026"] == ["application withdrawn"])
    plans = group_plans(signings[:4] + [ag("000002", d(2021, 1, 5)), ag("000004", d(2020, 3, 1)), ag("000005", d(2020, 3, 1)),
                                        ag("000006", d(2020, 3, 1)), ag("000007", d(2020, 3, 1)), ag("000008", d(2020, 3, 1)),
                                        ag("000009", d(2020, 3, 1)), ag("000009", d(2021, 3, 1), "第二届董事会第一次会议", prices=(6.0,)),
                                        ag("000011", d(2021, 1, 1)), ag("000012", d(2021, 1, 1)), ag("000013", d(2020, 3, 1)),
                                        ag("000014", d(2020, 5, 2), "第一届董事会第二次会议"), ag("000014", d(2020, 9, 9), "第一届董事会第六次会议", prices=(6.0,)),
                                        ag("000015", d(2025, 4, 29)), ag("000019", d(2021, 4, 10)), ag("000026", d(2022, 1, 7)),
                                        ag("000027", d(2022, 1, 7)), ag("000028", d(2026, 9, 20))])
    link_plans(plans, events, d(2026, 9, 16))
    got = {(p["code"], p["b"].isoformat()): (p["outcome"], p["t"].isoformat(), len(p["exits"]), len(p["documents"])) for p in plans}
    want = {("000001", "2021-01-05"): ("plan ended", "2021-03-20", 1, 0), ("000001", "2021-04-01"): ("issued", "2021-09-01", 0, 0),
            ("000001", "2022-06-01"): ("issued", "2023-01-01", 0, 0), ("000002", "2021-01-05"): ("pending", "2026-09-16", 0, 0),
            ("000004", "2020-03-01"): ("new plan", "2021-06-01", 0, 0), ("000005", "2020-03-01"): ("issued by bids", "2020-12-01", 0, 0),
            ("000006", "2020-03-01"): ("subscribers exited", "2020-06-01", 1, 1), ("000007", "2020-03-01"): ("pending", "2026-09-16", 0, 0),
            ("000008", "2020-03-01"): ("issued", "2025-06-01", 0, 0), ("000009", "2020-03-01"): ("new locked plan", "2021-01-15", 0, 0),
            ("000009", "2021-03-01"): ("pending", "2026-09-16", 0, 1), ("000011", "2021-01-01"): ("issued", "2021-06-01", 0, 0),
            ("000012", "2021-01-01"): ("review ended", "2021-08-01", 0, 0), ("000013", "2020-03-01"): ("issued", "2020-10-01", 0, 1),
            ("000014", "2020-05-02"): ("new locked plan", "2020-09-09", 0, 1), ("000014", "2020-09-09"): ("pending", "2026-09-16", 0, 0),
            ("000015", "2025-04-29"): ("moved to first day", "2026-06-10", 0, 0), ("000019", "2021-04-10"): ("review ended", "2022-05-20", 0, 0),
            ("000026", "2022-01-07"): ("pending", "2026-09-16", 0, 0), ("000027", "2022-01-07"): ("application withdrawn", "2022-02-16", 0, 0)}
    wrong = {k: (got.get(k), v) for k, v in want.items() if got.get(k) != v}
    moved_then = [(p["then"][0].isoformat(), p["then"][1]) for p in plans if p["code"] == "000015" and p.get("then")]
    if moved_then != [("2026-07-24", "issued")]:
        wrong["000015 then"] = moved_then
    check(f"each plan takes the first end after it and on or before a later plan, its own plan document (the nearest plan's) is no later "
          f"plan, an end five years on still counts, exits end a plan with nothing else, an issue for assets ends none, and a document "
          f"after the data end starts no plan and ends none (wrong: {wrong})",
          not wrong and len(got) == len(want))
    covered_docs = [row("100010", d(2021, 3, 1), "预案", "u1"), row("100011", d(2021, 3, 1), "预案", "u2"),
                    row("100012", d(2021, 3, 1), "预案", "u3"), row("100013", d(2021, 3, 1), "预案", "u4"),
                    row("100014", d(2026, 9, 20), "预案", "u5")]
    near = [ag("100010", d(2021, 3, 1), state="not read"), ag("100011", d(2021, 3, 1), state="locked"),
            ag("100012", d(2021, 3, 5), state="first day"), ag("100013", d(2020, 1, 1), state="locked")]
    wanted = unread_plans(covered_docs, near)
    check(f"a plan document up to the data end is wanted when the agreements near it read neither a locked price nor first-day pricing "
          f"({[(r['secCode'], st) for r, st in wanted]})",
          [(r["secCode"], st) for r, st in wanted] == [("100010", ["not read"]), ("100013", [])])
    ks = [known_state({"PRICE_PRINCIPLE": t}) for t in ("本次发行股份募集配套资金的定价基准日为公司第四届董事会第二十六次会议决议公告日。",
                                                        "本次非公开发行的定价基准日为发行期首日。发行价格不低于定价基准日前二十个交易日股票交易均价的90%。",
                                                        "本次非公开发行股票的定价基准日为公司第八届董事会第十三次会议决议的公告日,发行价格为22.73元/股。")]
    check(f"a completed placement's pricing text tells matching funds and first-day pricing from a locked placement ({ks})",
          ks == ["matching funds of an asset deal", "priced on the first day of the offering", "a locked cash placement"])
    one = {"prices": [3.0, 5.0, 7.5], "outcome": "issued", "detail": {"P": "4.95"}}
    check("the issue price is set against the nearest price the document names", abs(price_ratio(one) - 0.99) < 1e-12)

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "pdf").mkdir()
        for name, body in (("1", b"a"), ("2", b"bb")):
            (root / "pdf" / f"{name}.pdf").write_bytes(body)
        calls = []

        def reader(path):
            calls.append(path.name)
            return f"text of {path.name}"

        cache = root / "cache.jsonl.gz"
        first_read, c1 = text_cache(["1", "2", "3"], root / "pdf", cache, reader)
        again, c2 = text_cache(["1", "2"], root / "pdf", cache, reader)
        os.utime(root / "pdf" / "2.pdf", (1, 1))
        third, c3 = text_cache(["1", "2"], root / "pdf", cache, reader)
        check(f"PDF text is read once, kept, and read again only for a PDF whose size or time changed ({c1}, {c2}, {c3}, calls {calls})",
              first_read == {"1": "text of 1.pdf", "2": "text of 2.pdf"} and c1 == {"read": 2, "no PDF": 1}
              and c2 == {"cached": 2} and c3 == {"cached": 1, "read": 1} and calls == ["1.pdf", "2.pdf", "2.pdf"] and third == first_read)

    print(f"\n{'selftest passed' if not fails else 'selftest FAILED: ' + ', '.join(fails)}")
    return 0 if not fails else 1


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true", help="offline checks only")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    out = P.RAW / f"plans_printout_{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}.txt"
    tee = F.Tee(sys.stdout, out)
    sys.stdout = tee
    try:
        print(f"printout also written to data/raw/b120/{out.name}")
        return report()
    finally:
        sys.stdout = tee.stream
        tee.fh.close()


if __name__ == "__main__":
    sys.exit(main())
