# -*- coding: utf-8 -*-
"""Reconcile the page registry against what is on disk and what reached the
panel, and fix the README line that still says two tracks.

Recomputable: it reads the disk and the panel rather than taking anything on
faith, so rerunning it after a fetch updates the two derived fields.
"""
import csv
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, "data")
from parse_gaokao_provincial import (  # noqa: E402
    cells, decode_page, headline, sources, supplementary_of, title_track,
    TABLE, TR)

REG = Path("data/gaokao_sources.json")
shutil.copyfile(REG, REG.with_name(REG.name + ".expired_20260827_pre_reconcile"))
d = json.loads(REG.read_text(encoding="utf-8"))

# ---- what is on disk, keyed the way the registry keys it -------------------
keep, dupes = sources()
on_disk = {}
for f in keep:
    a = f.stem.split("_")
    track = a[2] if len(a) > 2 and a[2] in ("arts", "science", "both") else "both"
    on_disk[(a[0], int(a[1]), track)] = f.stem

# ---- what reached the panel ------------------------------------------------
reached = set()
with Path("data/gaokao_provincial.csv").open(encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        reached.add(r["source"])

# ---- the one page on disk with no row --------------------------------------
KNOWN = {("江苏", 2015, "both"): {
    "province": "江苏", "year": 2015, "track": "both", "verified": True,
    "quantity": "supplementary_round",
    "url": "http://edu.sina.com.cn/gaokao/2015-07-24/1030479174.shtml",
    "note": ("征求平行志愿, the supplementary round. Fetched and held. It "
             "disagrees with the main arts page on 26 of the 43 schools they "
             "share and puts 15 of them at 342, the tier control line, so the "
             "two are not two readings of one quantity. The parser excludes it "
             "by its own title and prints the exclusion")}}
have = {(r["province"], int(r["year"]), r["track"]) for r in d["pages"]}
for k, row in KNOWN.items():
    if k not in have:
        d["pages"].append(row)

# ---- what each page says about itself --------------------------------------
def inspect(stem: str) -> dict:
    """Headline, the track the page states, and whether it holds a table."""
    page = decode_page(
        Path("data/raw/gaokao/provincial/%s.html" % stem).read_bytes())
    wide = 0
    for tbl in TABLE.findall(page):
        rows = [c for c in (cells(tr) for tr in TR.findall(tbl)) if c]
        if len(rows) >= 5:
            wide += 1
    head = headline(page)
    return {"headline": head, "title_track": title_track(head),
            "supplementary": supplementary_of(head), "tables": wide}


# ---- derived fields, recomputed every time this runs -----------------------
for r in d["pages"]:
    k = (r["province"], int(r["year"]), r["track"])
    stem = on_disk.get(k)
    r["on_disk"] = stem or False
    r["in_panel"] = bool(stem and stem in reached)
    for key in ("headline", "title_track", "out_of_panel_because"):
        r.pop(key, None)
    if not stem:
        continue
    seen = inspect(stem)
    r["headline"] = seen["headline"]
    if seen["title_track"] and seen["title_track"] != r["track"]:
        r["title_track"] = seen["title_track"]
    if not r["in_panel"]:
        if seen["supplementary"]:
            r["out_of_panel_because"] = (
                "the page's own title says %s, a supplementary round"
                % seen["supplementary"])
        elif seen["tables"] == 0:
            r["out_of_panel_because"] = (
                "the saved page holds no table of five rows or more; the "
                "article body is not in it")
        else:
            r["out_of_panel_because"] = "unexplained, and that is a defect"

d["pages"].sort(key=lambda r: (r["province"], r["year"], r["track"]))

d["_comment"] = d["_comment"] + [
    "",
    "Reconciled 2026-08-27 against the directory and against the panel, by",
    "`data/gaokao_sources.json`'s own reconciliation step. Two fields are",
    "derived and are rewritten on each run rather than maintained by hand:",
    "`on_disk` is the file stem holding this page or false, and `in_panel` is",
    "whether any row in `data/gaokao_provincial.csv` came from it.",
    "",
    "A row can be on disk and out of the panel for two stated reasons, and",
    "both are printed by the parser rather than assumed. The page carries no",
    "article body, which is five provinces here; or its own title says it is a",
    "supplementary round, which is three pages.",
    "",
    "`title_track` appears only where the page's own title states a track other",
    "than the one in the file name, and the title is the authority. Guangdong",
    "is the case: the file named for arts is titled for science and supplies",
    "the science column, while the file named for science holds no table. A",
    "reader of `in_panel` alone would conclude Guangdong's science table is",
    "missing when it is present under the other name.",
    "",
    "The fetcher wrote every page twice, once under `<province>_<year>_<track>`",
    "and once under `<province>_<year>`, so the directory holds more files than",
    "there are pages. The loader passes over the duplicates by content hash and",
    "names the ones it skipped. Nothing was removed from disk.",
]

REG.write_text(json.dumps(d, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
               encoding="utf-8", newline="\n")

n = len(d["pages"])
disk = sum(1 for r in d["pages"] if r["on_disk"])
panel = sum(1 for r in d["pages"] if r["in_panel"])
print("registry rows %d, on disk %d, in panel %d, duplicate files skipped %d"
      % (n, disk, panel, len(dupes)))
for r in d["pages"]:
    if r["on_disk"] and not r["in_panel"]:
        print("  out of panel: %-6s %d %-8s  %s"
              % (r["province"], r["year"], r["track"],
                 r.get("out_of_panel_because", "?")))
    if r.get("title_track"):
        print("  title states another track: %-6s %d  file says %-8s "
              "title says %-8s" % (r["province"], r["year"], r["track"],
                                   r["title_track"]))

# ---- the README line ------------------------------------------------------
p = Path("README.md")
s = p.read_text(encoding="utf-8")
old = "**Status, 2026-08-27.** Both tracks have run."
new = "**Status, 2026-08-27.** All three tracks have run."
if s.count(old) == 1:
    p.write_text(s.replace(old, new, 1), encoding="utf-8", newline="\n")
    print("README status line updated")
else:
    assert s.count(new) == 1, "README status line is neither shape"
    print("README status line already updated")
