"""B120 fetch: the census of plan ends, and the PDFs that carry each locked plan's price.

**Why this exists.** The probe found that the platform's placement category holds the plans
themselves and very few of the announcements that end them: for 终止 in 2023-03 the category held
1 row, the same query with no category 274, 26 of them about an issue, a subscription or a pricing
base date. So every keyword here is asked with no category and the titles are sorted locally. The
two query settings the probe tried returned the same rows, so one is asked. Ends whose titles carry no
终止 (a lapsed approval or resolution, a withdrawn application, a refusal) come from four more keywords,
each asked page 1 of every month first and past page 1 only when its months hold 9,000 rows or fewer
in all. The plans themselves come from the placement category, where they are.

**What it prints, with no criteria.** Section 1: the title census by class and year, the templates
and a spread of samples in each class. Section 2: two answers known before the run, printed against
the census. The companies the press named among the plans moved to first-day pricing in June and
July 2026 should be in the adjusted class, and each completed locked cash placement in the B110
offering table from 2020-09-01 should have a subscription agreement announcement for the same code
in the three years before its issue day. The ones not found are named. Section 3, with `--pdfs`:
the agreement and adjustment PDFs, then a spread of them read for the pricing base date and the
price. Section 4: the first versions of the plan documents, split by whether an agreement announcement
of the same code falls from 45 days before to 120 days after; with `--plan-pdfs` the PDFs of those
without one, and of a spread of 60 with one to check the reading, are fetched. Section 5: cost.

**What it writes.** Nothing under `results/`. Pages and PDFs land under `data/raw/b120/`, as the
probe's do, and the probe's cache is reused. Every run but `--plan` and `--selftest` also writes its
printout to `data/raw/b120/printout_<time>.txt`. `--offline` reads the cache only: it sends no
request, asks no recent window again and adds nothing to the request log, so it prints what the
last run read.

    python experiments/b120_fetch.py --selftest
    python experiments/b120_fetch.py --plan         # offline: windows cached, windows left, minutes left
    python experiments/b120_fetch.py                # sections 1, 2 and 4
    python experiments/b120_fetch.py --pdfs         # and section 3
    python experiments/b120_fetch.py --pdfs --plan-pdfs   # and the plan documents of section 4
    python experiments/b120_fetch.py --pdfs --offline   # the same printout again, from the cache

The network part runs on a machine whose connection reaches www.cninfo.com.cn.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import math
import re
import statistics
import sys
from pathlib import Path

import b120_probe as P

CENSUS = (("终止", P.START, None), ("认购协议", P.START, None), ("定价基准日", P.START, None),
          ("调整", dt.date(2026, 5, 1), dt.date(2026, 8, 31)))
# Ends that carry no 终止 in their title: a lapsed approval or resolution, a withdrawn application, a refusal.
# Each is asked page 1 of every month first; a keyword whose months hold more rows than EXTRA_ROW_CAP in all
# is too broad to be read as a title census and is not asked past page 1 (printed as a gap, with its size).
EXTRA = (("失效", P.START, None), ("撤回", P.START, None), ("不予", P.START, None), ("否决", P.START, None))
EXTRA_ROW_CAP = 9000
# The plans themselves. The placement category holds them (the probe: 10,879 rows, 2,452 companies).
PLAN_KEYWORD = ("预案", P.START, None)
SETTING = ("szse", "")
FETCH_DELAY = 0.6

PLACEMENT = re.compile(r"向(?:[一二三四五六七八九十\d]+名)?特定对象发|非公开发|定向增发|定向发行")
NOT_PLACEMENT = re.compile(r"不特定对象|可转换|可转债|公司债|债券|H股|存托凭证|GDR|首次公开发行|配股|募投项目|募集资金投资项目|"
                           r"募集资金用途|结余募集资金|信用评级|员工持股|股权激励|限制性股票|购买资产|重大资产|重组|吸收合并|"
                           r"分拆|优先股|配套|简易程序|基金份额|合伙协议|认购[^，。；]{0,6}?基金|收益凭证|理财|意向书|优先认购权|"
                           r"转增|限售|上市流通|增资|对外投资")
AGREEMENT = re.compile(r"认购[^，。；]{0,16}?(?:协议|合同)|(?:非公开发行|向特定对象发行)(?:A股)?股(?:份|票)(?:之)?协议")
# A company announcing its own subscription to another company's offering names that company between 认购 and the offering.
SUBSCRIBER_SIDE = re.compile(r"认购(?!本次|公司|本公司|上市公司|甲方|新增|非公开|特定对象|向)[^，。；《》“”、的与及签对人方暨之]{2,24}?"
                             r"(?:非公开发行|向特定对象发行|定向增发|发行的?(?:A股)?股(?:票|份))")
# 终止 governing the offering itself, not a termination agreement with one subscriber.
_OFFER = r"(?:非公开发|向(?:[一二三四五六七八九十\d]+名)?特定对象发|定向增发|定向发行)"
PLAN_END = re.compile(r"终止[^，。；《》]{0,20}?" + _OFFER + r"|" + _OFFER + r"(?:(?!协议|合同)[^，。；《》]){0,24}?终止(?!协议|合同)")
REVIEW_NOTICE = re.compile(r"终止审查|注册程序终止|终止注册")
OTHER_RECEIVER = re.compile(r"关于(?!公司|本公司)[^收关]{2,30}?收到")
LAPSED = re.compile(r"(?:批复|批文|核准|注册|决议|有效期|方案|预案|事项)[^，。；]{0,12}?(?:失效|到期|届满)")
REFUSED = re.compile(r"不予(?:核准|注册)|未(?:获得?|能)?[^，。；]{0,20}?通过|否决")
CLASSES = ("plan ended", "review ended", "review ended, offering not named", "review refused", "voted down", "plan lapsed",
           "application withdrawn", "agreement ended", "agreement signed", "agreement text", "agreement supplemented",
           "base date or price adjusted", "no-sale undertaking", "subscribes to another company's offering")
PDF_CLASSES = ("agreement signed", "agreement text", "agreement supplemented", "agreement ended", "base date or price adjusted",
               "review ended, offering not named")
PLAN_DOC_SKIP = re.compile(r"修订|更新|摘要|提示|说明|更正|补充|调整|论证分析|可行性|意见|核查|承诺|回报|分红|募集资金使用|取消|失效|稳定股价")
PLAN_DOC_NEAR = (45, 120)
PLAN_DOC_CHECK = 60
WANTED = "plan_documents_wanted.txt"
# Companies the press named among the plans moved to first-day pricing from 2026-06-03 to 2026-07-03.
WAVE_NAMES = ("香山股份", "有研新材", "皖维高新", "法尔胜", "青达环保", "茂化实华", "和远气体", "中颖电子", "爱司凯", "安阳钢铁",
              "蓝丰生化")
WAVE = (dt.date(2026, 6, 1), dt.date(2026, 7, 10))
RECALL_FROM = "2020-09-01"
RECALL_YEARS = 3

BASE_BOARD = re.compile(r"定价基准日[为是][^。；]{0,60}?(董事会|股东大会|股东会)[^。；]{0,40}?决议公告日")
BASE_FIRST = re.compile(r"定价基准日[为是][^。；]{0,20}?发行期的?首日")
PRICE = re.compile(r"(?:发行价格|认购价格|发行价)(?:为|确定为|调整为|由)?[^。；]{0,16}?(\d+(?:\.\d+)?)\s*元\s*/\s*股")


def title_classes(title) -> set[str]:
    """Every class a title falls in; a title can fall in more than one."""
    t = P.clean_title(title)
    subscriber = bool(SUBSCRIBER_SIDE.search(t))
    placement = bool(PLACEMENT.search(t)) and not NOT_PLACEMENT.search(t) and not subscriber
    agreement = bool(AGREEMENT.search(t)) and not NOT_PLACEMENT.search(t) and not subscriber
    ended = bool(re.search(r"终止|解除", t))
    plan_end = bool(PLAN_END.search(t))
    notice = bool(re.search(r"收到|决定|通知书", t)) and bool(re.search(r"审核|注册|审查", t))
    out = set()
    if subscriber and (PLACEMENT.search(t) or AGREEMENT.search(t)):
        out.add("subscribes to another company's offering")
    if (REVIEW_NOTICE.search(t) and not PLACEMENT.search(t) and not NOT_PLACEMENT.search(t) and not OTHER_RECEIVER.search(t)
            and re.search(r"收到|通知书|决定", t)):
        out.add("review ended, offering not named")
    if placement and not plan_end and REFUSED.search(t) and not re.search(r"尚未|风险", t):
        out.add("voted down" if re.search(r"股东大会|股东会", t) else "review refused")
    if placement and not plan_end and LAPSED.search(t) and not re.search(r"延长|延期|即将", t):
        out.add("plan lapsed")
    if placement and not plan_end and "撤回" in t and not re.search(r"重新|再次", t):
        out.add("application withdrawn")
    if plan_end and placement and not notice:
        out.add("plan ended")
    if "终止" in t and placement and notice:
        out.add("review ended")
    if agreement and ended:
        out.add("agreement ended")
    if agreement and not ended and re.search(r"补充", t):
        out.add("agreement supplemented")
    if agreement and not ended and not re.search(r"补充", t):
        out.add("agreement signed" if re.search(r"签署|签订|签定|订立|公告", t) else "agreement text")
    if placement and re.search(r"调整|修订|变更", t) and re.search(r"定价基准日|发行价格|定价", t):
        out.add("base date or price adjusted")
    if "定价基准日" in t and "减持" in t:
        out.add("no-sale undertaking")
    return out


def window_rows(root: Path, kw: str, w0: dt.date, w1: dt.date, today: dt.date, network: bool, category: bool = False,
                max_pages: int | None = None) -> tuple[list[dict], str, int | None]:
    """One keyword's rows in one month, the state, and the total the platform reported on page 1."""
    first = P.cache_path(root, kw, category, *SETTING, w0, w1, 1)
    if not network and not first.exists():
        # the month still open when the last run asked it is cached under that run's day
        ends = sorted(x.name.split("_")[1] for x in first.parent.glob(f"{w0.isoformat()}_*_p001.json"))
        if not ends:
            return [], "not cached", None
        w1 = dt.date.fromisoformat(ends[-1])
        first = P.cache_path(root, kw, category, *SETTING, w0, w1, 1)
    rows, state = P.fetch_window(root, kw, w0, w1, category, *SETTING, today, max_pages=max_pages)
    total = None
    if first.exists():
        try:
            total = int(json.loads(first.read_text(encoding="utf-8"))["totalAnnouncement"])
        except (ValueError, KeyError, TypeError):
            total = None
    return rows, state, total


