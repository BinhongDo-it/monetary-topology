"""Fetch the Federal Reserve's discount window loan-level workbooks for B113.

What this is for. B113 reads which depository institutions have an edge to the discount
window. The Federal Reserve publishes every discount window loan, one workbook a quarter, from
22 July 2010 to 2024Q2, with the borrower's ABA routing number, and the Call Report's panel of
reporters carries the same number, so a loan joins to the filer whose fed funds price the
size arm reads.

Where the files are. The page https://www.federalreserve.gov/regreform/discount-window.htm
links each workbook by its full name. The folder part of those links is not a page: asked for
on its own it answers not found or 403, while the full names answer with the workbook. The
two 2010 workbooks sit under /newsevents/files/ and the rest under /regreform/files/; 2010Q3 to
2017Q4 are .xls and 2018Q1 to 2024Q2 are .xlsx, as the page lists them on 2026-09-16.

Rules this obeys:
  - resumable: a workbook already on disk that opens is skipped, so a re-run after a timeout
    costs only what is missing
  - never deletes and never overwrites: a download is written to a .part file and renamed to
    its own name only after it opens; a file in the way is renamed with an .expired suffix
  - detects truncation: an .xlsx must open as a zip whose members test clean and that holds a
    worksheet; an .xls must carry the compound-file header and end on a sector boundary; a
    download that fails either is left under its .part name and reported, never read
  - reports before it spends (`D38`): times the first download and prints the measured cost
    of the rest
  - writes data/b59/dw/MANIFEST.json with each workbook's URL, bytes, digest and retrieval date

Run from the repo root with the venv active:
    .\\.venv\\Scripts\\Activate.ps1
    python scripts/fetch_dw_lending.py
    python scripts/fetch_dw_lending.py --from 2016Q1
    python scripts/fetch_dw_lending.py --selftest
"""
import argparse
import datetime
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "b59" / "dw"
BASE = "https://www.federalreserve.gov"
FIRST, LAST = "2010Q3", "2024Q2"
OLE = bytes.fromhex("D0CF11E0A1B11AE1")


def quarters(first: str = FIRST, last: str = LAST):
    y, q = int(first[:4]), int(first[-1])
    out = []
    while f"{y}Q{q}" <= last:
        out.append((y, q))
        y, q = (y, q + 1) if q < 4 else (y + 1, 1)
    return out


def name_of(y: int, q: int) -> str:
    return f"dw_data_{y}_q{q}." + ("xlsx" if y >= 2018 else "xls")


def url_of(y: int, q: int) -> str:
    return f"{BASE}/{'newsevents' if y == 2010 else 'regreform'}/files/{name_of(y, q)}"


def opens(path: Path, kind: str) -> bool:
    """Whether a workbook on disk is whole, judged by its own bytes."""
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if kind == "xlsx":
        if data[:2] != b"PK":
            return False
        try:
            with zipfile.ZipFile(path) as z:
                return z.testzip() is None and any(n.startswith("xl/worksheets/") for n in z.namelist())
        except (zipfile.BadZipFile, OSError):
            return False
    if data[:8] != OLE or len(data) < 1024:
        return False
    sector = 1 << int.from_bytes(data[30:32], "little")
    return sector in (512, 4096) and (len(data) - 512) % sector == 0


def set_aside(path: Path, why: str) -> Path:
    """Rename a file that is in the way. Nothing here deletes or overwrites."""
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    new = path.with_name(f"{path.name}.expired_{stamp}_{why}")
    path.rename(new)
    return new


def fetch(y: int, q: int, manifest: dict, opener=urllib.request.urlopen) -> str:
    name, kind = name_of(y, q), name_of(y, q).rsplit(".", 1)[1]
    dest = OUT / name
    if dest.exists() and opens(dest, kind):
        if name not in manifest:
            data = dest.read_bytes()
            manifest[name] = {"url": url_of(y, q), "bytes": len(data),
                              "sha256": hashlib.sha256(data).hexdigest(),
                              "retrieved": "on disk before the manifest"}
        return "on disk"
    if dest.exists():
        set_aside(dest, "did_not_open")
    part = dest.with_name(name + ".part")
    if part.exists():
        set_aside(part, "earlier_part")
    req = urllib.request.Request(url_of(y, q), headers={"User-Agent": "Mozilla/5.0 (research download)"})
    with opener(req, timeout=120) as r, part.open("wb") as fh:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            fh.write(chunk)
    if not opens(part, kind):
        return f"downloaded {part.stat().st_size:,} bytes that do not open as .{kind}; left as {part.name}"
    part.rename(dest)
    data = dest.read_bytes()
    manifest[name] = {"url": url_of(y, q), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                      "retrieved": datetime.date.today().isoformat()}
    return "fetched"


def write_manifest(manifest: dict) -> None:
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n",
                                       encoding="utf-8", newline="\n")


