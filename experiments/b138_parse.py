"""B138 block two: read the consideration, the share structure and the dates off each implementation notice.

Input: the text of every notice fetched by `b138_fetch.py` (`data/raw/b138/pdf_text/`) and the fetch
manifest. One row per company: the main notice (its title is the implementation notice itself); a
company with two main notices takes the later one, and both ids are kept. Every number read carries
the sentence it was read from, so any row can be checked against the notice by eye (rule 25).

**The consideration.** The first sentence after the notice's summary heading that names a per-share
amount and is not a profit distribution or an additional consideration. Its form is one of:
``shares`` (x shares per share), ``shares_cash`` (shares and cash), ``cash``, ``warrant`` (with or
without shares), ``directed`` (a capital-reserve conversion to the tradable holders only),
``shares_directed`` (shares from the holders and a directed conversion in one plan), ``all_holder``
(a conversion to every holder, usually followed by a hand-over), ``other``. ``shares``, ``directed``
and ``shares_directed`` convert with no price; the rest wait for bars or are named.

**The whole plan.** A sentence is cut at semicolons, so the clause after one is read as well: a plan
that sends shares "and at the same time" converts reserves to the tradable holders is one plan with
two parts (``shares_directed``). And the plan's summary is searched for what the company itself
receives or gives up as part of the reform: an asset swap, donated or injected assets or cash, a
debt waived, shares bought back or cancelled against a debt, a one-way shrink of the non-tradable
stock, a new issue for assets. A plan with any of these is named and not converted (``component``
and the words around it are kept), because its share leg is not the whole consideration. Words in a
holder's undertaking for after the reform, and "shrink" in the clause that adjusts an additional
consideration for later share changes, are not counted.

**The share structure.** The pre-reform column: non-tradable total, tradable A, B (domestic-listed
foreign shares) and H (overseas-listed). Tables flatten into text with the percentage glued to the
number, so a number is read with its thousands commas first. ``万股`` multiplies by 10,000, and a
count printed in ``万股`` is read to the 万. A table's "tradable shares, total" row comes before its
A, B and H rows; the total and the A row are read apart, and where B or H shares sit inside the
total the A shares are the A row (or the total less B and H, each agreeing with its own printed
percentage). The parts are then added with their class labels kept.

**Checks.** Where the notice states the total consideration in shares, ``c * N_A`` against it; where it
states the total share capital, ``N_A + N_N + N_B + N_H`` against it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
RAW = ROOT / "data" / "raw" / "b138"
MANIFEST = RAW / "fetch_manifest.json"
TEXT = RAW / "pdf_text"

MAIN = re.compile(r"^(董事会)?(关于)?股权分置改革方案实施(的)?公告$")
NUM = r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
AMT = r"(\d+(?:\.\d+)?)"
BASE = r"(10|1|十|一)"

SUMMARY = re.compile(r"重要(?:内容)?提示|方案(?:简介|要点|的主要内容|基本内容)|对价(?:安排|方案)(?:为|：|:)")
SKIP = re.compile(r"利润分配|年度股东大会批准|追加|预案|分红派息|派息方案|20\d\d年度分配")
PER = re.compile(r"每(?:持有)?" + BASE + r"股")


def flat(text: str) -> str:
    return re.sub(r"\s+", "", text)


def to_num(s: str) -> float:
    return float(s.replace(",", ""))


def base_of(s: str) -> float:
    return {"10": 10.0, "1": 1.0, "十": 10.0, "一": 1.0}[s]


def sentences(t: str) -> list[str]:
    return [s for s in re.split(r"[。；;●★]|\d、(?=[^\d])", t) if s]


def consideration_sentence(t: str) -> str | None:
    m = SUMMARY.search(t)
    start = m.start() if m else 0
    for part in (t[start:], t):
        for s in sentences(part):
            if PER.search(s) and re.search(r"对价|获|送|派|转增|权证|新增", s) and not SKIP.search(s):
                if re.search(r"股东|流通", s):
                    return s
    return None


def whole_sentence(t: str, s: str) -> str:
    """The sentence up to its full stop: the clauses a semicolon cut off ``s`` are part of the plan."""
    k = t.find(s)
    if k < 0:
        return s
    a = max(t.rfind("。", 0, k), t.rfind("●", 0, k), t.rfind("★", 0, k)) + 1
    b = t.find("。", k + len(s))
    return t[a: b if b >= 0 else len(t)]


CONV_TO_TRADABLE = re.compile(
    r"每(?:持有)?" + BASE + r"股[^。；]{0,24}?(?:获得|获|转增)[^。；\d]{0,16}?" + AMT + r"股[^。；]{0,10}?转增"
    r"|每(?:持有)?" + BASE + r"股[^。；\d]{0,24}?转增[^。；\d]{0,10}?" + AMT + r"股")


def joint_conversion(t: str, s: str) -> float | None:
    """A directed conversion in the clauses that follow a share transfer, per tradable share."""
    rest = whole_sentence(t, s).replace(s, "", 1)
    if "转增" not in rest or re.search(r"全体股东|有限公司获得|追加|追送", rest):
        return None
    for clause in re.split(r"[；;]", rest):
        if "转增" not in clause or not re.search(r"流通股|定向", clause):
            continue
        m = CONV_TO_TRADABLE.search(clause)
        if m:
            g = [x for x in m.groups() if x is not None]
            return to_num(g[1]) / base_of(g[0])
    return None


PLAN_HEAD = re.compile(r"重要(?:内容)?提示|方案(?:简介|要点|的主要内容|主要内容|基本内容|实施内容|实施办法|概述)"
                       r"|对价(?:安排|方案)(?:为|：|:|的|一|二|\d)|改革方案为")
PLAN_WINDOW = 500
COMPONENT = re.compile(r"资产置换|置换|捐赠|赠与|赠送(?!股)|注入|豁免[^，。；]{0,20}债务|债务[^，。；]{0,12}豁免|以股抵债"
                       r"|非公开发行|购买资产|代为偿还|注资|资产重组|债务重组|定向回购|单向缩股|缩股比例")
#: an undertaking for after the reform, or an exception to a lock-up, is not part of the consideration
UNDERTAKING = re.compile(r"承诺")
LATER = re.compile(r"完成后|完毕后|择机|将在|十二个月内|12个月内|三十六个月|36个月|除外|除了[^。]{0,40}外")


def plan_component(t: str) -> tuple[str, str] | None:
    """The first thing in the plan's summary that the company receives or gives up as part of the reform."""
    for m in PLAN_HEAD.finditer(t):
        a, b = m.start(), min(len(t), m.start() + PLAN_WINDOW)
        for k in COMPONENT.finditer(t, a, b):
            lo = t.rfind("。", 0, k.start()) + 1
            hi = t.find("。", k.end())
            sentence = t[lo: hi if hi >= 0 else len(t)]
            # the undertaking's heading may sit a sentence or two before its numbered items
            lead = t[max(0, lo - 200): k.start()]
            if (UNDERTAKING.search(sentence) or UNDERTAKING.search(lead)) and LATER.search(sentence):
                continue
            return k.group(0), t[max(0, k.start() - 80): k.end() + 80]
    return None


