"""B147: turn each hospital file into one table of cells, and count what is in it.

A hospital's machine-readable file comes in three layouts (CSV with one line per item and payer,
CSV with one line per item and a block of columns per payer, JSON). This module reads any of them
into the same arrays, one entry per (row, payer and plan) cell, and writes them to a cache under
data/cache/b147/ keyed by the SHA-256 of the source file, so the files are parsed once.

    row   an item as the file prints it: every (code, code type) the line carries, setting,
          modifiers, drug unit and type, billing class, description. Lines that carry no code at
          all (a modifier's own line) are counted and left out.
    col   (payer name, plan name) as printed.
    cell  the method the file prints for it, the negotiated dollar amount, the negotiated
          percentage, whether an algorithm text is present, and the row's gross charge.

A byte that is not UTF-8 (one file carries Windows-1252 characters in its descriptions) is read as
the replacement character; no number is affected. Nothing is decided here. The module prints, for each file, the template version, the date, the
number of rows and columns, how many cells carry each method, and how many carry a dollar amount,
a percentage, only an algorithm, or nothing.

Cells are gathered in typed arrays (array.array), about forty bytes a cell, so a file of seven or
eight million cells stays well under a gigabyte while it is read. The two ways of gathering (typed
arrays, and the Python lists the first round used) give the same arrays; --selftest checks it on
planted files and --compare-store checks it on the files on disk against their caches.

The header row of a CSV is compared, name by name, with the column names of the CMS data dictionary
saved beside the files (template 3.0.0). A header the dictionary does not name is printed and not
read; the reader takes columns only by the names it knows.

Run from the repository root:

    python experiments/b147_parse.py              # parse what is not cached, print the census
    python experiments/b147_parse.py --only uihc_dt
    python experiments/b147_parse.py --selftest   # offline: the three layouts on planted files
    python experiments/b147_parse.py --compare-store garfield cvmc   # re-parse into a scratch cache, compare
"""

from __future__ import annotations

import argparse
import array
import csv
import ctypes
import hashlib
import io
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data" / "raw" / "b147"
CACHE = REPO / "data" / "cache" / "b147"
MD = ".md"      # the dictionary keeps the name it has at the source
DICTIONARY = RAW / "cms_dictionary" / ("CSV_README" + MD)
PARSER_VERSION = 3

HOSPITALS = ["garfield", "mh_tmc", "ohsu", "deaconess", "cvmc", "cheshire", "uihc_dt", "uihc"]
#: the two Iowa files are two campuses of one legal entity (State University of Iowa)
SAME_ENTITY = {"uihc": "State University of Iowa", "uihc_dt": "State University of Iowa"}
METHODS = ["percent of total billed charges", "fee schedule", "case rate", "per diem", "other"]
M_P, M_F, M_C, M_D, M_O, M_BLANK = 0, 1, 2, 3, 4, 5
METHOD_LETTER = "PFCDO-"

csv.field_size_limit(1 << 30)


def method_code(text) -> int:
    t = (text or "").strip().lower()
    if not t:
        return M_BLANK
    if t in METHODS:
        return METHODS.index(t)
    return M_O


def num(text):
    """(value, decimals that are not trailing zeros), or (nan, 0) when the field holds no number."""
    if text is None:
        return float("nan"), 0
    if isinstance(text, (int, float)):
        v = float(text)
        s = repr(round(v, 6))
    else:
        s = text.strip().replace(",", "").replace("$", "")
        if not s:
            return float("nan"), 0
        try:
            v = float(s)
        except ValueError:
            return float("nan"), 0
    if "e" in s.lower():
        return v, 6
    dec = len(s.split(".")[1].rstrip("0")) if "." in s else 0
    return v, dec


#: typecode of each cell field in the typed store; the numpy dtype it becomes
FIELDS = {"row": ("i", np.int32), "col": ("i", np.int32), "meth": ("b", np.int8), "dollar": ("d", np.float64),
          "ddec": ("b", np.int8), "pct": ("d", np.float64), "pdec": ("b", np.int8), "gross": ("d", np.float64),
          "algo": ("b", bool)}


