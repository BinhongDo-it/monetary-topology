"""Fetch and inventory the World Bank Distortions to Agricultural Incentives
China spreadsheet (Anderson project, Working Paper 29).

Rules this obeys:
  - genuinely resumable: streams into a .part file and continues it with an
    HTTP Range request on the next run, so a timeout costs only the bytes
    still missing
  - never deletes: a bad or stale file is renamed with a suffix, not removed
  - reports before it spends: prints Content-Length from a HEAD first
  - prints an inventory, writes no criteria

Run from the repo root with the venv active:
    .\\.venv\\Scripts\\Activate.ps1
    python scripts/fetch_dai_china.py
Re-run it after a timeout; it picks up where it stopped.
"""
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "dai"
RAW.mkdir(parents=True, exist_ok=True)

BASE = "https://documents1.worldbank.org/curated/en/383671468315545700"
STEM = "560720NWP0CN0v1479B001PUBLIC10China"
TARGETS = {
    # name: list of candidate urls, tried in order
    "dai_china_wp29.txt": [
        f"{BASE}/txt/{STEM}.txt",
        f"{BASE}/text/{STEM}.txt",
    ],
    # The txt is pdftotext output: one spreadsheet cell per line, so columns
    # can only be rebuilt by guessing. The PDF keeps x/y coordinates, which is
    # why it is the one to parse. Same document, different rendering.
    "dai_china_wp29.pdf": [
        f"{BASE}/pdf/{STEM}.pdf",
    ],
}

MIN_BYTES = 20_000
SENTINEL = "China"
CHUNK = 65_536
READ_TIMEOUT = 300
ATTEMPTS = 4
UA = {"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity"}


def head(url: str):
    req = urllib.request.Request(url, headers=UA, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            n = r.headers.get("Content-Length")
            return (int(n) if n else None), r.headers.get("Accept-Ranges", "none")
    except Exception as e:
        return None, f"<HEAD failed: {type(e).__name__}>"


def integrity(path: Path, expect: int | None):
    if not path.exists():
        return False, "absent"
    n = path.stat().st_size
    if expect and n != expect:
        return False, f"size {n} != Content-Length {expect}"
    if n < MIN_BYTES:
        return False, f"too small ({n} bytes)"
    if path.suffix.lower() == ".pdf":
        with open(path, "rb") as fh:
            if fh.read(5) != b"%PDF-":
                return False, "no %PDF- magic, probably an error page"
            fh.seek(max(0, n - 2048))
            if b"%%EOF" not in fh.read():
                return False, "no %%EOF trailer, truncated"
        return True, f"ok ({n} bytes, pdf trailer present)"
    head_txt = path.read_text(encoding="utf-8", errors="ignore")[:4000]
    if SENTINEL not in head_txt:
        return False, "sentinel string missing, probably an error page"
    if "<html" in head_txt.lower():
        return False, "html body, not the document"
    return True, f"ok ({n} bytes)"


def park(path: Path, why: str) -> None:
    """Rename a file out of the way. Never removes anything."""
    i, bad = 0, path.with_suffix(path.suffix + ".corrupt")
    while bad.exists():
        i += 1
        bad = path.with_suffix(path.suffix + f".corrupt{i}")
    path.rename(bad)
    print(f"       parked -> {bad.name} ({why})")


def stream(url: str, part: Path, total: int | None) -> bool:
    """One attempt. Returns True if the body reached `total` (or ended cleanly)."""
    have = part.stat().st_size if part.exists() else 0
    headers = dict(UA)
    if have:
        headers["Range"] = f"bytes={have}-"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=READ_TIMEOUT) as r:
            resuming = r.status == 206
            if have and not resuming:
                print(f"       server ignored Range, restarting from 0")
                park(part, "server would not resume")
                have = 0
            mode = "ab" if (have and resuming) else "wb"
            with open(part, mode) as fh:
                while True:
                    buf = r.read(CHUNK)
                    if not buf:
                        break
                    fh.write(buf)
                    have += len(buf)
                    if total:
                        print(f"\r       {have:,} / {total:,} bytes"
                              f"  ({100*have/total:5.1f}%)", end="", flush=True)
                    else:
                        print(f"\r       {have:,} bytes", end="", flush=True)
            print()
        return total is None or have >= total
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"\n       interrupted at {have:,} bytes: {type(e).__name__}: {e}")
        return False