def read_consideration(s: str, t: str | None = None) -> dict:
    out: dict = {"sentence": s}
    if t is not None:
        conv = joint_conversion(t, s)
        if conv:
            out["conversion"] = conv
            out["whole_sentence"] = whole_sentence(t, s)
    has_warrant = "权证" in s
    has_conv = "转增" in s
    to_tradable = bool(re.search(r"(?:向|对)[^，]{0,20}流通(?:A)?股股东", s)) or "定向" in s
    to_all = bool(re.search(r"全体股东|总股本为基数", s)) and not to_tradable
    m_sh = re.search(r"每(?:持有)?" + BASE + r"股[^，；]{0,40}?(?:获得|获送|获付|获|得到|新增|转增|送|支付|给付|执行|安排)"
                     r"[^；\d]{0,90}?" + AMT + r"(?:股|对价)", s)
    m_eq = re.search(r"相当于[^；\d]{0,40}?每(?:持有)?" + BASE + r"股[^；\d]{0,40}?" + AMT + r"股", s)
    if m_eq:
        out["stated_equiv"] = to_num(m_eq.group(2)) / base_of(m_eq.group(1))
    # the amount must not be the tail of a comma-grouped total (600145's 1,248,398 yuan read as 398)
    m_cash = re.search(r"每(?:持有)?" + BASE + r"股[^；]{0,60}?(?<![\d,，.])" + AMT + r"元", s)
    m_w = re.search(r"每(?:持有)?" + BASE + r"股[^；]{0,60}?" + AMT + r"份", s)
    if m_sh:
        out["shares"] = to_num(m_sh.group(2)) / base_of(m_sh.group(1))
    if m_cash and "元" in s and not re.search(r"行权价[^，]{0,6}" + re.escape(m_cash.group(2)) + "元", s):
        out["cash"] = to_num(m_cash.group(2)) / base_of(m_cash.group(1))
    if has_warrant and m_w:
        out["warrants"] = to_num(m_w.group(2)) / base_of(m_w.group(1))
        k = re.search(r"认(沽|购)", s)
        out["warrant_side"] = {"沽": "put", "购": "call"}.get(k.group(1)) if k else None
        p = re.search(r"行权价(?:格)?(?:为)?" + AMT + r"元", s)
        out["strike"] = to_num(p.group(1)) if p else None
    n_conv = len(re.findall(r"转增" + AMT + r"股", s))
    # a conversion that comes with cash, a shrink, injected or donated assets, or shares from the holders
    # is a combination; an equivalent the company computed at a price or a book value is a price it chose;
    # "new shares" does not say who gives them. All three are named, not converted. A company's own
    # "equivalent to x shares" for a plain transfer or conversion is kept as a check on the conversion.
    # cash to holders, not the capital reserve's yuan amount a conversion draws on (600681)
    combo = bool(re.search(r"现金|派现|派发|缩股|捐赠|注入|赠与|非流通股(?:股东)?(?:支付|送)", s))
    priced = bool(re.search(r"均价|市盈率|净资产|豁免|作价|折算|新增股份|资产置换|重组|红股", s))
    # a dividend to every holder, the non-tradable holders handing theirs over: the per-share number in
    # the sentence is the company's dividend, not the consideration (002041, 600887, 600825, 000623)
    priced = priced or bool(re.search(r"全体股东[^；]{0,12}(?:派现|派送现金|派发现金|分配现金|现金红利)", s))
    two_amounts = ("stated_equiv" in out and "shares" in out and not has_conv
                   and abs(out["stated_equiv"] - out["shares"]) > 0.01 * out["shares"])
    if out.get("conversion") and "shares" in out and not has_conv and "cash" not in out and not has_warrant:
        out["form"] = "shares_directed"
    elif has_warrant:
        out["form"] = "warrant"
    elif has_conv and n_conv > 1:
        out["form"] = "mixed_conversion"  # different ratios to different holders: named, not converted
    elif (has_conv and combo) or priced or two_amounts:
        out["form"] = "other"
    elif has_conv and to_all:
        out["form"] = "all_holder"
    elif has_conv:
        out["form"] = "directed"
    elif "shares" in out and "cash" in out:
        out["form"] = "shares_cash"
    elif "shares" in out:
        out["form"] = "shares"
    elif "cash" in out:
        out["form"] = "cash"
    else:
        out["form"] = "other"
    return out