def census(root: Path, today: dt.date, network: bool = True) -> tuple[dict, list]:
    """announcementId -> row over every census keyword, and the windows that did not come back whole."""
    bag, gaps = {}, []
    for kw, start, end in CENSUS:
        for w0, w1 in P.month_windows(start, min(end or today, today)):
            rows, state, _ = window_rows(root, kw, w0, w1, today, network)
            if state != "ok":
                gaps.append((kw, w0.isoformat(), state))
            for r in rows:
                bag[str(r["announcementId"])] = r
        print(f"  {kw}: {len(bag)} rows so far", flush=True)
    return bag, gaps


def extra_census(root: Path, today: dt.date, network: bool = True, cap: int = EXTRA_ROW_CAP) -> tuple[dict, list, dict]:
    """The extra keywords: page 1 of every month first, then the other pages of a keyword whose months hold `cap` rows or fewer."""
    bag, gaps, sizes = {}, [], {}
    for kw, start, end in EXTRA:
        windows, totals = P.month_windows(start, min(end or today, today)), {}
        for w0, w1 in windows:
            rows, state, total = window_rows(root, kw, w0, w1, today, network, max_pages=1)
            if state != "ok" or total is None:
                gaps.append((kw, w0.isoformat(), state if state != "ok" else "no total on page 1"))
                continue
            totals[(w0, w1)] = total
            for r in rows:
                bag[str(r["announcementId"])] = r
        size = sum(totals.values())
        sizes[kw] = {"rows": size, "months": len(totals), "pages": sum(math.ceil(t / P.PAGE_SIZE) for t in totals.values())}
        if size > cap:
            gaps.append((kw, "all months", f"{size} rows is more than {cap}: page 1 of each month only"))
        else:
            for (w0, w1), total in totals.items():
                if total <= P.PAGE_SIZE:
                    continue
                rows, state, _ = window_rows(root, kw, w0, w1, today, network)
                if state != "ok":
                    gaps.append((kw, w0.isoformat(), state))
                for r in rows:
                    bag[str(r["announcementId"])] = r
        print(f"  {kw}: {size} rows over {len(totals)} months{'' if size <= cap else ', more than the cap: page 1 only'}", flush=True)
    return bag, gaps, sizes


