"""Probe one Appendix subdirectory on the NYSE tick-pilot server.

The root index lists six venues times four appendix sections as DIRECTORIES:
NYSE_BI / _BII / _BIII / _BIV, and the same for Arca, CHI, MKT, NATL, NSX. So
B.II (marketable order data), B.III (market maker registration) and B.IV (market
maker participation) all exist and are free. B14 used only B.I.

The one question that decides L2's exposure variable is whether B.III or B.IV
identifies individual market makers (an MPID) or only counts them. Spillover
travels through the market maker, so an MPID-level file makes the exposure a
direct measurement rather than a proxy; a count-only file makes it useless for
that purpose.

The earlier run hit HTTP 503 on every subdirectory, which is rate limiting rather
than absence: the same server served the root index in the same run. So requests
here are spaced, and one directory is asked for at a time.

Downloads at most one data file, and only the head of it.

Usage
    python experiments/b14_appendix_probe.py --selftest
    python experiments/b14_appendix_probe.py --list NYSE_BIV
    python experiments/b14_appendix_probe.py --head NYSE_BIV <filename>
"""
import argparse
import ast
import gzip
import io
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
RAW = os.path.join(ROOT, "data", "raw", "b14_appendix_probe")
BASE = "https://ftp.nyxdata.com/Tick_Pilot/"
UA = "Mozilla/5.0 (compatible; research/1.0)"
#: Copied verbatim from b14_fetch_2018, which settled this on 2026-08-19: the host
#: redirects to https and then presents a certificate that is not valid for its own
#: name, so hostname checking is disabled FOR THIS HOST ONLY, never globally, and
#: only for a host whose mismatch is a registered property of the carrier rather
#: than something discovered at fetch time. Forgetting to carry it over is what
#: produced CERTIFICATE_VERIFY_FAILED on the first run of this file.
INSECURE_HOSTS = ("ftp.nyxdata.com",)
_LAX = ssl.create_default_context()
_LAX.check_hostname = False
_LAX.verify_mode = ssl.CERT_NONE


def ctx_for(url):
    """The lax context for the registered host, the default one for everything else."""
    host = urllib.parse.urlparse(url).hostname or ""
    return _LAX if host in INSECURE_HOSTS else None
#: The earlier run fired every subdirectory back to back and got 503 on all of
#: them while the root index succeeded, so the pause is the fix, not a retry loop.
PAUSE_SECONDS = 6.0
RETRIES = 3
#: Only the head of one file is ever read.
HEAD_BYTES = 1 << 18


def get(url, want_bytes=None):
    for attempt in range(RETRIES):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        if want_bytes:
            req.add_header("Range", "bytes=0-%d" % (want_bytes - 1))
        try:
            with urllib.request.urlopen(req, timeout=120, context=ctx_for(url)) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            body = e.read()
            if e.code in (503, 429) and attempt + 1 < RETRIES:
                wait = PAUSE_SECONDS * (attempt + 2)
                print("    HTTP %d, waiting %.0fs and retrying" % (e.code, wait))
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
        if n and not n.startswith("?") and n != "..":
            out.append(n)
    return out


def list_dir(name):
    url = BASE + name + "/"
    print("listing %s" % url)
    st, body = get(url)
    print("  status %s, %d bytes" % (st, len(body)))
    if st != 200:
        print("  %r" % body[:300])
        return 1
    names = links(body.decode("utf-8", "replace"))
    print("  %d entries" % len(names))
    for n in names[:25]:
        print("    %s" % n)
    if len(names) > 25:
        print("    ... and %d more" % (len(names) - 25))
    os.makedirs(RAW, exist_ok=True)
    p = os.path.join(RAW, "%s_index.html" % name)
    with open(p, "wb") as fh:
        fh.write(body)
    print("  raw index kept at %s" % os.path.relpath(p, ROOT))
    print("\n  next: --head %s <one of the filenames above>" % name)
    return 0