# --------------------------------------------------------------------------
# share structure


SECTION = re.compile(r"(?:股份|股权|股本)结构(?:变动|变化)|方案实施前后|改革前后|实施前[，,]|改革前[，,]|变动前")
# A share count: comma-grouped, or at least five digits, and not followed by a percent or a decimal of a ratio.
COUNT = r"(\d{1,3}(?:,\d{3})+|\d{5,})(?:\.\d+)?(万)?"
NN_LABELS = (r"非流通股(?:份)?(?:股数|股份)?(?:合计|总数|为|共计)", r"未上市流通股(?:份)?合计",
             r"非流通股股东(?:合计)?持有(?:的)?(?:股数|股份)(?:为|共计|合计)?")
NA_A_LABELS = (r"(?<![非市件的B])流通A股(?:股份)?(?:合计|股数为|为)?", r"人民币普通股(?:合计)?",
               r"(?<![非市件的B流通H])A股")
NA_T_LABELS = (r"(?<![非市件的])流通股(?:份)?(?:股数为|合计|为)(?:\(含[^)]{0,6}\)|（含[^）]{0,6}）)?",
               r"已上市流通股(?:份)?合计")
NA_LABELS = NA_A_LABELS[:2] + NA_T_LABELS + NA_A_LABELS[2:]
NB_LABELS = (r"境内上市外资股(?:合计)?", r"(?<![非])流通B股(?:股份)?(?:为)?", r"(?<![A])B股")
NH_LABELS = (r"境外上市外资股(?:合计)?", r"H股")
TOTAL_LABELS = (r"股份总(?:额|数)", r"总股本(?:为|共)?")
STATED = (r"对价(?:安排)?(?:股份|股票)(?:总数|合计|总额|总计)(?:为|共计|共)?",
          r"支付(?:的)?(?:对价)?股(?:份|票)(?:总数|合计|总额)?(?:为|共计|共)",
          r"送出(?:股份)?(?:总数|合计)?(?:为|共计)?")


