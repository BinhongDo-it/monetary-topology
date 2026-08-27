# -*- coding: utf-8 -*-
"""C3. Reduce the provincial filing tables to one tidy panel.

**Ten column layouts across sixteen provinces**, so the parser reads a header
rather than counting positions. What it needs from a row is two things, an
institution and a score, and it locates both from the header text:

    institution   院校名称 / 学校名称 / 院校全称 / 院校代号及名称
    score         投档线 / 投档分 / 投档最低分 / 最低分 / 总分 / 常规志愿投档最低分

**Three shapes the header does not resolve, handled by name.** Some provinces
put the track in its own column, some put one score column per track, and some
publish one file per track and say so only in the title. All three appear.

**Scores carry a tie-break suffix in several provinces.** `691.145144282` is a
filing score of 691 followed by the subject scores concatenated as an ordering
key, so the integer part is taken and the rest discarded rather than read as a
fraction.

**Only the ordering inside a province is used downstream**, which is why the
different provincial scales do not need reconciling: Jiangsu runs to 480 and
Hainan past 800, and a comparison is never made across that line.

    python data/parse_gaokao_provincial.py
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "raw" / "gaokao" / "provincial"
OUT = ROOT / "data" / "gaokao_provincial.csv"

CHARSET = re.compile(rb'charset=["\']?([\w-]+)', re.I)
CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
TABLE = re.compile(r"<table[^>]*>(.*?)</table>", re.S | re.I)

NAME_H = ("院校名称", "学校名称", "院校全称", "院校代号及名称", "院校")
SCORE_H = ("投档最低分", "常规志愿投档最低分", "投档线", "投档分数", "投档分",
           "录取最低分", "最低分", "总分")
TRACK_H = ("科类", "科类名称", "计划性质")
RANK_H = ("最低位次", "最低排位", "最低排名", "投档名次")

#: A supplementary round is a second filing against the seats the first round
#: left empty, so a school that filled in round one is absent and a school that
#: did not files at or near the tier control line. Jiangsu's two arts pages
#: disagree on 26 of the 43 schools they share, and the supplementary one puts
#: 15 of them at 342, which was the control line. **The two pages are not two
#: readings of one quantity**, and mixing them would put the control line into
#: the ordering as though it were a filing score. The page says which it is in
#: its own title.
SUPPLEMENTARY = ("征求", "征集", "补录", "降分", "缺额", "剩余计划")

#: Only the part of the headline that carries the score noun is tested for the
#: words above. `2015江西一本院校投档线公布 21日征集志愿` is the main table
#: with a trailing line about supplementary filing opening on the 21st, and
#: testing the whole string throws it away. `海南高考本科一批征集志愿平行投档
#: 分数线` is the supplementary table, and there the word sits inside the noun
#: phrase the score belongs to.
SCORE_NOUN = ("投档线", "投档分", "分数线", "投档最低分", "录取线", "最低分",
              "最低位次")
SEGMENT = re.compile(r"[\s，,、。：:_|]+")

#: The track as the page states it, which is not always the track the file
#: name states. Guangdong's two files are named for one track and titled for
#: the other, so the science page would have entered the panel as arts.
TITLE_TRACK = (
    (re.compile(r"[（(]\s*文[科史]?\s*[）)]|文史类|文科|文史"), "arts"),
    (re.compile(r"[（(]\s*理\s*[科工]?\s*[）)]|理工类|理科|理工"), "science"),
    (re.compile(r"(?:一本|一批|批次?|高招)\s*文(?![化学])"), "arts"),
    (re.compile(r"(?:一本|一批|批次?|高招)\s*理(?![论])"), "science"),
)


def headline(page: str) -> str:
    m = re.search(r"<title>(.*?)</title>", page, re.S)
    if not m:
        return ""
    t = re.sub(r"\s+", " ", m.group(1)).strip()
    for tail in ("_新浪", "—教育", " —", "_中国教育"):
        t = t.split(tail)[0]
    return t.strip()


def supplementary_of(head: str) -> str | None:
    segs = [x for x in SEGMENT.split(head) if x]
    core = [x for x in segs if any(n in x for n in SCORE_NOUN)] or segs
    for k in SUPPLEMENTARY:
        if any(k in x for x in core):
            return k
    return None


def title_track(head: str) -> str | None:
    hits = [(m.start(), t) for pat, t in TITLE_TRACK
            for m in [pat.search(head)] if m]
    if not hits:
        return None
    tracks = {t for _, t in hits}
    return hits[0][1] if len(tracks) == 1 else None

ARTS = ("文史", "文科")
SCIENCE = ("理工", "理科")


def decode_page(body: bytes) -> str:
    m = CHARSET.search(body[:4000])
    declared = (m.group(1).decode("ascii", "replace").lower() if m else "")
    for enc in ([declared] if declared else []) + ["gb18030", "utf-8"]:
        enc = {"gb2312": "gb18030", "gbk": "gb18030"}.get(enc, enc)
        try:
            return body.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return body.decode("utf-8", "replace")


def cells(tr: str) -> list[str]:
    return [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c))
            .replace("&nbsp;", " ").replace("　", " ").strip()
            for c in CELL.findall(tr)]


def score_of(text: str) -> int | None:
    """The filing score, with any ordering suffix discarded.

    `691.145144282` is 691 followed by the subject scores run together as a
    tie-break key. Reading it as a decimal would keep the right integer, but
    saying so here is cheaper than leaving the next reader to work out why a
    filing score has nine decimal places.
    """
    m = re.match(r"^\s*(\d{2,3})(?:\.\d+)?\s*$", text)
    if not m:
        return None
    v = int(m.group(1))
    return v if 100 <= v <= 999 else None


def track_of(text: str) -> str | None:
    if any(k in text for k in ARTS):
        return "arts"
    if any(k in text for k in SCIENCE):
        return "science"
    return None


def header_index(row: list[str], keys) -> int | None:
    """First column whose header contains any of `keys`, keys tried in order.

    Order matters, so the longer and more specific label is listed first: a
    loose key finds a column that merely contains it.
    """
    for k in keys:
        for i, c in enumerate(row):
            if k in c:
                return i
    return None


CODE_ONLY = re.compile(r"代号|代码|编码")


def name_index(row: list[str]) -> int | None:
    """The column holding the institution, not the one holding its number.

    **`院校` matches `院校代号` before it matches `院校名称`**, and taking the
    code column looks like success: the parser runs, finds cells, strips their
    leading digits as it is meant to for the provinces that glue a code to a
    name, and is left with empty strings, so every table returns zero rows
    while nothing raises. Ten of sixteen provinces went that way. A cell is
    therefore only a name column if it says so, or if it says nothing about
    being a code.
    """
    for k in NAME_H:
        for i, c in enumerate(row):
            if k not in c:
                continue
            if ("名称" in c) or ("全称" in c) or not CODE_ONLY.search(c):
                return i
    return None


TRACK_CELLS = ("文史类", "理工类", "文科", "理科", "文史", "理工")


def two_level(head: list[str], rows: list[list[str]], hi: int):
    """Column of the score for each track when the header spans two rows.

    Shandong writes `院校 | 文科 | 理科` across merged cells and then repeats
    `计划数 投档比例 投出数 最高分 最低分` under each of them. Reading the
    first row alone puts arts at column 1 and science at column 2, which are
    the plan count and the filing ratio: **the parser runs, the scores are
    integers in the right range, and every number is wrong.** Shandong read
    100, 105 and 120 for its whole first tier that way.

    Returns `(per_track, start)` or `None` when this is not that shape. The
    group width is computed from the two row widths rather than assumed, so a
    table with three tracks or a two-column stub reads as not-this-shape and
    falls through to the single-row path.
    """
    if hi + 1 >= len(rows):
        return None
    sub = rows[hi + 1]
    labels = [(i, track_of(c)) for i, c in enumerate(head)
              if c.strip() in TRACK_CELLS and track_of(c)]
    if len(labels) < 2 or len(sub) <= len(head):
        return None
    if header_index(sub, SCORE_H) is None:
        return None
    if len(sub) % len(labels):
        return None
    width = len(sub) // len(labels)
    inner = header_index(sub[:width], SCORE_H)
    if inner is None:
        return None
    body = [len(r) for r in rows[hi + 2:hi + 14] if len(r) > 2]
    if not body:
        return None
    offset = max(set(body), key=body.count) - len(sub)
    if offset < 0:
        return None
    per_track = {}
    for k, (_, t) in enumerate(labels):
        per_track.setdefault(t, offset + k * width + inner)
    return per_track, hi + 2


def parse_table(rows: list[list[str]], default_track: str | None):
    """Yield (institution, track, score, rank) from one table."""
    head = None
    for i, r in enumerate(rows[:6]):
        has_score = header_index(r, SCORE_H) is not None
        has_track_cols = sum(1 for c in r if c.strip() in TRACK_CELLS) >= 1
        if name_index(r) is not None and (has_score or has_track_cols):
            head, hi, start = r, i, i + 1
            break
    if head is None:
        return
    name_i = name_index(head)
    track_i = header_index(head, TRACK_H)
    rank_i = header_index(head, RANK_H)

    # One score column per track, as in the provinces that print both side by
    # side, or a single score column whose track comes from elsewhere.
    stacked = two_level(head, rows, hi)
    if stacked is not None:
        per_track, start = stacked
    else:
        per_track = {}
        for i, c in enumerate(head):
            if any(k in c for k in SCORE_H) or c in TRACK_CELLS:
                t = track_of(c)
                if t:
                    per_track.setdefault(t, i)
    single_i = None
    if not per_track:
        single_i = header_index(head, SCORE_H)
        if single_i is None:
            return

    # A header that names one column `院校代号及名称` while the rows carry the
    # code and the name in two cells leaves every later column shifted by one.
    # Detected from the widths rather than assumed.
    widths = [len(r) for r in rows[start:start + 12] if len(r) > 2]
    shift = 0
    if widths and stacked is None and "代号及名称" in head[name_i]:
        common = max(set(widths), key=widths.count)
        if common == len(head) + 1:
            shift = 1
            name_i += 1

    for r in rows[start:]:
        if len(r) <= name_i:
            continue
        name = r[name_i].strip()
        # Some provinces glue the code to the name, others split it across the
        # cell after the header's combined label.
        name = re.sub(r"^[A-Z]?\d{3,5}\s*", "", name).strip()
        if not name or len(name) < 2 or not re.search(r"[一-鿿]", name):
            continue
        rank = None
        if rank_i is not None and rank_i < len(r):
            rm = re.search(r"(\d{2,7})", r[rank_i].replace("-", ""))
            rank = int(rm.group(1)) if rm else None
        if per_track:
            for t, i in ((k, v + shift) for k, v in per_track.items()):
                if i < len(r):
                    s = score_of(r[i])
                    if s:
                        yield name, t, s, rank
        else:
            t = default_track
            ti = track_i + shift if track_i is not None else None
            if ti is not None and ti < len(r):
                t = track_of(r[ti]) or t
            si = single_i + shift
            s = score_of(r[si]) if si < len(r) else None
            if s and t:
                yield name, t, s, rank


def sources() -> tuple[list[Path], list[tuple[str, str]]]:
    """One file per distinct page, keyed on content.

    The fetcher wrote every page twice, once under `<province>_<year>_<track>`
    and once under `<province>_<year>`, and 24 of the 34 pages on disk are a
    byte-identical pair. Reading the directory produced two copies of every
    row, and the per-file dedup did not see it because it resets between
    files. **Nothing is removed from disk**; the loader keeps the stem that
    carries the most fields and names the ones it passed over.
    """
    by_hash: dict[str, list[Path]] = {}
    for f in sorted(SRC.glob("*.html")):
        by_hash.setdefault(
            hashlib.sha256(f.read_bytes()).hexdigest(), []).append(f)
    keep, skipped = [], []
    for group in by_hash.values():
        chosen = max(group, key=lambda f: (len(f.stem.split("_")), f.stem))
        keep.append(chosen)
        skipped.extend((f.stem, chosen.stem) for f in group if f is not chosen)
    return sorted(keep), sorted(skipped)


def main() -> int:
    lines = ["province,year,track,institution,score,rank,source"]
    per_file = []
    keep, skipped = sources()
    excluded: list[tuple[str, str, str]] = []
    relabelled: list[tuple[str, str, str, str]] = []
    for f in keep:
        parts = f.stem.split("_")
        province, year = parts[0], int(parts[1])
        default = {"arts": "arts", "science": "science"}.get(
            parts[2] if len(parts) > 2 else "", None)
        page = decode_page(f.read_bytes())
        head_text = headline(page)
        hit = supplementary_of(head_text)
        if hit:
            excluded.append((f.stem, hit, head_text))
            continue
        stated = title_track(head_text)
        if stated and default and stated != default:
            relabelled.append((f.stem, default, stated, head_text))
        default = stated or default
        got = []
        for tbl in TABLE.findall(page):
            rows = [c for c in (cells(tr) for tr in TR.findall(tbl)) if c]
            got.extend(parse_table(rows, default))
        seen = set()
        for name, track, score, rank in got:
            key = (province, year, track, name)
            if key in seen:
                continue
            seen.add(key)
            lines.append("%s,%d,%s,%s,%d,%s,%s"
                         % (province, year, track, name.replace(",", ""), score,
                            rank if rank is not None else "", f.stem))
        per_file.append((f.stem, len(seen)))

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    for stem, n in per_file:
        print("  %-34s %5d" % (stem, n))
    for stem, chosen in skipped:
        print("  skipped, same bytes as %-28s %s" % (chosen, stem))
    for stem, was, now, head_text in relabelled:
        print("  relabelled %s -> %-8s %-22s %s" % (was, now, stem, head_text))
    for stem, word, head_text in excluded:
        print("  excluded, title says %-6s %-24s %s" % (word, stem, head_text))
    print("\nwrote %s  %d rows" % (OUT, len(lines) - 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