class Table:
    def __init__(self, store: str = "array"):
        self.rows, self.row_keys = {}, []
        self.cols, self.col_keys = {}, []
        if store == "array":
            self.a = {k: array.array(tc) for k, (tc, _) in FIELDS.items()}
        elif store == "list":
            self.a = {k: [] for k in FIELDS}
        else:
            raise ValueError(store)
        self.store = store
        self.row_extra = []          # (gross, min, max, discounted cash) as printed, first seen
        self.left_out = {"lines without any code": 0}
        self.lines = 0

    def row(self, key, extra):
        i = self.rows.get(key)
        if i is None:
            i = self.rows[key] = len(self.row_keys)
            self.row_keys.append(key)
            self.row_extra.append(extra)
        return i

    def col(self, payer, plan):
        key = ((payer or "").strip(), (plan or "").strip())
        i = self.cols.get(key)
        if i is None:
            i = self.cols[key] = len(self.col_keys)
            self.col_keys.append(key)
        return i

    def cell(self, r, c, meth, dollar, pct, gross, algo):
        dv, dd = num(dollar)
        pv, pd = num(pct)
        gv, _ = num(gross)
        m = method_code(meth)
        if m == M_BLANK and not (dv == dv) and not (pv == pv) and not algo:
            return                    # an empty block in a wide file: the payer has no entry on this row
        a = self.a
        a["row"].append(r); a["col"].append(c); a["meth"].append(m)
        a["dollar"].append(dv); a["ddec"].append(dd); a["pct"].append(pv); a["pdec"].append(pd)
        a["gross"].append(gv); a["algo"].append(bool(algo))


def _row_key(get, header):
    codes = []
    for h in header:
        if h.startswith("code|") and h.count("|") == 1:
            c = get(h)
            if c:
                codes.append((get(h + "|type").upper(), c))
    codes = tuple(sorted(set(codes)))
    key = (codes, get("setting").lower(), get("modifiers"), get("drug_unit_of_measurement"),
           get("drug_type_of_measurement").upper(), get("billing_class").lower(), get("description"))
    return codes, key


def read_csv(stream, t: Table) -> dict:
    r = csv.reader(stream)
    meta_h = [h.strip() for h in next(r)]
    meta_v = next(r)
    meta = {h: v for h, v in zip(meta_h, meta_v) if h and len(h) < 60}
    header = ["|".join(p.strip() for p in h.split("|")) for h in next(r)]
    low = [h.lower() for h in header]
    idx = {h: i for i, h in enumerate(low)}
    wide = "payer_name" not in idx
    blocks = {}
    if wide:
        for i, h in enumerate(header):
            p = h.split("|")
            if p[0].lower() == "standard_charge" and len(p) == 4:
                blocks.setdefault((p[1], p[2]), {})[p[3].lower()] = i
        blocks = {k: v for k, v in blocks.items() if "methodology" in v or "negotiated_dollar" in v}
        col_ids = {k: t.col(*k) for k in blocks}
    for line in r:
        if not line or not any(line):
            continue
        t.lines += 1

        def get(name, line=line):
            i = idx.get(name)
            return line[i].strip() if i is not None and i < len(line) else ""

        codes, key = _row_key(get, low)
        if not codes:
            t.left_out["lines without any code"] += 1
            continue
        gross = get("standard_charge|gross")
        ri = t.row(key, (gross, get("standard_charge|min"), get("standard_charge|max"),
                         get("standard_charge|discounted_cash")))
        if wide:
            for k, b in blocks.items():
                def f(name, b=b):
                    i = b.get(name)
                    return line[i].strip() if i is not None and i < len(line) else ""
                t.cell(ri, col_ids[k], f("methodology"), f("negotiated_dollar"),
                       f("negotiated_percentage"), gross, f("negotiated_algorithm"))
        else:
            if not get("payer_name"):
                continue
            t.cell(ri, t.col(get("payer_name"), get("plan_name")), get("standard_charge|methodology"),
                   get("standard_charge|negotiated_dollar"), get("standard_charge|negotiated_percentage"),
                   gross, get("standard_charge|negotiated_algorithm"))
    return {"layout": "csv wide" if wide else "csv tall", "version": meta.get("version"),
            "last_updated_on": meta.get("last_updated_on"), "hospital_name": meta.get("hospital_name")}