PCT = (r"(?:股)?[，,、]?(?:约)?占(?:公司)?(?:总股本|股份总数|总股份)(?:\d{1,2}(?=的))?(?:的)?(?:比例)?(?:为)?"
       r"(\d+(?:\.\d+)?)[%％]")


def unglue(s: str) -> str:
    """A plain run like 1062000000106200000 is before, a zero change, and after; the before is kept."""
    if "," in s or len(s) < 13:
        return s
    k = (len(s) - 1) // 2
    if len(s) % 2 == 1 and s[:k] == s[k + 1:] and s[k] == "0":
        return s[:k]
    return s


def _first(t: str, labels, span: int = 8, wan: bool = False):
    v, _, src = _first_pct(t, labels, span, wan)
    return v, src


def _first_pct(t: str, labels, span: int = 8, wan: bool = False):
    """The count and the percentage of the total written right after it, if any."""
    best = None
    for lab in labels:
        m = re.search(lab + r"[^\d%％]{0," + str(span) + r"}?" + COUNT, t)
        if m and (best is None or m.start() < best.start()):
            best = m
    if best is None:
        return None, None, None
    v = to_num(unglue(best.group(1)))
    if (best.group(2) or wan) and v < 1e7:
        v *= 1e4
    p = re.match(PCT, t[best.end(): best.end() + 24])
    return v, (float(p.group(1)) / 100 if p else None), t[max(0, best.start() - 8): best.end() + 26]


def _first_glued(t: str, labels, span: int = 8, wan: bool = False):
    """The count and the percentage a table glues right after it (``82,500,00023.02%``), if any."""
    best = None
    for lab in labels:
        m = re.search(lab + r"[^\d%％]{0," + str(span) + r"}?" + COUNT, t)
        if m and (best is None or m.start() < best.start()):
            best = m
    if best is None:
        return None, None
    v = to_num(unglue(best.group(1)))
    if (best.group(2) or wan) and v < 1e7:
        v *= 1e4
    g = re.match(r"(\d{1,3}\.\d{1,4})[%％]?", t[best.end(): best.end() + 10])
    return v, (float(g.group(1)) / 100 if g else None)


