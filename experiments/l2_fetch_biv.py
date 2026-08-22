"""L2: fetch Appendix B.IV, market maker participation statistics.

Registered before the code, gate one. B.IV
measures market-maker BEHAVIOUR per (trading centre, day, symbol), which is the
one thing candidate zero does not predict: projecting quotes onto the nickel
lattice is arithmetic on the quote and needs nobody to change their mind.

Measured 2026-08-20 on the head of one file: 33 fields, no MPID, no firm and no
member identifier. So B.IV cannot serve as an exposure variable (market-maker
overlap is not computable from it) and this station does not try to use it as one.

Windows needed, all of them A11's own and unchanged:
    split      2016-04, 2016-05
    placebo    2016-06, 2016-07  ->  2016-08, 2016-09
    real       2016-08, 2016-09  ->  2016-11, 2016-12
2016-10 is fetched too: the pilot took effect on 2016-10-03, so that month is the
transition and is wanted for description even though no window uses it.

D12, enumerate before selecting: filenames come from each directory's own index,
never from a pattern guessed here. The Arca prefix is not assumed.

The host redirects to https and then presents a certificate that is not valid for
its own name. Hostname checking is disabled FOR THAT HOST ONLY, carried over from
b14_fetch_2018 where it was settled on 2026-08-19. The first run of the sibling
probe forgot to carry it and died on CERTIFICATE_VERIFY_FAILED, so the selftest
here asserts the exemption is wired into the request path and not merely defined.

Nothing is deleted. A file already on disk is skipped, and a stale .part is
renamed with an .expired suffix.

Usage
    python experiments/l2_fetch_biv.py --selftest
    python experiments/l2_fetch_biv.py --index
    python experiments/l2_fetch_biv.py --fetch
    python experiments/l2_fetch_biv.py --verify
"""
import argparse
import ast
import gzip
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw", "b14_biv")
BASE = "https://ftp.nyxdata.com/Tick_Pilot/"
#: One directory per venue, from the root index measured 2026-08-20.
DIRS = ("NYSE_BIV", "NYSE_Arca_BIV")
#: A11's windows, unchanged, plus the transition month.
MONTHS = ["2016%02d" % m for m in range(4, 13)]
UA = "Mozilla/5.0 (compatible; research/1.0)"
PAUSE_SECONDS = 6.0
RETRIES = 3

#: Carried over verbatim from b14_fetch_2018. For this host only, never globally,
#: and only because the mismatch is a registered property of the carrier.
INSECURE_HOSTS = ("ftp.nyxdata.com",)
_LAX = ssl.create_default_context()
_LAX.check_hostname = False
_LAX.verify_mode = ssl.CERT_NONE


def ctx_for(url):
    host = urllib.parse.urlparse(url).hostname or ""
    return _LAX if host in INSECURE_HOSTS else None


def get(url):
    for attempt in range(RETRIES):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=300, context=ctx_for(url)) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            body = e.read()
            if e.code in (503, 429) and attempt + 1 < RETRIES:
                wait = PAUSE_SECONDS * (attempt + 2)
                print("      HTTP %d, waiting %.0fs" % (e.code, wait))
                time.sleep(wait)
                continue
            return e.code, body
        except (urllib.error.URLError, OSError) as e:
            return None, str(e).encode()
    return None, b""


def links(html):
    out = []
    for href in re.findall(r'href="([^"]+)"', html):
        n = href.rstrip("/").split("/")[-1]
        if n and not n.startswith("?") and n != ".." and n.endswith(".gzip"):
            out.append(n)
    return out


def index_dir(d):
    st, body = get(BASE + d + "/")
    if st != 200:
        print("  %-16s status %s  %r" % (d, st, body[:160]))
        return []
    names = links(body.decode("utf-8", "replace"))
    print("  %-16s %d gzip entries" % (d, len(names)))
    return names


def wanted(names):
    """D12: pick from what the directory actually lists, by month, not by pattern."""
    out = {}
    for m in MONTHS:
        hits = [n for n in names if m in n]
        if len(hits) == 1:
            out[m] = hits[0]
        elif len(hits) > 1:
            out[m] = None
            print("      %s: %d candidates, none taken: %s" % (m, len(hits), " ".join(hits)))
    return out


def do_index():
    print("index of the two B.IV directories\n")
    for d in DIRS:
        names = index_dir(d)
        w = wanted(names)
        for m in MONTHS:
            print("      %s  %s" % (m, w.get(m) or "ABSENT"))
        time.sleep(PAUSE_SECONDS)
    return 0


def stamp():
    return time.strftime("%Y%m%d_%H%M%S")