def read_json(stream, t: Table) -> dict:
    doc = json.load(stream)
    for item in doc.get("standard_charge_information", []):
        codes = tuple(sorted({(str(c.get("type", "")).upper(), str(c.get("code", "")))
                              for c in item.get("code_information", []) if c.get("code")}))
        drug = item.get("drug_information") or {}
        for sc in item.get("standard_charges", []):
            t.lines += 1
            if not codes:
                t.left_out["lines without any code"] += 1
                continue
            mods = "|".join(sc.get("modifiers") or []) if isinstance(sc.get("modifiers"), list) else str(sc.get("modifiers") or "")
            payers = sc.get("payers_information") or []
            bc = str(sc.get("billing_class") or (payers[0].get("billing_class") if payers else "") or "").lower()
            key = (codes, str(sc.get("setting", "")).lower(), mods, str(drug.get("unit", "")),
                   str(drug.get("type", "")).upper(), bc, str(item.get("description", "")).strip())
            gross = sc.get("gross_charge")
            ri = t.row(key, (gross, sc.get("minimum"), sc.get("maximum"), sc.get("discounted_cash")))
            for p in payers:
                t.cell(ri, t.col(p.get("payer_name"), p.get("plan_name")), p.get("methodology"),
                       p.get("standard_charge_dollar"), p.get("standard_charge_percentage"), gross,
                       p.get("standard_charge_algorithm"))
    return {"layout": "json", "version": doc.get("version"), "last_updated_on": doc.get("last_updated_on"),
            "hospital_name": doc.get("hospital_name")}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def source_of(hid: str, raw: Path = RAW) -> Path:
    files = sorted(p for p in (raw / hid).iterdir()
                   if p.suffix.lower() in (".csv", ".zip", ".json") and ".expired" not in p.name)
    if len(files) != 1:
        raise SystemExit("expected one source file under %s, found %d" % (raw / hid, len(files)))
    return files[0]


def parse_file(path: Path, store: str = "array") -> tuple[Table, dict]:
    t = Table(store)
    suf = path.suffix.lower()
    if suf == ".zip":
        with zipfile.ZipFile(path) as z:
            members = [i for i in z.infolist() if i.filename.lower().endswith((".csv", ".json"))]
            if len(members) != 1:
                raise SystemExit("expected one data member in " + path.name)
            with z.open(members[0]) as b:
                if members[0].filename.lower().endswith(".csv"):
                    meta = read_csv(io.TextIOWrapper(b, encoding="utf-8-sig", errors="replace", newline=""), t)
                else:
                    meta = read_json(io.TextIOWrapper(b, encoding="utf-8-sig"), t)
            meta["member"] = members[0].filename
            meta["member_bytes"] = members[0].file_size
    elif suf == ".json":
        with open(path, encoding="utf-8-sig") as f:
            meta = read_json(f, t)
    else:
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            meta = read_csv(f, t)
    return t, meta


def to_arrays(t: Table) -> dict:
    a = t.a
    if t.store == "list":
        return {"row": np.asarray(a["row"], dtype=np.int32), "col": np.asarray(a["col"], dtype=np.int32),
                "meth": np.asarray(a["meth"], dtype=np.int8), "dollar": np.asarray(a["dollar"], dtype=np.float64),
                "ddec": np.asarray(a["ddec"], dtype=np.int8), "pct": np.asarray(a["pct"], dtype=np.float64),
                "pdec": np.asarray(a["pdec"], dtype=np.int8), "gross": np.asarray(a["gross"], dtype=np.float64),
                "algo": np.asarray(a["algo"], dtype=bool)}
    out = {}
    for k, (tc, dt) in FIELDS.items():
        raw = np.frombuffer(a[k], dtype={"i": np.int32, "b": np.int8, "d": np.float64}[tc]) if len(a[k]) else \
            np.zeros(0, dtype={"i": np.int32, "b": np.int8, "d": np.float64}[tc])
        out[k] = raw.astype(dt) if dt is bool else raw.copy()
    return out


# ---------------------------------------------------------------- the header against the dictionary (D54)

_DICT_PATTERNS = None