def plan_rows(root: Path, today: dt.date, network: bool = True) -> tuple[dict, list]:
    """The plans themselves, from the placement category."""
    kw, start, end = PLAN_KEYWORD
    bag, gaps = {}, []
    for w0, w1 in P.month_windows(start, min(end or today, today)):
        rows, state, _ = window_rows(root, kw, w0, w1, today, network, category=True)
        if state != "ok":
            gaps.append((kw, w0.isoformat(), state))
        for r in rows:
            bag[str(r["announcementId"])] = r
    print(f"  {kw} (placement category): {len(bag)} rows", flush=True)
    return bag, gaps


def plan_documents(rows) -> list[dict]:
    """First versions of placement plans: a plan (预案) for an offering to named or unnamed subscribers; not a revision,
    summary, notice, opinion or analysis."""
    out = []
    for r in rows:
        t = P.clean_title(r["announcementTitle"])
        if ("预案" in t and PLACEMENT.search(t) and not NOT_PLACEMENT.search(t) and not SUBSCRIBER_SIDE.search(t)
                and not PLAN_DOC_SKIP.search(t)):
            out.append(r)
    return sorted(out, key=lambda r: (int(r["announcementTime"]), str(r["announcementId"])))


def split_plan_documents(docs: list[dict], classes: dict, near: tuple[int, int] = PLAN_DOC_NEAR) -> tuple[list[dict], list[dict]]:
    """Plan documents with no agreement announcement of the same code from near[0] days before to near[1] days after,
    and those with one."""
    days = collections.defaultdict(list)
    for c in ("agreement signed", "agreement text", "agreement supplemented", "agreement ended"):
        for r in classes.get(c, []):
            days[str(r["secCode"])].append(P.day_of(r))
    uncovered, covered = [], []
    for r in docs:
        d = P.day_of(r)
        lo, hi = d - dt.timedelta(days=near[0]), d + dt.timedelta(days=near[1])
        (covered if any(lo <= x <= hi for x in days.get(str(r["secCode"]), [])) else uncovered).append(r)
    return uncovered, covered


def by_class(rows) -> dict:
    out = collections.defaultdict(list)
    for r in rows:
        for c in title_classes(r["announcementTitle"]):
            out[c].append(r)
    return out


def wave_check(adjusted: list[dict], names=WAVE_NAMES, window=WAVE) -> tuple[list[str], list[str], int]:
    inside = [r for r in adjusted if window[0] <= P.day_of(r) <= window[1]]
    seen = {str(r["secName"]).replace(" ", "") for r in inside}
    found = [n for n in names if n in seen]
    return found, [n for n in names if n not in seen], len({r["secCode"] for r in inside})


def recall_check(offerings: list[dict], agreements: list[dict], years: int = RECALL_YEARS) -> tuple[list[dict], list[dict]]:
    """Offerings with a subscription agreement announcement for the same code in the `years` before T, and those without."""
    days = collections.defaultdict(list)
    for r in agreements:
        days[str(r["secCode"])].append(P.day_of(r))
    found, missed = [], []
    for s in offerings:
        T = dt.date.fromisoformat(str(s["ISSUE_DATE"])[:10])
        lo = T.replace(year=T.year - years) if not (T.month == 2 and T.day == 29) else T.replace(year=T.year - years, day=28)
        hit = any(lo <= d <= T for d in days.get(str(s["SECURITY_CODE"]), []))
        (found if hit else missed).append(s)
    return found, missed


