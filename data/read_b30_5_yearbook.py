"""B30-5 arm B: read the official per-city housing price out of the yearbook table.

Source: China Statistical Yearbook 2024, chapter 19 (real estate), table 19-16,
"Main Indicators of Real Estate Projects in 35 Large and Medium-sized Cities
(2023)". Column 12 is the average selling price of newly built residential
buildings in yuan per square metre, given **per city**, which is what makes this
the right counterpart: no capital-versus-province mismatch enters at all.

The single sheet is kept at ``data/raw/yearbook2024_19-16_35cities.xlsx``,
extracted once from the yearbook archive supplied by hand. The archive is RAR5
and neither 7-Zip's free build nor any tool installable without root reads it,
so the sheet is kept beside the reader rather than the archive: this script runs
anywhere, needs no archiver, and re-derives every number from a file on disk.

What it writes: ``data/b30_5/nbs/housing_price.json``, the shape arm B of
``experiments/b30_5_carrier_check.py`` reads.

Run:
    python data\\read_b30_5_yearbook.py
"""

import json
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "raw" / "yearbook2024_19-16_35cities.xlsx"
OUT = ROOT / "data" / "b30_5" / "nbs" / "housing_price.json"
YEAR = "2023"

# The yearbook prints city names with spacing used for typographic alignment,
# so they are compared with the whitespace stripped. Only the twelve cities the
# panel carries are named here; the sheet holds thirty-five and every one of
# them is written out, so the other twenty-three are ready the day the panel
# reaches them.
NAME_EN = {
    "北京": "Beijing", "天津": "Tianjin", "石家庄": "Shijiazhuang",
    "太原": "Taiyuan", "呼和浩特": "Hohhot", "沈阳": "Shenyang",
    "大连": "Dalian", "长春": "Changchun", "哈尔滨": "Harbin",
    "上海": "Shanghai", "南京": "Nanjing", "杭州": "Hangzhou",
    "宁波": "Ningbo", "合肥": "Hefei", "福州": "Fuzhou", "厦门": "Xiamen",
    "南昌": "Nanchang", "济南": "Jinan", "青岛": "Qingdao",
    "郑州": "Zhengzhou", "武汉": "Wuhan", "长沙": "Changsha",
    "广州": "Guangzhou", "深圳": "Shenzhen", "南宁": "Nanning",
    "海口": "Haikou", "重庆": "Chongqing", "成都": "Chengdu",
    "贵阳": "Guiyang", "昆明": "Kunming", "西安": "Xian",
    "兰州": "Lanzhou", "西宁": "Xining", "银川": "Yinchuan",
    "乌鲁木齐": "Urumqi",
}

COL_ALL, COL_RESIDENTIAL = 11, 12


def main():
    try:
        import openpyxl
    except ImportError:
        raise SystemExit("openpyxl is needed to read the sheet: pip install openpyxl")
    if not SRC.exists():
        raise SystemExit("no sheet at %s" % SRC)

    wb = openpyxl.load_workbook(SRC, data_only=True)
    ws = wb[wb.sheetnames[0]]

    # The header is checked rather than assumed. A yearbook that renumbers its
    # columns between editions would otherwise be read silently in the wrong
    # place, and every number would still look like a price.
    head = " ".join(str(ws.cell(r, c).value or "")
                    for r in range(3, 7) for c in (COL_RESIDENTIAL - 1, COL_RESIDENTIAL))
    head = re.sub(r"\s+", "", head)
    if "平均" not in head or "销售价格" not in head or "元/平方米" not in head:
        raise SystemExit(
            "column %d does not carry the average selling price header. Read: "
            "%r. Nothing is written; check the table rather than the reader."
            % (COL_RESIDENTIAL, head[:120]))

    series, total, unknown = {}, None, []
    for r in range(7, ws.max_row + 1):
        name = ws.cell(r, 1).value
        if not isinstance(name, str):
            continue
        name = re.sub(r"\s+", "", name)
        res = ws.cell(r, COL_RESIDENTIAL).value
        allb = ws.cell(r, COL_ALL).value
        if not isinstance(res, (int, float)):
            continue
        if name in ("总计", "合计"):
            total = {"residential": res, "all_uses": allb}
            continue
        en = NAME_EN.get(name)
        if en is None:
            unknown.append(name)
            continue
        series[en] = {YEAR: float(res)}

    if unknown:
        print("city names in the sheet with no mapping, named rather than "
              "dropped quietly: %s" % ", ".join(unknown))

    print("%d cities read, year %s, yuan per square metre, residential"
          % (len(series), YEAR))
    for en in sorted(series, key=lambda k: -series[k][YEAR]):
        print("  %-14s %9.0f" % (en, series[en][YEAR]))
    if total:
        print("  %-14s %9.0f   (the sheet's own 35-city total row)"
              % ("[all 35]", total["residential"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "meta": {
            "source": "China Statistical Yearbook 2024, table 19-16, Main "
                      "Indicators of Real Estate Projects in 35 Large and "
                      "Medium-sized Cities (2023)",
            "variable": "average selling price of newly built residential "
                        "buildings, yuan per square metre",
            "year": YEAR,
            "unit_of_observation": "city, so no capital-versus-province "
                                   "mismatch enters",
            "scope_note": "newly built only, averaged over the whole "
                          "municipality including its outer districts",
            "file": str(SRC.relative_to(ROOT)),
            "total_row": total,
        },
        "series": series,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nwritten: %s" % OUT)


if __name__ == "__main__":
    main()