def dictionary_patterns(path: Path = DICTIONARY) -> list:
    """The column names the CMS CSV dictionary prints in bold in its tables, as regular expressions.

    Placeholders become patterns: [i] a number, [state] two letters, [payer_name] and [plan_name] any
    text without a bar. Names are compared lower-cased with the spaces around the bars removed."""
    global _DICT_PATTERNS
    if _DICT_PATTERNS is not None and path == DICTIONARY:
        return _DICT_PATTERNS
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = re.split(r"(?<!\\)\|", line)[1:3]
        for c in cells:
            for m in re.findall(r"\*\*(.+?)\*\*", c):
                names.add(m.replace("\\|", "|").replace("\\[", "[").replace("\\]", "]").replace("\\_", "_"))
    pats = []
    for n in sorted(names):
        n = "|".join(p.strip() for p in n.lower().split("|"))
        esc = re.escape(n)
        esc = esc.replace(re.escape("[i]"), r"\d+").replace(re.escape("[state]"), r"[a-z]{2}")
        esc = esc.replace(re.escape("[payer_name]"), r"[^|]+").replace(re.escape("[plan_name]"), r"[^|]*")
        pats.append(re.compile("^" + esc + "$"))
    if path == DICTIONARY:
        _DICT_PATTERNS = pats
    return pats


def header_names(path: Path) -> list:
    """Row three of a CSV (the column header), read without reading the rest of the file."""
    def first3(stream):
        r = csv.reader(stream)
        next(r); next(r)
        return ["|".join(p.strip() for p in h.split("|")).lower() for h in next(r)]
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            mem = [i for i in z.infolist() if i.filename.lower().endswith(".csv")]
            if len(mem) != 1:
                return []
            with z.open(mem[0]) as b:
                return first3(io.TextIOWrapper(b, encoding="utf-8-sig", errors="replace", newline=""))
    if path.suffix.lower() == ".csv":
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            return first3(f)
    return []


def header_check(path: Path, patterns: list | None = None) -> dict | None:
    """Each header name compared with the dictionary. None for a JSON file (its keys are read by name)."""
    names = header_names(path)
    if not names:
        return None
    pats = patterns if patterns is not None else dictionary_patterns()
    unknown = [n for n in names if n and not any(p.match(n) for p in pats)]
    return {"columns": len(names), "named_by_the_dictionary": len(names) - len(unknown), "not_named": unknown}


def peak_memory_bytes() -> int | None:
    """Peak working set of this process (Windows); None elsewhere."""
    if sys.platform != "win32":
        try:
            import resource
            return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
        except Exception:
            return None

    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    k32 = ctypes.WinDLL("kernel32")
    psapi = ctypes.WinDLL("psapi")
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong]
    if not psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
        return None
    return int(pmc.PeakWorkingSetSize)