def completed_locked_cash(since: str = RECALL_FROM) -> list[dict]:
    """The B110 offering table's cash placements priced in advance, issued on or after `since`."""
    import b110_fetch as F110
    import b110_placements as B110
    table = F110.snapshot_on_disk("RPT_SEO_DETAIL")
    if table is None:
        return []
    out = []
    for s in table["rows"]:
        if str(s.get("SEO_TYPE")) != "1" or s.get("ISSUE_WAY") != B110.PRICED_WAY or str(s.get("ISSUE_DATE") or "")[:10] < since:
            continue
        o = {"principle": s.get("PRICE_PRINCIPLE") or "", "gross": B110.num(s.get("TOTAL_RAISE_FUNDS")),
             "net": B110.num(s.get("NET_RAISE_FUNDS"))}
        if B110.priced_state(o) == "cash":
            out.append(s)
    return out


def flat_text(text: str) -> str:
    """PDF lines break inside sentences; join them before reading a clause."""
    return re.sub(r"[ \t\r\n　]+", "", text)


def read_terms(text: str) -> dict:
    t = flat_text(text)
    board, first = bool(BASE_BOARD.search(t)), bool(BASE_FIRST.search(t))
    base = "both" if board and first else "board or shareholder resolution date" if board else "first day of the offering" if first else "none"
    prices = sorted({float(m.group(1)) for m in PRICE.finditer(t)})
    clause = next((m.group(0) for m in (BASE_BOARD.search(t), BASE_FIRST.search(t)) if m), "")
    return {"base": base, "prices": prices, "clause": clause[:120]}


def print_census(bag: dict, gaps: list, sizes: dict | None = None) -> dict:
    rows = sorted(bag.values(), key=lambda r: (int(r["announcementTime"]), str(r["announcementId"])))
    classes = by_class(rows)
    print(f"\n== 1. census: {len(rows)} announcements from the keywords {[k for k, _, _ in CENSUS + EXTRA]}, no category")
    for kw, size in (sizes or {}).items():
        print(f"  {kw}: {size['rows']} rows over {size['months']} months, {size['pages']} pages"
              f"{'' if size['rows'] <= EXTRA_ROW_CAP else f'; more than {EXTRA_ROW_CAP}, page 1 of each month only'}")
    for g in gaps[:15]:
        print(f"  gap: {g}")
    if len(gaps) > 15:
        print(f"  gaps: {len(gaps)} in all")
    unclassed = [r for r in rows if not title_classes(r["announcementTitle"])]
    print(f"  in no class: {len(unclassed)}")
    for c in CLASSES:
        rs = classes.get(c, [])
        years = collections.Counter(P.day_of(r).year for r in rs)
        print(f"\n  {c}: {len(rs)} announcements, {len({r['secCode'] for r in rs})} companies; by year {dict(sorted(years.items()))}")
        for t, n in collections.Counter(P.template(r["announcementTitle"]) for r in rs).most_common(12):
            print(f"    {n:5d}  {t[:100]}")
        for r in P.pick_spread(rs, 6):
            print(f"      {r['secCode']} {r['secName']} {P.day_of(r)} {P.clean_title(r['announcementTitle'])[:80]}")
    both = collections.Counter(tuple(sorted(title_classes(r["announcementTitle"]))) for r in rows)
    print("\n  titles in two classes or more:")
    for k, n in both.most_common():
        if len(k) > 1:
            print(f"    {n:5d}  {k}")
    return classes


def print_known(classes: dict) -> None:
    print("\n== 2. answers known before the run")
    found, missing, companies = wave_check(classes.get("base date or price adjusted", []))
    print(f"  plans adjusted from {WAVE[0]} to {WAVE[1]}: {companies} companies (the press counted about 40); of the "
          f"{len(WAVE_NAMES)} it named, found {len(found)}: {found}; not found: {missing}")
    offerings = completed_locked_cash()
    if not offerings:
        print("  the B110 offering table is not on this disk; the recall of completed placements is not read")
        return
    agreements = [r for c in ("agreement signed", "agreement text", "agreement supplemented") for r in classes.get(c, [])]
    hit, missed = recall_check(offerings, agreements)
    print(f"  completed locked cash placements issued from {RECALL_FROM}: {len(offerings)}; with an agreement announcement for the "
          f"same code in the {RECALL_YEARS} years before T {len(hit)}, without {len(missed)}")
    by_year = collections.Counter(str(s['ISSUE_DATE'])[:4] for s in missed)
    print(f"    without, by year of T: {dict(sorted(by_year.items()))}")
    for s in sorted(missed, key=lambda s: s["ISSUE_DATE"])[:40]:
        print(f"    {s['SECURITY_CODE']} {s['SECURITY_NAME_ABBR']} T {str(s['ISSUE_DATE'])[:10]} P {s['ISSUE_PRICE']} "
              f"to {str(s.get('ISSUE_OBJECT') or '')[:30]}")


