"""Fetch the euro area series B112 reads: where central bank reserves sit, where they come in,
and how much of each national banking system's business crosses a border.

What this is for. B112 asks how long newly created reserves stay ahead in the national banking
system they first land in, and whether that time follows the cross-border edges or the rules
that set the price of holding reserves (the corridor and the two-tier system). The classes are
the national components of the Eurosystem: minimum reserves "shall be held on reserve accounts,
denominated in euro, with the relevant NCBs in each euro area Member State in which they are
established" (Regulation (EU) 2021/378, Article 3(1)(b)). So the class a unit of reserves sits
in is read off the balance sheet of that central bank.

What each dataflow carries here:
  TGB  each central bank's TARGET balance, monthly from 2008-05, end of period and period average
  ILM  each central bank's balance sheet, monthly from 2016-06: current accounts and deposit
       facility (the reserves), longer-term refinancing (where refinancing enters), securities
       held for monetary policy (what that central bank bought), banknotes, government deposits;
       and for the euro area the weekly statement, the daily liquidity series and the
       maintenance period averages
  BSI  each country's MFI loans to and deposits from the central bank and from other MFIs,
       domestic and other euro area counterparts apart, monthly from 1999-01; and total assets
  PSS  value and number of TARGET payments sent inside each national component and to other
       components, annual
  FM   the key ECB rates, daily

Rules this obeys:
  - enumerate before choosing (`D12`): every key below was chosen from the series keys the
    dataflow returned on 2026-09-16, and every request carries the series count that
    enumeration found, so a response with fewer series is named rather than accepted
  - resumable: a file on disk that passes the checks is skipped, so a rerun after a timeout
    costs only what is missing
  - never deletes: a file that fails the checks is renamed with a suffix and fetched again
  - detects truncation: every row has the header's column count, every series has strictly
    increasing periods and numeric values, and the metadata file names the same series
  - measured cost only (`D38`): each request prints the seconds it took and no total is quoted

Run from the repo root with the venv active:
    python experiments/b112_fetch.py --list       # the requests, no network
    python experiments/b112_fetch.py --fetch
    python experiments/b112_fetch.py --check      # re-verify what is on disk, no network
    python experiments/b112_fetch.py --selftest   # seeded faults, no network
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import io
import json
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "b112" / "raw"
MANIFEST = RAW / "manifest.json"

API = "https://data-api.ecb.europa.eu/service/data"
UA = "monetary-topology research fetcher (contact via repository)"
TIMEOUT = 180
PAUSE = 1.0

# The twenty-one national components with a balance sheet in ILM and a TARGET balance in TGB,
# as enumerated on 2026-09-16. `4F` is the ECB itself, `U2` the euro area as a whole.
COUNTRIES = ("AT", "BE", "BG", "CY", "DE", "EE", "ES", "FI", "FR", "GR", "HR",
             "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PT", "SI", "SK")

# Weekly euro area statement, grouped by the counterpart area and currency each item carries.
WEEKLY = {
    "u2_eur": ("A050000+A050100+A050200+A050300+A050400+A050500+A050600+A060000+A070000"
               "+A070100+A070200+A080000+L020000+L020100+L020200+L020300+L020400+L020500"
               "+L050000+L050100+L050200", "U2.EUR", 21),
    "u4_eur": ("A040000+A040100+A040200+L060000", "U4.EUR", 4),
    "z5_eur": ("L010000+L030000+L040000", "Z5.EUR", 3),
    "z5_z01": ("A110000+L120000+L140000+L150000+T000000", "Z5.Z01", 5),
}


def requests() -> list[dict]:
    """Every request, with the series count enumeration found for it."""
    out = [dict(name="tgb_all", flow="TGB", key="M...A094T.U2.EUR.", start=None, expect=46)]
    for c in COUNTRIES + ("4F",):
        out.append(dict(name=f"ilm_m_{c.lower()}", flow="ILM", key=f"M.{c}....", start=None,
                        expect=54 if c == "4F" else 55))
    out.append(dict(name="ilm_m_u2_mp", flow="ILM",
                    key="M.U2.C.L020100MP+L020200MP+A050200MP+A070100MP+A050100MP+A050500MP"
                        "+A050A00MP+L050100MP.U2.EUR", start=None, expect=8))
    out.append(dict(name="ilm_m_u2_mp_notes", flow="ILM", key="M.U2.C.L010000MP.Z5.EUR",
                    start=None, expect=1))
    for tag, (items, tail, n) in WEEKLY.items():
        out.append(dict(name=f"ilm_w_{tag}", flow="ILM", key=f"W.U2.C.{items}.{tail}",
                        start="2008-01-01", expect=n))
    out.append(dict(name="ilm_d_u2", flow="ILM",
                    key="D.U2.C.EXLIQ+MRR+L020100+L020200+A050500+NLIQ+TOMO+BMK1.U2.EUR",
                    start="2008-01-01", expect=8))
    out.append(dict(name="ilm_d_u2_faaf", flow="ILM", key="D.U2.C.FAAF1+FAAF2.Z5.Z01",
                    start="2008-01-01", expect=2))
    for c in COUNTRIES + ("U2",):
        out.append(dict(name=f"bsi_interbank_{c.lower()}", flow="BSI",
                        key=f"M.{c}.N.A.A20+L20.A.1.U2+U5+U6.1000+1100+1200.Z01.E",
                        start=None, expect=18))
        out.append(dict(name=f"bsi_assets_{c.lower()}", flow="BSI",
                        key=f"M.{c}.N.A.T00.A.1.Z5.0000.Z01.E", start=None, expect=1))
    out.append(dict(name="pss_target", flow="PSS", key="A....P101.....", start=None,
                    expect=1185))
    out.append(dict(name="fm_key_rates", flow="FM",
                    key="D.U2.EUR.4F.KR.DFR+MLFR+MRR_FR+MRR_MBR+MRR_RT.LEV",
                    start="2007-01-01", expect=5))
    names = [r["name"] for r in out]
    assert len(names) == len(set(names)), "two requests share a file name"
    return out


def url_of(req: dict, detail: str) -> str:
    q = f"format=csvdata&detail={detail}"
    if req["start"]:
        q += f"&startPeriod={req['start']}"
    return f"{API}/{req['flow']}/{req['key']}?{q}"


def get(url: str) -> str:
    r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/csv"})
    with urllib.request.urlopen(r, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8")


# ---------------------------------------------------------------------------
# Checks. Each returns a list of problems; an empty list means the file is usable.
# ---------------------------------------------------------------------------

def _rows(text: str) -> tuple[list[str], list[list[str]], list[str]]:
    problems = []
    if not text.endswith("\n"):
        problems.append("does not end with a newline")
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as e:
        return [], [], [f"does not parse as CSV: {e}"]
    rows = [r for r in rows if r]
    if not rows:
        return [], [], ["empty"]
    return rows[0], rows[1:], problems


def check_data(text: str, expect: int) -> tuple[list[str], dict]:
    """Column count, period order, numeric values, series count against enumeration."""
    header, body, problems = _rows(text)
    if not header:
        return problems, {}
    for col in ("KEY", "TIME_PERIOD", "OBS_VALUE"):
        if col not in header:
            return problems + [f"no {col} column (header starts {header[:4]})"], {}
    k, t, v = header.index("KEY"), header.index("TIME_PERIOD"), header.index("OBS_VALUE")
    last: dict[str, str] = {}
    first: dict[str, str] = {}
    counts: dict[str, int] = {}
    bad_width = bad_order = bad_value = 0
    for row in body:
        if len(row) != len(header):
            bad_width += 1
            continue
        key, period, value = row[k], row[t], row[v]
        if key in last and period <= last[key]:
            bad_order += 1
        if value != "":
            try:
                float(value)
            except ValueError:
                bad_value += 1
        first.setdefault(key, period)
        last[key] = period
        counts[key] = counts.get(key, 0) + 1
    if bad_width:
        problems.append(f"{bad_width} row(s) with a column count other than the header's")
    if bad_order:
        problems.append(f"{bad_order} period(s) not after the previous one in the same series")
    if bad_value:
        problems.append(f"{bad_value} non-numeric value(s)")
    if len(counts) < expect:
        problems.append(f"{len(counts)} series, enumeration found {expect}")
    summary = {"series": len(counts), "rows": sum(counts.values()),
               "first": min(first.values()) if first else None,
               "last": max(last.values()) if last else None}
    return problems, summary


def check_meta(text: str, data_keys: set[str]) -> list[str]:
    header, body, problems = _rows(text)
    if not header:
        return problems
    for col in ("KEY", "TITLE", "UNIT", "UNIT_MULT"):
        if col not in header:
            return problems + [f"metadata has no {col} column"]
    k = header.index("KEY")
    width = len(header)
    keys = {r[k] for r in body if len(r) == width}
    if any(len(r) != width for r in body):
        problems.append("metadata has a row with a column count other than the header's")
    missing = sorted(data_keys - keys)
    if missing:
        problems.append(f"metadata does not name {len(missing)} series, first {missing[0]}")
    return problems


def keys_in(text: str) -> set[str]:
    header, body, _ = _rows(text)
    if "KEY" not in header:
        return set()
    k = header.index("KEY")
    return {r[k] for r in body if len(r) == len(header)}


def retire(path: Path, why: str) -> None:
    """Never delete: rename with a suffix and leave it where it was."""
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dead = path.with_name(f"{path.name}.expired_{stamp}_{why}")
    path.rename(dead)
    print(f"    renamed {path.name} -> {dead.name}")


def verify_pair(req: dict, data_path: Path, meta_path: Path) -> tuple[list[str], dict]:
    if not data_path.exists() or not meta_path.exists():
        return ["not on disk"], {}
    data = data_path.read_text(encoding="utf-8")
    problems, summary = check_data(data, req["expect"])
    problems += check_meta(meta_path.read_text(encoding="utf-8"), keys_in(data))
    return problems, summary


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list() -> int:
    reqs = requests()
    by_flow: dict[str, int] = {}
    for r in reqs:
        by_flow[r["flow"]] = by_flow.get(r["flow"], 0) + 1
        print(f"{r['name']:24s} {r['flow']:4s} expect {r['expect']:5d}  {r['key']}"
              + (f"  from {r['start']}" if r["start"] else ""))
    print(f"\n{len(reqs)} requests, each a data file and a metadata file: "
          + ", ".join(f"{f} {n}" for f, n in sorted(by_flow.items())))
    return 0


def cmd_fetch(only: str | None) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    reqs = [r for r in requests() if not only or only in r["name"]]
    left = []
    for i, req in enumerate(reqs, 1):
        tag = f"[{i}/{len(reqs)}] {req['name']}"
        data_path, meta_path = RAW / f"{req['name']}.csv", RAW / f"{req['name']}.meta.csv"
        problems, summary = verify_pair(req, data_path, meta_path)
        if not problems:
            print(f"{tag}: on disk, {summary['series']} series, {summary['rows']} rows, skipped")
            continue
        for p in (data_path, meta_path):
            if p.exists():
                retire(p, "failed_check")
        texts = {}
        for detail, path in (("dataonly", data_path), ("nodata", meta_path)):
            url = url_of(req, detail)
            t0 = time.time()
            try:
                texts[detail] = get(url)
            except urllib.error.HTTPError as e:
                body = e.read()[:300].decode("utf-8", errors="replace").replace("\n", " ")
                print(f"{tag}: HTTP {e.code} on {detail}, left for the next run\n    {url}\n"
                      f"    server said: {body}")
                break
            except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError,
                    ValueError) as e:
                # a read that times out, a stream cut short, or bytes that are not UTF-8 all
                # cost the same as an HTTP error: this request, left for the next run
                print(f"{tag}: {type(e).__name__} {e} on {detail}, left for the next run")
                break
            print(f"{tag}: {detail} {len(texts[detail])} chars in {time.time() - t0:.1f}s")
            time.sleep(PAUSE)
        if len(texts) < 2:
            left.append(req["name"])
            continue
        problems, summary = check_data(texts["dataonly"], req["expect"])
        problems += check_meta(texts["nodata"], keys_in(texts["dataonly"]))
        hard = [p for p in problems if not p.endswith(f"enumeration found {req['expect']}")]
        if hard:
            print(f"{tag}: not written: " + "; ".join(hard))
            left.append(req["name"])
            continue
        data_path.write_text(texts["dataonly"], encoding="utf-8", newline="")
        meta_path.write_text(texts["nodata"], encoding="utf-8", newline="")
        manifest[req["name"]] = {
            "flow": req["flow"], "key": req["key"], "start": req["start"],
            "expect": req["expect"], **summary,
            "sha256_data": hashlib.sha256(texts["dataonly"].encode("utf-8")).hexdigest(),
            "sha256_meta": hashlib.sha256(texts["nodata"].encode("utf-8")).hexdigest(),
            "fetched": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "short": [p for p in problems if p not in hard],
        }
        MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8",
                            newline="\n")
        note = f", SHORT: {problems[0]}" if problems else ""
        print(f"{tag}: written, {summary['series']} series, {summary['rows']} rows, "
              f"{summary['first']} to {summary['last']}{note}")
    if left:
        print(f"\n{len(left)} request(s) still missing, rerun --fetch: {', '.join(left)}")
        return 1
    print(f"\nall {len(reqs)} requests on disk under {RAW}")
    return 0


def cmd_check() -> int:
    bad = 0
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    for req in requests():
        data_path, meta_path = RAW / f"{req['name']}.csv", RAW / f"{req['name']}.meta.csv"
        problems, summary = verify_pair(req, data_path, meta_path)
        entry = manifest.get(req["name"])
        if not problems and entry:
            if hashlib.sha256(data_path.read_bytes()).hexdigest() != entry["sha256_data"]:
                problems.append("data file differs from the manifest hash")
        hard = [p for p in problems if not p.endswith(f"enumeration found {req['expect']}")]
        if hard:
            bad += 1
            print(f"{req['name']:24s} " + "; ".join(hard))
        else:
            print(f"{req['name']:24s} ok  {summary['series']:5d} series {summary['rows']:7d} rows"
                  f"  {summary['first']} to {summary['last']}"
                  + (f"  SHORT ({problems[0]})" if problems else ""))
    print(f"\n{bad} request(s) failing")
    return 1 if bad else 0


def cmd_selftest() -> int:
    """Seed each fault the checks exist for and require that it is caught."""
    good = ("KEY,FREQ,TIME_PERIOD,OBS_VALUE\n"
            "A.M.X,M,2020-01,1.5\nA.M.X,M,2020-02,2.5\nA.M.Y,M,2020-01,3\nA.M.Y,M,2020-02,\n")
    meta = 'KEY,TITLE,UNIT,UNIT_MULT\nA.M.X,"x, a title",EUR,6\nA.M.Y,y,EUR,6\n'
    p, s = check_data(good, 2)
    assert p == [] and s == {"series": 2, "rows": 4, "first": "2020-01", "last": "2020-02"}, (p, s)
    assert check_meta(meta, keys_in(good)) == []
    seeds = {
        "cut mid-row": (good[:-6], 2, "column count"),
        "no final newline": (good.rstrip("\n"), 2, "newline"),
        "repeated period": (good + "A.M.Y,M,2020-02,4\n", 2, "not after"),
        "period out of order": (good + "A.M.X,M,2019-12,4\n", 2, "not after"),
        "non-numeric value": (good.replace("2.5", "n/a"), 2, "non-numeric"),
        "series short of enumeration": (good, 3, "enumeration found 3"),
        "an error page served with 200": ("<html><body>busy</body></html>\n", 2, "no KEY"),
    }
    caught = 0
    for name, (text, expect, needle) in seeds.items():
        problems, _ = check_data(text, expect)
        ok = any(needle in q for q in problems)
        caught += ok
        print(f"  {'caught' if ok else 'MISSED'}  {name}: {problems}")
    meta_seeds = {
        "metadata missing a series": (meta.replace("A.M.Y,y,EUR,6\n", ""), "does not name"),
        "metadata without UNIT_MULT": (meta.replace(",UNIT_MULT", "").replace(",6", ""),
                                       "no UNIT_MULT"),
    }
    for name, (text, needle) in meta_seeds.items():
        problems = check_meta(text, keys_in(good))
        ok = any(needle in q for q in problems)
        caught += ok
        print(f"  {'caught' if ok else 'MISSED'}  {name}: {problems}")
    total = len(seeds) + len(meta_seeds)
    # the request table itself: unique names, and each key has the dimension count of its flow
    dims = {"TGB": 7, "ILM": 6, "BSI": 11, "PSS": 10, "FM": 7}
    shape_ok = all(len(r["key"].split(".")) == dims[r["flow"]] for r in requests())
    print(f"  {'caught' if shape_ok else 'MISSED'}  every key has its flow's dimension count")
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "x.csv"
        f.write_text("a", encoding="utf-8")
        retire(f, "test")
        renamed = [x.name for x in Path(d).iterdir()]
        kept = len(renamed) == 1 and renamed[0].startswith("x.csv.expired_")
    print(f"  {'caught' if kept else 'MISSED'}  a failed file is renamed, not removed")
    passed = caught == total and shape_ok and kept
    print(f"\nselftest: {caught} of {total} seeded faults caught; table shape "
          f"{'ok' if shape_ok else 'WRONG'}; rename {'ok' if kept else 'WRONG'}")
    return 0 if passed else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--list", action="store_true")
    g.add_argument("--fetch", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--selftest", action="store_true")
    ap.add_argument("--only", help="fetch only requests whose name contains this")
    a = ap.parse_args()
    if a.list:
        return cmd_list()
    if a.fetch:
        return cmd_fetch(a.only)
    if a.check:
        return cmd_check()
    if a.selftest:
        return cmd_selftest()
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