def do_fetch():
    os.makedirs(RAW, exist_ok=True)
    got = skipped = missing = 0
    for d in DIRS:
        print("\n=== %s ===" % d)
        w = wanted(index_dir(d))
        time.sleep(PAUSE_SECONDS)
        for m in MONTHS:
            fn = w.get(m)
            if not fn:
                print("  %s  ABSENT from the directory index, not guessed at" % m)
                missing += 1
                continue
            dst = os.path.join(RAW, fn)
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                print("  %s  %-46s on disk, %.1f MB" % (m, fn, os.path.getsize(dst) / 1e6))
                skipped += 1
                continue
            st, body = get(BASE + d + "/" + fn)
            if st != 200 or not body:
                print("  %s  %-46s FAILED status %s" % (m, fn, st))
                missing += 1
                time.sleep(PAUSE_SECONDS)
                continue
            tmp = dst + ".part"
            if os.path.exists(tmp):
                os.rename(tmp, tmp + ".expired_" + stamp())
            with open(tmp, "wb") as fh:
                fh.write(body)
            os.rename(tmp, dst)
            print("  %s  %-46s %.1f MB" % (m, fn, len(body) / 1e6))
            got += 1
            time.sleep(PAUSE_SECONDS)
    print("\n  fetched %d, already on disk %d, absent or failed %d" % (got, skipped, missing))
    return do_verify()


def do_verify():
    """No network. Decompress each file and read its header and field line."""
    if not os.path.isdir(RAW):
        print("  nothing on disk at %s" % os.path.relpath(RAW, ROOT))
        return 2
    files = sorted(f for f in os.listdir(RAW) if f.endswith(".gzip"))
    if not files:
        print("  no gzip on disk")
        return 2
    print("\nverify, no network, %d files" % len(files))
    bad = 0
    for f in files:
        p = os.path.join(RAW, f)
        try:
            with gzip.open(p, "rt", encoding="utf-8", errors="replace") as fh:
                head = fh.readline().rstrip("\n")
                field = fh.readline().rstrip("\n")
                n = 2
                for _ in fh:
                    n += 1
        except (OSError, EOFError) as e:
            print("  %-46s UNREADABLE %s" % (f, e))
            bad += 1
            continue
        nf = len(field.split("|")) - 1 if field.startswith("F|") else -1
        ok = head.startswith("H|") and nf == 33
        print("  %-46s %9d rows  %2d fields  %s  %s"
              % (f, n, nf, head[:24], "ok" if ok else "**SHAPE**"))
        if not ok:
            bad += 1
    print("\n  %d readable, %d with a wrong shape" % (len(files) - bad, bad))
    print("  33 fields is what the 2026-08-20 head measured; a different count is a")
    print("  format change and must be looked at before any reading is taken.")
    return 0 if not bad else 1


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    chk("the months are A11's own windows plus the transition month",
        MONTHS[0] == "201604" and MONTHS[-1] == "201612" and len(MONTHS) == 9)
    chk("both venues' B.IV directories are listed", DIRS == ("NYSE_BIV", "NYSE_Arca_BIV"))
    chk("the lax TLS context applies to the registered host only",
        ctx_for(BASE) is _LAX and ctx_for("https://www.finra.org/x") is None)
    chk("and it is wired into the request path, not merely defined",
        "context=ctx_for(url)" in src)
    chk("the lax context skips hostname checking, which is this host's actual failure",
        _LAX.check_hostname is False and _LAX.verify_mode == ssl.CERT_NONE)
    chk("requests are spaced, because the failure mode on this host is 503 rate "
        "limiting", PAUSE_SECONDS >= 5 and RETRIES >= 2)
    chk("filenames come from the directory index: the link parser keeps gzips and "
        "drops the parent",
        links('<a href="../">..</a><a href="X_201604.gzip">x</a>') == ["X_201604.gzip"])
    w = wanted(["A_201604.gzip", "A_201605.gzip", "B_201604.gzip"])
    chk("a month with two candidates takes neither and says so: " + repr(w.get("201604")),
        w.get("201604") is None and w.get("201605") == "A_201605.gzip")
    chk("a month absent from the index is absent, not guessed", "201612" not in w)
    tree = ast.parse(src)
    banned = {("os", "remove"), ("os", "unlink"), ("os", "rmdir"), ("shutil", "rmtree")}
    hits = [getattr(n, "lineno", "?") for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name)
            and (n.func.value.id, n.func.attr) in banned]
    chk("no deletion call anywhere: " +
        (("lines " + ", ".join(map(str, hits))) if hits else "zero"), not hits)
    chk("no statistic is computed here; this file only fetches and checks shape",
        not ({n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
             & {"deltas", "six", "median", "tabulate"}))
    chk("no CJK in this file",
        not re.search("[\\u4e00-\\u9fff\\u3000-\\u303f\\uff00-\\uffef]", src))
    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--index", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.verify:
        return do_verify()
    if a.index:
        return do_index()
    if a.fetch:
        return do_fetch()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