def split_tradable(region: str, out: dict, wan: bool) -> None:
    """Where B or H shares sit inside the tradable total, put the A shares in ``NA`` and keep B and H.

    Two ways, each checked against something the table prints on its own: the A row plus the B and H
    rows adds to the tradable total; or, with no readable A row, the total less B and H, where each of
    them agrees with the percentage of the company printed beside it and the tradable total plus the
    non-tradable shares is the company's total."""
    vT, _, srcT = _first_pct(region, NA_T_LABELS, wan=wan)
    vA, _, srcA = _first_pct(region, NA_A_LABELS, wan=wan)
    out["tradable_total"] = vT
    if not vT:
        return
    glued = {"NB": _first_glued(region, NB_LABELS, wan=wan), "NH": _first_glued(region, NH_LABELS, wan=wan)}
    cand = {k: out[k] for k in ("NB", "NH") if out[k] and 0.01 * vT <= out[k] < vT}
    if not cand:
        return
    picks = []
    if len(cand) == 2 and cand["NB"] != cand["NH"]:
        picks.append(("NB", "NH"))
    # an empty B row followed by the H count reads one number twice: it is the H count
    picks += [("NH",)] if "NH" in cand else []
    picks += [("NB",)] if "NB" in cand and cand.get("NH") != cand["NB"] else []
    for keys in picks:
        f = sum(cand[k] for k in keys)
        if vA and vT - vA >= 0.005 * vT and abs(vA + f - vT) <= 0.001 * vT:
            out["NA"], out["NA_src"], out["NA_how"] = vA, srcA, "the A row; A, B and H add to the tradable total"
            for k in ("NB", "NH"):
                if k not in keys:
                    out[k], out[k + "_src"] = None, None
            return
    tot, nn = out["total"], out["NN"]
    for keys in picks:
        f = sum(cand[k] for k in keys)
        agree = all(glued[k][1] is not None and tot and abs(cand[k] / tot - glued[k][1]) <= 0.005 for k in keys)
        if agree and nn and tot and abs(vT + nn - tot) <= 0.005 * tot and vT - f > 0:
            out["NA"], out["NA_src"] = vT - f, f"derived: {srcT} less B and H"
            out["NA_how"] = "the tradable total less B and H, each at its printed percentage"
            for k in ("NB", "NH"):
                if k not in keys:
                    out[k], out[k + "_src"] = None, None
            return