def load(hid: str, raw: Path = RAW, cache: Path = CACHE, quiet: bool = False, trust_cache: bool = False,
         store: str = "array") -> dict:
    """Arrays, row keys, column keys and meta for one hospital, from the cache when it is current.

    trust_cache: read the cache without the source file (a copy of the cache taken to another machine);
    the meta then names the source by its SHA-256, which is all the check would have compared."""
    npz, side = cache / (hid + ".cells.npz"), cache / (hid + ".meta.json")
    if trust_cache:
        if not (npz.exists() and side.exists()):
            raise SystemExit("trust_cache: no cache for " + hid + " under " + str(cache))
        meta = json.loads(side.read_text(encoding="utf-8"))
        if meta.get("parser_version") != PARSER_VERSION:
            raise SystemExit("trust_cache: the cache of %s was written by parser %s, this is %s"
                             % (hid, meta.get("parser_version"), PARSER_VERSION))
        with np.load(npz, allow_pickle=False) as z:
            arr = {k: z[k] for k in z.files}
        return {"id": hid, "arr": arr, "meta": meta, "row_keys": meta["row_keys"],
                "col_keys": [tuple(c) for c in meta["col_keys"]], "row_extra": meta["row_extra"]}
    src = source_of(hid, raw)
    digest = sha256_file(src)
    cache.mkdir(parents=True, exist_ok=True)
    if npz.exists() and side.exists():
        meta = json.loads(side.read_text(encoding="utf-8"))
        if meta.get("source_sha256") == digest and meta.get("parser_version") == PARSER_VERSION:
            with np.load(npz, allow_pickle=False) as z:
                arr = {k: z[k] for k in z.files}
            return {"id": hid, "arr": arr, "meta": meta, "row_keys": meta["row_keys"],
                    "col_keys": [tuple(c) for c in meta["col_keys"]], "row_extra": meta["row_extra"]}
    if not quiet:
        print("parsing " + hid + " ...", flush=True)
    t, meta = parse_file(src, store)
    arr = to_arrays(t)
    meta.update({"source": src.name, "source_bytes": src.stat().st_size, "source_sha256": digest,
                 "parser_version": PARSER_VERSION, "lines": t.lines, "left_out": t.left_out,
                 "row_keys": [[list(map(list, k[0]))] + list(k[1:]) for k in t.row_keys],
                 "col_keys": [list(c) for c in t.col_keys],
                 "row_extra": [[None if x is None else str(x) for x in e] for e in t.row_extra]})
    tmp = cache / (hid + ".cells.tmp.npz")
    np.savez_compressed(tmp, **arr)
    tmp.replace(npz)
    side.write_text(json.dumps(meta, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return {"id": hid, "arr": arr, "meta": meta, "row_keys": meta["row_keys"],
            "col_keys": [tuple(c) for c in t.col_keys], "row_extra": meta["row_extra"]}


def census(h: dict) -> dict:
    a = h["arr"]
    n = len(a["row"])
    has_d = np.isfinite(a["dollar"]) & (a["dollar"] > 0)
    has_p = np.isfinite(a["pct"]) & (a["pct"] > 0)
    has_g = np.isfinite(a["gross"]) & (a["gross"] > 0)
    out = {"id": h["id"], "hospital_name": h["meta"].get("hospital_name"), "layout": h["meta"].get("layout"),
           "version": h["meta"].get("version"), "last_updated_on": h["meta"].get("last_updated_on"),
           "source": h["meta"].get("source"), "source_bytes": h["meta"].get("source_bytes"),
           "source_sha256": h["meta"].get("source_sha256"), "lines": h["meta"].get("lines"),
           "left_out": h["meta"].get("left_out"), "rows": len(h["row_keys"]), "columns": len(h["col_keys"]),
           "cells": int(n), "by_method": {}, "dollar_decimals": {}}
    try:
        out["header_check"] = header_check(source_of(h["id"]))
    except (SystemExit, OSError, StopIteration):
        out["header_check"] = None
    for m, name in enumerate(METHODS + ["(no method printed)"]):
        k = a["meth"] == m
        out["by_method"][name] = {
            "cells": int(k.sum()), "with_dollar": int((k & has_d).sum()),
            "with_percentage": int((k & has_p).sum()),
            "with_percentage_and_gross_no_dollar": int((k & has_p & has_g & ~has_d).sum()),
            "algorithm_only": int((k & a["algo"] & ~has_d & ~has_p).sum()),
            "nothing": int((k & ~a["algo"] & ~has_d & ~has_p).sum())}
    for d in range(0, 7):
        c = int((has_d & (a["ddec"] == d)).sum())
        if c:
            out["dollar_decimals"][str(d)] = c
    return out


def print_census(c: dict) -> None:
    print("== %-10s %s  [%s, template %s, updated %s]" % (c["id"], c["hospital_name"], c["layout"],
                                                        c["version"], c["last_updated_on"]))
    print("   lines %d  rows %d  columns %d  cells %d  left out %s" % (c["lines"], c["rows"], c["columns"],
                                                                     c["cells"], c["left_out"]))
    for name, v in c["by_method"].items():
        if v["cells"]:
            print("   %-34s cells %8d  dollar %8d  pct %8d  pct+gross only %8d  algorithm only %7d  nothing %7d"
                  % (name, v["cells"], v["with_dollar"], v["with_percentage"],
                     v["with_percentage_and_gross_no_dollar"], v["algorithm_only"], v["nothing"]))
    print("   decimals in printed dollars (trailing zeros dropped): " + str(c["dollar_decimals"]))
    hc = c.get("header_check")
    if hc is not None:
        print("   header: %d columns, %d named by the CMS dictionary; not named (not read): %s"
              % (hc["columns"], hc["named_by_the_dictionary"], hc["not_named"]))


def selftest() -> int:
    fails = []

    def ok(label, cond):
        print(("ok    " if cond else "FAIL  ") + label)
        if not cond:
            fails.append(label)

    tall = ('hospital_name,last_updated_on,version\n"H","2026-01-01","3.0.0"\n'
            'description,code|1,code|1|type,setting,modifiers,drug_unit_of_measurement,drug_type_of_measurement,'
            'standard_charge|gross,payer_name,plan_name,standard_charge|negotiated_dollar,'
            'standard_charge|negotiated_percentage,standard_charge|negotiated_algorithm,standard_charge|methodology\n'
            '"X","1","CPT","outpatient","","","","100.00","A","p","","80","","percent of total billed charges"\n'
            '"X","1","CPT","outpatient","","","","100.00","B","p","55.50","","","fee schedule"\n'
            '"Y","2","CPT","outpatient","","","","40.00","A","p","","","see contract","other"\n'
            '"Modifier","","","both","50","","","","A","p","","","","")\n')
    wide = ('hospital_name,last_updated_on,version\n"H","1/1/2026","3.0.0"\n'
            'description,code | 1,code | 1 | type,setting,modifiers,standard_charge | gross,'
            'standard_charge | A | p | negotiated_dollar,standard_charge | A | p | negotiated_percentage,'
            'standard_charge | A | p | methodology,standard_charge | B | p | negotiated_dollar,'
            'standard_charge | B | p | negotiated_percentage,standard_charge | B | p | methodology\n'
            '"X","1","CPT","outpatient","","100.00","","80","Percent of total billed charges","55.50","","Fee Schedule"\n'
            '"Y","2","CPT","outpatient","","40.00","","","","","",""\n')
    js = json.dumps({"hospital_name": "H", "version": "2.2.0", "last_updated_on": "2024-11-19",
                     "standard_charge_information": [
                         {"description": "X", "code_information": [{"code": "1", "type": "CPT"}],
                          "standard_charges": [{"gross_charge": 100.0, "setting": "outpatient", "payers_information": [
                              {"payer_name": "A", "plan_name": "p", "standard_charge_percentage": 80.0,
                               "methodology": "percent of total billed charges"},
                              {"payer_name": "B", "plan_name": "p", "standard_charge_dollar": 55.5,
                               "methodology": "fee schedule"}]}]}]})
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        results = {}
        for name, text in (("tall.csv", tall), ("wide.csv", wide), ("j.json", js)):
            p = d / name
            p.write_text(text, encoding="utf-8", newline="")
            t, meta = parse_file(p)
            a = to_arrays(t)
            results[name] = (t, meta, a)
            x = [(int(m), float(dl) if dl == dl else None, float(pc) if pc == pc else None)
                 for m, dl, pc, r in zip(a["meth"], a["dollar"], a["pct"], a["row"]) if r == 0]
            ok(name + ": row X reads a percentage cell of 80 and a fee-schedule cell of 55.50",
               sorted(x, key=str) == sorted([(M_P, None, 80.0), (M_F, 55.5, None)], key=str))
        t, meta, a = results["tall.csv"]
        ok("tall: the line without a code is left out and counted", t.left_out["lines without any code"] == 1)
        ok("tall: the algorithm-only cell is kept and flagged", bool(a["algo"][a["meth"] == M_O].all()) and int((a["meth"] == M_O).sum()) == 1)
        t, meta, a = results["wide.csv"]
        ok("wide: an empty payer block makes no cell", len(a["row"]) == 2 and meta["layout"] == "csv wide")
        ok("wide: headers with spaces around the bars are read", len(t.col_keys) == 2)
        z = d / "z.zip"
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("inner file.csv", tall)
        t2, meta2 = parse_file(z)
        ok("zip: the member is read in place and gives the same cells", repr(t2.a) == repr(results["tall.csv"][0].a))
        ok("num: trailing zeros are not counted as decimals", num("147.8400") == (147.84, 2) and num("770.0000") == (770.0, 0))
        ok("num: a float percentage keeps its printed decimals", num(86.57000000000001) == (86.57000000000001, 2))
        # the cache refuses a stale source
        raw, cache = d / "raw", d / "cache"
        (raw / "h").mkdir(parents=True)
        (raw / "h" / "f.csv").write_text(tall, encoding="utf-8", newline="")
        h1 = load("h", raw, cache, quiet=True)
        (raw / "h" / "f.csv").write_text(tall.replace("55.50", "66.60"), encoding="utf-8", newline="")
        h2 = load("h", raw, cache, quiet=True)
        ok("cache: a changed source file is parsed again", float(np.nanmax(h2["arr"]["dollar"])) == 66.6
           and float(np.nanmax(h1["arr"]["dollar"])) == 55.5)
        # the typed store gives the same arrays as the list store, on every planted layout
        for name in ("tall.csv", "wide.csv", "j.json"):
            ta, _ = parse_file(d / name, "array")
            tl, _ = parse_file(d / name, "list")
            aa, al = to_arrays(ta), to_arrays(tl)
            same = all(aa[k].dtype == al[k].dtype and aa[k].shape == al[k].shape
                       and aa[k].tobytes() == al[k].tobytes() for k in FIELDS)
            ok(name + ": typed arrays and lists give identical arrays", same and ta.row_keys == tl.row_keys)
        # a store that drops a field would be caught: corrupt one value in the typed store and compare
        ta, _ = parse_file(d / "tall.csv", "array")
        ta.a["dollar"][1] += 0.01
        tl, _ = parse_file(d / "tall.csv", "list")
        ok("the store comparison catches one changed cent",
           to_arrays(ta)["dollar"].tobytes() != to_arrays(tl)["dollar"].tobytes())
        # trust_cache reads the cache without the source
        moved = raw / "h" / "f.csv"
        moved.rename(raw / "h" / "f.csv.away")
        h3 = load("h", raw, cache, quiet=True, trust_cache=True)
        ok("trust_cache: the cache is read with the source gone, same arrays",
           h3["arr"]["dollar"].tobytes() == h2["arr"]["dollar"].tobytes())
        # the header against the dictionary: a planted dictionary with three names
        dic = d / ("dict" + MD)
        dic.write_text("| **description** | **description** | x |\n| **code \\| \\[i\\]** | **code \\| \\[i\\]** | x |\n"
                       "| **payer_name** | \\-- | x |\n| \\-- | **standard_charge \\| \\[payer_name\\] \\| \\[plan_name\\] "
                       "\\| negotiated_dollar** | x |\n", encoding="utf-8")
        pats = dictionary_patterns(dic)
        hdr = d / "hdr.csv"
        hdr.write_text('a,b\n"1","2"\ndescription,code | 3,payer_name,standard_charge | Aetna | PPO | negotiated_dollar,'
                       'mystery_price\n', encoding="utf-8", newline="")
        hc = header_check(hdr, pats)
        ok("header check: names the dictionary covers pass, an unknown name is reported",
           hc["not_named"] == ["mystery_price"] and hc["named_by_the_dictionary"] == 4)
    real = header_check_real()
    ok("header check: the real dictionary names the template's tall payer columns", real)
    print("\n%d failed" % len(fails))
    return 1 if fails else 0


def header_check_real() -> bool:
    if not DICTIONARY.exists():
        return True
    pats = dictionary_patterns()
    names = ["description", "code|1", "code|1|type", "setting", "standard_charge|gross", "payer_name", "plan_name",
             "standard_charge|negotiated_dollar", "standard_charge|methodology", "standard_charge|a b|c|negotiated_percentage"]
    return all(any(p.match(n) for p in pats) for n in names) and not any(p.match("mystery_price") for p in pats)


def compare_store(ids: list) -> int:
    """Re-parse with the typed store into a scratch cache and compare every array with the cache on disk."""
    bad = 0
    with tempfile.TemporaryDirectory() as d:
        for hid in ids:
            old = load(hid, quiet=True)
            new = load(hid, cache=Path(d), quiet=True, store="array")
            diff = [k for k in FIELDS if old["arr"][k].dtype != new["arr"][k].dtype
                    or old["arr"][k].tobytes() != new["arr"][k].tobytes()]
            keys_same = old["row_keys"] == json.loads(json.dumps(new["row_keys"])) and \
                [list(c) for c in old["col_keys"]] == [list(c) for c in new["col_keys"]]
            print("%-10s cells %9d  arrays %s  keys %s" % (hid, len(old["arr"]["row"]),
                                                            "identical" if not diff else "DIFFER " + str(diff),
                                                            "identical" if keys_same else "DIFFER"), flush=True)
            bad += bool(diff) or not keys_same
            del old, new
    print("peak memory %.2f GB" % ((peak_memory_bytes() or 0) / 1e9))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--compare-store", nargs="*")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.compare_store is not None:
        return compare_store(a.compare_store or HOSPITALS[:6])
    for hid in (a.only or HOSPITALS):
        h = load(hid)
        print_census(census(h))
        del h
        print("   peak memory of this process so far %.2f GB" % ((peak_memory_bytes() or 0) / 1e9), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