def print_pdfs(root: Path, classes: dict, sample: int) -> None:
    pool = {}
    for c in PDF_CLASSES:
        for r in classes.get(c, []):
            pool[str(r["announcementId"])] = r
    rows = sorted(pool.values(), key=lambda r: int(r["announcementTime"]))
    have = sum(1 for r in rows if (root / "pdf" / f"{r['announcementId']}.pdf").exists())
    log = P.read_request_log(root).get("pdf", {"ok": []})["ok"]
    per = statistics.median(s for s, _ in log) + FETCH_DELAY if log else 2.0
    print(f"\n== 3. PDFs of {PDF_CLASSES}: {len(rows)}, on disk {have}, to fetch {len(rows) - have}, "
          f"about {(len(rows) - have) * per / 60:.0f} minutes at {per:.2f}s each", flush=True)
    states = collections.Counter()
    for i, r in enumerate(rows):
        path, state = P.fetch_pdf(root, r)
        states[state if path is not None else "refused"] += 1
        if (i + 1) % 100 == 0:
            print(f"  {i + 1} of {len(rows)}: {dict(states)}", flush=True)
    print(f"  done: {dict(states)}")
    print(f"\n  a spread of {sample} read for the base date and the price:")
    for r in P.pick_spread([r for r in rows if (root / 'pdf' / f"{r['announcementId']}.pdf").exists()], sample):
        text, pages = P.pdf_text(root / "pdf" / f"{r['announcementId']}.pdf")
        head = f"    {r['secCode']} {r['secName']} {P.day_of(r)} {P.clean_title(r['announcementTitle'])[:70]}"
        if text is None:
            print(f"{head}\n      no text: PyMuPDF is not installed")
            continue
        terms = read_terms(text)
        print(f"{head}\n      {pages} pages; base {terms['base']}; prices {terms['prices']}; {terms['clause']}")


def print_plan_documents(root: Path, plans: dict, classes: dict, fetch: bool, check: int = PLAN_DOC_CHECK, sample: int = 24) -> None:
    docs = plan_documents(plans.values())
    uncovered, covered = split_plan_documents(docs, classes)
    checks = P.pick_spread(covered, check)
    print(f"\n== 4. plan documents (first versions): {len(docs)} of {len(plans)} rows in the category; with an agreement announcement "
          f"of the same code from {PLAN_DOC_NEAR[0]} days before to {PLAN_DOC_NEAR[1]} days after {len(covered)}, without {len(uncovered)}")
    years = collections.Counter(P.day_of(r).year for r in uncovered)
    print(f"  without, by year: {dict(sorted(years.items()))}")
    wanted = [plans[i] for i in wanted_ids(root) if i in plans]
    print(f"  wanted by b120_plans.py (agreements near them read no pricing base date): {len(wanted)} listed and in the category")
    pool = {str(r["announcementId"]): r for r in uncovered + checks + wanted}
    rows = sorted(pool.values(), key=lambda r: int(r["announcementTime"]))
    todo = [r for r in rows if not (root / "pdf" / f"{r['announcementId']}.pdf").exists()]
    kb = sum(float(r.get("adjunctSize") or 0) for r in todo)
    log = [(sec, n) for sec, n in P.read_request_log(root).get("pdf", {"ok": []})["ok"] if n > 300_000]
    rate = sum(n for _, n in log) / sum(sec for sec, _ in log) if log else 300_000.0
    print(f"  to read: the {len(uncovered)} without, a spread of {len(checks)} with and the {len(wanted)} wanted, {len(rows)} PDFs; "
          f"on disk {len(rows) - len(todo)}; "
          f"to fetch {len(todo)}, {kb / 1024:.0f} MB, about {(kb * 1024 / rate + len(todo) * FETCH_DELAY) / 60:.0f} minutes "
          f"at {rate / 1000:.0f} KB/s and a {FETCH_DELAY}s pause", flush=True)
    if not fetch:
        print("  not fetched: pass --plan-pdfs")
        return
    states = collections.Counter()
    for i, r in enumerate(rows):
        path, state = P.fetch_pdf(root, r)
        states[state if path is not None else "refused"] += 1
        if (i + 1) % 100 == 0:
            print(f"  {i + 1} of {len(rows)}: {dict(states)}", flush=True)
    print(f"  done: {dict(states)}")
    print(f"\n  a spread of {sample} without an agreement announcement, read for the base date and the price:")
    for r in P.pick_spread([r for r in uncovered if (root / 'pdf' / f"{r['announcementId']}.pdf").exists()], sample):
        text, pages = P.pdf_text(root / "pdf" / f"{r['announcementId']}.pdf")
        head = f"    {r['secCode']} {r['secName']} {P.day_of(r)} {P.clean_title(r['announcementTitle'])[:60]}"
        if text is None:
            print(f"{head}\n      no text: PyMuPDF is not installed")
            continue
        terms = read_terms(text)
        print(f"{head}\n      {pages} pages; base {terms['base']}; prices {terms['prices']}; {terms['clause']}")


def wanted_ids(root: Path) -> list[str]:
    """The plan documents b120_plans.py listed as the place left to read a plan's pricing base date."""
    path = root / WANTED
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        field = line.split("\t", 1)[0].strip()
        if field and not field.startswith("#") and field.isdigit():
            out.append(field)
    return out


def plan(root: Path, today: dt.date) -> int:
    print("== plan, offline")
    total = cached = 0
    for (kw, start, end), category in [(k, False) for k in CENSUS + EXTRA] + [(PLAN_KEYWORD, True)]:
        windows = P.month_windows(start, min(end or today, today))
        have = sum(1 for w0, w1 in windows if P.cache_path(root, kw, category, *SETTING, w0, w1, 1).exists())
        total += len(windows)
        cached += have
        print(f"  {kw}: {len(windows)} month windows, first page cached for {have}")
    log = P.read_request_log(root).get("query", {"ok": []})["ok"]
    per = statistics.median(s for s, _ in log) + FETCH_DELAY if log else 1.5
    print(f"  windows left {total - cached}; the probe's 终止 month without a category took 10 pages, so at most about "
          f"{(total - cached) * 10 * per / 60:.0f} minutes at {per:.2f}s a page")
    return 0