def read_structure(t: str) -> dict:
    wan = bool(re.search(r"单位[：:（(]?万股|[（(]万股[)）]", t))
    m = SECTION.search(t)
    region = t[m.start(): m.start() + 2500] if m else ""
    out: dict = {"section": bool(m)}
    rest = "。".join(s for s in re.split(r"[。；]", t) if not PER.search(s))
    for key, labs in (("NN", NN_LABELS), ("NA", NA_LABELS), ("NB", NB_LABELS), ("NH", NH_LABELS),
                      ("total", TOTAL_LABELS)):
        span = 4 if key == "total" else 8
        v, p, src = _first_pct(region, labs, span=span, wan=wan) if region else (None, None, None)
        if v is None and key in ("NN", "NA", "total"):
            # outside the section, only sentences that are not the consideration itself
            v, p, src = _first_pct(rest, labs, wan=wan)
        out[key], out[key + "_pct"], out[key + "_src"] = v, p, src
    out["foreign_words"] = bool(re.search(r"流通B股|B股股东|H股股东|境外上市外资股股东|境内上市外资股股东", t))
    if out["total"] is None:
        v, src = _first(t, TOTAL_LABELS, wan=wan)
        out["total"], out["total_src"] = v, src
    m = re.search("(?:" + "|".join(STATED) + r")[^\d%％]{0,6}?(\d{1,3}(?:,\d{3})+|\d{5,})(?:\.\d+)?(万)?股", t)
    v, src = (None, None)
    if m:
        v = to_num(m.group(1)) * (1e4 if m.group(2) else 1.0)
        src = t[max(0, m.start() - 8): m.end() + 8]
    out["stated_total"], out["stated_total_src"] = v, src
    out["NA_how"] = None
    if region:
        split_tradable(region, out, wan)
    # accept the structure only if its parts add up to the notice's own total
    na, nn = out["NA"], out["NN"]
    nb, nh = out["NB"] or 0.0, out["NH"] or 0.0
    tot = out["total"]
    out["sum_check"] = None
    if na and nn and tot:
        gaps = {"A+N": abs(na + nn - tot) / tot, "A+N+B+H": abs(na + nn + nb + nh - tot) / tot}
        key = min(gaps, key=gaps.get)
        out["sum_check"] = (key, gaps[key])
        if key == "A+N":
            out["NB"], out["NH"] = None, None
    # three ways a structure is accepted, each checked against something the notice wrote independently
    out["route"] = None
    if out["sum_check"] and out["sum_check"][1] <= 0.005:
        out["route"] = "parts add to the total"
    elif na and nn and out["NA_pct"] and out["NN_pct"] and not (out["NB"] or out["NH"]):
        ta, tn = na / out["NA_pct"], nn / out["NN_pct"]
        if abs(ta - tn) / tn <= 0.005 and abs(out["NA_pct"] + out["NN_pct"] - 1) <= 0.005:
            out["route"] = "each class's percentage gives the same total"
    elif nn and out["NN_pct"] and not out["foreign_words"] and not re.search(r"除|以外", out["NN_src"] or ""):
        derived = nn / out["NN_pct"] - nn
        if na and abs(na - derived) / derived <= 0.005:
            out["route"] = "tradable count matches the one implied by the non-tradable percentage"
        elif not na:
            out["NA"], out["NA_src"] = derived, "derived: NN / pct - NN"
            out["route"] = "tradable derived from the non-tradable percentage (no B or H in the text)"
    # "total less one class" was tried and dropped: nothing independent checks it, and a count read off one
    # holder's line instead of the class total gave n near 0.99 (000520, 600533, 600267, 600141, 600235)
    out["structure_ok"] = out["route"] is not None
    return out


def read_dates(t: str) -> dict:
    out = {}
    m = re.search(r"(?:股权登记日|股份变更登记日)(?:[：:为]|\(|（)?[^\d]{0,12}(\d{4})年(\d{1,2})月(\d{1,2})日", t)
    if m:
        out["record_day"] = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return out


def read_notice(text: str) -> dict:
    t = flat(text)
    row: dict = {"chars": len(t)}
    s = consideration_sentence(t)
    row["consideration"] = read_consideration(s, t) if s else {"form": "none", "sentence": None}
    comp = plan_component(t)
    if comp:
        row["consideration"]["component"], row["consideration"]["component_src"] = comp
    row["structure"] = read_structure(t)
    row.update(read_dates(t))
    return row


def companies() -> list[dict]:
    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by: dict = {}
    for r in rows:
        title = re.sub(r"[（(].*?[)）]", "", r["title"])
        if not MAIN.match(title):
            continue
        by.setdefault(r["code"], []).append(r)
    out = []
    for code, rs in sorted(by.items()):
        rs.sort(key=lambda r: (r["day"], r["id"]))
        use = rs[-1]
        out.append({"code": code, "name": use["name"], "id": use["id"], "day": use["day"],
                    "ids": [r["id"] for r in rs], "status": use.get("status", "missing")})
    return out


def parse_all() -> list[dict]:
    out = []
    for c in companies():
        p = TEXT / f"{c['id']}.txt"
        if not p.exists():
            out.append({**c, "parse": "no text"})
            continue
        out.append({**c, **read_notice(p.read_text(encoding="utf-8")), "parse": "read"})
    return out
