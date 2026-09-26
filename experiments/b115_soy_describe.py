"""B115: print the objects in the soybean branch's raw files, before any criterion is written.

The files are the ones experiments/b115_soy_fetch.py put under data/b115/raw. Every file is
checked against the SHA-256 its manifest recorded before a byte of it is read. Nothing here
scores anything: the objects are printed so that the criteria can be written against them.

  agtransport  one row per market and week ending date. Per market: its type, its sources, the
               weeks it covers per year, its longest gap, and whether basis equals bid minus
               futures price, which is how the platform describes the basis column.
  dce          one row per contract and trading day. Per product and year: the header the file
               uses, trading days, contracts, the rows and days with volume, and the contract
               traded on the most days. The contract prefixes are read, so a file holding another
               product or year shows it.
  cepea        one row per day: the Paranagua indicator in reais and in US dollars per 60 kg bag.
  fred         one row per business day: yuan per US dollar, with "." where no rate was set.
  joint        per year of the window, the days each daily series has a value, and the days all
               of them do; and the weeks the Gulf and Portland soybean basis is quoted.

    python experiments/b115_soy_describe.py              # print, and write the record
    python experiments/b115_soy_describe.py --selftest   # offline, planted faults

Run from the repository root with the venv active. Reading the DCE workbooks needs openpyxl,
and the CEPEA workbook needs xlrd; the script names whichever is missing.
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import csv
import hashlib
import io
import json
import sys
import tempfile
import zipfile
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data" / "b115" / "raw"
MANIFEST_NAME = "b115_soy_manifest.json"
OUT = REPO / "results" / "b115_soy_describe.json"

WINDOW = ("2016-01-01", "2020-12-31")
YEARS = tuple(range(2016, 2021))
PRODUCTS = {"a": "no1_soybeans", "b": "no2_soybeans", "m": "soybean_meal", "c": "corn"}
#: the exact header names read from the DCE files; a name is matched whole, so 前收盘价 is not 收盘价
DCE_COLUMNS = {"合约": "contract", "日期": "date", "收盘价": "close", "结算价": "settle",
               "成交量": "volume", "持仓量": "open_interest", "成交金额": "turnover", "成交额": "turnover"}
DAILY = ("dce_b_traded", "dce_m_traded", "cepea", "fred")


def fmt(x: float, digits: int = 6) -> float:
    """A float through an explicit format spec, so the record carries no platform digits."""
    return float(f"{x:.{digits}g}")


# ------------------------------------------------- reading, checked against the manifest

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_checked(raw: Path, rel: str, manifest: dict) -> bytes:
    entry = manifest.get(rel)
    if entry is None:
        raise RuntimeError(f"{rel} is not in the manifest")
    data = (raw / rel).read_bytes()
    if sha256(data) != entry["sha256"]:
        raise RuntimeError(f"{rel} differs from the SHA-256 its manifest recorded")
    return data


# ------------------------------------------------- AgTransport

def parse_week(s: str) -> date:
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


def describe_agt(rows: list[dict]) -> dict:
    by_market = collections.defaultdict(list)
    for r in rows:
        by_market[r["market_name"]].append(r)
    out = {}
    for name in sorted(by_market):
        rs = by_market[name]
        weeks = sorted({parse_week(r["date"]) for r in rs})
        gaps = [(b - a).days for a, b in zip(weeks, weeks[1:])]
        dup = len(rs) - len({(r["date"], r["market_name"]) for r in rs})
        ident = [abs(float(r["bid"]) - float(r["futures_price"]) - float(r["basis"]))
                 for r in rs if all(k in r for k in ("bid", "futures_price", "basis"))]
        basis = [float(r["basis"]) for r in rs if "basis" in r]
        out[name] = {
            "market_type": sorted({r.get("market_type", "") for r in rs}),
            "sources": sorted({r.get("source", "") for r in rs}),
            "rows": len(rs), "weeks": len(weeks), "duplicate_rows": dup,
            "first_week": weeks[0].isoformat(), "last_week": weeks[-1].isoformat(),
            "weeks_by_year": {str(y): sum(w.year == y for w in weeks) for y in YEARS},
            "longest_gap_days": max(gaps) if gaps else 0,
            "basis_min": fmt(min(basis)) if basis else None, "basis_max": fmt(max(basis)) if basis else None,
            "bid_minus_futures_minus_basis_max": fmt(max(ident), 3) if ident else None,
            "contract_months": dict(sorted(collections.Counter(r.get("contract_month", "") for r in rs).items())),
        }
    return out


# ------------------------------------------------- DCE

def dce_tables(data: bytes, name: str):
    """Every table in a DCE file as (label, header, rows): a zip of csv or workbook members, or a workbook."""
    blobs = []
    if name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            blobs = [(n, z.read(n)) for n in sorted(z.namelist())]
    else:
        blobs = [(name.rsplit("/", 1)[-1], data)]
    for member, b in blobs:
        if b[:4] == b"PK\x03\x04":
            try:
                import openpyxl
            except ImportError as e:
                raise RuntimeError("openpyxl is needed to read the DCE workbooks (pip install openpyxl)") from e
            wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True)
            try:
                for ws in wb.worksheets:
                    it = ws.iter_rows(values_only=True)
                    head = next(it, None) or ()
                    yield (f"{member}[{ws.title}]", ["" if h is None else str(h).strip() for h in head],
                           [list(r) for r in it])
            finally:
                wb.close()
        else:
            text = b.decode("gb18030")
            lines = [ln for ln in text.splitlines() if ln.strip()]
            head = [h.strip().strip('"').strip() for h in lines[0].split(",")]
            yield f"{member}[csv]", head, [[c.strip().strip('"') for c in ln.split(",")] for ln in lines[1:]]


def column_index(header: list[str]) -> dict:
    idx = {}
    for i, h in enumerate(header):
        key = DCE_COLUMNS.get(h)
        if key is not None and key not in idx:
            idx[key] = i
    return idx


def cell_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def cell_number(v) -> float | None:
    t = cell_text(v).replace(",", "")
    if t == "":
        return None
    try:
        return float(t)
    except ValueError:
        return None


def describe_dce_table(header: list[str], rows: list[list]) -> dict:
    idx = column_index(header)
    missing = [k for k in ("contract", "date", "volume", "settle") if k not in idx]
    if missing:
        return {"header": header, "missing_columns": missing}
    recs = []
    for r in rows:
        if not any(cell_text(v) for v in r):
            continue
        get = lambda k: r[idx[k]] if idx[k] < len(r) else None
        recs.append((cell_text(get("contract")), cell_text(get("date")), cell_number(get("volume")) or 0.0,
                     cell_number(get("settle"))))
    days = sorted({d for _, d, _, _ in recs})
    traded_days = sorted({d for _, d, v, _ in recs if v > 0})
    by_contract = collections.Counter(c for c, _, v, _ in recs if v > 0)
    top = by_contract.most_common(1)
    return {
        "header": header, "rows": len(recs), "blank_rows_skipped": len(rows) - len(recs),
        "prefixes": sorted({"".join(ch for ch in c if not ch.isdigit()) for c, _, _, _ in recs}),
        "contracts": len({c for c, _, _, _ in recs}),
        "trading_days": len(days), "first_day": days[0] if days else None, "last_day": days[-1] if days else None,
        "days_with_volume": len(traded_days),
        "rows_with_volume": sum(v > 0 for _, _, v, _ in recs),
        "volume_total": fmt(sum(v for _, _, v, _ in recs), 12),
        "most_traded_contract": top[0][0] if top else None,
        "most_traded_contract_days": top[0][1] if top else 0,
        "traded_days_list": traded_days,
    }


# ------------------------------------------------- CEPEA and FRED

def parse_cepea(cells: list[list]) -> dict:
    """cells: the sheet as rows of values; the header row starts with 'Data'."""
    title = next((cell_text(r[0]) for r in cells if r and cell_text(r[0])), "")
    head_at = next((i for i, r in enumerate(cells) if r and cell_text(r[0]) == "Data"), None)
    if head_at is None:
        return {"title": title, "missing_columns": ["Data"]}
    header = [cell_text(v) for v in cells[head_at]]
    days, brl, usd, bad = [], {}, {}, 0
    for r in cells[head_at + 1:]:
        t = cell_text(r[0]) if r else ""
        if not t:
            continue
        try:
            d = datetime.strptime(t, "%d/%m/%Y").date()
        except ValueError:
            bad += 1
            continue
        days.append(d)
        brl[d], usd[d] = cell_number(r[1]), cell_number(r[2])
    in_w = [d for d in days if WINDOW[0] <= d.isoformat() <= WINDOW[1]]
    pairs = [(brl[d], usd[d]) for d in in_w if brl[d] is not None and usd[d] not in (None, 0.0)]
    return {
        "title": title, "header": header, "rows": len(days), "unparsed_rows": bad,
        "first_day": days[0].isoformat() if days else None, "last_day": days[-1].isoformat() if days else None,
        "strictly_increasing": all(a < b for a, b in zip(days, days[1:])),
        "days_in_window": len(in_w),
        "brl_min": fmt(min(p[0] for p in pairs)) if pairs else None, "brl_max": fmt(max(p[0] for p in pairs)) if pairs else None,
        "usd_min": fmt(min(p[1] for p in pairs)) if pairs else None, "usd_max": fmt(max(p[1] for p in pairs)) if pairs else None,
        "brl_per_usd_min": fmt(min(p[0] / p[1] for p in pairs), 5) if pairs else None,
        "brl_per_usd_max": fmt(max(p[0] / p[1] for p in pairs), 5) if pairs else None,
        "days_list": sorted(d.isoformat() for d in in_w if brl[d] is not None and usd[d] is not None),
    }


def read_cepea(data: bytes) -> list[list]:
    try:
        import xlrd
    except ImportError as e:
        raise RuntimeError("xlrd is needed to read the CEPEA workbook (pip install xlrd)") from e
    # the server's workbook shares sectors between the root storage and the workbook stream, which
    # xlrd calls corruption; the file is whole (its size is the served length), and xlrd reads it
    # when told to go on
    with contextlib.redirect_stdout(io.StringIO()):
        wb = xlrd.open_workbook(file_contents=data, ignore_workbook_corruption=True, logfile=io.StringIO())
    sh = wb.sheet_by_index(0)
    return [[sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(sh.nrows)]


def parse_fred(text: str) -> dict:
    rows = list(csv.reader(io.StringIO(text)))
    body = [r for r in rows[1:] if r]
    missing = [r for r in body if r[1].strip() in (".", "")]
    in_w = [r for r in body if WINDOW[0] <= r[0] <= WINDOW[1]]
    vals = [float(r[1]) for r in in_w if r[1].strip() not in (".", "")]
    return {
        "header": rows[0], "rows": len(body), "missing": len(missing),
        "first_day": body[0][0], "last_day": body[-1][0],
        "days_in_window": len(in_w), "missing_in_window": len(in_w) - len(vals),
        "min_in_window": fmt(min(vals)) if vals else None, "max_in_window": fmt(max(vals)) if vals else None,
        "days_list": sorted(r[0] for r in in_w if r[1].strip() not in (".", "")),
    }


def joint_by_year(series: dict[str, list[str]]) -> dict:
    """series: name -> ISO days with a value. Per year: each series' count, and the days all share."""
    out = {}
    for y in YEARS:
        sets = {k: {d for d in v if d.startswith(str(y))} for k, v in series.items()}
        both = set.intersection(*sets.values()) if sets else set()
        out[str(y)] = dict(sorted({**{k: len(s) for k, s in sets.items()}, "all": len(both)}.items()))
    return out