def selftest() -> int:
    import io
    import tempfile
    fails = []

    def expect(ok, label):
        print("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            fails.append(label)

    qs = quarters()
    expect(len(qs) == 56 and qs[0] == (2010, 3) and qs[-1] == (2024, 2),
           "fifty-six quarters from 2010Q3 to 2024Q2")
    expect(len(quarters("2016Q1")) == 34, "and thirty-four from 2016Q1")
    expect(url_of(2010, 3) == BASE + "/newsevents/files/dw_data_2010_q3.xls"
           and url_of(2017, 4) == BASE + "/regreform/files/dw_data_2017_q4.xls"
           and url_of(2018, 1) == BASE + "/regreform/files/dw_data_2018_q1.xlsx"
           and url_of(2024, 2) == BASE + "/regreform/files/dw_data_2024_q2.xlsx",
           "each name and folder is the one the page links")
    global OUT
    saved = OUT
    with tempfile.TemporaryDirectory() as tmp:
        T = Path(tmp)
        good_x = T / "a.xlsx"
        with zipfile.ZipFile(good_x, "w") as z:
            z.writestr("xl/workbook.xml", "<workbook/>")
            z.writestr("xl/worksheets/sheet1.xml", "<sheet>" + "x" * 5000 + "</sheet>")
        raw = good_x.read_bytes()
        (T / "half.xlsx").write_bytes(raw[: len(raw) // 2])
        (T / "page.xlsx").write_bytes(b"<!DOCTYPE html><title>Page Not Found</title>")
        expect(opens(good_x, "xlsx"), "a whole .xlsx opens")
        expect(not opens(T / "half.xlsx", "xlsx"), "a truncated .xlsx does not")
        expect(not opens(T / "page.xlsx", "xlsx"), "an error page saved under an .xlsx name does not")
        with zipfile.ZipFile(T / "doc.xlsx", "w") as z:
            z.writestr("word/document.xml", "<document/>")
        expect(not opens(T / "doc.xlsx", "xlsx"), "nor does a whole zip that holds no worksheet")
        ole = bytearray(512 + 512 * 4)
        ole[:8] = OLE
        ole[30:32] = (9).to_bytes(2, "little")
        (T / "a.xls").write_bytes(bytes(ole))
        (T / "cut.xls").write_bytes(bytes(ole[:512 + 700]))
        (T / "page.xls").write_bytes(b"<!DOCTYPE html><title>Page Not Found</title>" + b" " * 2000)
        expect(opens(T / "a.xls", "xls"), "a compound file ending on a sector boundary opens")
        expect(not opens(T / "cut.xls", "xls"), "one cut inside a sector does not")
        expect(not opens(T / "page.xls", "xls"), "and an error page under an .xls name does not")
        blank = bytearray(512 + 512 * 4)
        blank[30:32] = (9).to_bytes(2, "little")
        (T / "blank.xls").write_bytes(bytes(blank))
        expect(not opens(T / "blank.xls", "xls"),
               "nor a file with the right length and sector field and no compound-file signature")

        OUT = T / "dw"
        OUT.mkdir()
        try:
            class Resp(io.BytesIO):
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

            man = {}
            (OUT / "dw_data_2024_q2.xlsx").write_bytes(b"not a workbook")
            st = fetch(2024, 2, man, opener=lambda req, timeout: Resp(raw))
            kept = [p for p in OUT.iterdir() if ".expired_" in p.name and "did_not_open" in p.name]
            expect(st == "fetched" and opens(OUT / "dw_data_2024_q2.xlsx", "xlsx")
                   and len(kept) == 1 and kept[0].read_bytes() == b"not a workbook",
                   "a file in the way is renamed with its bytes intact, and the download takes its name")
            expect(man["dw_data_2024_q2.xlsx"]["bytes"] == len(raw)
                   and man["dw_data_2024_q2.xlsx"]["sha256"] == hashlib.sha256(raw).hexdigest(),
                   "the manifest records the bytes and digest of what was kept")
            st2 = fetch(2024, 2, man, opener=lambda req, timeout: (_ for _ in ()).throw(AssertionError("fetched twice")))
            expect(st2 == "on disk", "a workbook already on disk that opens is not fetched again")
            st3 = fetch(2023, 4, man, opener=lambda req, timeout: Resp(b"<html>Page Not Found</html>"))
            expect("do not open" in st3 and (OUT / "dw_data_2023_q4.xlsx.part").exists()
                   and not (OUT / "dw_data_2023_q4.xlsx").exists(),
                   "a download that does not open stays under its .part name and is reported")
            st4 = fetch(2023, 4, man, opener=lambda req, timeout: Resp(raw))
            parts = [p for p in OUT.iterdir() if p.name.startswith("dw_data_2023_q4.xlsx.part.expired_")]
            expect(st4 == "fetched" and len(parts) == 1,
                   "and the next run renames that .part before writing a new one")
        finally:
            OUT = saved
    if fails:
        print("\n  selftest FAILED")
        return 1
    print("\n  selftest passed")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="first", default=FIRST)
    ap.add_argument("--to", dest="last", default=LAST)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    OUT.mkdir(parents=True, exist_ok=True)
    mpath = OUT / "MANIFEST.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
    todo = quarters(a.first, a.last)
    print(f"{len(todo)} quarter(s), {a.first} to {a.last}, into {OUT}")
    bad, measured = [], None
    for i, (y, q) in enumerate(todo):
        t = time.time()
        try:
            status = fetch(y, q, manifest)
        except urllib.error.HTTPError as e:
            status = f"HTTP {e.code} for {url_of(y, q)}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            status = f"failed: {e}"
        took = time.time() - t
        print(f"  {y}Q{q}  {status}  ({took:.1f} s)")
        if status not in ("fetched", "on disk"):
            bad.append((y, q, status))
        if status == "fetched":
            if measured is None:
                measured = took
                rest = len(todo) - i - 1
                print(f"  measured {measured:.1f} s for this workbook; {rest} more at most, "
                      f"about {measured * rest / 60:.1f} minutes")
            time.sleep(1.0)
        write_manifest(manifest)
    have = sum(1 for y, q in todo if (OUT / name_of(y, q)).exists())
    print(f"\n  on disk and whole: {have} of {len(todo)}")
    for y, q, s in bad:
        print(f"  NOT FETCHED {y}Q{q}: {s}")
    if bad:
        print("  run it again; what is on disk is kept and only the rest is fetched")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