def fetch(name: str, urls: list[str]) -> Path | None:
    dest, part = RAW / name, RAW / (name + ".part")
    total, ranges = None, "none"
    for url in urls:
        total, ranges = head(url)
        print(f"  HEAD {url}\n       Content-Length={total}  Accept-Ranges={ranges}")
        if total:
            break
    ok, why = integrity(dest, total)
    if ok:
        print(f"  SKIP {name}: {why}")
        return dest
    if dest.exists():
        park(dest, why)
    for attempt in range(1, ATTEMPTS + 1):
        for url in urls:
            print(f"  GET  attempt {attempt}/{ATTEMPTS}  {url}")
            if stream(url, part, total):
                part.rename(dest)
                ok, why = integrity(dest, total)
                print(f"       {why}")
                if ok:
                    return dest
                park(dest, why)
        wait = 5 * attempt
        print(f"       backing off {wait}s, then resuming from "
              f"{part.stat().st_size if part.exists() else 0:,} bytes")
        time.sleep(wait)
    print(f"  GAVE UP on {name}. The .part file is kept; re-run to resume.")
    return None


def inventory_pdf(path: Path) -> dict:
    """Page count and whether a real text layer is present. No table parsing."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return {"bytes": path.stat().st_size, "note": "pypdf not installed"}
    r = PdfReader(str(path))
    n = len(r.pages)
    probe = [0, n // 3, n // 2, (2 * n) // 3, n - 1]
    chars = []
    for i in sorted(set(max(0, min(n - 1, j)) for j in probe)):
        try:
            chars.append((i, len((r.pages[i].extract_text() or ""))))
        except Exception as e:
            chars.append((i, f"<{type(e).__name__}>"))
    return {
        "bytes": path.stat().st_size,
        "pages": n,
        "text_layer_chars_by_page": chars,
        "has_text_layer": any(isinstance(c, int) and c > 200 for _, c in chars),
    }


def inventory(path: Path) -> dict:
    if path.suffix.lower() == ".pdf":
        return inventory_pdf(path)
    text = path.read_text(encoding="utf-8", errors="ignore")
    years = sorted({int(y) for y in re.findall(r"\b(19[5-9]\d|20[0-1]\d)\b", text)})
    goods = ["rice", "wheat", "maize", "corn", "soybean", "cotton", "sugar",
             "pork", "poultry", "egg", "milk", "fruit", "vegetable", "tobacco",
             "groundnut", "rapeseed", "tea", "beef", "sheep", "fish"]
    hits = {g: len(re.findall(rf"\b{g}s?\b", text, re.I)) for g in goods}
    return {
        "bytes": len(text.encode("utf-8")),
        "lines": text.count("\n") + 1,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
        "year_min": years[0] if years else None,
        "year_max": years[-1] if years else None,
        "n_distinct_years": len(years),
        "commodity_mentions": {k: v for k, v in
                               sorted(hits.items(), key=lambda kv: -kv[1]) if v},
    }


def main() -> None:
    print(f"target dir: {RAW}")
    out = {}
    for name, urls in TARGETS.items():
        p = fetch(name, urls)
        if p is not None:
            out[name] = inventory(p)
    if not out:
        sys.exit("nothing complete yet; re-run to resume")
    man = RAW / "dai_manifest.json"
    man.write_text(json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True),
                   encoding="utf-8", newline="\n")
    print("\n--- inventory ---")
    print(json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True))
    print(f"\nmanifest written: {man}")


if __name__ == "__main__":
    main()
