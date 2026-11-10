"""B138 block two: fetch every split-share reform implementation notice listed on cninfo.

The listing comes from `b138_probe.listing` (answer pages cached under `data/raw/b138/cninfo/`).
Every row of the implementation-notice listing is fetched, the main notices and the corrections,
progress notes and additional-consideration notices alike; the reader decides which to use.

Resumable: a PDF already on disk that opens and ends with ``%%EOF`` is kept. One that does not is
renamed with an ``.expired`` suffix and fetched again. Nothing is deleted. The text of each PDF is
written beside it under `data/raw/b138/pdf_text/`. `data/raw/b138/fetch_manifest.json` lists every
row with its size, SHA-256, page count and status, rewritten at the end of each run and every 100 files.

    python experiments/b138_fetch.py            # everything still missing
    python experiments/b138_fetch.py --limit 20
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import os
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import b138_probe as P  # noqa: E402

MANIFEST = P.RAW / "fetch_manifest.json"


def pdf_ok(b: bytes) -> bool:
    return b.startswith(b"%PDF") and b"%%EOF" in b[-2048:]


def text_of(path: Path) -> tuple[str, int]:
    import pymupdf
    with pymupdf.open(path) as doc:
        return "\n".join(page.get_text() for page in doc), doc.page_count


def is_html(r: dict) -> bool:
    return str(r["adjunctUrl"]).lower().endswith((".html", ".htm"))


def html_ok(b: bytes) -> bool:
    return b"</html>" in b[-512:].lower()


def html_text(b: bytes) -> str:
    """The 2005 pilot notices are GBK HTML pages; tags and entities are dropped, line breaks kept."""
    m = re.search(rb"charset=[\"']?([A-Za-z0-9_-]+)", b[:2048])
    enc = m.group(1).decode() if m else "gbk"
    s = b.decode("gb18030" if enc.lower() in ("gbk", "gb2312") else enc, errors="replace")
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</tr>", "\n", s)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def one(r: dict) -> dict:
    aid = str(r["announcementId"])
    kind = "html" if is_html(r) else "pdf"
    ok = html_ok if kind == "html" else pdf_ok
    path = P.RAW / kind / f"{aid}.{kind}"
    status = "cached"
    if path.exists() and not ok(path.read_bytes()):
        os.replace(path, path.with_name(f"{path.name}.bad_{P._stamp()}.expired"))
    if not path.exists():
        req = urllib.request.Request(P.STATIC + r["adjunctUrl"], headers=P.PDF_HEADERS)
        body = P.fetch(kind, req, aid)
        if not ok(body):
            bad = path.with_name(f"{path.name}.truncated_{P._stamp()}.expired")
            P.atomic_write_bytes(bad, body)
            return {"id": aid, "status": "truncated", "bytes": len(body), "kind": kind}
        P.atomic_write_bytes(path, body)
        status = "fetched"
    b = path.read_bytes()
    tpath = P.RAW / "pdf_text" / f"{aid}.txt"
    try:
        text, pages = (html_text(b), 1) if kind == "html" else text_of(path)
    except Exception as exc:  # a file that will not open is named, not skipped silently
        return {"id": aid, "status": f"unreadable: {exc!r}"[:200], "bytes": len(b), "kind": kind}
    if not tpath.exists() or tpath.stat().st_size != len(text.encode("utf-8")):
        P.atomic_write_bytes(tpath, text.encode("utf-8"))
    return {"id": aid, "status": status, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
            "pages": pages, "chars": len(text), "kind": kind}


def write_manifest(rows: list[dict], done: dict) -> None:
    out = []
    for r in rows:
        aid = str(r["announcementId"])
        m = {"id": aid, "code": str(r["secCode"]), "name": P.clean_title(r.get("secName")),
             "title": P.clean_title(r.get("announcementTitle")), "day": P.day_of(r["announcementTime"]),
             "url": r["adjunctUrl"]}
        m.update({k: v for k, v in done.get(aid, {"status": "missing"}).items() if k != "id"})
        out.append(m)
    P.atomic_write_bytes(MANIFEST, json.dumps(out, ensure_ascii=False, indent=0, sort_keys=True).encode("utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    rows = P.listing(P.KEYWORDS[0])
    rows.sort(key=lambda r: (r["announcementTime"], str(r["announcementId"])))
    todo = rows[: a.limit] if a.limit else rows
    print(f"{len(rows)} rows in the listing, {len(todo)} this run", flush=True)
    done: dict = {}
    t0 = time.monotonic()
    for i, r in enumerate(todo, 1):
        try:
            done[str(r["announcementId"])] = one(r)
        except Exception as exc:  # refused after retries: named in the manifest, the run goes on
            done[str(r["announcementId"])] = {"id": str(r["announcementId"]), "status": f"failed: {exc!r}"[:200]}
        if i % 50 == 0 or i == len(todo):
            st = {}
            for v in done.values():
                k = v["status"].split(":")[0]
                st[k] = st.get(k, 0) + 1
            print(f"  {i}/{len(todo)}  {time.monotonic() - t0:.0f} s  {st}", flush=True)
        if i % 100 == 0:
            write_manifest(rows, done)
    write_manifest(rows, done)
    bad = [v for v in done.values() if v["status"] not in ("cached", "fetched")]
    print(f"done in {time.monotonic() - t0:.0f} s; {len(bad)} not read: "
          + "; ".join(f"{v['id']} {v['status']}" for v in bad[:10]), flush=True)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
