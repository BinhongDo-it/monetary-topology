"""B37: the argentinadatos ``blue`` series, fetched without touching B5's table.

Why a separate fetcher. ``ARGENTINADATOS_CASAS`` in ``parallel_rates`` is B5's,
and its docstring is load-bearing: it says which series are agent classes and
which are not. Adding a row there would change what B5 retrieves, which rule
nineteen forbids as a side effect of another stage's work. So B37 pulls its own
series, under its own file name, with its own manifest, and shares only the
parser. The parser is shared on purpose: B5's section 3.1 keeps the two source
formats under two different names because mixing them is the one error the
calibration arm cannot survive, and reimplementing one of them here would put a
third copy of that convention in the repository.

What it is for. B37 asks how many roots a number has, by measuring how far two
independent publishers of the same number disagree. ``oficial`` and
``mayorista`` have one legal reference behind them and are already on disk from
both publishers; they give the instrument's floor. ``blue`` has no publisher of
record at all, so the two houses each sample an informal market on their own.
The gap between those two disagreements is the reading.

Run:
    python fetch_b37_blue.py
    python fetch_b37_blue.py --check
"""

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from monetary_topology.parallel_rates import (
    WINDOW_END,
    WINDOW_START,
    parse_argentinadatos_rows,
)

CASA = "blue"
BASE = "https://api.argentinadatos.com/v1/cotizaciones/dolares/{casa}"
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
NAME = "argentinadatos_%s.json" % CASA
MANIFEST = RAW / "b37_blue_manifest.json"
TIMEOUT = 180
RETRIES = 3
BACKOFF = 2.0


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def download(url: str) -> bytes:
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "monetary-topology research script"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code < 500:
                raise
            last = "HTTP %s" % e.code
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            last = str(getattr(e, "reason", e))
        wait = BACKOFF * (2 ** attempt)
        print("  %s, waiting %.0fs (try %d of %d)" % (last, wait, attempt + 1,
                                                      RETRIES))
        time.sleep(wait)
    raise SystemExit("gave up after %d tries. Last: %s" % (RETRIES, last))


def write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(path)


def summarise(rows: list) -> dict:
    """The parser normalises the date key to ``date``.

    The first version of this read ``fecha``, which is what the API sends and
    what the parser's docstring quotes as its **input**. The parser returns
    ``date``. Nothing raised: the summary simply came back with nulls and a
    window count of zero while the file on disk was correct. A docstring says
    what a function eats, not what it hands back; the return statement says
    that.
    """
    dates = sorted(r["date"] for r in rows if r.get("date"))
    if not dates:
        raise SystemExit("no row carries a date key. Fields on the first row: "
                         "%s" % (sorted(rows[0]) if rows else "no rows"))
    inside = [d for d in dates
              if WINDOW_START.isoformat() <= d <= WINDOW_END.isoformat()]
    return {
        "casa": CASA,
        "rows": len(rows),
        "first": dates[0],
        "last": dates[-1],
        "rows_in_registered_window": len(inside),
        "window_first": inside[0] if inside else None,
        "window_last": inside[-1] if inside else None,
        "window": [WINDOW_START.isoformat(), WINDOW_END.isoformat()],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report what is on disk and fetch nothing")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / NAME

    if out.exists() and not a.force:
        raw = out.read_bytes()
        try:
            rows = parse_argentinadatos_rows(json.loads(raw.decode("utf-8")), CASA)
        except Exception as e:
            print("on disk but it does not parse: %s (%s)" % (out.name, e))
            if a.check:
                return 1
            rows = None
        if rows is not None:
            summary = summarise(rows)
            summary["sha256"] = sha256(raw)
            print("already on disk: %s" % out.name)
            print("  %s" % json.dumps(summary, ensure_ascii=False))
            # The manifest describes what is on disk, so it is rewritten even
            # when nothing was fetched. Otherwise a manifest written by a buggy
            # summary outlives the fix.
            MANIFEST.write_text(json.dumps(summary, ensure_ascii=False, indent=1),
                                encoding="utf-8")
            print("manifest refreshed: %s" % MANIFEST)
            return 0
    if a.check:
        print("not on disk: %s" % out.name)
        return 1

    url = BASE.format(casa=CASA)
    print("fetching %s" % url)
    raw = download(url)
    rows = parse_argentinadatos_rows(json.loads(raw.decode("utf-8")), CASA)
    if not rows:
        raise SystemExit("the endpoint answered and the parser found no rows. "
                         "Nothing written.")
    write_atomic(out, raw)
    s = summarise(rows)
    s["sha256"] = sha256(raw)
    s["retrieved_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    MANIFEST.write_text(json.dumps(s, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print("written: %s" % out)
    print("manifest: %s" % MANIFEST)
    print("  %s" % json.dumps(s, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