def go_offline():
    """Read the cache only: no request, no recent window asked again, nothing added to the request log.
    Returns the function that undoes it."""
    saved = (P.OPEN, P.WAITS, P.TRIES, P.FRESH_DAYS, P.log_request)

    def refuse(req, timeout):
        raise OSError("offline: no request is sent")

    P.OPEN, P.WAITS, P.TRIES = refuse, (0.0,), 1
    P.FRESH_DAYS = -10 ** 9
    P.log_request = lambda *args, **kwargs: None

    def undo():
        P.OPEN, P.WAITS, P.TRIES, P.FRESH_DAYS, P.log_request = saved

    return undo


class Tee:
    """Writes the printout to the terminal and to a file."""

    def __init__(self, stream, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.stream, self.fh = stream, open(path, "w", encoding="utf-8", newline="\n")

    def write(self, s):
        self.stream.write(s)
        self.fh.write(s)
        return len(s)

    def flush(self):
        self.stream.flush()
        self.fh.flush()


def selftest() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'} {name}")
        if not cond:
            fails.append(name)

    cases = {
        "方盛制药关于终止非公开发行股票事项的公告": {"plan ended"},
        "关于终止2022年度向特定对象发行股票事项并撤回申请文件的公告": {"plan ended"},
        "关于终止2023年度向特定对象发行A股股票并签署相关终止协议的公告": {"plan ended"},
        "关于收到深圳证券交易所《关于终止对公司申请向特定对象发行股票审核决定》的公告": {"review ended"},
        "新城控股关于终止2016年度非公开发行A股股票事项并不再向证券交易所提交发行上市注册申请文件的公告": {"plan ended"},
        "新城控股关于与特定对象签署附生效条件的股份认购协议之终止协议暨关联交易的公告": {"agreement ended"},
        "关于与特定对象签订附条件生效的股份认购协议的公告": {"agreement signed"},
        "远大产业控股股份有限公司非公开发行股票之附条件生效的股份认购协议": {"agreement text"},
        "关于与特定对象签署附条件生效的股份认购协议之补充协议的公告": {"agreement supplemented"},
        "关于调整向特定对象发行股票定价基准日及发行价格的公告": {"base date or price adjusted"},
        "关于控股股东本次非公开发行股票定价基准日前六个月至本次发行完成后六个月不存在减持情况或减持计划承诺的公告": {"no-sale undertaking"},
        "关于终止向不特定对象发行可转换公司债券事项的公告": set(),
        "关于终止发行股份及支付现金购买资产并募集配套资金暨关联交易事项的公告": set(),
        "关于终止公司2020年度非公开发行股票部分募投项目并将结余募集资金永久补充流动资金的公告": set(),
        "关于终止公司2023年第一期员工持股计划的公告": set(),
        "关于终止2020年非公开发股票的公告": {"plan ended"},
        "关于签订附条件生效的股份认购暨战略合作协议的公告": {"agreement signed"},
        "关于2021年度向特定对象发行股票股权认购协议的公告": {"agreement signed"},
        "关于与湖北小米长江产业基金合伙企业（有限合伙）签订附条件生效的战略合作协议及股份认购协议的公告": {"agreement signed"},
        "关于终止参与认购罗顿发展非公开发行股票事项暨关联交易的公告": {"subscribes to another company's offering"},
        "公司关于认购英特集团非公开发行股票并签署《股份认购协议》暨关联交易公告": {"subscribes to another company's offering"},
        "关于特定对象认购本次非公开发行股票涉及关联交易的公告": set(),
        "关于收到中国证监会行政许可申请终止审查通知书的公告": {"review ended, offering not named"},
        "关于控股股东收到《证监会行政许可申请终止审查通知书》的公告": set(),
        "关于非公开发行股票批复到期失效的公告": {"plan lapsed"},
        "关于非公开发行股票股东大会决议有效期即将到期并延长有效期的公告": set(),
        "关于非公开发行限售股份上市流通的提示性公告": set(),
        "关于撤回非公开发行股票申请文件的公告": {"application withdrawn"},
        "关于公司非公开发行股票申请未获得中国证监会发行审核委员会审核通过的公告": {"review refused"},
        "关于非公开发行股票相关议案未获股东大会审议通过的公告": {"voted down"},
        "关于终止2023年度以简易程序向特定对象发行股票事项的公告": set(),
        "关于参与认购产业基金份额暨签订合伙协议的公告": set(),
        "关于终止非公开发行股票募集配套资金的公告": set(),
        "关于与张朝益签署非公开发行股票之附条件生效的股票认购协议之终止协议的公告": {"agreement ended"},
        "关于2020年度非公开发行A股股票认购协议终止的公告": {"agreement ended"},
        "关于非公开发行股票事项终止的公告": {"plan ended"},
        "关于2021年非公开发行股票批复到期失效并签署相关终止协议的公告": {"plan lapsed"},
        "关于收到中国证监会终止审查公司原2019年非公开发行A股股票申请通知书的公告": {"review ended"},
        "非公开发行A股股票预案到期失效的公告": {"plan lapsed"},
    }
    wrong = {t: title_classes(t) for t, want in cases.items() if title_classes(t) != want}
    check(f"titles fall in their classes ({len(cases) - len(wrong)} of {len(cases)}; wrong: {wrong})", not wrong)

    def row(code, name, day, title="t"):
        ms = int(dt.datetime(day.year, day.month, day.day, 12, tzinfo=P.CHINA).timestamp() * 1000)
        return {"secCode": code, "secName": name, "announcementId": f"{code}{day:%Y%m%d}", "announcementTitle": title,
                "announcementTime": ms, "adjunctUrl": "x.PDF"}

    adj = [row("600206", "有研新材", dt.date(2026, 6, 13)), row("002513", "蓝丰 生化", dt.date(2026, 6, 10)),
           row("000001", "法尔胜", dt.date(2026, 5, 20))]
    found, missing, companies = wave_check(adj, names=("有研新材", "蓝丰生化", "法尔胜", "皖维高新"))
    check(f"the wave check reads names inside the window only, spaces ignored ({found}, {missing}, {companies})",
          found == ["有研新材", "蓝丰生化"] and missing == ["法尔胜", "皖维高新"] and companies == 2)
    offs = [{"SECURITY_CODE": "600206", "ISSUE_DATE": "2025-06-30 00:00:00"}, {"SECURITY_CODE": "600206", "ISSUE_DATE": "2029-01-02 00:00:00"},
            {"SECURITY_CODE": "000002", "ISSUE_DATE": "2024-02-29 00:00:00"}, {"SECURITY_CODE": "000003", "ISSUE_DATE": "2024-03-01 00:00:00"}]
    ags = [row("600206", "有研新材", dt.date(2024, 9, 1)), row("000002", "x", dt.date(2021, 2, 28)), row("000003", "y", dt.date(2024, 3, 2))]
    hit, missed = recall_check(offs, ags)
    check(f"an agreement counts from three years before T through T ({[s['SECURITY_CODE'] for s in hit]} found)",
          [s["ISSUE_DATE"][:10] for s in hit] == ["2025-06-30", "2024-02-29"]
          and [s["ISSUE_DATE"][:10] for s in missed] == ["2029-01-02", "2024-03-01"])
    text = ("3、本次发行的定价基准日为公司第二届董事会第十九次会议决\n议公告日（2025年9\n月23日）。本次发行的发行\n价格为6.30元/\n股，"
            "不低于定价基准日前20个交易日公司股票交易均价的80%。")
    got = read_terms(text)
    check(f"a clause broken across lines is read whole ({got})",
          got["base"] == "board or shareholder resolution date" and got["prices"] == [6.3])
    first = read_terms("本次向特定对象发行股票的定价基准日为发行期首日，发行价格不低于定价基准日前二十个交易日公司股票交易均价的百分之八十。")
    moved = read_terms("本次发行的定价基准日由“公司第九届董事会第三次会议决议公告日”调整为“发行期首日”，发行价格由“7.05元/股”调整为“不低于”。")
    check(f"first-day pricing reads as first day, and an adjustment that names both reads as neither yet ({first['base']}, {moved})",
          first["base"] == "first day of the offering" and first["prices"] == [] and moved["base"] == "none" and moved["prices"] == [7.05])
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        w0, w1 = dt.date(2026, 9, 1), dt.date(2026, 9, 16)
        page = {"totalAnnouncement": 1, "announcements": [row("600206", "有研新材", dt.date(2026, 9, 3), "关于终止向特定对象发行股票事项的公告")]}
        P.atomic_write_bytes(P.cache_path(root, "终止", False, *SETTING, w0, w1, 1), json.dumps(page, ensure_ascii=False).encode("utf-8"))
        asked = []
        saved_open = P.OPEN
        P.OPEN = lambda req, timeout: asked.append(req) or b""
        undo = go_offline()
        try:
            rows, state = P.fetch_window(root, "终止", w0, w1, False, *SETTING, dt.date(2026, 9, 17))
            path, pstate = P.fetch_pdf(root, {"announcementId": "1", "adjunctUrl": "finalpage/x.PDF"})
        finally:
            undo()
            P.OPEN = saved_open
        check(f"offline, a window that ended yesterday comes from the cache, a missing PDF is not asked for, and the "
              f"request log stays empty ({state}, {len(rows)} rows, {pstate[:30]})",
              state == "ok" and len(rows) == 1 and not asked and path is None and not (root / "request_log.tsv").exists())
        global CENSUS
        saved_census, CENSUS = CENSUS, (("终止", dt.date(2026, 9, 1), None),)
        undo = go_offline()
        try:
            bag, gaps = census(root, dt.date(2026, 9, 17), network=False)
        finally:
            undo()
            CENSUS = saved_census
        check(f"offline the next day, the month the last run asked while it was open is read under that run's day ({len(bag)} rows, gaps {gaps})",
              len(bag) == 1 and gaps == [])
        global EXTRA
        saved_extra, EXTRA = EXTRA, (("失效", dt.date(2021, 1, 1), dt.date(2021, 2, 28)),)
        def put(kw, w0, w1, page, total, n, tag):
            rows_ = [row(f"{700000 + i}", tag, w0 + dt.timedelta(days=i % 20), f"{tag} 关于非公开发行股票批复到期失效的公告")
                     for i in range(n)]
            for i, r in enumerate(rows_):
                r["announcementId"] = f"{tag}{w0:%m}{page}{i}"
            P.atomic_write_bytes(P.cache_path(root, kw, False, *SETTING, w0, w1, page),
                                 json.dumps({"totalAnnouncement": total, "announcements": rows_}, ensure_ascii=False).encode("utf-8"))
        jan, feb = (dt.date(2021, 1, 1), dt.date(2021, 1, 31)), (dt.date(2021, 2, 1), dt.date(2021, 2, 28))
        put("失效", *jan, 1, 45, 30, "a")
        put("失效", *jan, 2, 45, 15, "a")
        put("失效", *feb, 1, 3, 3, "b")
        undo = go_offline()
        try:
            wide, wide_gaps, wide_sizes = extra_census(root, dt.date(2026, 9, 17), network=False, cap=48)
            narrow, narrow_gaps, narrow_sizes = extra_census(root, dt.date(2026, 9, 17), network=False, cap=47)
        finally:
            undo()
            EXTRA = saved_extra
        check(f"an extra keyword is read past page 1 only when its months hold no more rows than the cap "
              f"(cap 48: {len(wide)} rows, gaps {wide_gaps}; cap 47: {len(narrow)} rows, gaps {narrow_gaps}; sizes {narrow_sizes})",
              len(wide) == 48 and wide_gaps == [] and len(narrow) == 33 and len(narrow_gaps) == 1
              and narrow_sizes == {"失效": {"rows": 48, "months": 2, "pages": 3}})
    windows = {kw: len(P.month_windows(s, min(e or dt.date(2026, 9, 17), dt.date(2026, 9, 17)))) for kw, s, e in CENSUS + EXTRA}
    check(f"the census asks 80 month windows for three keywords and 4 for the adjustment months, and 80 for each extra keyword ({windows})",
          windows == {"终止": 80, "认购协议": 80, "定价基准日": 80, "调整": 4, "失效": 80, "撤回": 80, "不予": 80, "否决": 80})
    docs = plan_documents([row("000001", "a", dt.date(2021, 3, 1), "2021年度非公开发行A股股票预案"),
                           row("000002", "b", dt.date(2021, 3, 1), "2021年度向特定对象发行A股股票预案（修订稿）"),
                           row("000003", "c", dt.date(2021, 3, 1), "2021年度向特定对象发行A股股票预案（摘要）"),
                           row("000004", "d", dt.date(2021, 3, 1), "2021年度以简易程序向特定对象发行股票预案"),
                           row("000005", "e", dt.date(2021, 3, 1), "向不特定对象发行可转换公司债券预案"),
                           row("000006", "f", dt.date(2021, 3, 1), "关于非公开发行股票预案披露的提示性公告"),
                           row("000007", "g", dt.date(2021, 3, 1), "深圳某某股份有限公司2021年度非公开发行股票预案"),
                           row("000008", "h", dt.date(2021, 3, 1), "2021年度非公开发行A股股票预案（更新稿）")])
    check(f"plan documents are first versions of a placement plan ({[r['secCode'] for r in docs]})",
          [r["secCode"] for r in docs] == ["000001", "000007"])
    d0 = dt.date(2022, 6, 1)
    plan_docs = [row(c, c, d0, "2022年度非公开发行股票预案") for c in ("100001", "100002", "100003", "100004", "100005")]
    ags = {"agreement signed": [row("100001", "x", d0 - dt.timedelta(days=45)), row("100002", "x", d0 - dt.timedelta(days=46)),
                                row("100005", "x", d0 + dt.timedelta(days=121))],
           "agreement ended": [row("100003", "x", d0 + dt.timedelta(days=120))]}
    uncovered, covered = split_plan_documents(plan_docs, ags)
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / WANTED).write_text("# header\n# columns\n1225561284\t600206\t2026-06-13\tnot read\n\nnot-an-id\tx\n1225561313\t000001\n",
                                        encoding="utf-8")
        got_wanted = wanted_ids(Path(tmp))
        none_wanted = wanted_ids(Path(tmp) / "absent")
    check(f"the wanted list is read by its first field, comments and malformed lines skipped, and an absent list is empty ({got_wanted}, {none_wanted})",
          got_wanted == ["1225561284", "1225561313"] and none_wanted == [])
    check(f"a plan document is covered by an agreement announcement of its code from 45 days before to 120 days after "
          f"(covered {[r['secCode'] for r in covered]}, uncovered {[r['secCode'] for r in uncovered]})",
          [r["secCode"] for r in covered] == ["100001", "100003"] and [r["secCode"] for r in uncovered] == ["100002", "100004", "100005"])
    print(f"\n{'selftest passed' if not fails else 'selftest FAILED: ' + ', '.join(fails)}")
    return 0 if not fails else 1


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true", help="offline: what is cached and what is left")
    ap.add_argument("--pdfs", action="store_true", help="also fetch and read the agreement and adjustment PDFs")
    ap.add_argument("--plan-pdfs", action="store_true", help="also fetch the plan documents no agreement announcement covers")
    ap.add_argument("--offline", action="store_true", help="read the cache only")
    ap.add_argument("--sample", type=int, default=24, help="PDFs read for their terms in section 3")
    ap.add_argument("--selftest", action="store_true", help="offline checks only")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    today = P.TODAY()
    if args.plan:
        return plan(P.RAW, today)
    P.DELAY = FETCH_DELAY
    if args.offline:
        go_offline()
    out = P.RAW / f"printout_{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}{'_offline' if args.offline else ''}.txt"
    tee = Tee(sys.stdout, out)
    sys.stdout = tee
    try:
        print(f"printout also written to data/raw/b120/{out.name}")
        print("== fetching the census, one setting, no category" if not args.offline else "== the census from the cache", flush=True)
        bag, gaps = census(P.RAW, today, network=not args.offline)
        extra, extra_gaps, sizes = extra_census(P.RAW, today, network=not args.offline)
        plans, plan_gaps = plan_rows(P.RAW, today, network=not args.offline)
        classes = print_census({**bag, **extra}, gaps + extra_gaps + plan_gaps, sizes)
        print_known(classes)
        if args.pdfs:
            print_pdfs(P.RAW, classes, args.sample)
        print_plan_documents(P.RAW, plans, classes, fetch=args.plan_pdfs)
        P.section_cost(P.RAW)
    finally:
        sys.stdout = tee.stream
        tee.fh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