def iso(d8: str) -> str:
    return f"{d8[:4]}-{d8[4:6]}-{d8[6:8]}"


# ------------------------------------------------- the whole reading

def describe(raw: Path) -> dict:
    manifest = json.loads((raw / MANIFEST_NAME).read_text(encoding="utf-8"))
    pages = sorted(k for k in manifest if k.startswith("agtransport/") and k.endswith(".json"))
    agt = [row for k in pages for row in json.loads(load_checked(raw, k, manifest).decode("utf-8"))]
    count = manifest.get("agtransport/_count", {}).get("rows")
    objects = {"agtransport": {"rows": len(agt), "rows_at_fetch": count, "markets": describe_agt(agt)}}

    dce, traded = {}, collections.defaultdict(list)
    for k in sorted(m for m in manifest if m.startswith("dce/")):
        year, product = k[4:8], k[9:].rsplit(".", 1)[0]
        tables = [(label, describe_dce_table(h, rows)) for label, h, rows in dce_tables(load_checked(raw, k, manifest), k)]
        for label, t in tables:
            days = t.pop("traded_days_list", [])
            if product in ("no2_soybeans", "soybean_meal"):
                traded["dce_b_traded" if product == "no2_soybeans" else "dce_m_traded"] += [iso(d) for d in days]
            dce[f"{k} {label}"] = {"year": year, "product": product, **t}
    objects["dce"] = dce

    cepea = parse_cepea(read_cepea(load_checked(raw, "cepea/soja_paranagua_series.xls", manifest)))
    fred = parse_fred(load_checked(raw, "fred/DEXCHUS.csv", manifest).decode("utf-8-sig"))
    series = {"dce_b_traded": traded["dce_b_traded"], "dce_m_traded": traded["dce_m_traded"],
              "cepea": cepea.pop("days_list", []), "fred": fred.pop("days_list", [])}
    objects["cepea"], objects["fred"] = cepea, fred
    objects["joint_days_by_year"] = joint_by_year(series)
    objects["export_basis_weeks_by_year"] = {
        m: objects["agtransport"]["markets"].get(m, {}).get("weeks_by_year")
        for m in ("Gulf - Louisiana", "Portland")}
    return objects