def head_file(name, fname):
    url = BASE + name + "/" + fname
    print("head of %s" % url)
    st, body = get(url, want_bytes=HEAD_BYTES)
    print("  status %s, %d bytes read" % (st, len(body)))
    if st not in (200, 206):
        print("  %r" % body[:300])
        return 1
    if fname.endswith(".gzip") or fname.endswith(".gz"):
        try:
            body = gzip.GzipFile(fileobj=io.BytesIO(body)).read(HEAD_BYTES)
        except (OSError, EOFError) as e:
            print("  partial gzip, decompressed what was available (%s)" % e)
            d = gzip.decompressobj(16 + 15)
            try:
                body = d.decompress(body)
            except Exception:
                pass
    text = body.decode("utf-8", "replace")
    lines = text.splitlines()
    print("\n  first 6 lines:")
    for line in lines[:6]:
        print("    %s" % line[:400])
    for line in lines[:4]:
        if line.startswith("F|"):
            fields = line.rstrip().split("|")
            print("\n  field line: %d fields" % (len(fields) - 1))
            for i, f in enumerate(fields):
                print("    %3d %s" % (i, f))
            hits = [f for f in fields
                    if re.search(r"MPID|Market_?Maker|MM_?ID|Firm|Participant|Member",
                                 f, re.I)]
            print("\n  identifier-looking fields: %s" % (hits or "NONE"))
            print("  -> %s" % ("this file names market makers, so the exposure can be "
                               "measured on the mechanism"
                               if any(re.search(r"MPID|MM_?ID|Firm|Member", f, re.I)
                                      for f in fields)
                               else "counts only as far as the field line shows; "
                                    "the exposure would have to be a proxy"))
            break
    os.makedirs(RAW, exist_ok=True)
    p = os.path.join(RAW, fname + ".head.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("\n  head kept at %s" % os.path.relpath(p, ROOT))
    return 0


def selftest():
    ok = True

    def chk(n, c):
        nonlocal ok
        print(("  PASS  " if c else "  FAIL  ") + n)
        ok = ok and c

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    chk("the base is the server that served the root index in the same run",
        BASE.startswith("https://ftp.nyxdata.com/"))
    chk("requests are spaced, because the earlier failure was 503 rate limiting "
        "and not absence", PAUSE_SECONDS >= 5 and RETRIES >= 2)
    chk("at most a head is read, not a whole file", HEAD_BYTES <= (1 << 20))
    chk("the lax TLS context applies to the registered host",
        ctx_for("https://ftp.nyxdata.com/Tick_Pilot/") is _LAX)
    chk("and to nothing else: finra.org gets the default verifying context",
        ctx_for("https://www.finra.org/x") is None)
    chk("the lax context really does skip hostname checking, which is the failure "
        "this host actually shows",
        _LAX.check_hostname is False and _LAX.verify_mode == ssl.CERT_NONE)
    chk("the request path uses it, not just defines it",
        "context=ctx_for(url)" in src)
    chk("the link parser drops the parent entry",
        links('<a href="../">..</a><a href="x.gzip">x</a>') == ["x.gzip"])
    chk("it keeps a real filename", "NYSE_BIV_A.gzip" in
        links('<a href="/Tick_Pilot/NYSE_BIV/NYSE_BIV_A.gzip">f</a>'))
    tree = ast.parse(src)
    banned = {("os", "remove"), ("os", "unlink"), ("shutil", "rmtree")}
    chk("no deletion call anywhere",
        not [1 for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
             and (n.func.value.id, n.func.attr) in banned])
    chk("no CJK in this file",
        not re.search("[\\u4e00-\\u9fff\\u3000-\\u303f\\uff00-\\uffef]", src))
    print("\n  " + ("all passed" if ok else "some failed"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--list", metavar="DIR")
    ap.add_argument("--head", nargs=2, metavar=("DIR", "FILE"))
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.list:
        return list_dir(a.list)
    if a.head:
        return head_file(a.head[0], a.head[1])
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