def print_objects(o: dict) -> None:
    a = o["agtransport"]
    print(f"agtransport  {a['rows']} rows (count at fetch {a['rows_at_fetch']})")
    print(f"  {'market':22s} {'type':17s} {'weeks':>5s}  {'2016':>4s} {'2017':>4s} {'2018':>4s} {'2019':>4s} {'2020':>4s}"
          f"  {'gap d':>5s}  {'dup':>3s}  {'|bid-fut-basis|':>15s}  basis range")
    for name, m in a["markets"].items():
        wy = m["weeks_by_year"]
        print(f"  {name:22s} {'/'.join(m['market_type']):17s} {m['weeks']:5d}  "
              + " ".join(f"{wy[str(y)]:4d}" for y in YEARS)
              + f"  {m['longest_gap_days']:5d}  {m['duplicate_rows']:3d}  {m['bid_minus_futures_minus_basis_max']:15.3g}"
              + f"  {m['basis_min']} .. {m['basis_max']}")
    print("\ndce")
    for k, t in o["dce"].items():
        if "missing_columns" in t:
            print(f"  {k}: missing columns {t['missing_columns']} in header {t['header']}")
            continue
        print(f"  {k:60s} prefixes {','.join(t['prefixes']):3s} days {t['trading_days']:3d} {t['first_day']}..{t['last_day']}"
              f"  contracts {t['contracts']:2d}  days with volume {t['days_with_volume']:3d}  rows with volume {t['rows_with_volume']:4d}/{t['rows']:4d}"
              f"  most traded {t['most_traded_contract']} ({t['most_traded_contract_days']} d)")
    c, f = o["cepea"], o["fred"]
    print(f"\ncepea  {c.get('title')}  header {c.get('header')}  rows {c.get('rows')}  {c.get('first_day')}..{c.get('last_day')}"
          f"  increasing {c.get('strictly_increasing')}  unparsed {c.get('unparsed_rows')}")
    print(f"  window: {c.get('days_in_window')} days, R$ {c.get('brl_min')}..{c.get('brl_max')}, US$ {c.get('usd_min')}..{c.get('usd_max')},"
          f" R$ per US$ {c.get('brl_per_usd_min')}..{c.get('brl_per_usd_max')}")
    print(f"fred   header {f['header']}  rows {f['rows']}  {f['first_day']}..{f['last_day']}  missing {f['missing']}")
    print(f"  window: {f['days_in_window']} days, {f['missing_in_window']} missing, {f['min_in_window']}..{f['max_in_window']}")
    print("\njoint days by year (a day counts for DCE when the product traded)")
    for y, d in o["joint_days_by_year"].items():
        print(f"  {y}  " + "  ".join(f"{k} {v:3d}" for k, v in d.items()))
    print("export basis weeks by year")
    for m, wy in o["export_basis_weeks_by_year"].items():
        print(f"  {m:18s} {wy}")


# ------------------------------------------------- self-test

def selftest() -> int:
    checks, fails = 0, []

    def expect(cond, what):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(what)

    with tempfile.TemporaryDirectory() as td:
        raw = Path(td)
        (raw / "x.bin").write_bytes(b"abc")
        man = {"x.bin": {"sha256": sha256(b"abd")}}
        try:
            load_checked(raw, "x.bin", man)
            expect(False, "a file that differs from its manifest hash is read")
        except RuntimeError:
            pass
        expect(load_checked(raw, "x.bin", {"x.bin": {"sha256": sha256(b"abc")}}) == b"abc",
               "a file that matches its manifest hash is refused")

    rows = [{"date": f"2018-01-{d:02d}T00:00:00.000", "market_name": "Gulf - Louisiana", "market_type": "30-Day to Arrive",
             "source": "s", "bid": "10.00", "futures_price": "9.50", "basis": "0.50", "contract_month": "Mar"}
            for d in (5, 12, 26)]
    rows.append(dict(rows[0], date="2018-02-02T00:00:00.000", basis="0.51"))
    m = describe_agt(rows)["Gulf - Louisiana"]
    expect(m["weeks"] == 4 and m["longest_gap_days"] == 14, "the longest gap between week ending dates is misread")
    expect(abs(m["bid_minus_futures_minus_basis_max"] - 0.01) < 1e-9, "a basis off bid minus futures is not reported")
    expect(m["weeks_by_year"]["2018"] == 4 and m["duplicate_rows"] == 0, "weeks per year or duplicates are misread")
    m2 = describe_agt(rows + [dict(rows[1])])["Gulf - Louisiana"]
    expect(m2["duplicate_rows"] == 1, "a repeated market-week is not counted")

    head = ["ROWNUM", "合约", "日期", "前收盘价", "前结算价", "开盘价", "最高价", "最低价", "收盘价", "结算价",
            "涨跌1", "涨跌2", "成交量", "成交金额", "持仓量"]
    idx = column_index(head)
    expect(idx["close"] == 8 and idx["settle"] == 9, "a header name is matched inside a longer one (前收盘价 read as 收盘价)")
    csv_text = ",".join(f'"{h}"' for h in head) + "\n" + "\n".join(
        f'"{i}","b1809","2018070{d}","3500","3500","0","0","0","3500","3510","0","0","{v}","0","5"'
        for i, (d, v) in enumerate(((2, 0), (3, 12), (6, 7)), 1)) + "\n"
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as z:
        z.writestr("b.csv", csv_text.encode("gb18030"))
    t_csv = [describe_dce_table(h, r) for _, h, r in dce_tables(zbuf.getvalue(), "x.zip")][0]
    expect(t_csv["trading_days"] == 3 and t_csv["days_with_volume"] == 2 and t_csv["prefixes"] == ["b"]
           and t_csv["most_traded_contract"] == "b1809", "a zipped gb18030 csv is misread")

    try:
        import openpyxl
        have_openpyxl = True
    except ImportError:
        have_openpyxl = False
    if have_openpyxl:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["   ", "ROWNUM", "合约", "日期", "前收盘价", "前结算价", "开盘价", "最高价", "最低价", "收盘价", "结算价",
                   "涨跌1", "涨跌2", "成交量", "成交额", "持仓量"])
        ws.append([None, 1, "m1809", 20180702, 3000, 3000, 3001, 3002, 2999, 3000, 3000.5, 0, 0, 100, 3.0e8, 5])
        ws.append([None, 2, "m1809", 20180703, 3000, 3000, 3001, 3002, 2999, 3000, 3000.5, 0, 0, 0, 0, 5])
        ws.append([None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None])
        xbuf = io.BytesIO()
        wb.save(xbuf)
        t_x = [describe_dce_table(h, r) for _, h, r in dce_tables(xbuf.getvalue(), "y.xlsx")][0]
        expect(t_x["trading_days"] == 2 and t_x["days_with_volume"] == 1 and t_x["blank_rows_skipped"] == 1
               and t_x["prefixes"] == ["m"] and t_x["first_day"] == "20180702",
               "a workbook with a blank first column and numeric cells is misread")
        zbuf2 = io.BytesIO()
        with zipfile.ZipFile(zbuf2, "w") as z:
            z.writestr("2018011113545470783.csv", xbuf.getvalue())
        try:
            t_z = [describe_dce_table(h, r) for _, h, r in dce_tables(zbuf2.getvalue(), "c.zip")][0]
        except Exception:
            t_z = {}
        expect(t_z.get("trading_days") == 2, "a workbook inside a zip under a .csv name is not read as a workbook")
    else:
        expect(False, "openpyxl is not installed, so the workbook cases are not checked")

    cells = [["INDICADOR DA SOJA CEPEA/ESALQ - PARANAGUÁ", "", ""], ["", "", ""], ["Fonte: Cepea", "", ""],
             ["Data", "À vista R$", "À vista US$"], ["29/12/2015", 80.0, 20.0], ["04/01/2016", 82.0, 20.5],
             ["05/01/2016", 83.0, 20.75], ["bad", 1.0, 1.0]]
    c = parse_cepea(cells)
    expect(c["rows"] == 3 and c["unparsed_rows"] == 1 and c["days_in_window"] == 2 and c["strictly_increasing"]
           and c["days_list"] == ["2016-01-04", "2016-01-05"] and abs(c["brl_per_usd_min"] - 4.0) < 1e-9,
           "the CEPEA sheet is misread")
    c2 = parse_cepea(cells[:5] + [["28/12/2015", 1.0, 1.0]])
    expect(not c2["strictly_increasing"], "dates out of order pass as increasing")

    f = parse_fred("observation_date,DEXCHUS\n2015-12-31,6.49\n2016-01-04,6.51\n2016-01-05,.\n2016-01-06,6.55\n")
    expect(f["rows"] == 4 and f["missing"] == 1 and f["days_in_window"] == 3 and f["missing_in_window"] == 1
           and f["days_list"] == ["2016-01-04", "2016-01-06"], "the FRED file is misread")

    j = joint_by_year({"a": ["2016-01-04", "2016-01-05", "2017-01-03"], "b": ["2016-01-05", "2017-01-03"]})
    expect(j["2016"] == {"a": 2, "all": 1, "b": 1} and j["2017"]["all"] == 1 and j["2018"]["all"] == 0,
           "joint days are miscounted")

    for what in fails:
        print(f"SELFTEST FAIL  {what}")
    print(f"selftest: {checks - len(fails)} of {checks} passed")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    objects = describe(RAW)
    print_objects(objects)
    record = {
        "stage": "B115",
        "config": {"window": list(WINDOW), "raw": "data/b115/raw", "manifest": MANIFEST_NAME},
        "objects": objects,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"\nrecord {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
